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
from quickannotator.constants import TileStatus
from quickannotator.db import get_session
from quickannotator.db.models import Tile
import sqlalchemy
from quickannotator.dl.training import train_pred_loop


class ActorManager:
    def __init__(self, project_id: int, annotation_class_id: int, create_actor=False):
        if create_actor:
            name = self.get_actor_name(project_id, annotation_class_id)
            self.actor = DLActor.options(name=name).remote(name, annotation_class_id, 256, 20)
        else:
            self.actor_name = ActorManager.get_actor_name(project_id, annotation_class_id)
            self.actor = ray.get_actor(self.actor_name)

    @staticmethod
    def get_actor_name(project_id: int, annotation_class_id: int) -> str:
        return f"dl_actor_{project_id}_{annotation_class_id}"
    
    @staticmethod
    def create_actor(name: str, classid, tile_size, magnification):
        


@ray.remote
class DLActor:
    def __init__(self,actor_name,classid,tile_size,magnification):
        
        print(f"{actor_name=}")
        print(f"{classid=}")
        print(f"{tile_size=}")
        self.actor_name=actor_name #TODO: i don't know if there is a way to get this reflexively instead of passing it in? -- trying to get something working first : ) 
        self.classid=classid
        self.tile_size=tile_size
        self.enable_training=False # starts not training
        self.closedown = False 
        self.allow_pred=True # --- don't know if we'll ever need this, so hard setting to true
        self.hexid=None
        self.magnification = magnification

    def start_dlproc(self,allow_pred=True):
        #--------- this is a bit of a disaster - need to basically make sure we're not launching multple
        #TODO: check if hexid is alive and valid -- can't start two trainings!
        # if is_training(self.hexid):
        #     return False
        #need to check if is already training, if yes, no opt
        print("starting up", self.actor_name)
        #---------------------------

        #scaling_config = ray.train.ScalingConfig(num_workers=2, use_gpu=True,resources_per_worker={"GPU":.5})
        ## will fail on single node single gpu --- (DLActor pid=174521) Duplicate GPU detected : rank 1 and rank 0 both on CUDA device 1000

        #--- NEED A GPU CONTAINER TO TEST THIS        
        total_gpus  = ray.cluster_resources().get("GPU", 0)
        # total_gpus_available=  ray.available_resources().get("GPU", 0)
        # print(total_gpus,total_gpus_available)
        # resource_to_request = (total_gpus_available/total_gpus)/2 * 1.01
        # print(f"resource_to_request: {resource_to_request}")

        scaling_config = ray.train.ScalingConfig(num_workers=int(total_gpus), use_gpu=True,
                                                resources_per_worker={"GPU":.01}, placement_strategy="STRICT_SPREAD")
        
        #----
#        scaling_config = ray.train.ScalingConfig(num_workers=1, use_gpu=False)
        trainer = ray.train.torch.TorchTrainer(train_pred_loop,
                                       scaling_config=scaling_config,
                                       train_loop_config={'actor_name':self.actor_name,
                                                          'classid':self.classid,
                                                         'tile_size':self.tile_size,
                                                         'magnification':self.magnification})
        self.hexid = trainer.fit().hex() ##widly -- this doesn't save the result in the actor
        return self.hexid
    
    def infer(self,image_id,tileids): #only bulk should be performed, there is no difference between doing 1 versus 100 tiles, so this reduces code complexity
                                      #NOTE: there is another option here - that we accept ids from the tile table directly instead of having to accept both image_id and tile_id
        if not self.allow_pred:
            print("not doing inference --- actor was started with prediction disabled")
            return False
        # probably need to *Delete* the tiles that are associated with this tileid before executing the below, so that they're not duplicated
        # i would do that in a seperate function as "infer" doesn't logically mean "delete", so the expected behavior might be weird if it delets stuff unprompted
        # perhaps that could be clarified with a e.g., named function paramter - or perhaps a seperate function is really needed
        with get_session() as db_session:
            stmt = sqlalchemy.update(Tile).where(Tile.tile_id.in_(tileids), Tile.image_id == image_id,
                                                Tile.annotation_class_id == self.classid)\
                                                    .values(pred_status=TileStatus.STARTPROCESSING,pred_datetime=sqlalchemy.func.now()) ## should add date time

            # Execute the update
            db_session.execute(stmt)

        #need a similar statement to get the DL starting
        return True
    
    def getTileStatus(self,image_id,tile_ids): #probably belongs else where but need this for debug
        with get_session() as db_session:
            stmt = db_session.query(Tile).filter(Tile.tile_id.in_(tile_ids),Tile.image_id == image_id,
                            Tile.annotation_class_id == self.classid)

            result = stmt.all()
        
        return result

    def getClassId(self):
        return self.classid
        
    def getHexId(self):
        return self.hexid

    def setHexId(self,hexid:str): # not sure if set is smart to have -- should likely be done internally
        self.hexid=hexid
        return self.hexid

    def setEnableTraining(self,enable_training: bool):
        self.enable_training=enable_training
        return self.enable_training
    
    def getEnableTraining(self):
        return self.enable_training
    
    def getCloseDown(self):
        return self.closedown
    
    def setCloseDown(self,closedown: bool):
        self.closedown=closedown
        return self.closedown
    
    def getActorName(self):
        return self.actor_name
    
    def getTileSize(self):
        return self.tile_size

