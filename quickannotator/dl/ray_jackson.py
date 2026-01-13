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

@ray.remote(max_concurrency=3)
class DLActor:
    def __init__(self, annotation_class_id: int, tile_size: int, magnification: float):
        self.logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)
        self.logger.info(f"Initializing DLActor with {annotation_class_id=}, {tile_size=}, {magnification=}")
        self.annotation_class_id = annotation_class_id
        self.tile_size = tile_size
        self.proc_running_since = None
        self.allow_pred = True  # --- don't know if we'll ever need this, so hard setting to true
        self.enable_training = True
        self.magnification = magnification

    def start_dlproc(self):
        if self.get_proc_running_since() is not None:
            self.logger.warning("Already running, not starting again")
            return

        self.logger.info(f"Starting up {build_actor_name(annotation_class_id=self.annotation_class_id)}")
        self.set_proc_running_since()

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
        result = trainer.fit()
        self.logger.info(f"Training result: {result}")


    def get_class_id(self):
        return self.annotation_class_id

    def get_actor_name(self):
        return build_actor_name(annotation_class_id=self.annotation_class_id)

    def get_tile_size(self):
        return self.tile_size

    def get_proc_running_since(self):
        return self.proc_running_since

    def set_proc_running_since(self, reset=False):
        if reset:
            self.proc_running_since = None
            self.logger.info("Resetting procRunningSince to None")
        else:
            self.proc_running_since = datetime.now()
            self.logger.info(f"Setting procRunningSince to {self.proc_running_since}")

    def get_allow_pred(self):
        return self.allow_pred

    def set_allow_pred(self, allow_pred: bool):
        self.allow_pred = allow_pred
        return self.allow_pred

    def get_enable_training(self):
        return self.enable_training

    def set_enable_training(self, enable_training: bool):
        self.enable_training = enable_training
        return self.enable_training
    
    def get_detailed_state(self) -> dict:
        state = {
            'annotation_class_id': self.annotation_class_id,
            'proc_running_since': self.proc_running_since,
            'allow_pred': self.allow_pred,
            'enable_training': self.enable_training,
        }
        return state

def start_processing(annotation_class_id: int):
    # Step 1: Build the actor name and retrieve the corresponding DLActor instance
    actor_name = build_actor_name(annotation_class_id=annotation_class_id)
    annotation_class = get_annotation_class_by_id(annotation_class_id)
    current_actor = DLActor.options(name=actor_name, get_if_exists=True).remote(annotation_class_id,
                                                                               annotation_class.work_tilesize,
                                                                               annotation_class.work_mag)
    logger.info("Got ray actor for annotation class ID: %s", annotation_class_id)

    # Step 2: Retrieve the list of currently processing actors
    actor_queue = get_processing_actors(sort_by_date=True)
    logger.info(f"Current processing actors: {len(actor_queue)}")

    # Step 3: Ensure the number of active actors does not exceed the maximum allowed
    while len(actor_queue) >= constants.MAX_ACTORS_PROCESSING:
        oldest_actor = actor_queue.pop(0)['actor']

        if oldest_actor != current_actor:   # Can do a direct comparison since ray returns the exact same actor object.
            logger.info(f"Stopping actor {oldest_actor} to make room for new processing.")
            oldest_actor.set_proc_running_since.remote(reset=True)

    # Step 4: Start the processing task on the current actor
    current_actor.start_dlproc.remote()
    logger.info(f"Instructed actor {actor_name} to start processing.")
    return current_actor


def get_processing_actors(sort_by_date=True):
    actor_names = ray.util.list_named_actors()
    dated_actors = []
    for name in actor_names:
        actor = ray.get_actor(name)
        date = ray.get(actor.get_proc_running_since.remote())
        if date:  # actors with date == None are not processing
            dated_actors.append({'date': date, 'actor': actor, 'name': name})

    if sort_by_date:
        return dated_actors
    else:
        return sorted(dated_actors, key=lambda x: x['date'])

