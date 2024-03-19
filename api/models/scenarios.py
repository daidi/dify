from datetime import datetime

from celery import states
from sqlalchemy.dialects.postgresql import UUID

from extensions.ext_database import db


class Scenarios(db.Model):
    """Scenarios result/status."""

    __tablename__ = 'scenarios'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='scenarios_pkey'),
    )

    id = db.Column(UUID, nullable=False,server_default=db.text('uuid_generate_v4()'))
    tenant_id = db.Column(UUID, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    interact_role = db.Column(db.String(255), nullable=False)
    interact_goal = db.Column(db.String(512), nullable=False)
    interact_tools = db.Column(db.JSON, nullable=True)
    interact_nums = db.Column(db.Integer, nullable=False)
    user_role = db.Column(db.String(255), nullable=False)
    user_goal = db.Column(db.String(512), nullable=False)
    user_tools = db.Column(db.JSON, nullable=True)
    dataset_ids = db.Column(db.JSON, nullable=True)
    language = db.Column(db.String(255), nullable=True)
    permission = db.Column(db.String(255), nullable=False,
                           server_default=db.text("'only_me'::character varying"))
    created_by = db.Column(UUID, nullable=False)
    updated_by = db.Column(UUID, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))

