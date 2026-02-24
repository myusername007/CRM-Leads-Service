"""
Lead Service — вся бізнес-логіка по роботі з лідами.

Правила:
  - Не можна пропускати етапи (тільки наступний або "lost")
  - Не можна змінювати стадії "transferred" і "paid"
  - Передача в продажі можлива ТІЛЬКИ при: ai_score >= 0.6 + є бізнес-домен
  - AI тільки рекомендує — рішення приймає менеджер
"""

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude_service import analyze_lead
from app.models.lead import (
    Lead, Sale, ColdStage, SaleStage,
    COLD_STAGE_ORDER, SALE_STAGE_ORDER
)
from app.schemas.lead import LeadCreate, AIResult

# Мінімальний AI score для передачі в продажі
MIN_TRANSFER_SCORE = 0.6

# Стадії, які не можна змінювати
LOCKED_COLD_STAGES = {ColdStage.transferred}
LOCKED_SALE_STAGES = {SaleStage.paid}


class StageValidationError(ValueError):
    """Порушення правил переходу між стадіями."""
    pass


class TransferValidationError(ValueError):
    """Порушення умов передачі в продажі."""
    pass


def _validate_cold_stage_transition(current: ColdStage, new: ColdStage) -> None:
    """Перевіряє, чи можливий перехід між холодними стадіями."""
    if current in LOCKED_COLD_STAGES:
        raise StageValidationError(
            f"Cannot change stage: lead is in locked stage '{current.value}'"
        )

    # "lost" завжди дозволений (крім transferred)
    if new == ColdStage.lost:
        return

    current_idx = COLD_STAGE_ORDER.index(current)
    new_idx = COLD_STAGE_ORDER.index(new)

    if new_idx != current_idx + 1:
        raise StageValidationError(
            f"Invalid stage transition: '{current.value}' → '{new.value}'. "
            f"Next allowed: '{COLD_STAGE_ORDER[current_idx + 1].value}' or 'lost'"
        )


def _validate_sale_stage_transition(current: SaleStage, new: SaleStage) -> None:
    """Перевіряє, чи можливий перехід між стадіями продажу."""
    if current in LOCKED_SALE_STAGES:
        raise StageValidationError(
            f"Cannot change stage: sale is in locked stage '{current.value}'"
        )

    if new == SaleStage.lost:
        return

    current_idx = SALE_STAGE_ORDER.index(current)
    new_idx = SALE_STAGE_ORDER.index(new)

    if new_idx != current_idx + 1:
        raise StageValidationError(
            f"Invalid sale stage transition: '{current.value}' → '{new.value}'"
        )


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    lead = Lead(
        source=data.source,
        business_domain=data.business_domain,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def get_lead(db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


async def list_leads(db: AsyncSession) -> List[Lead]:
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return list(result.scalars().all())


async def update_lead_stage(
    db: AsyncSession, lead: Lead, new_stage: ColdStage
) -> Lead:
    _validate_cold_stage_transition(lead.stage, new_stage)
    lead.stage = new_stage
    lead.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(lead)
    return lead


async def update_messages_count(
    db: AsyncSession, lead: Lead, count: int
) -> Lead:
    lead.messages_count = count
    lead.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(lead)
    return lead


# ── AI ────────────────────────────────────────────────────────────────────────

async def run_ai_analysis(db: AsyncSession, lead: Lead) -> AIResult:
    """
    Викликає AI і зберігає результат у лід.
    AI отримує тільки ті дані, які потрібні для оцінки:
      source, stage, messages_count, has_business_domain
    """
    result = await analyze_lead(
        source=lead.source.value,
        stage=lead.stage.value,
        messages_count=lead.messages_count,
        has_business_domain=lead.business_domain is not None,
    )

    lead.ai_score = result.score
    lead.ai_recommendation = result.recommendation
    lead.ai_reason = result.reason
    lead.ai_analyzed_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(lead)
    return result


# ── Transfer to Sales ─────────────────────────────────────────────────────────

async def transfer_to_sales(db: AsyncSession, lead: Lead) -> Sale:
    """
    Передача ліда в продажі — вирішує МЕНЕДЖЕР, не AI.
    AI тільки надав оцінку. Система перевіряє бізнес-умови.
    """
    # Бізнес-правило 1: потрібна AI-оцінка
    if lead.ai_score is None:
        raise TransferValidationError(
            "AI analysis required before transfer. Run /analyze first."
        )

    # Бізнес-правило 2: AI score >= 0.6
    if lead.ai_score < MIN_TRANSFER_SCORE:
        raise TransferValidationError(
            f"AI score {lead.ai_score:.2f} is below threshold {MIN_TRANSFER_SCORE}. "
            "Lead is not ready for sales."
        )

    # Бізнес-правило 3: потрібен бізнес-домен
    if lead.business_domain is None:
        raise TransferValidationError(
            "Business domain must be set before transfer to sales."
        )

    # Бізнес-правило 4: лід має бути на стадії qualified
    if lead.stage != ColdStage.qualified:
        raise TransferValidationError(
            f"Lead must be in 'qualified' stage to transfer. Current: '{lead.stage.value}'"
        )

    # Перевести лід
    lead.stage = ColdStage.transferred
    lead.updated_at = datetime.now(timezone.utc)

    # Створити запис продажу
    sale = Sale(lead_id=lead.id)
    db.add(sale)

    await db.commit()
    await db.refresh(lead)
    await db.refresh(sale)
    return sale


# ── Sales stage ───────────────────────────────────────────────────────────────

async def get_sale(db: AsyncSession, sale_id: uuid.UUID) -> Sale | None:
    result = await db.execute(select(Sale).where(Sale.id == sale_id))
    return result.scalar_one_or_none()


async def get_sale_by_lead(db: AsyncSession, lead_id: uuid.UUID) -> Sale | None:
    result = await db.execute(select(Sale).where(Sale.lead_id == lead_id))
    return result.scalar_one_or_none()


async def update_sale_stage(
    db: AsyncSession, sale: Sale, new_stage: SaleStage
) -> Sale:
    _validate_sale_stage_transition(sale.stage, new_stage)
    sale.stage = new_stage
    sale.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sale)
    return sale
