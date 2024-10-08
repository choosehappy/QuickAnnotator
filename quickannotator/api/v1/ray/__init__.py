from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView

bp = Blueprint('ray', __name__, description="Ray cluster operations")

@bp.route('/')
class Ray(MethodView):
    def get(self):
        """
        Get the state of the ray cluster.
        """
        pass

@bp.route('/obj/<string:object_ref>')
class ObjectRef(MethodView):
    def get(self, object_ref):
        """
        Get the state of an object using an object ref.
        """
        pass
