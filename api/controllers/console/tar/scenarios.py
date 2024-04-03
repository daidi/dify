import json
import logging

from flask import request
from flask_login import current_user
from flask_restful import Resource, reqparse, marshal
from werkzeug.exceptions import Forbidden, NotFound

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
from services.tar_service import TarService


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

        tools = ['clipboard', 'hotkey', 'ocr', 'voice', 'mic', 'input']  # 可选的工具列表

        parser.add_argument('interact_tools', type=str, required=False, choices=tools, location='json', action='append',
                            default=[])
        parser.add_argument('user_tools', type=str, required=False, choices=tools, location='json', action='append',
                            default=[])

        parser.add_argument('id', type=str, required=False, location='json')
        parser.add_argument('name', type=str, required=True, location='json')
        parser.add_argument('description', type=str, required=True, location='json')
        parser.add_argument('language', type=str, required=True, location='json')
        parser.add_argument('dataset_ids', type=list, required=False, location='json', action='append', default=[])
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

        print(f"interact_tools:{interact_tools};user_tools:{user_tools}")

        # 检测是否存在重复工具
        overlap = set(interact_tools) & set(user_tools)

        # 如果存在重复工具，返回400错误并提示
        if overlap:
            return 'The same tool cannot be in both interact_tools and user_tools: {}'.format(', '.join(overlap)), 400

        # The role of the current user in the ta table must be admin or owner
        if not current_user.is_admin_or_owner:
            raise Forbidden()

        copilot_prompt = f"模拟{args['description']}场景，其中你扮演一名{args['user_role']}，你的目标是{args['user_goal']}。{args['interact_role']}（由我扮演）会提出问题，目标是{args['interact_goal']}。请根据这个场景回答我的问题。"
        mock_prompt = f"模拟{args['description']}场景，其中我扮演一名{args['user_role']}，我的目标是{args['user_goal']}。{args['interact_role']}（由你扮演）会提出问题，目标是{args['interact_goal']}。请根据这个场景回答我的问题。"
        summary_prompt = "下面是一段对话，请总结这段对话：\n{{query}}"

        # 创建app
        if args.get('id'):
            scene = SceneService.update_scene(args['id'], args, current_user)
            TarService.update_app(scene.copilot_id, '[auto]' + args['name'], copilot_prompt, args['dataset_ids'])
            TarService.update_app(scene.mock_id, '[auto]' + args['name'], mock_prompt, args['dataset_ids'])
            TarService.update_app(scene.summary_id, '[auto]' + args['name'], summary_prompt, args['dataset_ids'])

        else:
            app_1, api_token_1 = TarService.create_app('[copilot]' + args['name'], copilot_prompt, args['dataset_ids'],
                                                       'chat')
            app_2, api_token_2 = TarService.create_app('[mock]' + args['name'], mock_prompt, args['dataset_ids'],
                                                       'chat')
            app_3, api_token_3 = TarService.create_app('[summary]' + args['name'], summary_prompt, args['dataset_ids'],
                                                       'completion')

            # check if scene name already exists
            if Scenarios.query.filter_by(name=args['name'], tenant_id=current_user.current_tenant_id).first():
                raise SceneNameDuplicateError(f'Dataset with name {args["name"]} already exists.')
            scene = Scenarios(**args)
            scene.copilot_id = app_1.id
            scene.copilot_key = api_token_1.token
            scene.mock_id = app_2.id
            scene.mock_key = api_token_2.token
            scene.summary_id = app_3.id
            scene.summary_key = api_token_3.token
            scene.created_by = current_user.id
            scene.updated_by = current_user.id
            scene.tenant_id = current_user.current_tenant_id
            scene.id = None
            db.session.add(scene)
            db.session.commit()

        return {}, 201


api.add_resource(ScenariosApi, '/scenarios')
