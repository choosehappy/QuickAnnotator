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
get_image_parser.add_argument('project_id', location='args', type=int, required=False)
get_image_parser.add_argument('image_id', location='args', type=int, required=False)

## POST Image parser
post_image_parser = api_ns_image.parser()
post_image_parser.add_argument('image', location='files',type=FileStorage, required=False)
post_image_parser.add_argument('name', location='args', type=str, required=False)
post_image_parser.add_argument('path', location='args', type=str, required=False)

## DELETE Image parser
delete_image_parser = api_ns_image.parser()
delete_image_parser.add_argument('image_id', location='args', type=int, required=True)

## POST TissueMask and POST ThumbnailFile parser
post_file_parser = api_ns_image.parser()
post_file_parser.add_argument('file', location='files',type=FileStorage, required=True)

# ------------------------ ROUTES ------------------------
@api_ns_image.route('/')
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

    @api_ns_image.expect(post_image_parser, validate=True)
    def post(self, project_id):
        """     upload an Image   """


        return 200

    @api_ns_image.expect(delete_image_parser, validate=True)
    def delete(self, project_id):
        """     delete an Image   """
        return 204


#################################################################################
@api_ns_image.route('/<int:image_id>/image_file', endpoint="image")
class ImageFile(Resource):
    def get(self, project_id, image_id):
        """     returns an Image file   """

        return 200


#################################################################################

@api_ns_image.route('/<int:image_id>/thumbnail', endpoint="thumbnail_file")
class ThumbnailFile(Resource):
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200


    @api_ns_image.expect(post_file_parser, validate=True)
    def put(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 201


    def delete(self, project_id):
        """    delete a Thumbnail file   """
        return 204

#################################################################################

@api_ns_image.route('/<int:image_id>/tissue_mask', endpoint="tissue_mask_file")
class TissueMaskFile(Resource):
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200


    @api_ns_image.expect(post_file_parser, validate=True)
    def put(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 201

    def delete(self, project_id, image_id):
        """    delete a Thumbnail file   """
        return 204


#################################################################################

@api_ns_image.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<int:format>', endpoint="patch")
class PatchFile(Resource):
    def get(self, project_id, image_id, level, col, row, format):
        """     returns a patch file   """
        return 200
