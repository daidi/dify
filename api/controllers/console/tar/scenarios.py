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
        parser.add_argument('name', nullable=False, required=True,
                            help='type is required. Name must be between 1 to 40 characters.',
                            type=_validate_name)
        args = parser.parse_args()

        # The role of the current user in the ta table must be admin or owner
        if not current_user.is_admin_or_owner:
            raise Forbidden()

        try:
            dataset = SceneService.create_scene(
                tenant_id=current_user.current_tenant_id,
                name=args['name'],
                account=current_user
            )
        except services.errors.scene.SceneNameDuplicateError:
            raise SceneNameDuplicateError()

        return marshal(dataset, scene_fields), 201


api.add_resource(ScenariosApi, '/tar/scenes')
