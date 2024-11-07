from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import quickannotator.db as qadb

bp = Blueprint('setting', __name__, description='Setting operations')


# ------------------------ RESPONSE MODELS ------------------------
class SettingRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = qadb.Setting

class GetSettingArgsSchema(Schema):
    setting_id = fields.Integer()

class PutSettingArgsSchema(Schema):
    setting_value = fields.Str()

class SearchSettingArgsSchema(Schema):
    project_id = fields.Int()
# ------------------------ ROUTES ------------------------


@bp.route('/')
class Setting(MethodView):

    @bp.arguments(GetSettingArgsSchema, location='query')
    @bp.response(200, SettingRespSchema)
    def get(self, args):
        """     returns a Setting

        """

        return {}, 200

    @bp.arguments(PutSettingArgsSchema, location='query')
    def put(self, args):
        """     update a setting.

        """

        return 201

@bp.route('/search')
class SettingSearch(MethodView):
    """     get a list of Settings,
    e.g., get all settings for a project.
    """
    @bp.arguments(SearchSettingArgsSchema, location='query')
    @bp.response(200, SettingRespSchema(many=True))
    def get(self, args):
        return [], 200

@bp.route('/reset')
class ResetSetting(MethodView):
    def post(self, args):
        """     reset one or all Settings

        """

        return 200