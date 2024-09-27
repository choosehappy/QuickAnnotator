from flask_restx import Namespace, Resource

api_ns_project = Namespace('project', description='Project related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
get_project_parser = api_ns_project.parser()
get_project_parser.add_argument('project_id', location='args', type=int, required=False)

put_project_parser = api_ns_project.parser()
put_project_parser.add_argument('name', location='args', type=str, required=False)

delete_project_parser = api_ns_project.parser()
delete_project_parser.add_argument('project_id', location='args', type=int, required=True)

# ------------------------ ROUTES ------------------------
@api_ns_project.route('/')
class Project(Resource):
    @api_ns_project.expect(get_project_parser)
    def get(self):
        """     returns a Project or list of Projects

        """

        return 200

    @api_ns_project.expect(put_project_parser)
    def put(self):
        """     create or update a Project

        """

        return 201

    @api_ns_project.expect(delete_project_parser)
    def delete(self):
        """     delete a Project

        """

        return 204