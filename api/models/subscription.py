import enum
from extensions.ext_database import db
from models import StringUUID
from datetime import datetime, timedelta


class SubscriptionPlan(str, enum.Enum):
    SANDBOX = 'sandbox'
    PROFESSIONAL = 'professional'
    TEAM = 'team'


class SubscriptionInterval(str, enum.Enum):
    MONTH = 'month'
    YEAR = 'year'


class ResourceType(str, enum.Enum):
    MEMBERS = 'members'
    APPS = 'apps'
    VECTOR_SPACE = 'vector_space'
    DOCUMENTS_UPLOAD_QUOTA = 'documents_upload_quota'
    ANNOTATION_QUOTA = 'annotation_quota'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='subscription_pkey'),
        db.UniqueConstraint('tenant_id', name='unique_tenant_active_subscription')
    )

    id = db.Column(StringUUID, server_default=db.text('uuid_generate_v4()'), primary_key=True)
    tenant_id = db.Column(StringUUID, nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    interval = db.Column(db.String(50), nullable=False)
    docs_processing = db.Column(db.Boolean, nullable=False)
    can_replace_logo = db.Column(db.Boolean, nullable=False)
    model_load_balancing_enabled = db.Column(db.Boolean, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)  # sandbox 无限制，其他套餐需要设置
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))


class UsageLimit(db.Model):
    __tablename__ = 'usage_limits'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='usage_limit_pkey'),
    )

    id = db.Column(StringUUID, server_default=db.text('uuid_generate_v4()'), primary_key=True)
    plan = db.Column(db.String(50), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    limit = db.Column(db.Integer, nullable=False)
    current_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))

    def get_resource_type(self) -> ResourceType:
        resource_type_str = self.resource_type
        return ResourceType(resource_type_str)
