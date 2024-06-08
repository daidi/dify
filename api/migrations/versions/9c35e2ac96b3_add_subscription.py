"""add subscription

Revision ID: 9c35e2ac96b3
Revises: 4e99a8df00ff
Create Date: 2024-06-08 02:32:51.087400

"""
from alembic import op
import models as models
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9c35e2ac96b3'
down_revision = '4e99a8df00ff'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('subscriptions',
                    sa.Column('id', models.StringUUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
                    sa.Column('tenant_id', models.StringUUID(), nullable=False),
                    sa.Column('plan', sa.String(length=50), nullable=False),
                    sa.Column('interval', sa.String(length=50), nullable=False),
                    sa.Column('docs_processing', sa.Boolean(), nullable=False),
                    sa.Column('can_replace_logo', sa.Boolean(), nullable=False),
                    sa.Column('model_load_balancing_enabled', sa.Boolean(), nullable=False),
                    sa.Column('start_date', sa.DateTime(), nullable=False),
                    sa.Column('end_date', sa.DateTime(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id', name='subscription_pkey'),
                    sa.UniqueConstraint('tenant_id', name='unique_tenant_active_subscription')
                    )
    op.create_table('usage_limits',
                    sa.Column('id', models.StringUUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
                    sa.Column('plan', sa.String(length=50), nullable=False),
                    sa.Column('resource_type', sa.String(length=50), nullable=False),
                    sa.Column('limit', sa.Integer(), nullable=False),
                    sa.Column('current_size', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id', name='usage_limit_pkey')
                    )

    # 插入初始数据到 usage_limits 表
    usage_limits_data = [
        {"plan": "sandbox", "resource_type": "members", "limit": 1, "current_size": 0},
        {"plan": "sandbox", "resource_type": "apps", "limit": 10, "current_size": 0},
        {"plan": "sandbox", "resource_type": "vector_space", "limit": 10, "current_size": 0},
        {"plan": "sandbox", "resource_type": "documents_upload_quota", "limit": 50, "current_size": 0},
        {"plan": "sandbox", "resource_type": "annotation_quota_limit", "limit": 10, "current_size": 0},
        {"plan": "sandbox", "resource_type": "credits", "limit": 50, "current_size": 0},
        {"plan": "professional", "resource_type": "members", "limit": 3, "current_size": 0},
        {"plan": "professional", "resource_type": "apps", "limit": 50, "current_size": 0},
        {"plan": "professional", "resource_type": "vector_space", "limit": 200, "current_size": 0},
        {"plan": "professional", "resource_type": "documents_upload_quota", "limit": 500, "current_size": 0},
        {"plan": "professional", "resource_type": "annotation_quota_limit", "limit": 2000, "current_size": 0},
        {"plan": "professional", "resource_type": "credits", "limit": 2000, "current_size": 0},
        {"plan": "team", "resource_type": "members", "limit": 1000, "current_size": 0},
        {"plan": "team", "resource_type": "apps", "limit": 1000, "current_size": 0},
        {"plan": "team", "resource_type": "vector_space", "limit": 1024, "current_size": 0},
        {"plan": "team", "resource_type": "documents_upload_quota", "limit": 100000, "current_size": 0},
        {"plan": "team", "resource_type": "annotation_quota_limit", "limit": 10000, "current_size": 0},
        {"plan": "team", "resource_type": "credits", "limit": 10000, "current_size": 0},
    ]

    # 执行插入操作
    op.bulk_insert(
        sa.table(
            'usage_limits',
            sa.column('plan', sa.String(length=50)),
            sa.column('resource_type', sa.String(length=50)),
            sa.column('limit', sa.Integer()),
            sa.column('current_size', sa.Integer())
        ),
        usage_limits_data
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('scenarios', schema=None) as batch_op:
        batch_op.alter_column('summary_key',
                              existing_type=sa.VARCHAR(length=255),
                              nullable=True)
        batch_op.alter_column('mock_key',
                              existing_type=sa.VARCHAR(length=255),
                              nullable=True)
        batch_op.alter_column('summary_id',
                              existing_type=sa.UUID(),
                              nullable=True)
        batch_op.alter_column('mock_id',
                              existing_type=sa.UUID(),
                              nullable=True)

    op.drop_table('usage_limits')
    op.drop_table('subscriptions')
    # ### end Alembic commands ###