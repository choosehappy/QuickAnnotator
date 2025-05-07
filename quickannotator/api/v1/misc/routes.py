from flask_smorest import Blueprint
from flask.views import MethodView
from quickannotator.db import Base
from eralchemy import render_er
from flask import send_file
import tempfile

bp = Blueprint('misc', __name__, description='Miscellaneous operations')

@bp.route('/erd')
class ERD(MethodView):
    def get(self):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp_file:
            tmp_filepath = tmp_file.name
            # Generate the ER diagram using eralchemy
            render_er(Base.metadata, tmp_filepath)

        return send_file(tmp_filepath, mimetype='image/png')
