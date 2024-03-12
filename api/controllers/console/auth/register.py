import flask_login
from flask import current_app, request
from flask_restful import Resource, reqparse

import services
from constants.languages import supported_language
from controllers.console import api
from controllers.console.setup import setup_required
from libs.helper import email, str_len, timezone
from libs.password import valid_password
from services.account_service import AccountService, TenantService


class RegisterApi(Resource):
    """Resource for user login."""

    @setup_required
    def post(self):
        """Authenticate user and login."""
        parser = reqparse.RequestParser()
        parser.add_argument('workspace_id', type=str, required=False, nullable=True, location='json')
        parser.add_argument('email', type=email, required=False, nullable=True, location='json')
        parser.add_argument('name', type=str_len(30), required=True, nullable=False, location='json')
        parser.add_argument('password', type=valid_password, required=True, nullable=False, location='json')
        parser.add_argument('interface_language', type=supported_language, required=True, nullable=False,
                            location='json')
        parser.add_argument('timezone', type=timezone, required=True, nullable=False, location='json')
        args = parser.parse_args()

        # todo: Verify the recaptcha

        try:
            account = AccountService.authenticate(args['email'], args['password'])
        except services.errors.account.AccountLoginError:
            return {'code': 'unauthorized', 'message': 'Invalid email or password'}, 401

        TenantService.create_owner_tenant_if_not_exist(account)

        AccountService.update_last_login(account, request)

        # todo: return the user info
        token = AccountService.get_account_jwt_token(account)

        return {'result': 'success', 'data': token}


api.add_resource(RegisterApi, '/register')
