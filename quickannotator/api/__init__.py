from flask import Blueprint
from flask_restx import Api

from quickannotator.api.v1.annotation import api_ns_annotation
from quickannotator.api.v1.annotation_class import api_ns_annotation_class
from quickannotator.api.v1.image import api_ns_image
from quickannotator.api.v1.setting import api_ns_setting
from quickannotator.api.v1.ray import api_ns_ray
from quickannotator.api.v1.project import api_ns_project
from quickannotator.api.v1.tile import api_ns_tile
from quickannotator.api.v1.notification import api_ns_notification



api_blueprint = Blueprint("api_v1", __name__, url_prefix="/api/v1")

api = Api(
    api_blueprint,
    title='Quick Annotator API',
    version='1.0',
    description='The Quick Annotator API',
    # All API metadatas
)

api.add_namespace(api_ns_annotation)
api.add_namespace(api_ns_annotation_class)
api.add_namespace(api_ns_image)
api.add_namespace(api_ns_setting)
api.add_namespace(api_ns_ray)
api.add_namespace(api_ns_project)
api.add_namespace(api_ns_tile)
api.add_namespace(api_ns_notification)