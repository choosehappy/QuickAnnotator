from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import fields, Schema
import shapely

import quickannotator.db as qadb

bp = Blueprint('misc', __name__, description='Miscellaneous operations')