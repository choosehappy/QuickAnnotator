import configparser
from flask_restx import Resource, Api, Namespace, fields, marshal
from flask import current_app, request
from werkzeug.datastructures import FileStorage

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
api_ns_image = Namespace('image', description='Image related operations')

#################################################################################


image_model = api_ns_image.model('Image', {
    'id': fields.String(description="The image ID"),
    'name': fields.String(description="The image name"),
    'path': fields.String(description="The image path"),
    'height': fields.Integer(description="The image height"),
    'width': fields.Integer(description="The image width"),
    'datetime': fields.String(description="The datetime of upload for the image"),
    'num_annotations': fields.
    'image_file': fields.Raw(description="The image file", example="image.jpg"),
})

#################################################################################
@api_ns_image.route('/<string:project_id>', endpoint="image")
class Image(Resource):
    @api_ns_image.doc(params={
        'project_id': 'Which project?',
        'image_id': 'Which image?'})
    @api_ns_image.marshal_with(image_model)
    def get(self, project_id, id):
        """     returns an Image/ImageList   """
        image_id = request.args.get('image_id',None)
        if image_id:    # get single image
            data = [
                {
                    "id": "1",
                    "name": "image1",
                    "image_file": "image1.jpg"
                }]
        else:
            data = [
                {
                    "id": "1",
                    "name": "image1",
                    "image_file": "image1.jpg"
                },
                {
                    "id": "2",
                    "name": "image2",
                    "image_file": "image2.jpg"
                }
            ]

        return data
        

    def post(self, project_id):
        """    upload an Image   """
        data = request.json
        return 201
    
        

#################################################################################

@api_ns_image.route('/<string:project_id>/thumbnail', endpoint="thumbnail")
class ImageThumbnail(Resource):
    @api_ns_image.doc(params={'project_id': 'Which project?','image_id': 'Which image?'})
    def get(self, project_id, id):
        """     returns an Image/ImageList   """
        image_id = request.args.get('image_id',None)
        return 404
        

    def post(self, project_id):
        """    upload an Image   """
        data = request.json