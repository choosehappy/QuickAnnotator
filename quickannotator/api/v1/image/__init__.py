import configparser
from flask_restx import Resource, Api, Namespace, fields, marshal
from flask import current_app, request
from werkzeug.datastructures import FileStorage

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
api_ns_image = Namespace('image', description='Image related operations')

## Used for Swagger UI to be able to upload an image.
upload_parser = api_ns_image.parser()
upload_parser.add_argument('file', location='files',type=FileStorage, required=True)

#################################################################################


image_model = api_ns_image.model('Image', {
    'id': fields.String(description="The image ID"),
    'name': fields.String(description="The image name"),
    'path': fields.String(description="The image path"),
    'height': fields.Integer(description="The image height"),
    'width': fields.Integer(description="The image width"),
    'datetime': fields.String(description="The datetime of upload for the image"),
    'annotation_counts': fields.Raw(description="A json dict of counts by class"),
    'image_file': fields.Raw(description="The image file", example="image.jpg"),
})

#################################################################################
@api_ns_image.route('/<string:project_id>')
class Image(Resource):
    @api_ns_image.doc(params={'project_id': 'Which project?', 'image_id': 'Which image?'})
    @api_ns_image.marshal_with(image_model)
    def get(self, project_id, image_id):
        """     returns an Image/ImageList     """
        return 201


#################################################################################
@api_ns_image.route('/<string:project_id>/<string:image_id>/image_file', endpoint="image")
class ImageFile(Resource):
    @api_ns_image.doc(params={'project_id': 'Which project?', 'image_id': 'Which image?'})
    def get(self, project_id, image_id):
        """     returns an Image file   """

        return 200

    @api_ns_image.doc(params={'project_id': 'Which project?', 'image_id': 'Which image?'})
    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload an Image file   """
        data = request.json
        return 201

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/thumbnail', endpoint="thumbnail_file")
class ThumbnailFile(Resource):
    @api_ns_image.doc(params={'project_id': 'Which project?','image_id': 'Which image?'})
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200

    @api_ns_image.doc(params={'project_id': 'Which project?', 'image_id': 'Which image?'})
    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 200

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/tissue_mask', endpoint="tissue_mask_file")
class TissueMaskFile(Resource):
    @api_ns_image.doc(params={'project_id': 'Which project?','image_id': 'Which image?'})
    def get(self, project_id, image_id):
        """     returns a thumbnail file   """
        return 200

    @api_ns_image.doc(params={'project_id': 'Which project?', 'image_id': 'Which image?'})
    @api_ns_image.expect(upload_parser, validate=True)
    def post(self, project_id, image_id):
        """    upload a Thumbnail file   """
        return 200

#################################################################################

@api_ns_image.route('/<string:project_id>/<string:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<string:format>', endpoint="patch")
class PatchFile(Resource):
    @api_ns_image.doc(params={
        'project_id': 'Which project?',
        'image_id': 'Which image?',
        'level': 'Which downsample level?',
        'col': 'Which column?',
        'row': 'Which row?',
        'format': 'Which file format?',
    })
    def get(self, project_id, image_id, level, col, row, format):
        """     returns a patch file   """
        return 200

