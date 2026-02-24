from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.lead import LeadSource, BusinessDomain, ColdStage, SaleStage


# ── Lead schemas ──────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    source: LeadSource
    business_domain: Optional[BusinessDomain] = None


class LeadStageUpdate(BaseModel):
    stage: ColdStage


class LeadMessagesUpdate(BaseModel):
    messages_count: int = Field(..., ge=0)


class AIResult(BaseModel):
    score: float
    recommendation: str
    reason: str


class LeadResponse(BaseModel):
    id: uuid.UUID
    source: LeadSource
    stage: ColdStage
    business_domain: Optional[BusinessDomain]
    messages_count: int
    ai_score: Optional[float]
    ai_recommendation: Optional[str]
    ai_reason: Optional[str]
    ai_analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Sale schemas ──────────────────────────────────────────────────────────────

class SaleStageUpdate(BaseModel):
    stage: SaleStage


class SaleResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    stage: SaleStage
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
