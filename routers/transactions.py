"""
PoolFi Transaction Ledger Reporting Router
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Contribution, Payout, Group, GroupMember
from auth import get_current_user

logger = logging.getLogger("poolfi_core")
router = APIRouter(prefix="/api/transactions", tags=["Transaction Ledger"])

@router.get("/my-contributions")
async def get_my_contributions(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Contribution).filter(Contribution.member_id == current_user.id).all()

@router.get("/group/{group_id}/payouts")
async def get_group_payout_history(group_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g: raise HTTPException(404, "Group not found.")
    m = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id).first()
    if g.coordinator_id != current_user.id and not m:
        raise HTTPException(403, "Access denied. You do not belong to this group.")
    return db.query(Payout).filter(Payout.group_id == group_id).all()
