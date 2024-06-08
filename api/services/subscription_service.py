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
    def create_subscription(tenant_id: str, plan: str, interval: str, docs_processing: bool,
                            can_replace_logo: bool, model_load_balancing_enabled: bool) -> Subscription:
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
                docs_processing=docs_processing,
                can_replace_logo=can_replace_logo,
                model_load_balancing_enabled=model_load_balancing_enabled,
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
                docs_processing=docs_processing,
                can_replace_logo=can_replace_logo,
                model_load_balancing_enabled=model_load_balancing_enabled,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(subscription)
            db.session.commit()
            logging.info(
                f'Created subscription for tenant {tenant_id} with plan {plan} from {start_date} to {end_date}')

        return subscription

    @staticmethod
    def update_subscription(subscription_id: str, **kwargs) -> Subscription:
        """Update an existing subscription"""
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError("Subscription not found.")

        valid_fields = ['plan', 'interval', 'docs_processing', 'can_replace_logo', 'model_load_balancing_enabled',
                        'end_date']
        for field, value in kwargs.items():
            if field in valid_fields:
                setattr(subscription, field, value)
            else:
                raise AttributeError(f"Invalid field: {field}")

        subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        logging.info(f'Updated subscription {subscription_id}')
        return subscription

    @staticmethod
    def get_subscription(subscription_id: str) -> Subscription:
        """Get a subscription by its ID"""
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError("Subscription not found.")
        return subscription

    @staticmethod
    def get_all_subscriptions() -> List[Subscription]:
        """Get all subscription records"""
        subscriptions = Subscription.query.all()
        return subscriptions

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
            Subscription.end_date > now
        ).first()

        if active_subscription is None:
            active_subscription = Subscription(
                tenant_id=tenant_id,
                plan='sandbox',
                interval='month',
                docs_processing=False,
                can_replace_logo=False,
                model_load_balancing_enabled=False,
            )

        return active_subscription

    @staticmethod
    def get_usage_limits(plan: str) -> List[UsageLimit]:
        """Get all usage limits for a specific plan"""
        usage_limits = UsageLimit.query.filter_by(plan=plan).all()
        return usage_limits

    @staticmethod
    def get_subscription_with_limits(tenant_id: str) -> dict:
        """Get the active subscription along with its usage limits for a tenant"""
        active_subscription = SubscriptionService.get_active_subscription_by_tenant(tenant_id)

        usage_limits = SubscriptionService.get_usage_limits(active_subscription.plan)

        limits_info = [{
            "resource_type": limit.resource_type,
            "limit": limit.limit,
            "current_size": limit.current_size
        } for limit in usage_limits]

        subscription_info = {
            "tenant_id": active_subscription.tenant_id,
            "plan": active_subscription.plan,
            "interval": active_subscription.interval,
            "docs_processing": active_subscription.docs_processing,
            "can_replace_logo": active_subscription.can_replace_logo,
            "model_load_balancing_enabled": active_subscription.model_load_balancing_enabled,
            "start_date": active_subscription.start_date,
            "end_date": active_subscription.end_date,
            "usage_limits": limits_info
        }

        return subscription_info

    @staticmethod
    def get_subscriptions_by_tenant(tenant_id: str) -> Optional[Subscription]:
        """Get the active subscription for a tenant"""
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        now = datetime.utcnow().replace(tzinfo=None)

        # First, look for an active non-sandbox subscription
        active_subscription = Subscription.query.filter(
            Subscription.tenant_id == tenant_id,
            Subscription.end_date > now,
            Subscription.plan != 'sandbox'
        ).first()

        if active_subscription:
            return active_subscription

        # If no active non-sandbox subscription, check for sandbox subscription
        sandbox_subscription = Subscription.query.filter_by(
            tenant_id=tenant_id, plan='sandbox'
        ).first()

        return sandbox_subscription

    @staticmethod
    def delete_subscription(subscription_id: str) -> None:
        """Delete a subscription by its ID"""
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError("Subscription not found.")

        db.session.delete(subscription)
        db.session.commit()
        logging.info(f'Deleted subscription {subscription_id}')

    @staticmethod
    def create_usage_limit(tenant_id: str, resource_type: str, limit: int, current_size: int) -> UsageLimit:
        """Create a new usage limit for a tenant"""
        # Validate tenant existence
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        usage_limit = UsageLimit(
            tenant_id=tenant_id,
            resource_type=resource_type,
            limit=limit,
            current_size=current_size
        )

        db.session.add(usage_limit)
        db.session.commit()
        logging.info(f'Created usage limit for tenant {tenant_id} with resource type {resource_type}')
        return usage_limit

    @staticmethod
    def update_usage_limit(usage_limit_id: str, **kwargs) -> UsageLimit:
        """Update an existing usage limit"""
        usage_limit = UsageLimit.query.get(usage_limit_id)
        if not usage_limit:
            raise SubscriptionNotFoundError("Usage limit not found.")

        valid_fields = ['resource_type', 'limit', 'current_size']
        for field, value in kwargs.items():
            if field in valid_fields:
                setattr(usage_limit, field, value)
            else:
                raise AttributeError(f"Invalid field: {field}")

        usage_limit.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        logging.info(f'Updated usage limit {usage_limit_id}')
        return usage_limit

    @staticmethod
    def get_usage_limit(usage_limit_id: str) -> UsageLimit:
        """Get a usage limit by its ID"""
        usage_limit = UsageLimit.query.get(usage_limit_id)
        if not usage_limit:
            raise SubscriptionNotFoundError("Usage limit not found.")
        return usage_limit

    @staticmethod
    def get_usage_limits_by_tenant(tenant_id: str) -> List[UsageLimit]:
        """Get all usage limits for a tenant"""
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        usage_limits = UsageLimit.query.filter_by(tenant_id=tenant_id).all()
        return usage_limits

    @staticmethod
    def delete_usage_limit(usage_limit_id: str) -> None:
        """Delete a usage limit by its ID"""
        usage_limit = UsageLimit.query.get(usage_limit_id)
        if not usage_limit:
            raise SubscriptionNotFoundError("Usage limit not found.")

        db.session.delete(usage_limit)
        db.session.commit()
        logging.info(f'Deleted usage limit {usage_limit_id}')

    @staticmethod
    def refresh_usage_limits():
        """Refresh usage limits based on subscription plan"""
        subscriptions = Subscription.query.filter_by(end_date=None).all()
        for subscription in subscriptions:
            usage_limits = UsageLimit.query.filter_by(tenant_id=subscription.tenant_id).all()

            if subscription.plan == 'sandbox':
                new_limits = {
                    ResourceType.MEMBERS: 50,
                    ResourceType.APPS: 10,
                    ResourceType.VECTOR_SPACE: 100,
                    ResourceType.DOCUMENTS_UPLOAD_QUOTA: 2000,
                    ResourceType.ANNOTATION_QUOTA: 500,
                }
            elif subscription.plan == 'professional':
                new_limits = {
                    ResourceType.MEMBERS: 100,
                    ResourceType.APPS: 20,
                    ResourceType.VECTOR_SPACE: 500,
                    ResourceType.DOCUMENTS_UPLOAD_QUOTA: 10000,
                    ResourceType.ANNOTATION_QUOTA: 2000,
                }
            elif subscription.plan == 'team':
                new_limits = {
                    ResourceType.MEMBERS: 200,
                    ResourceType.APPS: 50,
                    ResourceType.VECTOR_SPACE: 1000,
                    ResourceType.DOCUMENTS_UPLOAD_QUOTA: 20000,
                    ResourceType.ANNOTATION_QUOTA: 5000,
                }

            for usage_limit in usage_limits:
                if usage_limit.resource_type in new_limits:
                    usage_limit.limit = new_limits[usage_limit.resource_type]
                    usage_limit.current_size = 0  # reset the current size
                    usage_limit.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    db.session.commit()
                    logging.info(
                        f'Refreshed usage limit for tenant {subscription.tenant_id} resource {usage_limit.resource_type}')
