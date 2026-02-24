import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class LeadSource(str, PyEnum):
    scanner = "scanner"
    partner = "partner"
    manual = "manual"


class BusinessDomain(str, PyEnum):
    first = "first"
    second = "second"
    third = "third"


class ColdStage(str, PyEnum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    transferred = "transferred"
    lost = "lost"


class SaleStage(str, PyEnum):
    new = "new"
    kyc = "kyc"
    agreement = "agreement"
    paid = "paid"
    lost = "lost"


# Valid transitions for cold stage
COLD_STAGE_ORDER = [
    ColdStage.new,
    ColdStage.contacted,
    ColdStage.qualified,
    ColdStage.transferred,
    ColdStage.lost,
]

# Valid transitions for sale stage
SALE_STAGE_ORDER = [
    SaleStage.new,
    SaleStage.kyc,
    SaleStage.agreement,
    SaleStage.paid,
    SaleStage.lost,
]


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Enum(LeadSource), nullable=False)
    stage = Column(Enum(ColdStage), nullable=False, default=ColdStage.new)
    business_domain = Column(Enum(BusinessDomain), nullable=True)
    messages_count = Column(Integer, nullable=False, default=0)

    # AI fields
    ai_score = Column(Float, nullable=True)
    ai_recommendation = Column(String(64), nullable=True)
    ai_reason = Column(Text, nullable=True)
    ai_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    sale = relationship("Sale", back_populates="lead", uselist=False)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, unique=True)
    stage = Column(Enum(SaleStage), nullable=False, default=SaleStage.new)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="sale")
