"""Add design_metadata to newsletters

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('newsletters', sa.Column('design_metadata', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column('newsletters', 'design_metadata')
