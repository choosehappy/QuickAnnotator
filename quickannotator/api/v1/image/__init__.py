import configparser
from flask_restx import Resource, Api, Namespace, fields, marshal
from flask import current_app, request, send_from_directory
from werkzeug.datastructures import FileStorage
from datetime import datetime

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
api_ns_image = Namespace('image', description='Image related operations')

# ------------------------ RESPONSE MODELS ------------------------


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
get_image_parser.add_argument('image_id', location='args', type=int, required=True)

## GET Image search parser
get_image_search_parser = api_ns_image.parser()
get_image_search_parser.add_argument('name', location='args', type=str, required=False)

## POST Image parser
post_image_parser = api_ns_image.parser()
post_image_parser.add_argument('image', location='files',type=FileStorage, required=False)
post_image_parser.add_argument('name', location='args', type=str, required=False)
post_image_parser.add_argument('path', location='args', type=str, required=False)

## DELETE Image parser
delete_image_parser = get_image_parser.copy()

## POST TissueMask and POST ThumbnailFile parser
upload_file_parser = api_ns_image.parser()
upload_file_parser.add_argument('file', location='files',type=FileStorage, required=True)

# ------------------------ ROUTES ------------------------
@api_ns_image.route('/', endpoint="image")
class Image(Resource):
    @api_ns_image.expect(get_image_parser)
    @api_ns_image.marshal_with(image_model)
    def get(self):
        """     returns an Image
        """
        id = request.args.get('image_id')

        datum = {}
        return datum, 200


    @api_ns_image.expect(post_image_parser, validate=True)
    @api_ns_image.marshal_with(image_model)
    def post(self):
        """     upload an Image   """

        datum = {}
        return datum, 200

    @api_ns_image.expect(delete_image_parser, validate=True)
    @api_ns_image.response(204, "Image  deleted")
    def delete(self):
        """     delete an Image   """
        return 204

#################################################################################
@api_ns_image.route('/<int:project_id>/search', endpoint="image_search")
class ImageSearch(Resource):
    @api_ns_image.expect(get_image_search_parser)
    @api_ns_image.marshal_with(image_model, as_list=True)
    def get(self):
        data = [{}]
        return data, 200

#################################################################################
@api_ns_image.route('/<int:image_id>/image_file', endpoint="image_file")
class ImageFile(Resource):
    def get(self, image_id):
        """     returns an Image file   """
        path = ''
        name = 'name'
        return send_from_directory(path, name)


#################################################################################

@api_ns_image.route('/<int:image_id>/thumbnail', endpoint="thumbnail_file")
class ThumbnailFile(Resource):
    def get(self, image_id):
        """     returns a thumbnail file   """
        path = ''
        name = 'name'
        return send_from_directory(path, name)


    @api_ns_image.expect(upload_file_parser, validate=True)
    @api_ns_image.response(201, "Thumbnail file  uploaded")
    def put(self, image_id):
        """    upload a Thumbnail file   """
        return 201

    @api_ns_image.response(204, "Thumbnail  deleted")
    def delete(self):
        """    delete a Thumbnail file   """
        return 204

#################################################################################

@api_ns_image.route('/<int:image_id>/tissue_mask', endpoint="tissue_mask_file")
class TissueMaskFile(Resource):
    def get(self, image_id):
        """     returns a thumbnail file   """
        return 200


    @api_ns_image.expect(upload_file_parser, validate=True)
    @api_ns_image.response(201, "Tissue mask file  uploaded")
    def put(self, image_id):
        """    upload a Thumbnail file   """
        return 201

    @api_ns_image.response(204, "Tissue mask  deleted")
    def delete(self, image_id):
        """    delete a Thumbnail file   """
        return 204


#################################################################################

@api_ns_image.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<int:format>', endpoint="patch")
class PatchFile(Resource):
    def get(self, image_id, level, col, row, format):
        """     returns a patch file   """
        return 200
