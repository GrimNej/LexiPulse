"""Add topic and unsubscribe_token to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Add topic column with default
    op.add_column('users', sa.Column('topic', sa.String(length=100), nullable=False, server_default='vocabulary'))
    
    # Add unsubscribe_token column (nullable for existing users)
    op.add_column('users', sa.Column('unsubscribe_token', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq_users_unsubscribe_token', 'users', ['unsubscribe_token'])
    
    # Create index on topic for filtering
    op.create_index('ix_users_topic', 'users', ['topic'])


def downgrade():
    op.drop_index('ix_users_topic', table_name='users')
    op.drop_constraint('uq_users_unsubscribe_token', 'users', type_='unique')
    op.drop_column('users', 'unsubscribe_token')
    op.drop_column('users', 'topic')
