"""Add newsletter_prompt and content fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # User changes
    op.add_column('users', sa.Column('newsletter_prompt', sa.Text(), nullable=True))
    op.alter_column('users', 'level', existing_type=sa.Integer(), nullable=True)

    # Newsletter changes
    op.alter_column('newsletters', 'words', existing_type=postgresql.JSONB(), nullable=True)
    op.add_column('newsletters', sa.Column('prompt_used', sa.Text(), nullable=True))
    op.add_column('newsletters', sa.Column('content_structure', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column('newsletters', 'content_structure')
    op.drop_column('newsletters', 'prompt_used')
    op.alter_column('newsletters', 'words', existing_type=postgresql.JSONB(), nullable=False)
    op.alter_column('users', 'level', existing_type=sa.Integer(), nullable=False)
    op.drop_column('users', 'newsletter_prompt')
