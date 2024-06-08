import os

import requests

from extensions.ext_database import db
from models.account import TenantAccountJoin, TenantAccountRole
from services.subscription_service import SubscriptionService


class BillingService:
    base_url = os.environ.get('BILLING_API_URL', 'BILLING_API_URL')
    secret_key = os.environ.get('BILLING_API_SECRET_KEY', 'BILLING_API_SECRET_KEY')

    @classmethod
    def get_info(cls, tenant_id: str):
        # params = {'tenant_id': tenant_id}
        # billing_info = cls._send_request('GET', '/subscription/info', params=params)

        subscription_info = SubscriptionService.get_subscription_with_limits(tenant_id)

        # 初始化默认的限额字典，以防止未定义的资源类型
        default_limits = {
            "members": {"limit": 1, "size": 0},
            "apps": {"limit": 10, "size": 0},
            "vector_space": {"limit": 5000, "size": 0},
            "documents_upload_quota": {"limit": 10000, "size": 0},
            "annotation_quota_limit": {"limit": 1000, "size": 0},
            "credits": {"limit": 50, "size": 0},
        }

        for limit in subscription_info["usage_limits"]:
            resource_type = limit["resource_type"]
            if resource_type in default_limits:
                default_limits[resource_type] = {
                    "limit": limit["limit"],
                    "size": limit["current_size"]
                }

        billing_info = {
            'enabled': True,
            'subscription': {
                'plan': subscription_info["plan"],  # 'sandbox', 'professional', 'team'
                'interval': subscription_info["interval"],  # 'month', 'year'
                'expire_time': subscription_info["end_date"],
            },
            "members": default_limits["members"],
            "apps": default_limits["apps"],
            "vector_space": default_limits["vector_space"],
            "documents_upload_quota": default_limits["documents_upload_quota"],
            "annotation_quota_limit": default_limits["annotation_quota_limit"],
            "credits": default_limits["credits"],
            'docs_processing': subscription_info['docs_processing'],
            'can_replace_logo': subscription_info['can_replace_logo'],
            'model_load_balancing_enabled': subscription_info['model_load_balancing_enabled']
        }
        return billing_info

    @classmethod
    def get_subscription(cls, plan: str,
                         interval: str,
                         prefilled_email: str = '',
                         tenant_id: str = ''):
        params = {
            'plan': plan,
            'interval': interval,
            'prefilled_email': prefilled_email,
            'tenant_id': tenant_id
        }
        return cls._send_request('GET', '/subscription/payment-link', params=params)

    @classmethod
    def get_model_provider_payment_link(cls,
                                        provider_name: str,
                                        tenant_id: str,
                                        account_id: str,
                                        prefilled_email: str):
        params = {
            'provider_name': provider_name,
            'tenant_id': tenant_id,
            'account_id': account_id,
            'prefilled_email': prefilled_email
        }
        return cls._send_request('GET', '/model-provider/payment-link', params=params)

    @classmethod
    def get_invoices(cls, prefilled_email: str = '', tenant_id: str = ''):
        params = {
            'prefilled_email': prefilled_email,
            'tenant_id': tenant_id
        }
        return cls._send_request('GET', '/invoices', params=params)

    @classmethod
    def _send_request(cls, method, endpoint, json=None, params=None):
        headers = {
            "Content-Type": "application/json",
            "Billing-Api-Secret-Key": cls.secret_key
        }

        url = f"{cls.base_url}{endpoint}"
        response = requests.request(method, url, json=json, params=params, headers=headers)

        return response.json()

    @staticmethod
    def is_tenant_owner_or_admin(current_user):
        tenant_id = current_user.current_tenant_id

        join = db.session.query(TenantAccountJoin).filter(
            TenantAccountJoin.tenant_id == tenant_id,
            TenantAccountJoin.account_id == current_user.id
        ).first()

        if not TenantAccountRole.is_privileged_role(join.role):
            raise ValueError('Only team owner or team admin can perform this action')
