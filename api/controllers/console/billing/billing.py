from flask_login import current_user
from flask_restful import Resource, reqparse

from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required, only_edition_cloud
from libs.login import login_required
from services.billing_service import BillingService
from services.subscription_service import SubscriptionService


class Subscription(Resource):

    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument('plan', type=str, required=True, location='args', choices=['professional', 'team'])
        parser.add_argument('interval', type=str, required=True, location='args', choices=['month', 'year'])
        args = parser.parse_args()

        BillingService.is_tenant_owner_or_admin(current_user)

        return BillingService.get_subscription(args['plan'],
                                               args['interval'],
                                               current_user.email,
                                               current_user.current_tenant_id)

    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def post(self):
        tenant_id = current_user.current_tenant_id

        parser = reqparse.RequestParser()
        parser.add_argument('plan', type=str, choices=['sandbox', 'professional', 'team'], location='json')
        parser.add_argument('interval', type=str, choices=['month', 'year'], location='json')
        parser.add_argument('payment_status', type=str, choices=['success', 'error'], location='json')

        args = parser.parse_args()

        plan = args['plan']
        interval = args['interval']
        payment_status = args['payment_status']

        if payment_status != 'success':
            return {'result': False, 'error': 'Invalid payment status'}, 400

        # 验证并更新订阅信息
        try:
            new_subscription = SubscriptionService.create_subscription(
                tenant_id=tenant_id,
                plan=plan,
                interval=interval,
            )
        except Exception as e:
            return {'result': 'fail', 'error': str(e)}, 500

        return {'result': 'success', 'message': 'Subscription updated successfully',
                'subscription_id': new_subscription.id}, 200


class Invoices(Resource):

    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def get(self):
        BillingService.is_tenant_owner_or_admin(current_user)
        return BillingService.get_invoices(current_user.email, current_user.current_tenant_id)


api.add_resource(Subscription, '/billing/subscription')
api.add_resource(Invoices, '/billing/invoices')
