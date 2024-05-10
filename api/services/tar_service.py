import base64
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Optional, cast

from flask import current_app
from flask_login import current_user
from sqlalchemy import func
from werkzeug.exceptions import Forbidden, NotFound, BadRequest

from constants.languages import language_timezone_mapping, languages
from constants.model_template import default_app_templates
from controllers.console.app.error import AppNotFoundError
from controllers.console.app.model_config import modify_app_model_config
from core.errors.error import ProviderTokenNotInitError, LLMBadRequestError
from core.model_manager import ModelManager
from core.model_runtime.entities.model_entities import ModelType, ModelPropertyKey
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from events.app_event import app_was_created
from events.tenant_event import tenant_was_created
from extensions.ext_redis import redis_client
from libs.helper import get_remote_ip
from libs.passport import PassportService
from libs.password import compare_password, hash_password, valid_password
from libs.rsa import generate_key_pair
from models.account import *
from models.model import AppModelConfig, App, Site, ApiToken, AppMode
from services.app_model_config_service import AppModelConfigService
from services.app_service import AppService
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
        args = {
            'name': name,
            'description': '自动创建应用，请勿修改',
            'mode': mode,  # 需要在 ALLOW_CREATE_APP_MODES 中的一个
            'icon': "🤖",
            'icon_background': "#FFEAD5",
            'data': ''
        }

        if not current_user.is_admin_or_owner:
            raise Forbidden()
        app_service = AppService()

        # get app detail
        app_model = db.session.query(App).filter(App.id == "a67aedae-91d4-45de-8372-63af6671710d").first()
        if not app_model or not app_model.is_public:
            raise BadRequest("basemodel error ,contact admin for more info")

        app_model.dataset_configs = json.dumps({
            'datasets': {'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                                      dataset_ids]
                         },
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2,
        })
        # set prompts
        app_model.pre_prompt = prompt
        app_model.retriever_resource = json.dumps({
            'enabled': True
        })

        args['data'] = app_service.export_app(app_model)

        # app = app_service.create_app(current_user.current_tenant_id, args, current_user)
        app = app_service.import_app(current_user.current_tenant_id, args['data'], args, current_user)

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
        # 更新基础信息
        args = {
            'name': name,
            'description': '自动创建应用，请勿修改',
            'icon': "🤖",
            'icon_background': "#FFEAD5",
        }

        app_model = db.session.query(App).filter(
            App.id == app_id,
            App.tenant_id == current_user.current_tenant_id,
            App.status == 'normal'
        ).first()

        if not app_model:
            raise AppNotFoundError()

        app_mode = AppMode.value_of(app_model.mode)
        if app_mode == AppMode.CHANNEL:
            raise AppNotFoundError()

        app_service = AppService()
        app_model = app_service.update_app(app_model, args)

        # 更新模型配置
        app_mode = AppMode.value_of(app_model.mode)
        app_template = default_app_templates[app_mode]
        default_model_config = app_template.get('model_config')
        default_model_config = default_model_config.copy() if default_model_config else None
        default_model_config.dataset_configs = json.dumps({
            'datasets': {'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                                      dataset_ids],
                         },
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2
        })
        default_model_config.pre_prompt = prompt
        default_model_config.retriever_resource = json.dumps({
            'enabled': True
        })

        modify_app_model_config(app_model, default_model_config)
