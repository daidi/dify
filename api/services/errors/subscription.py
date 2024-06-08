from services.errors.base import BaseServiceError


class SubscriptionNotFoundError(BaseServiceError):
    pass


class TenantNotFoundError(BaseServiceError):
    pass


class InvalidSubscriptionPlanError(BaseServiceError):
    pass

