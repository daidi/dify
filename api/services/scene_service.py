import datetime
import logging

from extensions.ext_database import db
from models.account import Account
from models.scenarios import Scenarios
from services.errors.account import NoPermissionError
from services.errors.scene import SceneNameDuplicateError


class SceneService:

    @staticmethod
    def get_scenes(page, per_page, tenant_id=None, user=None):
        if user:
            permission_filter = db.or_(Scenarios.created_by == user.id,
                                       Scenarios.permission == 'all_team_members')
        else:
            permission_filter = Scenarios.permission == 'all_team_members'
        scenes = Scenarios.query.filter(
            db.and_(Scenarios.tenant_id == tenant_id, permission_filter)) \
            .order_by(Scenarios.created_at.desc()) \
            .paginate(
            page=page,
            per_page=per_page,
            max_per_page=100,
            error_out=False
        )

        return scenes.items, scenes.total

    @staticmethod
    def get_scene(scene_id):
        scene = SceneService.query.filter_by(
            id=scene_id
        ).first()
        if scene is None:
            return None
        else:
            return scene

    @staticmethod
    def create_scene(tenant_id: str, account: Account, args: dict):
        # check if dataset name already exists
        if Scenarios.query.filter_by(name=args['name'], tenant_id=args['tenant_id']).first():
            raise SceneNameDuplicateError(f'Dataset with name {args["name"]} already exists.')
        scene = Scenarios(**args)
        scene.created_by = args['account'].id
        scene.updated_by = args['account'].id
        scene.tenant_id = args['tenant_id']
        db.session.add(scene)
        db.session.commit()
        return scene

    @staticmethod
    def update_scene(scene_id, data, user):
        filtered_data = {k: v for k, v in data.items() if v is not None or k == 'description'}
        scene = SceneService.get_scene(scene_id)
        SceneService.check_scene_permission(scene, user)

        filtered_data['updated_by'] = user.id
        filtered_data['updated_at'] = datetime.datetime.now()

        scene.query.filter_by(id=scene_id).update(filtered_data)

        db.session.commit()
        return scene

    @staticmethod
    def delete_scene(scene_id, user):
        # todo: cannot delete scene if it is being processed

        scene = SceneService.get_scene(scene_id)

        if scene is None:
            return False

        SceneService.check_scene_permission(scene, user)

        db.session.delete(scene)
        db.session.commit()
        return True

    @staticmethod
    def check_scene_permission(scene, user):
        if scene.tenant_id != user.current_tenant_id:
            logging.debug(
                f'User {user.id} does not have permission to access scene {scene.id}')
            raise NoPermissionError(
                'You do not have permission to access this scene.')
        if scene.permission == 'only_me' and scene.created_by != user.id:
            logging.debug(
                f'User {user.id} does not have permission to access scene {scene.id}')
            raise NoPermissionError(
                'You do not have permission to access this scene.')
