import json
import logging
from datetime import datetime, timezone
from typing import cast

import yaml
from flask import current_app
from flask_login import current_user
from flask_sqlalchemy.pagination import Pagination

from constants.model_template import default_app_templates
from core.agent.entities import AgentToolEntity
from core.errors.error import LLMBadRequestError, ProviderTokenNotInitError
from core.model_manager import ModelManager
from core.model_runtime.entities.model_entities import ModelPropertyKey, ModelType
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.tools.tool_manager import ToolManager
from core.tools.utils.configuration import ToolParameterConfigurationManager
from events.app_event import app_model_config_was_updated, app_was_created, app_was_deleted
from extensions.ext_database import db
from models.account import Account
from models.model import App, AppMode, AppModelConfig
from models.tools import ApiToolProvider
from services.tag_service import TagService
from services.workflow_service import WorkflowService


class AppService:
    def get_paginate_apps(self, tenant_id: str, args: dict) -> Pagination | None:
        """
        Get app list with pagination
        :param tenant_id: tenant id
        :param args: request args
        :return:
        """
        filters = [
            App.tenant_id == tenant_id,
            App.is_universal == False
        ]

        if args['mode'] == 'workflow':
            filters.append(App.mode.in_([AppMode.WORKFLOW.value, AppMode.COMPLETION.value]))
        elif args['mode'] == 'chat':
            filters.append(App.mode.in_([AppMode.CHAT.value, AppMode.ADVANCED_CHAT.value]))
        elif args['mode'] == 'agent-chat':
            filters.append(App.mode == AppMode.AGENT_CHAT.value)
        elif args['mode'] == 'channel':
            filters.append(App.mode == AppMode.CHANNEL.value)

        if 'name' in args and args['name']:
            name = args['name'][:30]
            filters.append(App.name.ilike(f'%{name}%'))
        if 'tag_ids' in args and args['tag_ids']:
            target_ids = TagService.get_target_ids_by_tag_ids('app',
                                                              tenant_id,
                                                              args['tag_ids'])
            if target_ids:
                filters.append(App.id.in_(target_ids))
            else:
                return None

        app_models = db.paginate(
            db.select(App).where(*filters).order_by(App.created_at.desc()),
            page=args['page'],
            per_page=args['limit'],
            error_out=False
        )

        return app_models

    def create_app(self, tenant_id: str, args: dict, account: Account) -> App:
        """
        Create app
        :param tenant_id: tenant id
        :param args: request args
        :param account: Account instance
        """
        app_mode = AppMode.value_of(args['mode'])
        app_template = default_app_templates[app_mode]

        # get model config
        default_model_config = app_template.get('model_config')
        default_model_config = default_model_config.copy() if default_model_config else None
        if default_model_config and 'model' in default_model_config:
            # get model provider
            model_manager = ModelManager()

            # get default model instance
            try:
                model_instance = model_manager.get_default_model_instance(
                    tenant_id=account.current_tenant_id,
                    model_type=ModelType.LLM
                )
            except (ProviderTokenNotInitError, LLMBadRequestError):
                model_instance = None
            except Exception as e:
                logging.exception(e)
                model_instance = None

            if model_instance:
                if model_instance.model == default_model_config['model']['name']:
                    default_model_dict = default_model_config['model']
                else:
                    llm_model = cast(LargeLanguageModel, model_instance.model_type_instance)
                    model_schema = llm_model.get_model_schema(model_instance.model, model_instance.credentials)

                    default_model_dict = {
                        'provider': model_instance.provider,
                        'name': model_instance.model,
                        'mode': model_schema.model_properties.get(ModelPropertyKey.MODE),
                        'completion_params': {}
                    }
            else:
                default_model_dict = default_model_config['model']

            default_model_config['model'] = json.dumps(default_model_dict)

        app = App(**app_template['app'])
        app.name = args['name']
        app.description = args.get('description', '')
        app.mode = args['mode']
        app.icon = args['icon']
        app.icon_background = args['icon_background']
        app.tenant_id = tenant_id

        db.session.add(app)
        db.session.flush()

        if default_model_config:
            app_model_config = AppModelConfig(**default_model_config)
            app_model_config.app_id = app.id
            db.session.add(app_model_config)
            db.session.flush()

            app.app_model_config_id = app_model_config.id

        db.session.commit()

        app_was_created.send(app, account=account)

        return app

    def import_app(self, tenant_id: str, data: str, args: dict, account: Account) -> App:
        """
        Import app
        :param tenant_id: tenant id
        :param data: import data
        :param args: request args
        :param account: Account instance
        """
        try:
            import_data = yaml.safe_load(data)
        except yaml.YAMLError as e:
            raise ValueError("Invalid YAML format in data argument.")

        app_data = import_data.get('app')
        model_config_data = import_data.get('model_config')
        workflow = import_data.get('workflow')

        if not app_data:
            raise ValueError("Missing app in data argument")

        app_mode = AppMode.value_of(app_data.get('mode'))
        if app_mode in [AppMode.ADVANCED_CHAT, AppMode.WORKFLOW]:
            if not workflow:
                raise ValueError("Missing workflow in data argument "
                                 "when app mode is advanced-chat or workflow")
        elif app_mode in [AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.COMPLETION]:
            if not model_config_data:
                raise ValueError("Missing model_config in data argument "
                                 "when app mode is chat, agent-chat or completion")
        else:
            raise ValueError("Invalid app mode")

        app = App(
            tenant_id=tenant_id,
            mode=app_data.get('mode'),
            name=args.get("name") if args.get("name") else app_data.get('name'),
            description=args.get("description") if args.get("description") else app_data.get('description', ''),
            icon=args.get("icon") if args.get("icon") else app_data.get('icon'),
            icon_background=args.get("icon_background") if args.get("icon_background") \
                else app_data.get('icon_background'),
            enable_site=True,
            enable_api=True
        )

        db.session.add(app)
        db.session.commit()

        app_was_created.send(app, account=account)

        if workflow:
            # init draft workflow
            workflow_service = WorkflowService()
            draft_workflow = workflow_service.sync_draft_workflow(
                app_model=app,
                graph=workflow.get('graph'),
                features=workflow.get('features'),
                account=account
            )
            workflow_service.publish_workflow(
                app_model=app,
                account=account,
                draft_workflow=draft_workflow
            )

        if model_config_data:
            app_model_config = AppModelConfig()
            app_model_config = app_model_config.from_model_config_dict(model_config_data)
            app_model_config.app_id = app.id

            db.session.add(app_model_config)
            db.session.commit()

            app.app_model_config_id = app_model_config.id

            app_model_config_was_updated.send(
                app,
                app_model_config=app_model_config
            )

        return app

    def export_app(self, app: App) -> str:
        """
        Export app
        :param app: App instance
        :return:
        """
        app_mode = AppMode.value_of(app.mode)

        export_data = {
            "app": {
                "name": app.name,
                "mode": app.mode,
                "icon": app.icon,
                "icon_background": app.icon_background,
                "description": app.description
            }
        }

        if app_mode in [AppMode.ADVANCED_CHAT, AppMode.WORKFLOW]:
            workflow_service = WorkflowService()
            workflow = workflow_service.get_draft_workflow(app)
            export_data['workflow'] = {
                "graph": workflow.graph_dict,
                "features": workflow.features_dict
            }
        else:
            app_model_config = app.app_model_config

            export_data['model_config'] = app_model_config.to_dict()

        return yaml.dump(export_data)

    def export_app_with_config(self, app: App, model_config: dict) -> str:
        """
        Export app
        :param model_config:
        :param app: App instance
        :return:
        """
        app_mode = AppMode.value_of(app.mode)

        export_data = {
            "app": {
                "name": app.name,
                "mode": app.mode,
                "icon": app.icon,
                "icon_background": app.icon_background,
                "description": app.description
            }
        }

        if app_mode in [AppMode.ADVANCED_CHAT, AppMode.WORKFLOW]:
            workflow_service = WorkflowService()
            workflow = workflow_service.get_draft_workflow(app)
            export_data['workflow'] = {
                "graph": workflow.graph_dict,
                "features": workflow.features_dict
            }
        else:
            app_model_config = app.app_model_config
            app_model_config.update(model_config)
            export_data['model_config'] = app_model_config.to_dict()

        return yaml.dump(export_data)

    def get_app(self, app: App) -> App:
        """
        Get App
        """
        # get original app model config
        if app.mode == AppMode.AGENT_CHAT.value or app.is_agent:
            model_config: AppModelConfig = app.app_model_config
            agent_mode = model_config.agent_mode_dict
            # decrypt agent tool parameters if it's secret-input
            for tool in agent_mode.get('tools') or []:
                if not isinstance(tool, dict) or len(tool.keys()) <= 3:
                    continue
                agent_tool_entity = AgentToolEntity(**tool)
                # get tool
                try:
                    tool_runtime = ToolManager.get_agent_tool_runtime(
                        tenant_id=current_user.current_tenant_id,
                        app_id=app.id,
                        agent_tool=agent_tool_entity,
                    )
                    manager = ToolParameterConfigurationManager(
                        tenant_id=current_user.current_tenant_id,
                        tool_runtime=tool_runtime,
                        provider_name=agent_tool_entity.provider_id,
                        provider_type=agent_tool_entity.provider_type,
                        identity_id=f'AGENT.{app.id}'
                    )

                    # get decrypted parameters
                    if agent_tool_entity.tool_parameters:
                        parameters = manager.decrypt_tool_parameters(agent_tool_entity.tool_parameters or {})
                        masked_parameter = manager.mask_tool_parameters(parameters or {})
                    else:
                        masked_parameter = {}

                    # override tool parameters
                    tool['tool_parameters'] = masked_parameter
                except Exception as e:
                    pass

            # override agent mode
            model_config.agent_mode = json.dumps(agent_mode)

            class ModifiedApp(App):
                """
                Modified App class
                """

                def __init__(self, app):
                    self.__dict__.update(app.__dict__)

                @property
                def app_model_config(self):
                    return model_config

            app = ModifiedApp(app)

        return app

    def update_app(self, app: App, args: dict) -> App:
        """
        Update app
        :param app: App instance
        :param args: request args
        :return: App instance
        """
        app.name = args.get('name')
        app.description = args.get('description', '')
        app.icon = args.get('icon')
        app.icon_background = args.get('icon_background')
        app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_name(self, app: App, name: str) -> App:
        """
        Update app name
        :param app: App instance
        :param name: new name
        :return: App instance
        """
        app.name = name
        app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_icon(self, app: App, icon: str, icon_background: str) -> App:
        """
        Update app icon
        :param app: App instance
        :param icon: new icon
        :param icon_background: new icon_background
        :return: App instance
        """
        app.icon = icon
        app.icon_background = icon_background
        app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_site_status(self, app: App, enable_site: bool) -> App:
        """
        Update app site status
        :param app: App instance
        :param enable_site: enable site status
        :return: App instance
        """
        if enable_site == app.enable_site:
            return app

        app.enable_site = enable_site
        app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_api_status(self, app: App, enable_api: bool) -> App:
        """
        Update app api status
        :param app: App instance
        :param enable_api: enable api status
        :return: App instance
        """
        if enable_api == app.enable_api:
            return app

        app.enable_api = enable_api
        app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()

        return app

    def delete_app(self, app: App) -> None:
        """
        Delete app
        :param app: App instance
        """
        db.session.delete(app)
        db.session.commit()

        app_was_deleted.send(app)

        # todo async delete related data by event
        # app_model_configs, site, api_tokens, installed_apps, recommended_apps BY app
        # app_annotation_hit_histories, app_annotation_settings, app_dataset_joins BY app
        # workflows, workflow_runs, workflow_node_executions, workflow_app_logs BY app
        # conversations, pinned_conversations, messages BY app
        # message_feedbacks, message_annotations, message_chains BY message
        # message_agent_thoughts, message_files, saved_messages BY message

    def get_app_meta(self, app_model: App) -> dict:
        """
        Get app meta info
        :param app_model: app model
        :return:
        """
        app_mode = AppMode.value_of(app_model.mode)

        meta = {
            'tool_icons': {}
        }

        if app_mode in [AppMode.ADVANCED_CHAT, AppMode.WORKFLOW]:
            workflow = app_model.workflow
            if workflow is None:
                return meta

            graph = workflow.graph_dict
            nodes = graph.get('nodes', [])
            tools = []
            for node in nodes:
                if node.get('data', {}).get('type') == 'tool':
                    node_data = node.get('data', {})
                    tools.append({
                        'provider_type': node_data.get('provider_type'),
                        'provider_id': node_data.get('provider_id'),
                        'tool_name': node_data.get('tool_name'),
                        'tool_parameters': {}
                    })
        else:
            app_model_config: AppModelConfig = app_model.app_model_config

            if not app_model_config:
                return meta

            agent_config = app_model_config.agent_mode_dict or {}

            # get all tools
            tools = agent_config.get('tools', [])

        url_prefix = (current_app.config.get("CONSOLE_API_URL")
                      + "/console/api/workspaces/current/tool-provider/builtin/")

        for tool in tools:
            keys = list(tool.keys())
            if len(keys) >= 4:
                # current tool standard
                provider_type = tool.get('provider_type')
                provider_id = tool.get('provider_id')
                tool_name = tool.get('tool_name')
                if provider_type == 'builtin':
                    meta['tool_icons'][tool_name] = url_prefix + provider_id + '/icon'
                elif provider_type == 'api':
                    try:
                        provider: ApiToolProvider = db.session.query(ApiToolProvider).filter(
                            ApiToolProvider.id == provider_id
                        )
                        meta['tool_icons'][tool_name] = json.loads(provider.icon)
                    except:
                        meta['tool_icons'][tool_name] = {
                            "background": "#252525",
                            "content": "\ud83d\ude01"
                        }

        return meta
