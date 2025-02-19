from flask_smorest import Blueprint, abort
from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from flask.views import MethodView
from quickannotator.db import db_session
import quickannotator.db.models as models

bp = Blueprint('notification', __name__, description='Notification operations')
# ------------------------ RESPONSE MODELS ------------------------
class NotificationRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Notification

class GetNotificationArgsSchema(Schema):
    notification_id = fields.Int()

class SearchNotificationArgsSchema(Schema):
    project_id = fields.Int()
    image_id = fields.Int()

# ------------------------ ROUTES ------------------------

@bp.route('/')
class Notification(MethodView):
    @bp.arguments(GetNotificationArgsSchema, location='query')
    @bp.response(200, NotificationRespSchema)
    def get(self, args):
        """     returns a Notification

        """
        return {}, 200

    def put(self):
        """     update a Notification

        """
        return 201

@bp.route('/search')
class SearchNotification(MethodView):
    @bp.arguments(SearchNotificationArgsSchema, location='query')
    @bp.response(200, NotificationRespSchema(many=True))
    def get(self, args):
        return [], 200

