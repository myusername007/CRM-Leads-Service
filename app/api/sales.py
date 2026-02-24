import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.lead import SaleStageUpdate, SaleResponse
from app.services import (
    get_lead, transfer_to_sales,
    get_sale, get_sale_by_lead, update_sale_stage,
    StageValidationError, TransferValidationError,
)

router = APIRouter(tags=["Sales"])


@router.post("/leads/{lead_id}/transfer", response_model=SaleResponse, status_code=201)
async def transfer_lead_endpoint(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Передати ліда в продажі.
    
    Умови (перевіряються системою, рішення — менеджера):
    - AI score >= 0.6
    - Вказаний бізнес-домен
    - Лід на стадії 'qualified'
    """
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        return await transfer_to_sales(db, lead)
    except TransferValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/leads/{lead_id}/sale", response_model=SaleResponse)
async def get_sale_by_lead_endpoint(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Отримати продаж по ID ліда."""
    sale = await get_sale_by_lead(db, lead_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found for this lead")
    return sale


@router.get("/sales/{sale_id}", response_model=SaleResponse)
async def get_sale_endpoint(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Отримати продаж за ID."""
    sale = await get_sale(db, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.patch("/sales/{sale_id}/stage", response_model=SaleResponse)
async def update_sale_stage_endpoint(
    sale_id: uuid.UUID,
    data: SaleStageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Змінити стадію продажу. Не можна пропускати стадії, не можна змінити 'paid'."""
    sale = await get_sale(db, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    try:
        return await update_sale_stage(db, sale, data.stage)
    except StageValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
