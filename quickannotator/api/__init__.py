from flask import Blueprint
from flask_restx import Api

from quickannotator.api.v1.annotation import api_ns_annotation
from quickannotator.api.v1.object_class import api_ns_class
from quickannotator.api.v1.image import api_ns_image
from quickannotator.api.v1.settings import api_ns_settings
from quickannotator.api.v1.ray import api_ns_ray



api_blueprint = Blueprint("api_v1", __name__, url_prefix="/api/v1")

api = Api(
    api_blueprint,
    title='Quick Annotator API',
    version='1.0',
    description='The Quick Annotator API',
    # All API metadatas
)

api.add_namespace(api_ns_annotation)
api.add_namespace(api_ns_class)
api.add_namespace(api_ns_image)
api.add_namespace(api_ns_settings)
api.add_namespace(api_ns_ray)