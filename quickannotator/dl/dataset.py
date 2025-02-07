import shapely.wkb
import numpy as np
import cv2
from sqlalchemy import Table, inspect
from quickannotator.db.helper import build_annotation_table_name
from torch.utils.data import IterableDataset
from quickannotator.dl.database import create_db_engine, get_database_path, get_session_aj
from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client
from quickannotator.db import db, Project, Image, AnnotationClass, Notification, Tile, Setting, Annotation, SearchCache
import openslide
import numpy as np
from PIL import Image as PILImage
import scipy.ndimage
import cv2


class TileDataset(IterableDataset):
    def __init__(self, classid, transforms=None, edge_weight=0):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight

        session = get_session_aj(create_db_engine(get_database_path()))
        self.tiles = session.query(Tile)\
                                    .filter(Tile.annotation_class_id == self.classid)\
                                    .all() 
        print(f"{len(self.tiles)=}")
        

    def __iter__(self):
        session = get_session_aj(create_db_engine(get_database_path())) #maybe self?
        engine = create_db_engine(get_database_path())
        inspector = inspect(engine)
        client = get_memcached_client() ## client should be a "self" variable
        for tile in self.tiles:
            image_id = tile.image_id
            tile_id = tile.id
            cache_key = f"{image_id}_{tile_id}"
            cache_val = client.get(cache_key)
            if cache_val:
                io_image, mask_image, weight = [decompress_from_jpeg(i) for i in cache_val]
            else:
                gtpred = 'gt'  # or 'pred' based on your requirement
                table_name = build_annotation_table_name(image_id, self.classid, gtpred == 'gt')
                if not inspector.has_table(table_name):
                    continue
                table = Table(table_name, db.metadata, autoload_with=engine)
                annotations = session.query(table).filter(table.c.polygon.ST_Within(tile.geom)).all()
                if len(annotations) == 0:
                    continue
                tpoly = shapely.wkb.loads(tile.geom.data)
                minx, miny, maxx, maxy = tpoly.bounds
                width = int(maxx - minx)
                height = int(maxy - miny)
                image = session.query(Image).filter_by(id=image_id).first()
                if not image:
                    continue
                image_path = image.path
                slide = openslide.OpenSlide("/opt/QuickAnnotator/quickannotator/"+image_path)
                region = slide.read_region((int(minx), int(miny)), 0, (width, height))
                io_image = np.array(region.convert("RGB"))
                mask_image = np.zeros((height, width), dtype=np.uint8)
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(annotation.polygon.data)
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-minx, yoff=-miny)
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                if self.edge_weight:
                    weight = scipy.ndimage.morphology.binary_dilation(mask_image, iterations=2) & ~mask_image
                else:
                    weight = np.ones(mask_image.shape, dtype=mask_image.dtype)
                client.set(cache_key, [compress_to_jpeg(i) for i in (io_image, mask_image, weight)])
            img_new = io_image
            mask_new = mask_image
            weight_new = weight
            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']
            yield img_new, mask_new.unsqueeze(0), weight_new