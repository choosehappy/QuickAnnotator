from flask_restx import Namespace, Resource, fields

api_ns_project = Namespace('project', description='Project related operations')

# ------------------------ MODELS ------------------------
project_model = api_ns_project.model('Project', {
    'id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'date': fields.DateTime(),
})
# ------------------------ REQUEST PARSERS ------------------------
get_project_parser = api_ns_project.parser()
get_project_parser.add_argument('project_id', location='args', type=int, required=True)

post_project_parser = api_ns_project.parser()
post_project_parser.add_argument('name', location='args', type=str, required=True)
post_project_parser.add_argument('is_dataset_large', location='args', type=bool, required=True)
post_project_parser.add_argument('description', location='args', type=str, required=True)

put_project_parser = post_project_parser.copy()
put_project_parser.add_argument('project_id', location='args', type=int, required=True)

delete_project_parser = api_ns_project.parser()
delete_project_parser.add_argument('project_id', location='args', type=int, required=True)

# ------------------------ ROUTES ------------------------
@api_ns_project.route('/')
class Project(Resource):
    @api_ns_project.expect(get_project_parser)
    @api_ns_project.marshal_with(project_model)
    def get(self):
        """     returns a Project

        """

        return 200

    @api_ns_project.expect(post_project_parser)
    @api_ns_project.response(200, 'Project created')
    def post(self):
        """     create a new Project
        """
        return 200


    @api_ns_project.expect(put_project_parser)
    @api_ns_project.response(201, 'Project updated')
    def put(self):
        """     update a Project

        """

        return 201

    @api_ns_project.expect(delete_project_parser)
    @api_ns_project.response(204, 'Project deleted')
    def delete(self):
        """     delete a Project

        """

        return 204

@api_ns_project.route('/all')
class SearchProject(Resource):
    """     get all Projects

    """
    @api_ns_project.marshal_with(project_model, as_list=True)
    def get(self):

        return [{}]