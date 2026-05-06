"""Remove legacy word-related tables and columns.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # Drop sent_words indexes
    op.drop_index("ix_sent_words_user_sent_at", table_name="sent_words")
    op.drop_index("ix_sent_words_user_word_lower", table_name="sent_words")
    
    # Drop sent_words table
    op.drop_table("sent_words")
    
    # Drop words column from newsletters
    op.drop_column("newsletters", "words")


def downgrade():
    # Add words column back to newsletters
    op.add_column(
        "newsletters",
        sa.Column("words", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    
    # Recreate sent_words table
    op.create_table(
        "sent_words",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word", sa.String(length=100), nullable=False),
        sa.Column("newsletter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level_at_send", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["newsletter_id"], ["newsletters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word", name="uq_sent_words_user_word")
    )
    op.create_index("ix_sent_words_user_sent_at", "sent_words", ["user_id", "sent_at"])
    op.create_index("ix_sent_words_user_word_lower", "sent_words", [sa.text("lower(word)"), "user_id"])
