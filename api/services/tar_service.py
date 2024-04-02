import base64
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Optional

from flask import current_app
from flask_login import current_user
from sqlalchemy import func
from werkzeug.exceptions import Forbidden, NotFound

from constants.languages import language_timezone_mapping, languages
from constants.model_template import model_templates
from core.errors.error import ProviderTokenNotInitError
from core.model_manager import ModelManager
from core.model_runtime.entities.model_entities import ModelType
from events.app_event import app_was_created
from events.tenant_event import tenant_was_created
from extensions.ext_redis import redis_client
from libs.helper import get_remote_ip
from libs.passport import PassportService
from libs.password import compare_password, hash_password, valid_password
from libs.rsa import generate_key_pair
from models.account import *
from models.model import AppModelConfig, App, Site, ApiToken
from services.errors.account import (
    AccountAlreadyInTenantError,
    AccountLoginError,
    AccountNotLinkTenantError,
    AccountRegisterError,
    CannotOperateSelfError,
    CurrentPasswordIncorrectError,
    InvalidActionError,
    LinkAccountIntegrateError,
    MemberNotInTenantError,
    NoPermissionError,
    RoleAlreadyAssignedError,
    TenantNotFound,
)
from tasks.mail_invite_member_task import send_invite_member_mail_task


class TarService:

    @staticmethod
    def create_app(name: str, prompt: str, dataset_ids: list, mode: str) -> tuple[App, ApiToken]:
        model_config_template = model_templates[mode + '_default']

        app = App(**model_config_template['app'])
        app_model_config = AppModelConfig(**model_config_template['model_config'])

        # get model provider
        model_manager = ModelManager()
        try:
            model_instance = model_manager.get_default_model_instance(
                tenant_id=current_user.current_tenant_id,
                model_type=ModelType.LLM
            )
        except ProviderTokenNotInitError:
            model_instance = None

        if model_instance:
            model_dict = app_model_config.model_dict
            model_dict['provider'] = model_instance.provider
            model_dict['name'] = model_instance.model
            app_model_config.model = json.dumps(model_dict)

        # set datasets
        app_model_config.dataset_configs = json.dumps({
            'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                         dataset_ids],
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2,
        })
        # set prompts
        app_model_config.pre_prompt = prompt

        app.name = name
        app.mode = mode
        app.icon = "🤖"
        app.icon_background = "#FFEAD5"
        app.tenant_id = current_user.current_tenant_id

        db.session.add(app)
        db.session.flush()

        app_model_config.app_id = app.id
        db.session.add(app_model_config)
        db.session.flush()

        app.app_model_config_id = app_model_config.id

        site = Site(
            app_id=app.id,
            title=app.name,
            default_language=current_user.interface_language,
            customize_token_strategy='not_allow',
            code=Site.generate_code(16)
        )

        db.session.add(site)
        db.session.commit()

        app_was_created.send(app)

        key = ApiToken.generate_api_key('app-', 24)
        api_token = ApiToken()
        setattr(api_token, 'app_id', app.id)
        api_token.tenant_id = current_user.current_tenant_id
        api_token.token = key
        api_token.type = 'app'
        db.session.add(api_token)
        db.session.commit()

        return app, api_token

    @staticmethod
    def update_app(app_id: str, name: str, prompt: str, dataset_ids: list):
        app: App = db.session.query(App).filter(
            App.id == app_id
        ).first()
        if app is None:
            raise NotFound('App not found')
        app.name = name

        original_app_model_config: AppModelConfig = db.session.query(AppModelConfig).filter(
            AppModelConfig.id == app.app_model_config_id
        ).first()
        if original_app_model_config is None:
            raise NotFound('app_model_config not found')
        original_app_model_config.dataset_configs = json.dumps({
            'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                         dataset_ids],
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2,
        })
        original_app_model_config.pre_prompt = prompt

        db.session.commit()
