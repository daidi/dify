"""add meeting

Revision ID: 28f99c5d7991
Revises: 5886a8a98774
Create Date: 2024-03-25 12:42:57.135823

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '28f99c5d7991'
down_revision = '5886a8a98774'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('meeting',
                    sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
                    sa.Column('tenant_id', postgresql.UUID(), nullable=False),
                    sa.Column('scene_id', postgresql.UUID(), nullable=False),
                    sa.Column('scene_name', sa.String(length=255), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('scene', sa.JSON(), nullable=True),
                    sa.Column('conversations', sa.JSON(), nullable=True),
                    sa.Column('type', sa.String(length=255), server_default='copilot', nullable=False, comment='mock, real, copilot'),
                    sa.Column('status', sa.String(length=255), server_default='pending', nullable=False, comment='ready, ongoing, analysis, done, failed'),
                    sa.Column('start_time', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
                    sa.Column('end_time', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
                    sa.Column('permission', sa.String(length=255), server_default=sa.text("'only_me'::character varying"), nullable=False),
                    sa.Column('audio_file', sa.String(length=655), nullable=True),
                    sa.Column('summary', sa.String(length=655), nullable=True),
                    sa.Column('created_by', postgresql.UUID(), nullable=False),
                    sa.Column('updated_by', postgresql.UUID(), nullable=False),
                    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
                    sa.PrimaryKeyConstraint('id', name='meeting_pkey')
                    )
    with op.batch_alter_table('scenarios', schema=None) as batch_op:
        batch_op.alter_column('app_id',
                              existing_type=postgresql.UUID(),
                              nullable=False)
        batch_op.alter_column('app_key',
                              existing_type=sa.VARCHAR(length=255),
                              nullable=False)
        batch_op.alter_column('interact_tools',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=True)
        batch_op.alter_column('user_tools',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=True)
        batch_op.alter_column('dataset_ids',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=True)

    with op.batch_alter_table('scenarios', schema=None) as batch_op:
        batch_op.alter_column('mock_id',
               existing_type=sa.UUID(),
               nullable=False)
        batch_op.alter_column('summary_id',
               existing_type=sa.UUID(),
               nullable=False)
        batch_op.alter_column('mock_key',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
        batch_op.alter_column('summary_key',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('scenarios', schema=None) as batch_op:
        batch_op.alter_column('dataset_ids',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=False)
        batch_op.alter_column('user_tools',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=False)
        batch_op.alter_column('interact_tools',
                              existing_type=postgresql.JSON(astext_type=sa.Text()),
                              nullable=False)
        batch_op.alter_column('app_key',
                              existing_type=sa.VARCHAR(length=255),
                              nullable=True)
        batch_op.alter_column('app_id',
                              existing_type=postgresql.UUID(),
                              nullable=True)

    op.drop_table('meeting')
    # ### end Alembic commands ###
