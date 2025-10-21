from itertools import product
import os
import shutil
from quickannotator.db.fsmanager import fsmanager
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import delete_annotation_classes
from quickannotator.db.crud.image import delete_images
from quickannotator.db.crud.project import delete_projects, get_project_by_id
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.api.v1.annotation.utils import AnnotationImporter, compute_actor_name
import quickannotator.constants as constants
from werkzeug.datastructures import FileStorage
import pandas as pd
import ray

def isHistoqcResult(tsv_path):
    with open(tsv_path, 'r') as f:
        for i in range(constants.TSVFields.HISTO_TSV_HEADLINE.value):
            line = f.readline()
            if not line:
                return False
            if not line.startswith('#'):
                return False
        return True
    
def save_tsv_to_temp_dir(project_id: int, file: FileStorage):
    # save tsv under current project folder
    project_path = fsmanager.nas_write.get_project_path(project_id=project_id ,relative=False)
    tsv_filepath = os.path.join(project_path, file.filename)
    os.makedirs(project_path, exist_ok=True)

    try:
        file.save(tsv_filepath)
    except IOError as e:
        print(f"Saving TSV File Error: An I/O error occurred when saving ${file.filename}: {e}")
    except Exception as e:
        print(f"Saving TSV File Error: An unexpected error occurred when saving ${file.filename}: {e}")
    
    return tsv_filepath
    
def import_from_tabular(project_id: int, file: FileStorage):
    tsv_filepath = save_tsv_to_temp_dir(project_id, file)
    # read tsv file
    header = 0
    col_name_filename = constants.TSVFields.FILE_NAME.value
    if isHistoqcResult(tsv_filepath):
        header = constants.TSVFields.HISTO_TSV_HEADLINE.value - 1
        col_name_filename = constants.TSVFields.HISTO_FILE_NAME.value 
    data = pd.read_csv(tsv_filepath, sep='\t', header=header, keep_default_na=False)
    columns = data.columns

    actor_ids = []
    for idx, row in data.iterrows():
        # create a actor for current row
            # actor_name = compute_actor_name(project_id, constants.NamedRayActorType.ANNOTATION_IMPORTER)
            importer = AnnotationImporter.remote()
            actor_id = importer._actor_id.hex()
            task_ref = importer.import_from_tsv_row.remote(project_id, col_name_filename, row, columns)
            actor_ids.append(actor_id)
    return  actor_ids

def delete_project_and_related_data(project_id):
    project = get_project_by_id(project_id)
    
    image_ids = [image.id for image in project.images]

    # This will not include the tissue mask, which is application-level.
    annotation_class_ids = [annotation_class.id for annotation_class in project.annotation_classes]

    # Ensure the mask class ID is included in the deletion
    AnnotationStore.bulk_drop_tables(image_ids, annotation_class_ids + [constants.MASK_CLASS_ID])

    # Delete all respective tiles
    # TODO: consider using cascaded delete
    tile_store = TileStoreFactory.get_tilestore()
    tile_store.delete_tiles(annotation_class_ids=annotation_class_ids)

    # Delete all respective images
    # TODO: consider using cascaded delete
    delete_images(image_ids)

    # Delete the annotation classes
    # TODO: consider using cascaded delete
    delete_annotation_classes(annotation_class_ids)

    # Clean up the file structure
    remove_project_folders(project_id)

    # Delete the project
    delete_projects(project_id)


def remove_project_folders(project_id: int):    # NOTE: This currently does not remove annotation class folders as these are not subfolders of the project.
    # remove the project folders
    full_project_path = fsmanager.nas_write.get_project_path(project_id, relative=False)
    if os.path.exists(full_project_path):
        try:
            shutil.rmtree(full_project_path)
        except OSError as e:
            print(f"Error deleting folder '{full_project_path}': {e}")