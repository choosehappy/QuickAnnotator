##TODO: there seems to be no reference to this. commenting out for now - if not used, delete this
# import shapely.wkb
# import numpy as np
# import cv2
# from sqlalchemy import Table
# from sqlalchemy.orm import sessionmaker
# from .database import db
# from quickannotator.db import build_annotation_table_name

# def generate_binary_masks(engine):
#     Session = sessionmaker(bind=engine)
#     session = Session()

#     annotation_classes = session.query(AnnotationClass).all()

#     for annotation_class in annotation_classes:
#         class_id = annotation_class.id
#         tiles = session.query(Tile).filter_by(annotation_class_id=class_id).all()

#         for tile in tiles:
#             image_id = tile.image_id
#             gtpred = 'gt'
#             table_name = build_annotation_table_name(image_id, class_id, gtpred == 'gt')

#             if not engine.dialect.has_table(engine, table_name):
#                 continue

#             table = Table(table_name, db.metadata, autoload_with=engine)
#             polygon = shapely.wkb.loads(tile.geom.data)
#             mask = np.zeros((tile.height, tile.width), dtype=np.uint8)
#             cv2.fillPoly(mask, [np.array(polygon.exterior.coords, dtype=np.int32)], 1)
#             mask_filename = f"mask_{tile.id}.png"
#             cv2.imwrite(mask_filename, mask)

#     session.close()