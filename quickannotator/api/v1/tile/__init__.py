from flask_restx import Namespace, Resource

api_ns_tile = Namespace('tile', description='Tile related operations')

# ------------------------ MODELS ------------------------


# ------------------------ REQUEST PARSERS ------------------------
get_tile_parser = api_ns_tile.parser()
get_tile_parser.add_argument('project_id', location='args', type=int, required=False)
get_tile_parser.add_argument('image_id', location='args', type=int, required=False)
get_tile_parser.add_argument('annotation_class_id', location='args', type=int, required=False)
get_tile_parser.add_argument('tile_id', location='args', type=int, required=False)


# ------------------------ ROUTES ------------------------

@api_ns_tile.route('/')
class Tile(Resource):
    @api_ns_tile.expect(get_tile_parser)
    def get(self):
        """     returns a Tile or list of Tiles
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

