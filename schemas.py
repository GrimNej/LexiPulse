from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── User Schemas ──────────────────────────────────────────────

class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    level: Optional[int] = Field(default=5, ge=1, le=10)
    is_active: bool = True
    timezone: str = "Asia/Kathmandu"
    topic: str = "general"
    newsletter_prompt: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    level: Optional[int] = Field(default=None, ge=1, le=10)
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    topic: Optional[str] = None
    newsletter_prompt: Optional[str] = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class UserStats(UserRead):
    total_newsletters: int
    current_level: int
    topic: str
    newsletter_prompt: Optional[str] = None


# ── Newsletter Schemas ────────────────────────────────────────

class NewsletterSection(BaseModel):
    heading: str
    content: str
    style: str = "paragraph"  # paragraph | bullet | quote


class NewsletterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    send_date: datetime
    sequence_num: int
    level_at_send: int
    source: str
    sent_at: datetime


# ── Feedback Schemas ──────────────────────────────────────────

class FeedbackAction(BaseModel):
    action: str  # want_more


# ── Admin Schemas ─────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    topic: str = Field(default="general", max_length=100)
    timezone: str = "Asia/Kathmandu"
    newsletter_prompt: Optional[str] = None


class SubscribeResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[UUID] = None


class UnsubscribeResponse(BaseModel):
    status: str
    message: str


class AdminUserCreateResponse(UserRead):
    pass


class SchedulerResult(BaseModel):
    sent: int
    failed: int
    total: int


class HealthCheck(BaseModel):
    status: str
    database: str
