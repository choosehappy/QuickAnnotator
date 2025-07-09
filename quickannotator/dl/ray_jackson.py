import logging
from quickannotator.db.logging import LoggingManager
import ray
from ray.train import ScalingConfig
import torch
from torch.nn import CrossEntropyLoss
from torch.optim import Adam
from torch.utils.data import DataLoader
import ray.train.torch
import ray.util.state
import ray
import torch
import torch.nn as nn
import ray.train.torch
import ray.train
from torch.nn import CrossEntropyLoss, MSELoss
from torch.optim import Adam

from quickannotator.db.crud.annotation_class import get_annotation_class_by_id, build_actor_name
from quickannotator.db.crud.tile import TileStoreFactory
import quickannotator.constants as constants
from quickannotator.db import get_session
from quickannotator.db.models import Tile
import sqlalchemy
from quickannotator.dl.training import train_pred_loop
from datetime import datetime

logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)

@ray.remote(max_concurrency=2)
class DLActor:
    def __init__(self, annotation_class_id: int, tile_size: int, magnification: float):
        self.logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)
        self.logger.info(f"Initializing DLActor with {annotation_class_id=}, {tile_size=}, {magnification=}")
        self.annotation_class_id = annotation_class_id
        self.tile_size = tile_size
        self.procRunningSince = None
        self.allow_pred = True  # --- don't know if we'll ever need this, so hard setting to true
        self.enable_training = True
        self.hexid = None
        self.magnification = magnification

    def start_dlproc(self, allow_pred=True):
        if self.getProcRunningSince() is not None:
            self.logger.warning("Already running, not starting again")
            return

        self.logger.info(f"Starting up {build_actor_name(annotation_class_id=self.annotation_class_id)}")
        self.setProcRunningSince()

        total_gpus = ray.cluster_resources().get("GPU", 0)
        self.logger.info(f"Total GPUs available: {total_gpus}")
        scaling_config = ray.train.ScalingConfig(
            num_workers=int(total_gpus),
            use_gpu=True,
            resources_per_worker={"GPU": .01},
            placement_strategy="STRICT_SPREAD"
        )
    
        trainer = ray.train.torch.TorchTrainer(
            train_pred_loop,
            scaling_config=scaling_config,
            train_loop_config={
                'annotation_class_id': self.annotation_class_id,
                'tile_size': self.tile_size,
                'magnification': self.magnification
            }
        )
        self.hexid = trainer.fit().hex()
        self.logger.info(f"DLActor started with hexid: {self.hexid}")
        return self.hexid

    # TODO: Remove.
    # def infer(self, image_id: int, tileids: list[int]):
    #     if not self.allow_pred:
    #         self.logger.warning("Not doing inference --- actor was started with prediction disabled")
    #         return False

    #     with get_session() as db_session:
    #         tilestore = TileStoreFactory.get_tilestore()
    #         tilestore.upsert_pred_tiles(
    #             image_id=image_id,
    #             annotation_class_id=self.annotation_class_id,
    #             tile_ids=tileids,
    #             pred_status=constants.TileStatus.PROCESSING,
    #             process_owns_tile=True
    #         )

    #     return True

    # TODO: Remove.
    # def getTileStatus(self, image_id, tile_ids):  # probably belongs elsewhere but need this for debug
    #     with get_session() as db_session:
    #         stmt = db_session.query(Tile).filter(Tile.tile_id.in_(tile_ids), Tile.image_id == image_id,
    #                                              Tile.annotation_class_id == self.annotation_class_id)

    #         result = stmt.all()

    #     return result

    def getClassId(self):
        return self.annotation_class_id

    def getHexId(self):
        return self.hexid

    def setHexId(self, hexid: str):  # not sure if set is smart to have -- should likely be done internally
        self.hexid = hexid
        return self.hexid

    def getActorName(self):
        return build_actor_name(annotation_class_id=self.annotation_class_id)

    def getTileSize(self):
        return self.tile_size

    def getProcRunningSince(self):
        self.logger.info(f"procRunningSince: {self.procRunningSince}")
        return self.procRunningSince

    def setProcRunningSince(self, reset=False):
        if reset:
            self.procRunningSince = None
            self.logger.info("Resetting procRunningSince to None")
        else:
            self.procRunningSince = datetime.now()
            self.logger.info(f"Setting procRunningSince to {self.procRunningSince}")

    def getAllowPred(self):
        return self.allow_pred

    def setAllowPred(self, allow_pred: bool):
        self.allow_pred = allow_pred
        return self.allow_pred

    def getEnableTraining(self):
        return self.enable_training

    def setEnableTraining(self, enable_training: bool):
        self.enable_training = enable_training
        return self.enable_training


def start_processing(annotation_class_id: int):
    # 1. Get named actor 
    actor_name = build_actor_name(annotation_class_id=annotation_class_id)
    annotation_class = get_annotation_class_by_id(annotation_class_id)
    current_actor = DLActor.options(name=actor_name, get_if_exists=True).remote(annotation_class_id,
                                                                               annotation_class.work_tilesize,
                                                                               annotation_class.work_mag)
    logger.info("Got ray actor for annotation class ID: %s", annotation_class_id)

    actor_queue = get_processing_actors(sort_by_date=True)
    logger.info(f"Current processing actors: {len(actor_queue)}")

    while len(actor_queue) >= constants.MAX_ACTORS_PROCESSING:
        # 3. Pop the oldest actor
        oldest_actor = actor_queue.pop(0)['actor']

        # 4. If the oldest actor is not the current one, flag it to cease processing
        if oldest_actor != current_actor:   # Can do a direct comparison since ray returns the exact same actor object.
            logger.info(f"Stopping actor {oldest_actor} to make room for new processing.")
            oldest_actor.setProcRunningSince.remote(reset=True)



    # 3. Set all tiles with pred_status=TileStatus.PROCESSING to TileStatus.UNSEEN


    # 4. Start the new actor or get the existing one
    current_actor.start_dlproc.remote()
    logger.info(f"Instructed actor {actor_name} to start processing.")
    return current_actor


def get_processing_actors(sort_by_date=True):
    actor_names = ray.util.list_named_actors()
    dated_actors = []
    for name in actor_names:
        actor = ray.get_actor(name)
        date = ray.get(actor.getProcRunningSince.remote())
        if date:  # actors with date == None are not processing
            dated_actors.append({'date': date, 'actor': actor, 'name': name})

    if sort_by_date:
        return dated_actors
    else:
        return sorted(dated_actors, key=lambda x: x['date'])
