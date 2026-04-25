import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    level = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    timezone = Column(String(50), nullable=False, default="Asia/Kathmandu")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    newsletters = relationship("Newsletter", back_populates="user", cascade="all, delete-orphan")
    sent_words = relationship("SentWord", back_populates="user", cascade="all, delete-orphan")
    feedback_tokens = relationship("FeedbackToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_is_active", "is_active"),
    )


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    send_date = Column(Date, nullable=False)
    sequence_num = Column(Integer, nullable=False, default=1)
    level_at_send = Column(Integer, nullable=False)
    words = Column(JSONB, nullable=False)
    source = Column(String(20), nullable=False, default="scheduled")
    sent_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="newsletters")
    sent_words = relationship("SentWord", back_populates="newsletter", cascade="all, delete-orphan")
    feedback_tokens = relationship("FeedbackToken", back_populates="newsletter", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "send_date", "sequence_num", name="uq_newsletter_user_date_seq"),
        Index("ix_newsletters_user_send_date", "user_id", "send_date"),
    )


class SentWord(Base):
    __tablename__ = "sent_words"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(100), nullable=False)
    newsletter_id = Column(UUID(as_uuid=True), ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False)
    level_at_send = Column(Integer, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="sent_words")
    newsletter = relationship("Newsletter", back_populates="sent_words")

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_sent_words_user_word"),
        Index("ix_sent_words_user_word_lower", text("lower(word)"), "user_id"),
        Index("ix_sent_words_user_sent_at", "user_id", "sent_at"),
    )


class FeedbackToken(Base):
    __tablename__ = "feedback_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    newsletter_id = Column(UUID(as_uuid=True), ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(64), unique=True, nullable=False)
    level_adjusted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="feedback_tokens")
    newsletter = relationship("Newsletter", back_populates="feedback_tokens")

    __table_args__ = (
        Index("ix_feedback_tokens_token", "token"),
        Index("ix_feedback_tokens_expires", "expires_at"),
    )
