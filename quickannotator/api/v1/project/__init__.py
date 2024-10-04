from flask_smorest import Blueprint, abort
from marshmallow import fields, Schema
from flask.views import MethodView
from quickannotator.db import db
import quickannotator.db as qadb

bp = Blueprint('project', __name__, description='Project operations')


# ------------------------ RESPONSE MODELS ------------------------
class ProjectRespSchema(Schema):
    """     Project response schema      """
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    date = fields.DateTime()

class GetProjectArgsSchema(Schema):
    project_id = fields.Int(required=True)
    
class PostProjectArgsSchema(Schema):
    name = fields.Str(required=True)
    is_dataset_large = fields.Bool(required=False)
    description = fields.Str(required=True)
    
class PutProjectArgsSchema(Schema):
    project_id = fields.Int(required=True)
    name = fields.Str(required=False)
    is_dataset_large = fields.Bool(required=False)
    description = fields.Str(required=False)
    
class DeleteProjectArgsSchema(GetProjectArgsSchema):
    pass

class SearchProjectArgsSchema(Schema):
    name = fields.Str(required=False)

# ------------------------ ROUTES ------------------------
@bp.route('/')
class Project(MethodView):
    @bp.arguments(GetProjectArgsSchema, location='query')
    @bp.response(200, ProjectRespSchema)
    def get(self, args):
        """     returns a Project
        """
        project_id = args['project_id']
        project = db.session.query(qadb.Project).filter(qadb.Project.id == project_id).first()
        if project is not None:
            return project
        else:
            abort(404, message="Project not found")

    @bp.arguments(PostProjectArgsSchema, location='json')
    @bp.response(200, description="Project created")
    def post(self, args):
        """     create a new Project
        """

        db.session.add(qadb.Project(name=args['name'], description=args['description'], is_dataset_large=args['is_dataset_large']))
        db.session.commit()
        return 200


    @bp.arguments(PutProjectArgsSchema, location='json')
    @bp.response(201, description="Project updated")
    def put(self, args):
        """     update a Project

        """

        return 201

    @bp.arguments(DeleteProjectArgsSchema, location='query')
    @bp.response(204, description="Project deleted")
    def delete(self, args):
        """     delete a Project

        """

        return 204

@bp.route('/all')
class SearchProject(MethodView):
    """     get all Projects

    """
    @bp.arguments(SearchProjectArgsSchema, location='query')
    @bp.response(200, ProjectRespSchema(many=True))
    def get(self, args):

        return [{}]