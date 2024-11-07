import quickannotator.db as qadb
from sqlalchemy import func, Table
from quickannotator.db import db
from sqlalchemy.orm import aliased
from sqlalchemy import exists

def tiles_within_bbox_old(db, image_id, annotation_class_id, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)

    tissue_mask_tablename = f"{image_id}_{annotation_class_id}_gt_annotation"
    tissue_mask_table = Table(tissue_mask_tablename, db.metadata, autoload_with=db.engine)

    tissue_mask_subquery = (
        db.session.query(tissue_mask_table.c.polygon)
        .filter(tissue_mask_table.c.polygon.ST_Intersects(envelope))
        .subquery()
    )

    # Query to get tiles that intersect with any polygon in the tissue mask subquery
    tiles = db.session.query(qadb.Tile).filter(
        qadb.Tile.image_id == image_id,
        qadb.Tile.annotation_class_id == annotation_class_id,
        qadb.Tile.geom.ST_Intersects(envelope),
        qadb.Tile.geom.ST_Intersects(tissue_mask_subquery.c.polygon)  # Filter by intersection with tissue mask polygons
    ).all()

    return tiles

def tiles_within_bbox(db, image_id, annotation_class_id, x1, y1, x2, y2):
    tm_class_id = 1
    envelope = func.BuildMbr(x1, y1, x2, y2)

    tissue_mask_tablename = f"{image_id}_{tm_class_id}_gt_annotation"
    tissue_mask_table = Table(tissue_mask_tablename, db.metadata, autoload_with=db.engine)
    # Step 1: Define a CTE to pre-filter polygons by the envelope
    envelope_intersecting_polygons = (
        db.session.query(tissue_mask_table.c.polygon)
        .filter(tissue_mask_table.c.polygon.ST_Intersects(envelope))
        .cte("envelope_intersecting_polygons")
    )

    # Step 2: Create an alias for the CTE to use in the main query
    eip_alias = aliased(envelope_intersecting_polygons)

    # Step 3: Main query to filter tiles by intersecting polygons
    tiles = db.session.query(qadb.Tile).filter(
        qadb.Tile.image_id == image_id,
        qadb.Tile.annotation_class_id == annotation_class_id,
        qadb.Tile.geom.ST_Intersects(envelope),
        exists()
        .where(eip_alias.c.polygon.ST_Intersects(qadb.Tile.geom))
    ).all()

    return tiles