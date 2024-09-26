import configparser
from flask_restx import Resource, Api, Namespace, fields, marshal
from flask import current_app, request
from werkzeug.datastructures import FileStorage
from datetime import datetime

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
api_ns_image = Namespace('image', description='Image related operations')

# ------------------------ MODELS ------------------------


image_model = api_ns_image.model('Image', {
    'id': fields.Integer(description="The image ID"),
    'name': fields.String(description="The image name"),
    'path': fields.String(description="The image path"),
    'height': fields.Integer(description="The image height"),
    'width': fields.Integer(description="The image width"),
    'date': fields.DateTime(description="The datetime of upload for the image"),
})

# ------------------------ REQUEST PARSERS ------------------------

## GET Image parser
get_image_parser = api_ns_image.parser()
get_image_parser.add_argument('image_id', location='args', type=int, required=False)

## POST TissueMask and POST ThumbnailFile parser
upload_parser = api_ns_image.parser()
upload_parser.add_argument('file', location='files',type=FileStorage, required=True)
#################################################################################
@api_ns_image.route('/<string:project_id>')
class Image(Resource):
    @api_ns_image.expect(get_image_parser)
    @api_ns_image.marshal_with(image_model)
    def get(self, project_id):
        """     returns an Image or list of Images
        Swagger docstrings support Markdown formatting:
        # Implementation details:

        ```python
            conn.execute()
        ```
        """
        id = request.args.get('image_id')

        datum = {
            'id': 1,
            'name': "testImage",
            'path': "/test/path",
            'height': 10000,
            'width': 20000,
            'date': datetime.now()
        }
        if id:
            return datum, 200

        else:
            data = [datum]

            return data, 200

#################################################################################


#################################################################################
@api_ns_image.route('/<string:project_id>/<string:image_id>/image_file', endpoint="image")
class ImageFile(Resource):
    def get(self, project_id, image_id):
        """     returns an Image file   """

        return 200


    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload an Image file   """
        data = request.json
        return 201

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/thumbnail', endpoint="thumbnail_file")
class ThumbnailFile(Resource):
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200


    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 200

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/tissue_mask', endpoint="tissue_mask_file")
class TissueMaskFile(Resource):
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200


    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 200

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<string:format>', endpoint="patch")
class PatchFile(Resource):
    def get(self, project_id, image_id, level, col, row, format):
        """     returns a patch file   """
        return 200

