import cv2

import torch
import numpy as np
import shapely.wkb
import shapely.geometry
import shapely.affinity

from sqlalchemy import func, select, update

from quickannotator.db.models import Tile
from quickannotator.db import get_session
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.db.crud.tile import TileStoreFactory, TileStore

from quickannotator.constants import TileStatus
from quickannotator.dl.utils import decompress_from_image_bytestream, get_memcached_client, load_tile
from quickannotator.api.v1.utils.shared_crud import AnnotationStore

from datetime import datetime


def preprocess_image(io_image, device):
    io_image = io_image / 255.0
    io_image = (io_image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    io_image = np.pad(io_image, ((32, 32), (32, 32), (0, 0)), mode='reflect')
    io_image = torch.tensor(io_image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(device)
    return io_image

def postprocess_output(outputs, min_area = 100, dilate_kernel = 2): ## These should be defined as class level settings from the user
    outputs = outputs.squeeze().detach().cpu().numpy()
    positive_mask = outputs> .5 #TODO: maybe UI or system threshold? probably a good idea
    
    kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
    positive_mask = cv2.dilate(positive_mask.astype(np.uint8), kernel, iterations=2)>0

    contours, _ = cv2.findContours(positive_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    polygons = [shapely.geometry.Polygon(contour[:, 0, :]) for contour in contours if cv2.contourArea(contour) >= min_area]
    return polygons



def delete_annotations(tile):
    table_name = build_annotation_table_name(tile.image_id, tile.annotation_class_id, is_gt=False)
    table = create_dynamic_model(table_name)  # Get the ORM class dynamically

    with get_session() as db_session:
        db_session.query(table).filter(table.tile_id == tile.tile_id).delete(synchronize_session=False) 
        #Why synchronize_session=False?
        #This ensures that SQLAlchemy does not try to synchronize in-memory objects, improving performance when deleting many rows.
        db_session.commit()


def save_annotations(tile,polygons): #TODO: i feel like this function likely exists elsewhere in the system as well?
    table_name = build_annotation_table_name(tile.image_id, tile.annotation_class_id, is_gt = False)
    table = create_dynamic_model(table_name)
    

    new_annotations = []
    for polygon in polygons:
        translated_polygon = shapely.affinity.translate(polygon, xoff=tile.x, yoff=tile.y) #elegant
        area = translated_polygon.area
        centroid = translated_polygon.centroid
        
        new_annotation = {
            'image_id': tile.image_id,
            'annotation_class_id': tile.annotation_class_id,
            'tile_id': tile.tile_id,
            'polygon': translated_polygon.wkt,
            'area': area,
            'isgt': False,
            'centroid': centroid.wkt
        }
        #print("new anno!\t\t:",new_annotation["image_id"],new_annotation["annotation_class_id"]) #TODO: push to logging or remove
        new_annotations.append(new_annotation)  
    #print(new_annotations)
    
    with get_session() as db_session:
        db_session.execute(table.__table__.insert(), new_annotations)
        db_session.commit()
        


def getPendingInferenceTiles(classid,batch_size_infer):
    with get_session() as db_session:  # Ensure this provides a session context
        # with db_session.begin():  # Explicit transaction
        subquery = (
            select(Tile.id)
            .where(Tile.annotation_class_id == classid,
                Tile.pred_status == TileStatus.STARTPROCESSING)
            .order_by(Tile.pred_datetime.desc()) #always get the latest ones first #TODO: should this be asc?
            .limit(batch_size_infer).with_for_update(skip_locked=True) #with_for_update is a Postgres specific clause
        )

        tiles = db_session.execute(
            update(Tile)
            .where(Tile.id.in_(subquery))
            .where(Tile.pred_status == TileStatus.STARTPROCESSING)  # Ensures another worker hasn't claimed it
            .values(pred_status=TileStatus.PROCESSING,pred_datetime=datetime.now())
            .returning(Tile)
        ).scalars().all()
        
        db_session.expunge_all()


        return tiles if tiles else None

    
def update_tile_status(tile_batch,status):
    # with get_session() as db_session:
    #     for tile in tile_batch:
    #         tile.pred_status = status
    #         tile.pred_datetime = func.now()
    #     db_session.bulk_save_objects(tile_batch)  # Bulk operation doesn't work with func now!!
    #     db_session.commit()  # Commit changes

    with get_session() as db_session: #two options here - iteratively add the annotations , or use datetime.datetime.now()  in the bulk function and set
                                        #the latter is a bit problematic if the database + web server have different times set, since func.now() is used everywhere else
                                    #one would need to change all func.now to datetime.datetime.now() to make it rock solid. lets see the performance of this first and adjust if needed
        for tile in tile_batch:
            tile.pred_status = status
            tile.pred_datetime = datetime.now()
            db_session.add(tile)  # Add each tile individually
        
        db_session.commit()  # Commit all changes


def run_inference(device, model, tiles):
    client = get_memcached_client()

    io_images = []
    
    for tile in tiles:
        img_cache_key = f"img_{tile.image_id}_{tile.id}" 
        try: #if memcache isn't working, no problem, just keep going
            img_cache_val = client.get(img_cache_key) or {}
        except:
            img_cache_val = {}
        
        if img_cache_val:
            io_image = decompress_from_image_bytestream(img_cache_val[0])

        else:
            io_image,tile.x,tile.y = load_tile(tile)

        cv2.imwrite("/opt/QuickAnnotator/quickannotator/data/output/img.png",io_image) #TODO: remove- - for debug
        io_images.append(io_image)

    io_images = [preprocess_image(io_image, device) for io_image in io_images]
    io_images = torch.cat(io_images, dim=0)
    print(f"io_images going on GPU: \t {io_images.shape}")
    
    model.eval()
    with torch.no_grad():
        outputs = model(io_images)  #output at target magnification level!
        outputs = torch.sigmoid(outputs) #BCEWithLogitsLoss needs a sigmoid at the end
        outputs = outputs[:, :, 32:-32, 32:-32]

        for j, output in enumerate(outputs):
            #---
            # oo = outputs.squeeze().detach().cpu().numpy()
            # cv2.imwrite("/opt/QuickAnnotator/output.png",oo) #TODO: remove- - for debug
            # np.save('/opt/QuickAnnotator/output.npy', oo)
            #---
            polygons = postprocess_output(output) #some parmaeters here should be added to the class level config -- see function prototype
            translated_polygons = [
                shapely.affinity.translate(polygon, xoff=tiles[j].x, yoff=tiles[j].y) for polygon in polygons
            ]
            print(f'saving annotations for tile {tiles[j].id}. Setting pred_status to DONEPROCESSING')
            with get_session() as db_session:
                store = AnnotationStore(tiles[j].image_id, tiles[j].annotation_class_id, is_gt=False, in_work_mag=True)
                store.delete_annotations_by_tile(tiles[j].tile_id)
                store.insert_annotations(translated_polygons, tiles[j].tile_id)
                
    
    print("updating tile status")
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    result = tilestore.upsert_pred_tiles(image_id=tiles[0].image_id, 
                      annotation_class_id=tiles[0].annotation_class_id, 
                      tile_ids={tile.tile_id for tile in tiles}, 
                      pred_status=TileStatus.DONEPROCESSING, 
                      process_owns_tile=True)
    # if result[0].pred_status != TileStatus.DONEPROCESSING:
    #     import pdb; pdb.set_trace()  # Conditional breakpoint
    # update_tile_status(tiles, TileStatus.DONEPROCESSING) #now taht the batch is done, need to update tile status
    return outputs