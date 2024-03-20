import json
import logging

from flask import request
from flask_login import current_user
from flask_restful import Resource, reqparse, marshal
from werkzeug.exceptions import Forbidden

import services.errors.scene
from constants.model_template import model_templates
from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.tar.error import SceneNameDuplicateError
from controllers.console.wraps import account_initialization_required
from core.errors.error import ProviderTokenNotInitError, LLMBadRequestError
from core.model_manager import ModelManager
from core.model_runtime.entities.model_entities import ModelType
from core.provider_manager import ProviderManager
from events.app_event import app_was_created
from extensions.ext_database import db
from fields.app_fields import scene_fields
from libs.login import login_required
from models.model import App, AppModelConfig, Site, ApiToken
from models.scenarios import Scenarios
from services.scene_service import SceneService


def _validate_name(name):
    if not name or len(name) < 1 or len(name) > 40:
        raise ValueError('Name must be between 1 to 40 characters.')
    return name


class ScenariosApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=20, type=int)
        scenes, total = SceneService.get_scenes(page, limit,
                                                current_user.current_tenant_id, current_user)

        data = marshal(scenes, scene_fields)
        response = {
            'data': data,
            'has_more': len(scenes) == limit,
            'limit': limit,
            'total': total,
            'page': page
        }
        return response, 200

    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        parser = reqparse.RequestParser()
        # const formItem = ref<sceneData>({
        #     name: '',
        #     description: '',
        #     language: '',
        #     dataset_ids: [],
        #     interact_role: '',
        #     interact_goal: '',
        #     interact_tools: [],
        #     interact_nums: 1,
        #     user_role: '',
        #     user_goal: '',
        #     user_tools: []
        # })

        tools = ['clipboard', 'hotkey', 'ocr', 'voice', 'mic']  # 可选的工具列表

        parser.add_argument('interact_tools', type=str, required=False, choices=tools, location='json', action='append')
        parser.add_argument('user_tools', type=str, required=False, choices=tools, location='json', action='append',
                            default=[])

        parser.add_argument('id', type=str, required=False, location='json')
        parser.add_argument('name', type=str, required=True, location='json')
        parser.add_argument('description', type=str, required=True, location='json')
        parser.add_argument('language', type=str, required=True, location='json')
        parser.add_argument('dataset_ids', type=str, required=False, location='json', action='append', default=[])
        parser.add_argument('interact_role', type=str, required=True, location='json')
        parser.add_argument('interact_goal', type=str, required=True, location='json')
        parser.add_argument('interact_nums', type=int, required=True, location='json')
        parser.add_argument('user_role', type=str, required=True, location='json')
        parser.add_argument('user_goal', type=str, required=True, location='json')
        parser.add_argument('id', type=str, required=False, location='json')
        args = parser.parse_args()

        # 提取工具列表
        interact_tools = args.get('interact_tools', [])
        user_tools = args.get('user_tools', [])

        # 检测是否存在重复工具
        overlap = set(interact_tools) & set(user_tools)

        # 如果存在重复工具，返回400错误并提示
        if overlap:
            return 'The same tool cannot be in both interact_tools and user_tools: {}'.format(', '.join(overlap)), 400

        # The role of the current user in the ta table must be admin or owner
        if not current_user.is_admin_or_owner:
            raise Forbidden()

        # 创建app
        if args.get('id'):
            scene = SceneService.update_scene(args['id'], args, current_user)
            original_app_model_config: AppModelConfig = db.session.query(AppModelConfig).filter(
                AppModelConfig.id == scene.app_id
            ).first()
            original_app_model_config.dataset_configs = {
                'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                             args['dataset_ids']],
                'reranking_model': {},
                'retrieval_model': 'single',
                'score_threshold': 0.5,
                'top_k': 2,
            }
            original_app_model_config.pre_prompt = f"模拟{args['description']}场景，其中你扮演一名{args['user_role']}，你的目标是{args['user_goal']}。{args['interact_role']}（由我扮演）会提出问题，目标是{args['interact_goal']}。请根据这个场景回答我的问题。"
            db.session.commit()

        else:
            model_config_template = model_templates['chat_default']

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
            app_model_config.dataset_configs = {
                'datasets': [{"dataset": {"enabled": True, "id": id}} for id in
                             args['dataset_ids']],
                'reranking_model': {},
                'retrieval_model': 'single',
                'score_threshold': 0.5,
                'top_k': 2,
            }
            # set prompts
            app_model_config.pre_prompt = f"模拟{args['description']}场景，其中你扮演一名{args['user_role']}，你的目标是{args['user_goal']}。{args['interact_role']}（由我扮演）会提出问题，目标是{args['interact_goal']}。请根据这个场景回答我的问题。"

            app.name = '[auto]' + args['name']
            app.mode = 'chat'
            app.icon = "🤖"
            app.icon_background = "#FFEAD5"
            app.tenant_id = current_user.current_tenant_id

            db.session.add(app)
            db.session.flush()

            app_model_config.app_id = app.id
            db.session.add(app_model_config)
            db.session.flush()

            app.app_model_config_id = app_model_config.id

            account = current_user

            site = Site(
                app_id=app.id,
                title=app.name,
                default_language=account.interface_language,
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

            # check if scene name already exists
            if Scenarios.query.filter_by(name=args['name'], tenant_id=current_user.current_tenant_id).first():
                raise SceneNameDuplicateError(f'Dataset with name {args["name"]} already exists.')
            scene = Scenarios(**args)
            scene.app_id = app.id
            scene.app_key = key
            scene.created_by = account.id
            scene.updated_by = account.id
            scene.tenant_id = current_user.current_tenant_id
            db.session.add(scene)
            db.session.commit()

        return {}, 201


api.add_resource(ScenariosApi, '/scenarios')
