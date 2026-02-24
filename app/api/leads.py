import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.lead import LeadCreate, LeadStageUpdate, LeadMessagesUpdate, LeadResponse, AIResult
from app.services import (
    create_lead, get_lead, list_leads,
    update_lead_stage, update_messages_count,
    run_ai_analysis,
    StageValidationError,
)

router = APIRouter(prefix="/leads", tags=["Leads"])


async def _get_lead_or_404(lead_id: uuid.UUID, db: AsyncSession):
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/", response_model=LeadResponse, status_code=201)
async def create_lead_endpoint(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Створити нового ліда."""
    return await create_lead(db, data)


@router.get("/", response_model=list[LeadResponse])
async def list_leads_endpoint(db: AsyncSession = Depends(get_db)):
    """Список всіх лідів."""
    return await list_leads(db)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead_endpoint(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Отримати ліда за ID."""
    return await _get_lead_or_404(lead_id, db)


@router.patch("/{lead_id}/stage", response_model=LeadResponse)
async def update_stage_endpoint(
    lead_id: uuid.UUID,
    data: LeadStageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Змінити стадію ліда. Не можна пропускати стадії."""
    lead = await _get_lead_or_404(lead_id, db)
    try:
        return await update_lead_stage(db, lead, data.stage)
    except StageValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{lead_id}/messages", response_model=LeadResponse)
async def update_messages_endpoint(
    lead_id: uuid.UUID,
    data: LeadMessagesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Оновити кількість повідомлень з лідом."""
    lead = await _get_lead_or_404(lead_id, db)
    return await update_messages_count(db, lead, data.messages_count)


@router.post("/{lead_id}/analyze", response_model=AIResult)
async def analyze_lead_endpoint(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Запустити AI-аналіз ліда через Claude API.
    
    AI отримує: source, stage, messages_count, has_business_domain.
    AI повертає: score, recommendation, reason.
    Результат зберігається в базі.
    Рішення про передачу в продажі приймає менеджер.
    """
    lead = await _get_lead_or_404(lead_id, db)
    try:
        return await run_ai_analysis(db, lead)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")
