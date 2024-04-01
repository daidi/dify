from flask import request
from flask_login import current_user
from flask_restful import Resource, reqparse, marshal
from werkzeug.exceptions import Forbidden

from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required
from core.file.upload_file_parser import UploadFileParser
from fields.app_fields import meeting_fields
from libs.login import login_required
from services.meeting_service import MeetingService


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
        meetings, total = MeetingService.get_meetings(page, limit,
                                                      current_user.current_tenant_id, current_user)
        for meeting in meetings:
            if 'audio_file' in meeting and meeting['audio_file']:
                meeting['audio_file'] = UploadFileParser.get_signed_temp_image_url({'id': meeting['audio_file']})
        data = marshal(meetings, meeting_fields)
        response = {
            'data': data,
            'has_more': len(meetings) == limit,
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
        parser.add_argument('scene_id', type=str, required=False, location='json')
        parser.add_argument('scene_name', type=str, required=False, location='json')
        parser.add_argument('conversations', type=str, required=False, location='json')
        parser.add_argument('status', type=str, required=False, location='json')
        parser.add_argument('type', type=str, required=False, location='json')
        parser.add_argument('audio_file', type=str, required=False, location='json')
        args = parser.parse_args()

        # The role of the current user in the ta table must be admin or owner
        if not current_user.is_admin_or_owner:
            raise Forbidden()

        meeting = MeetingService.create_or_update_meeting(current_user.current_tenant_id, current_user, args)

        return marshal(meeting, meeting_fields), 201


api.add_resource(MeetingApi, '/meeting')
