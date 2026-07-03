"""
PoolFi Transaction Ledger Reporting Router
Provides history logs for individual contributions and group cycle payouts.
"""

import logging
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

@router.get("/my-contributions", status_code=status.HTTP_200_OK)
async def get_my_contributions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the authenticated user's complete historical contribution ledger records.
    """
    records = db.query(Contribution).filter(Contribution.member_id == current_user["id"]).all()
    return records

@router.get("/group/{group_id}/payouts", status_code=status.HTTP_200_OK)
async def get_group_payout_history(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all verified outbound payout disbursements executed for a specific savings group.
    """
    records = db.query(Payout).filter(Payout.group_id == group_id).all()
    return records