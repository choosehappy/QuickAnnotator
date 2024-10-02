from flask_restx import Namespace, Resource, fields

api_ns_setting = Namespace('setting', description='Settings related operations')

# ------------------------ RESPONSE MODELS ------------------------

setting_model = api_ns_setting.model('Setting', {
    "id": fields.Integer(),
    "name": fields.String(),
    "value": fields.String(),
    "description": fields.String()
})
# ------------------------ REQUEST PARSERS ------------------------
base_parser = api_ns_setting.parser()
base_parser.add_argument('setting_id', type=str, location='args', required=False)

put_setting_parser = api_ns_setting.parser()
put_setting_parser.add_argument('setting_value', location='args', type=str, required=True)

search_setting_parser = api_ns_setting.parser()
search_setting_parser.add_argument('is_app_setting', type=bool, location='args', required=True)
search_setting_parser.add_argument('project_id', type=str, location='args', required=False)

# ------------------------ ROUTES ------------------------


@api_ns_setting.route('/<int:setting_id>')
class Setting(Resource):

    @api_ns_setting.marshal_with(setting_model)
    def get(self):
        """     returns a Setting

        """

        return 200

    @api_ns_setting.expect(put_setting_parser)
    @api_ns_setting.response(201, "Setting  updated.")
    def put(self):
        """     update a setting.

        """

        return 201

@api_ns_setting.route('/search')
class SettingSearch(Resource):
    """     get a list of Settings,
    e.g., get all settings for a project.
    """
    @api_ns_setting.expect(search_setting_parser)
    @api_ns_setting.marshal_with(setting_model, as_list=True)
    def get(self):
        return [{}], 200

@api_ns_setting.route('/reset')
class ResetSetting(Resource):
    @api_ns_setting.expect(base_parser)
    @api_ns_setting.response(200, "Setting(s)  reset to default.")
    def post(self):
        """     reset one or all Settings

        """

        return 200