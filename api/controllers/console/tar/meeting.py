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
from services.meeting_service import MeetingService
from services.scene_service import SceneService


def _validate_name(name):
    if not name or len(name) < 1 or len(name) > 40:
        raise ValueError('Name must be between 1 to 40 characters.')
    return name


class MeetingApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=20, type=int)
        scenes, total = MeetingService.get_meetings(page, limit,
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
        parser.add_argument('id', type=str, required=False, location='json')
        parser.add_argument('scene_id', type=str, required=True, location='json')
        parser.add_argument('scene_name', type=str, required=True, location='json')
        parser.add_argument('description', type=str, required=False, location='json')
        parser.add_argument('conversations', type=str, required=True, location='json')
        parser.add_argument('type', type=str, required=True, location='json')
        parser.add_argument('start_time', type=str, required=True, location='json')
        parser.add_argument('end_time', type=str, required=True, location='json')
        args = parser.parse_args()

        # The role of the current user in the ta table must be admin or owner
        if not current_user.is_admin_or_owner:
            raise Forbidden()

        meeting = MeetingService.create_or_update_meeting(current_user.current_tenant_id, current_user, args,
                                                             current_user.current_app_id)

        return {}, 201


api.add_resource(MeetingApi, '/meeting')
