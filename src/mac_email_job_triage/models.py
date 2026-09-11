from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["job", "bill", "personal", "newsletter", "promo", "other"]


class MessageRecord(BaseModel):
    source: str
    external_id: str
    thread_id: str | None = None
    sender: str = ""
    subject: str = ""
    received_at: datetime | None = None
    body: str = ""
    web_link: str | None = None


class TriageDecision(BaseModel):
    category: Category
    needs_reply: bool
    urgency: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1, max_length=600)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class BatchTriageItem(TriageDecision):
    external_id: str


class BatchTriageResponse(BaseModel):
    items: list[BatchTriageItem]


class JobRecord(BaseModel):
    provider: Literal["greenhouse", "lever", "ashby"]
    external_id: str
    company: str
    title: str
    location: str = ""
    description: str = ""
    apply_url: str
    published_at: datetime | None = None
    workplace_type: str | None = None
    compensation: str | None = None


class JobFit(BaseModel):
    relevant: bool
    match_score: int = Field(ge=0, le=100)
    remote_status: Literal["remote", "not_remote", "unclear"]
    rationale: str = Field(max_length=1000)
    gaps: list[str] = Field(default_factory=list, max_length=10)
