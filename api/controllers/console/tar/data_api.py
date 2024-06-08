from flask_restful import Resource, reqparse
from flask_login import current_user
from flask_restful.inputs import int_range

from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required
from libs.login import login_required
from services.data_api_service import DataAPIService


class DataAPIController(Resource):

    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        tenant_id = current_user.current_tenant_id

        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int_range(1, 99999), default=1, location='args')
        parser.add_argument('limit', type=int_range(1, 100), default=20, location='args')
        parser.add_argument('name', type=str, location='args')
        parser.add_argument('price_min', type=int, default=0, location='args')
        parser.add_argument('price_max', type=int, location='args')
        parser.add_argument('authorization_method', type=str, choices=['auto', 'manual', 'all'], default='all',
                            location='args')
        parser.add_argument('status', type=str, choices=['pending', 'approved', 'rejected', 'not_applied', 'all'],
                            default='all', location='args')

        args = parser.parse_args()

        try:
            result = DataAPIService.get_all_apis(
                tenant_id=tenant_id,
                page=args['page'],
                limit=args['limit'],
                name=args['name'],
                price_min=args['price_min'],
                price_max=args['price_max'],
                authorization_method=args['authorization_method'],
                status=args['status']
            )
            return {'result': 'success', 'data': result}, 200
        except Exception as e:
            return {'result': 'fail', 'error': str(e)}, 200

    @login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('api_id', type=str, required=True, location='json')
        args = parser.parse_args()

        tenant_id = current_user.current_tenant_id
        api_id = args['api_id']

        try:
            application = DataAPIService.apply_for_api(tenant_id, api_id)
            return {'result': 'success', 'status': application.status}, 200
        except Exception as e:
            return {'result': 'fail', 'error': str(e)}, 200


class DataAPICallController(Resource):

    @login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('api_id', type=str, required=True, location='json')
        args = parser.parse_args()

        tenant_id = current_user.current_tenant_id
        api_id = args['api_id']

        try:
            call = DataAPIService.call_api(tenant_id, api_id)
            return {'result': 'success', 'call_id': call.id}, 200
        except Exception as e:
            return {'result': 'fail', 'error': str(e)}, 200


api.add_resource(DataAPIController, '/data/apis')
api.add_resource(DataAPICallController, '/data/apis/call')
