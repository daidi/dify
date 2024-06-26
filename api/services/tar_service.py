import logging

from flask_login import current_user
from werkzeug.exceptions import Forbidden, BadRequest

from constants.model_template import default_app_templates
from controllers.console.app.error import AppNotFoundError
from controllers.console.app.model_config import modify_app_model_config
from models.account import *
from models.model import App, ApiToken, AppMode
from services.app_service import AppService
from services.tag_service import TagService


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
        if not app_model:
            raise BadRequest("basemodel error ,contact admin for more info")

        app_model_config = {}
        app_model_config["dataset_configs"] = json.dumps({
            'datasets': {'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                                      dataset_ids]
                         },
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2,
        })
        # set prompts
        app_model_config["pre_prompt"] = prompt
        app_model_config["retriever_resource"] = json.dumps({
            'enabled': True
        })

        args['data'] = app_service.export_app_with_config(app_model, app_model_config)

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

        TagService.save_tag_binding({
            'tag_ids': ["12586740-2e21-4254-a7e6-015add650657"],
            'target_id': app.id,
            'type': 'app'
        })

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
        # app_mode = AppMode.value_of(app_model.mode)
        # app_template = default_app_templates[app_mode]
        # default_model_config = app_template.get('model_config')
        default_model_config = app_model.app_model_config.to_dict()
        logging.info(default_model_config)
        # default_model_config = default_model_config.copy() if default_model_config else None
        default_model_config["dataset_configs"] = {
            'datasets': {'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                                      dataset_ids],
                         },
            'reranking_model': {},
            'retrieval_model': 'single',
            'score_threshold': 0.5,
            'top_k': 2
        }
        default_model_config["pre_prompt"] = prompt
        default_model_config["retriever_resource"] = {
            'enabled': True
        }

        modify_app_model_config(app_model, default_model_config)

        TagService.save_tag_binding({
            'tag_ids': ["12586740-2e21-4254-a7e6-015add650657"],
            'target_id': app_id,
            'type': 'app'
        })
