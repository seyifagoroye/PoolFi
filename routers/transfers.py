"""
PoolFi Transaction Ledger Reporting Router
Provides structured history logs for individual contributions and group cycle payouts with full data validation.
"""

import logging
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Contribution, Payout
from auth import get_current_user

logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/transactions",
    tags=["Transaction Ledger"]
)

# ---------------------------------------------------------------------
# PYDANTIC RESPONSE SCHEMAS (Phase 8 Data Safety)
# ---------------------------------------------------------------------

class ContributionLogResponse(BaseModel):
    id: int
    group_id: UUID
    member_id: int
    cycle_number: int
    expected_amount: float
    paid_amount: float
    status: str
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PayoutLogResponse(BaseModel):
    id: int
    group_id: UUID
    member_id: int
    cycle_number: int
    amount_disbursed: float
    nomba_reference: str
    status: str
    executed_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------
# ENDPOINTS WITH EXPLICIT RETURN SCHEMAS
# ---------------------------------------------------------------------

@router.get("/my-contributions", response_model=List[ContributionLogResponse], status_code=status.HTTP_200_OK)
async def get_my_contributions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the authenticated user's complete historical contribution ledger records.
    """
    logger.info(f"Ledger Audit: Fetching contribution history for User ID {current_user.get('id')}")
    records = db.query(Contribution).filter(Contribution.member_id == current_user["id"]).all()
    return records


@router.get("/group/{group_id}/payouts", response_model=List[PayoutLogResponse], status_code=status.HTTP_200_OK)
async def get_group_payout_history(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all verified outbound payout disbursements executed for a specific savings group.
    """
    # Defensive programming: ensure string converts cleanly or throw a structured 400
    try:
        target_uuid = UUID(group_id)
    except ValueError:
        logger.warning(f"Malformed Request: Provided group ID '{group_id}' is not a valid UUID format.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided group identifier must be a valid RFC4122 UUID string."
        )

    logger.info(f"Ledger Audit: Fetching payout logs for Group {target_uuid} requested by User {current_user.get('id')}")
    records = db.query(Payout).filter(Payout.group_id == target_uuid).all()
    return records