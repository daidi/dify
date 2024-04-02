from datetime import datetime

from celery import states
from sqlalchemy.dialects.postgresql import UUID

from extensions.ext_database import db


class Meeting(db.Model):
    """Meeting result/status."""

    __tablename__ = 'meeting'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='meeting_pkey'),
    )

    id = db.Column(UUID, nullable=False, server_default=db.text('uuid_generate_v4()'))
    tenant_id = db.Column(UUID, nullable=False)
    scene_id = db.Column(UUID, nullable=False)
    scene_name = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    scene = db.Column(db.JSON, nullable=True)
    conversations = db.Column(db.JSON, nullable=True)
    type = db.Column(db.String(255), nullable=False, server_default="copilot", comment="mock, real, copilot")
    status = db.Column(db.String(255), nullable=False, server_default="pending",
                       comment="ready, ongoing, analysis, done, failed")
    start_time = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    end_time = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    permission = db.Column(db.String(255), nullable=False,
                           server_default=db.text("'only_me'::character varying"))
    audio_file = db.Column(db.String(655), nullable=True)
    summary = db.Column(db.String(655), nullable=True)
    created_by = db.Column(UUID, nullable=False)
    updated_by = db.Column(UUID, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
