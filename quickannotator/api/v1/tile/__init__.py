from flask_restx import Namespace, Resource, fields

api_ns_tile = Namespace('tile', description='Tile related operations')

# ------------------------ RESPONSE MODELS ------------------------
tile_model = api_ns_tile.model('Tile', {
    'id': fields.Integer(),
    'image_id': fields.Integer(),
    'annotation_class_id': fields.Integer(),
    'upper_left_coord': fields.Raw(),
    'seen': fields.Integer(description='0: not seen by model, 1: predictions pending, 2: seen by model')
})

# ------------------------ REQUEST PARSERS ------------------------

get_tile_parser = api_ns_tile.parser()
get_tile_parser.add_argument('tile_id', location='args', type=int, required=True)

search_tile_parser = api_ns_tile.parser()
search_tile_parser.add_argument('image_id', location='args', type=int, required=True)
search_tile_parser.add_argument('annotation_class_id', location='args', type=int, required=True)
search_tile_parser.add_argument('bbox_polygon', location='args', type=bytes, required=True)


# ------------------------ ROUTES ------------------------

@api_ns_tile.route('/')
class Tile(Resource):
    @api_ns_tile.expect(get_tile_parser)
    @api_ns_tile.marshal_with(tile_model)
    def get(self):
        """     returns a Tile
        """


        return 200

    def put(self):
        """     create or update a Tile

        """

        return 201

    def delete(self):
        """     delete a Tile

        """

        return 204

@api_ns_tile.route('/search')
class TileSearch(Resource):
    @api_ns_tile.expect(search_tile_parser)
    @api_ns_tile.marshal_with(tile_model, as_list=True)
    def get(self):
        """     get all Tiles within a bounding box
        """

        return 200