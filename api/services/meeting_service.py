import datetime
import json
import logging

from extensions.ext_database import db
from models.account import Account
from models.meeting import Meeting
from services.errors.account import NoPermissionError
from services.scene_service import SceneService


class MeetingService:

    @staticmethod
    def get_meetings(page, per_page, tenant_id=None, user=None):
        if user:
            permission_filter = db.or_(Meeting.created_by == user.id,
                                       Meeting.permission == 'all_team_members')
        else:
            permission_filter = Meeting.permission == 'all_team_members'
        meetings = Meeting.query.filter(
            db.and_(Meeting.tenant_id == tenant_id, permission_filter)) \
            .order_by(Meeting.start_time.desc()) \
            .paginate(
            page=page,
            per_page=per_page,
            max_per_page=100,
            error_out=False
        )

        return meetings.items, meetings.total

    @staticmethod
    def get_meeting(meeting_id):
        meeting = Meeting.query.filter_by(
            id=meeting_id
        ).first()
        if meeting is None:
            return None
        else:
            meeting.conversations = json.loads(meeting.conversations)
            return meeting

    @staticmethod
    def create_or_update_meeting(tenant_id: str, account: Account, args: dict):
        if args.get('id'):
            if args['status'] == 'arrange':
                args['end_time'] = datetime.datetime.utcnow()
            meeting = MeetingService.update_meeting(args['id'], args, account)
        else:
            meeting = Meeting(**args)
            meeting.created_by = account.id
            meeting.updated_by = account.id
            meeting.tenant_id = tenant_id
            meeting.updated_at = datetime.datetime.utcnow()
            scene = SceneService.get_scene(meeting.scene_id)

            now = datetime.datetime.now()
            formatted_date = now.strftime("%Y年%m月%d日")
            meeting.name = f"{formatted_date}{scene.user_role}的{scene.name}"  # 后续AI覆盖
            db.session.add(meeting)
            db.session.commit()
        return meeting

    @staticmethod
    def update_meeting(meeting_id, data, user):
        filtered_data = {k: v for k, v in data.items() if v is not None or k == 'description'}
        meeting = MeetingService.get_meeting(meeting_id)
        MeetingService.check_meeting_permission(meeting, user)

        filtered_data['updated_by'] = user.id
        filtered_data['updated_at'] = datetime.datetime.now()

        Meeting.query.filter_by(id=meeting_id).update(filtered_data)

        db.session.commit()
        return meeting

    @staticmethod
    def delete_meeting(meeting_id, user):
        # todo: cannot delete meeting if it is being processed

        meeting = MeetingService.get_meeting(meeting_id)

        if meeting is None:
            return False

        MeetingService.check_meeting_permission(meeting, user)

        db.session.delete(meeting)
        db.session.commit()
        return True

    @staticmethod
    def check_meeting_permission(meeting, user):
        if meeting.tenant_id != user.current_tenant_id:
            logging.debug(
                f'User {user.id} does not have permission to access meeting {meeting.id}')
            raise NoPermissionError(
                'You do not have permission to access this meeting.')
        if meeting.permission == 'only_me' and meeting.created_by != user.id:
            logging.debug(
                f'User {user.id} does not have permission to access meeting {meeting.id}')
            raise NoPermissionError(
                'You do not have permission to access this meeting.')
