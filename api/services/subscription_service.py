import logging
from datetime import datetime, timezone
from typing import List, Optional

from extensions.ext_database import db
from models.subscription import Subscription, UsageLimit
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
        """Create a new subscription for a tenant"""

        # Validate tenant existence
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        # Validate plan
        if plan not in ['sandbox', 'professional', 'team']:
            raise InvalidSubscriptionPlanError("Invalid subscription plan.")

        subscription = Subscription(
            tenant_id=tenant_id,
            plan=plan,
            interval=interval,
            docs_processing=docs_processing,
            can_replace_logo=can_replace_logo,
            model_load_balancing_enabled=model_load_balancing_enabled
        )

        db.session.add(subscription)
        db.session.commit()
        logging.info(f'Created subscription for tenant {tenant_id} with plan {plan}')
        return subscription

    @staticmethod
    def update_subscription(subscription_id: str, **kwargs) -> Subscription:
        """Update an existing subscription"""
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError("Subscription not found.")

        valid_fields = ['plan', 'interval', 'docs_processing', 'can_replace_logo', 'model_load_balancing_enabled']
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
    def get_subscriptions_by_tenant(tenant_id: str) -> List[Subscription]:
        """Get all subscriptions for a tenant"""
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise TenantNotFoundError("Tenant not found.")

        subscriptions = Subscription.query.filter_by(tenant_id=tenant_id).all()
        return subscriptions

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
