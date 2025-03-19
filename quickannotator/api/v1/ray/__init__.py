from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
import ray

bp = Blueprint('ray', __name__, description="Ray cluster operations")

@bp.route('/<int:project_id>/<int:annotation_class_id>/startproc')
class DLActor(MethodView):
    @bp.response(200, description="DLActor created")
    def post(self):
        """     trigger the DLActor for the current project and annotation class to start processing    """


        
        return {"message":"DLActor created"}, 200