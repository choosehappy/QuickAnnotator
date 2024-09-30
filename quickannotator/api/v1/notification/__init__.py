from flask_restx import Namespace, Resource

api_ns_notification = Namespace('notification', description='Notification related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
get_notification_parser = api_ns_notification.parser()
get_notification_parser.add_argument('project_id', location='args', type=int, required=True)
get_notification_parser.add_argument('image_id', location='args', type=int, required=True)
get_notification_parser.add_argument('notification_id', location='args', type=int, required=False)
# ------------------------ ROUTES ------------------------

@api_ns_notification.route('/')
class Notification(Resource):
    def get(self):
        """     returns a Notification

        """

        return 200

    def put(self):
        """     update a Notification

        """

        return 201
