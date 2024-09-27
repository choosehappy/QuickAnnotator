from flask_restx import Namespace, Resource

api_ns_setting = Namespace('setting', description='Settings related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------


# ------------------------ ROUTES ------------------------


@api_ns_setting.route('/<int:project_id>')
class Setting(Resource):
    def get(self):
        """     returns a Setting or list of Settings
        """

        return 200

    def put(self):
        """     create or update a Setting

        """

        return 201


@api_ns_setting.route('/<int:project_id>/reset')
class ResetSetting(Resource):
    def post(self):
        """     reset one or all Settings

        """

        return 204