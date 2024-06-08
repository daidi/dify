import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from extensions.ext_database import db
from models.subscription import Subscription, UsageLimit, ResourceType
from models.account import Tenant

from services.errors.subscription import (
    SubscriptionNotFoundError,
    TenantNotFoundError,
    InvalidSubscriptionPlanError
)

limits_map = {
    'sandbox': {
        ResourceType.MEMBERS: 50,
        ResourceType.APPS: 10,
        ResourceType.VECTOR_SPACE: 100,
        ResourceType.DOCUMENTS_UPLOAD_QUOTA: 2000,
        ResourceType.ANNOTATION_QUOTA: 500,
        ResourceType.CREDITS: 50
    },
    'professional': {
        ResourceType.MEMBERS: 100,
        ResourceType.APPS: 20,
        ResourceType.VECTOR_SPACE: 500,
        ResourceType.DOCUMENTS_UPLOAD_QUOTA: 10000,
        ResourceType.ANNOTATION_QUOTA: 2000,
        ResourceType.CREDITS: 1000
    },
    'team': {
        ResourceType.MEMBERS: 200,
        ResourceType.APPS: 50,
        ResourceType.VECTOR_SPACE: 1000,
        ResourceType.DOCUMENTS_UPLOAD_QUOTA: 20000,
        ResourceType.ANNOTATION_QUOTA: 5000,
        ResourceType.CREDITS: 5000
    }
}


class SubscriptionService:

    @staticmethod
    def create_subscription(tenant_id: str, plan: str, interval: str) -> Subscription:
        """Create or renew a subscription for a tenant"""

        # Validate tenant existence
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        # Validate plan
        if plan not in ['sandbox', 'professional', 'team']:
            raise InvalidSubscriptionPlanError("Invalid subscription plan.")

        # Handle sandbox plan separately
        if plan == 'sandbox':
            # Sandbox plans have no end_date
            subscription = Subscription(
                tenant_id=tenant_id,
                plan=plan,
                interval=interval,
                docs_processing='standard',
                can_replace_logo=False,
                model_load_balancing_enabled=False,
                start_date=datetime.utcnow().replace(tzinfo=None),
                end_date=None,
            )
            db.session.add(subscription)
            db.session.commit()
            logging.info(f'Created subscription for tenant {tenant_id} with plan {plan}')
            return subscription

        # Check for active non-sandbox plans
        now = datetime.utcnow().replace(tzinfo=None)
        active_subscription = Subscription.query.filter(
            Subscription.tenant_id == tenant_id,
            Subscription.end_date > now,
            Subscription.plan != 'sandbox'
        ).first()

        if active_subscription:
            # If there is an active subscription of the same plan, renew its end_date
            start_date = active_subscription.end_date
        else:
            # If there is no active subscription, create a new one
            start_date = now

        if interval == 'month':
            end_date = start_date + timedelta(days=30)
        elif interval == 'year':
            end_date = start_date + timedelta(days=30 * 12)
        else:
            raise ValueError("Invalid subscription interval.")

        subscription = Subscription(
            tenant_id=tenant_id,
            plan=plan,
            interval=interval,
            docs_processing='priority',  # top-priority
            can_replace_logo=True,
            model_load_balancing_enabled=True,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(subscription)
        db.session.commit()
        logging.info(
            f'Created subscription for tenant {tenant_id} with plan {plan} from {start_date} to {end_date}')

        # Create usage limits
        SubscriptionService._create_initial_usage_limits(subscription)

        return subscription

    @staticmethod
    def _create_initial_usage_limits(subscription: Subscription):
        """Create initial usage limits for a new subscription"""

        limits = limits_map.get(subscription.plan, {})
        if subscription.interval == 'year':
            for month in range(12):
                month_start_date = subscription.start_date + timedelta(days=30 * month)
                month_end_date = month_start_date + timedelta(days=30)
                for resource_type, limit in limits.items():
                    usage_limit = UsageLimit(
                        tenant_id=subscription.tenant_id,
                        subscription_id=subscription.id,
                        plan=subscription.plan,
                        resource_type=resource_type.value,
                        limit=limit,
                        current_size=0,
                        is_yearly_monthly_plan=True,
                        monthly_cycle=month + 1,
                        start_date=month_start_date,
                        end_date=month_end_date,
                        created_at=month_start_date,
                        updated_at=month_start_date
                    )
                    db.session.add(usage_limit)
        elif subscription.interval == 'month':
            month_start_date = subscription.start_date
            month_end_date = subscription.end_date
            for resource_type, limit in limits.items():
                usage_limit = UsageLimit(
                    tenant_id=subscription.tenant_id,
                    subscription_id=subscription.id,
                    plan=subscription.plan,
                    resource_type=resource_type.value,
                    limit=limit,
                    current_size=0,
                    is_yearly_monthly_plan=False,
                    start_date=month_start_date,
                    end_date=month_end_date,
                    created_at=month_start_date,
                    updated_at=month_start_date
                )
                db.session.add(usage_limit)

        db.session.commit()
        logging.info(f'Created initial usage limits for tenant {subscription.tenant_id} for plan {subscription.plan}')

    @staticmethod
    def get_subscription_with_limits(tenant_id: str) -> dict:
        """Get the active subscription along with its usage limits for a tenant"""
        # Get the active subscription
        active_subscription = SubscriptionService.get_active_subscription_by_tenant(tenant_id)

        if not active_subscription:
            raise SubscriptionNotFoundError(f"No active subscription found for tenant {tenant_id}")

        # Get the usage limits for the active subscription plan
        usage_limits = SubscriptionService.get_usage_limits(active_subscription)

        # Convert usage limits to dictionary format
        limits_info = [{
            "resource_type": limit.resource_type,
            "limit": limit.limit,
            "current_size": limit.current_size
        } for limit in usage_limits]

        # Create the result dictionary
        subscription_info = {
            "tenant_id": active_subscription.tenant_id,
            "plan": active_subscription.plan,
            "interval": active_subscription.interval,
            "docs_processing": active_subscription.docs_processing,
            "can_replace_logo": active_subscription.can_replace_logo,
            "model_load_balancing_enabled": active_subscription.model_load_balancing_enabled,
            "start_date": active_subscription.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "end_date": active_subscription.end_date.strftime(
                '%Y-%m-%d %H:%M:%S') if active_subscription.end_date else None,
            "usage_limits": limits_info
        }

        return subscription_info

    @staticmethod
    def get_active_subscription_by_tenant(tenant_id: str) -> Optional[Subscription]:
        """Get the active subscription for a tenant"""
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        now = datetime.utcnow().replace(tzinfo=None)

        # Look for an active subscription
        active_subscription = Subscription.query.filter(
            Subscription.tenant_id == tenant_id,
            Subscription.start_date <= now,
            Subscription.end_date >= now
        ).first()

        if active_subscription is None:
            active_subscription = Subscription(
                tenant_id=tenant_id,
                plan='sandbox',
                interval='month',
                docs_processing='standard',
                can_replace_logo=False,
                model_load_balancing_enabled=False,
                start_date=datetime.utcnow().replace(tzinfo=None),
                end_date=None,
            )

        return active_subscription

    @staticmethod
    def get_usage_limits(active_subscription: Subscription) -> List[UsageLimit]:
        """Get all usage limits for a specific plan"""
        subscription_id = active_subscription.id
        if subscription_id is None:
            limits = limits_map.get('sandbox', {})
            usage_limits = []
            for resource_type, limit in limits.items():
                usage_limit = UsageLimit(
                    tenant_id=active_subscription.tenant_id,
                    subscription_id=active_subscription.id,
                    plan=active_subscription.plan,
                    resource_type=resource_type.value,
                    limit=limit,
                    current_size=0,
                    is_yearly_monthly_plan=False,
                    start_date=active_subscription.start_date,
                    end_date=active_subscription.end_date,
                )
                usage_limits.append(usage_limit)
            return usage_limits

        now = datetime.utcnow().replace(tzinfo=None)
        usage_limits = UsageLimit.query.filter(
            UsageLimit.subscription_id == subscription_id,
            UsageLimit.start_date < now,
            UsageLimit.end_date > now
        ).all()
        return usage_limits
