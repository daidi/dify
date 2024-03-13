import flask_login
from flask import current_app, request
from flask_restful import Resource, reqparse

import services
from constants.languages import supported_language, languages
from controllers.console import api
from controllers.console.setup import setup_required
from extensions.ext_database import db
from libs.helper import email, str_len, timezone
from libs.password import valid_password
from services.account_service import AccountService, TenantService, RegisterService


class RegisterApi(Resource):
    """Resource for user register."""

    @setup_required
    def post(self):
        """Authenticate user and login."""
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=email, required=False, nullable=True, location='json')
        parser.add_argument('name', type=str_len(30), required=True, nullable=False, location='json')
        parser.add_argument('password', type=valid_password, required=True, nullable=False, location='json')
        args = parser.parse_args()

        try:
            account = RegisterService.register(
                email=args['email'],
                name=args['name'],
                password=args['password'],
                open_id=None,
                provider=None
            )
        except Exception as e:
            return {'code': 'register_fail', 'message': str(e)}, 400

        # Set interface language
        preferred_lang = request.accept_languages.best_match(languages)
        if preferred_lang and preferred_lang in languages:
            interface_language = preferred_lang
        else:
            interface_language = languages[0]
        account.interface_language = interface_language
        db.session.commit()

        TenantService.create_owner_tenant_if_not_exist(account)

        return {'result': 'success', 'data': {}}


api.add_resource(RegisterApi, '/register')
