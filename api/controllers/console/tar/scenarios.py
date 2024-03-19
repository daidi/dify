from flask import request
from flask_login import current_user
from flask_restful import Resource, reqparse, marshal
from werkzeug.exceptions import Forbidden

import services.errors.scene
from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.tar.error import SceneNameDuplicateError
from controllers.console.wraps import account_initialization_required
from fields.app_fields import scene_fields
from libs.login import login_required
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
        provider = request.args.get('provider', default="vendor")
        scenes, total = SceneService.get_scenes(page, limit,
                                                current_user.current_tenant_id, current_user)

        response = {
            'data': scenes,
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
        parser.add_argument('user_tools', type=str, required=False, choices=tools, location='json', action='append')

        parser.add_argument('name', type=str, required=True, location='json')
        parser.add_argument('description', type=str, required=True, location='json')
        parser.add_argument('language', type=str, required=True, location='json')
        parser.add_argument('dataset_ids', type=str, required=True, location='json', action='append')
        parser.add_argument('interact_role', type=str, required=True, location='json')
        parser.add_argument('interact_goal', type=str, required=True, location='json')
        parser.add_argument('interact_tools', type=str, required=True, location='json', action='append')
        parser.add_argument('user_tools', type=str, required=True, location='json', action='append')
        parser.add_argument('interact_nums', type=int, required=True, location='json')
        parser.add_argument('user_role', type=str, required=True, location='json')
        parser.add_argument('user_goal', type=str, required=True, location='json')
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

        try:
            scene = SceneService.create_scene(
                tenant_id=current_user.current_tenant_id,
                account=current_user,
                args=args,
            )
        except services.errors.scene.SceneNameDuplicateError:
            raise SceneNameDuplicateError()

        return scene, 201


api.add_resource(ScenariosApi, '/scenarios')
