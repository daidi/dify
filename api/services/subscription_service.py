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
                docs_processing=False,
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
            if active_subscription.plan != plan:
                raise ValueError(f"Cannot upgrade to {plan} while {active_subscription.plan} plan is active.")

            # If there is an active subscription of the same plan, renew its end_date
            start_date = active_subscription.end_date
        else:
            # If there is no active subscription, create a new one
            start_date = now

        if interval == 'month':
            end_date = start_date + timedelta(days=30)
        elif interval == 'year':
            end_date = start_date + timedelta(days=365)
        else:
            raise ValueError("Invalid subscription interval.")

        if active_subscription:
            active_subscription.end_date = end_date
            db.session.commit()
            subscription = active_subscription
            logging.info(f'Renewed subscription for tenant {tenant_id} with plan {plan} until {end_date}')
        else:
            subscription = Subscription(
                tenant_id=tenant_id,
                plan=plan,
                interval=interval,
                docs_processing=True,
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
        limits_map = {
            'sandbox': {
                ResourceType.MEMBERS: 50,
                ResourceType.APPS: 10,
                ResourceType.VECTOR_SPACE: 100,
                ResourceType.DOCUMENTS_UPLOAD_QUOTA: 2000,
                ResourceType.ANNOTATION_QUOTA: 500
            },
            'professional': {
                ResourceType.MEMBERS: 100,
                ResourceType.APPS: 20,
                ResourceType.VECTOR_SPACE: 500,
                ResourceType.DOCUMENTS_UPLOAD_QUOTA: 10000,
                ResourceType.ANNOTATION_QUOTA: 2000
            },
            'team': {
                ResourceType.MEMBERS: 200,
                ResourceType.APPS: 50,
                ResourceType.VECTOR_SPACE: 1000,
                ResourceType.DOCUMENTS_UPLOAD_QUOTA: 20000,
                ResourceType.ANNOTATION_QUOTA: 5000
            }
        }

        limits = limits_map.get(subscription.plan, {})
        if subscription.interval == 'year':
            for month in range(12):
                month_start_date = subscription.start_date + timedelta(days=30 * month)
                for resource_type, limit in limits.items():
                    usage_limit = UsageLimit(
                        tenant_id=subscription.tenant_id,
                        plan=subscription.plan,
                        resource_type=resource_type.value,
                        limit=limit,
                        current_size=0,
                        created_at=month_start_date,
                        updated_at=month_start_date
                    )
                    db.session.add(usage_limit)
        elif subscription.interval == 'month':
            month_start_date = subscription.start_date
            for resource_type, limit in limits.items():
                usage_limit = UsageLimit(
                    tenant_id=subscription.tenant_id,
                    plan=subscription.plan,
                    resource_type=resource_type.value,
                    limit=limit,
                    current_size=0,
                    created_at=month_start_date,
                    updated_at=month_start_date
                )
                db.session.add(usage_limit)

        db.session.commit()
        logging.info(f'Created initial usage limits for tenant {subscription.tenant_id} for plan {subscription.plan}')