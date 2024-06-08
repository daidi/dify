import enum
from extensions.ext_database import db
from models import StringUUID
from datetime import datetime, timedelta


class DataAPI(db.Model):
    __tablename__ = 'data_apis'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='data_apis_pkey'),
    )

    id = db.Column(StringUUID, server_default=db.text('uuid_generate_v4()'), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.Text, nullable=True)
    price_per_call = db.Column(db.Integer, nullable=False)
    authorization_method = db.Column(db.String(50), nullable=False)


class DataAPIApplication(db.Model):
    __tablename__ = 'data_api_applications'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='data_api_applications_pkey'),
    )

    id = db.Column(StringUUID, server_default=db.text('uuid_generate_v4()'), primary_key=True)
    tenant_id = db.Column(StringUUID, nullable=False)
    data_api_id = db.Column(StringUUID, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')  # 状态：pending, approved, rejected
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)


class DataAPICall(db.Model):
    __tablename__ = 'data_api_calls'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='data_api_calls_pkey'),
    )

    id = db.Column(StringUUID, server_default=db.text('uuid_generate_v4()'), primary_key=True)
    tenant_id = db.Column(StringUUID, nullable=False)
    data_api_id = db.Column(StringUUID, nullable=False)
    called_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    billing_amount = db.Column(db.Integer, nullable=False)
