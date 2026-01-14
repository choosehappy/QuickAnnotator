import logging
import time
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
from ray.runtime_context import RuntimeContext
from ray.actor import ActorHandle


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
        breakpoint()
        if self.get_proc_running_since() is not None:
            self.logger.warning(f"{self.get_actor_name()} already running, not starting again")
            return
        
        # Set the processing start time so that other actors can compare.
        self.set_proc_running_since()

        # This function blocks start_dlproc from loading the model until sufficient previous actors have been stopped.
        try :
            truncate_processing_actors(self.get_actor_name(), self.get_proc_running_since())
        except RuntimeWarning:
            self.set_proc_running_since(reset=True)
            return

        self.logger.info(f"Starting up {self.get_actor_name()} DL processing...")

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
        self.logger.info(f"{self.get_actor_name()} training result: {result}")


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
    current_actor.start_dlproc.remote()
    logger.info(f"Instructed actor {actor_name} to start processing.")
    return current_actor



# def get_processing_actors(sort_by_date=True):
#     actor_names = ray.util.list_named_actors()
#     dated_actors = []
#     refs = []
#     actor_map = {}

#     for name in actor_names:
#         actor: ActorHandle = ray.get_actor(name)
#         ref = actor.get_proc_running_since.remote()
#         refs.append(ref)
#         actor_map[ref] = {'actor': actor, 'name': name}

#     dates = ray.get(refs)

#     for ref, date in zip(refs, dates):
#         if date:  # actors with date == None are not processing
#             actor_info = actor_map[ref]
#             actor_info['date'] = date
#             dated_actors.append(actor_info)

#     if sort_by_date:
#         return sorted(dated_actors, key=lambda x: x['date'])
#     else:
#         return dated_actors

def truncate_processing_actors(current_actor_name: str, current_actor_date: datetime):
    """
    Ensures the number of processing actors does not exceed the maximum allowed limit by truncating older actors.

    This function checks the current number of named actors and stops older actors if the count exceeds the 
    `constants.MAX_ACTORS_PROCESSING` limit. It prioritizes stopping actors that were started earlier than the 
    current actor to avoid deadlocks. The truncation process retries up to `constants.MAX_RETRIES_TRUNCATE_ACTORS` 
    times if necessary.

    Args:
        current_actor_name (str): The name of the current actor that should not be stopped.
        current_actor_date (datetime): The start time of the current actor, used to compare with other actors.

    Returns:
        bool: True if the truncation process succeeded or was not needed, False if the maximum retries were reached 
        without successfully truncating actors.

    Notes:
        - This function uses Ray to manage and interact with distributed actors.
        - It assumes that each actor has a `get_proc_running_since` method to retrieve its start time and a 
          `set_proc_running_since` method to signal it to stop.
        - Logging is used to record warnings and truncation actions.
    """
    retries = 0
    breakpoint()
    while (names := sorted(ray.util.list_named_actors())) and len(names) > constants.MAX_ACTORS_PROCESSING:
        if retries >= constants.MAX_RETRIES_TRUNCATE_ACTORS:
            logger.warning(f"Actor {current_actor_name} failed to truncate total number of actors to {constants.MAX_ACTORS_PROCESSING}. Aborting startup.")
            raise RuntimeWarning('Max retries reached in truncate_processing_actors')

        overflow_count = len(names) - constants.MAX_ACTORS_PROCESSING
        names_excluding_current = [name for name in names if name != current_actor_name]
        actor_names_to_stop = names_excluding_current[:overflow_count]

        actor_handles = {name: ray.get_actor(name) for name in actor_names_to_stop}
        actor_refs = {name: handle.get_proc_running_since.remote() for name, handle in actor_handles.items()}
        actor_dates: list[datetime] = ray.get(list(actor_refs.values()))

        stop_refs = []
        for name, date in zip(actor_refs.keys(), actor_dates):
            if date and date < current_actor_date:  # This actor can only signal older actors to stop, preventing deadlock.
                actor = actor_handles[name]
                stop_refs.append(actor.set_proc_running_since.remote(reset=True))  # Collect references to the stop calls.
                logger.info(f"{current_actor_name} truncated actor {name} to maintain max processing actors.")
        
        # Wait for all stop calls to complete.
        ray.get(stop_refs)
        time.sleep(constants.RETRY_DELAY_TRUNCATE_ACTORS)

        retries += 1

