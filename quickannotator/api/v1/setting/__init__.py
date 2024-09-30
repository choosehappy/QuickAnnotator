from flask_restx import Namespace, Resource

api_ns_setting = Namespace('setting', description='Settings related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
get_setting_parser = api_ns_setting.parser()
get_setting_parser.add_argument('project_id', location='args', type=int, required=False)
get_setting_parser.add_argument('setting_id', location='args', type=int, required=False)
get_setting_parser.add_argument('setting_name', location='args', type=str, required=False)

put_setting_parser = api_ns_setting.parser()
put_setting_parser.add_argument('setting_id', location='args', type=int, required=False)
put_setting_parser.add_argument('setting_name', location='args', type=str, required=False)
put_setting_parser.add_argument('setting_value', location='args', type=str, required=True)

# ------------------------ ROUTES ------------------------


@api_ns_setting.route('/')
class Setting(Resource):
    @api_ns_setting.expect(get_setting_parser)
    def get(self):
        """     returns a Setting or list of Settings

        """

        return 200

    @api_ns_setting.expect(put_setting_parser)
    def put(self):
        """     create or update a Setting

        """

        return 201


@api_ns_setting.route('/<int:setting_id>/reset')
class ResetSetting(Resource):
    def post(self):
        """     reset one or all Settings

        """

        return 204