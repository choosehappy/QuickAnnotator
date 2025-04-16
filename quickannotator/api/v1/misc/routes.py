from flask_smorest import Blueprint
from flask.views import MethodView
from quickannotator.db import Base
from eralchemy import render_er
from flask import send_file

bp = Blueprint('misc', __name__, description='Miscellaneous operations')

@bp.route('/erd')
class ERD(MethodView):
    def get(self):
        tmp_filepath = '/tmp/erd.png'
        # Generate the ER diagram using eralchemy
        # NOTE: Unfortunately eralchemy does not support in-memory rendering e.g., streams
        render_er(Base.metadata, tmp_filepath)  

        return send_file(tmp_filepath, mimetype='image/png')
