from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
import ray
from flask import current_app

bp = Blueprint('ray', __name__, description="Ray cluster operations")

