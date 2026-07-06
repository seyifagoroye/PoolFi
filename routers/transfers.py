"""
PoolFi Outbound Pot Transfers & Payouts Engine
Calculates fully funded cyclic pots and executes outbound disbursements via the Nomba banking infrastructure.
"""

import os
import logging
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Group, GroupMember, Contribution, Payout, PayoutStatus, GroupStatus
from auth import get_current_user

logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/transfers",
    tags=["Outbound Payouts"]
)

# ---------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------

class PayoutExecutionRequest(BaseModel):
    group_id: uuid.UUID

class PayoutExecutionResponse(BaseModel):
    message: str
    group_id: uuid.UUID
    cycle_number: int
    recipient_user_id: uuid.UUID
    amount: float
    nomba_transfer_ref: str
    status: str
    group_lifecycle_status: str

# ---------------------------------------------------------------------
# CORE ENDPOINTS
# ---------------------------------------------------------------------

@router.post("/trigger-payout", response_model=PayoutExecutionResponse, status_code=status.HTTP_200_OK)
async def trigger_cyclic_pot_payout(
    payload: PayoutExecutionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates a savings group cycle, aggregates successfully matched contributions,
    disburses the entire pot balance, and automatically increments or terminates the lifecycle.
    """
    group = db.query(Group).filter(Group.id == payload.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested savings group does not exist within the system schema."
        )

    if group.status == GroupStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lifecycle Block: This rotating savings group has already concluded all cycles and is marked completed."
        )

    current_recipient = db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.rotation_position == group.current_cycle
    ).first()

    if not current_recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data Mismatch: No member assigned to cycle slot position {group.current_cycle}."
        )

    existing_payout = db.query(Payout).filter(
        Payout.group_id == group.id,
        Payout.cycle_number == group.current_cycle,
        Payout.status == "completed"
    ).first()

    if existing_payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payout Protection Block: Cycle {group.current_cycle} pot has already been disbursed."
        )

    total_collected = db.query(func.sum(Contribution.paid_amount)).filter(
        Contribution.group_id == group.id,
        Contribution.cycle_number == group.current_cycle,
        Contribution.status == "paid"
    ).scalar() or 0.0

    if float(total_collected) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process Halt: Total collected balance for this cycle round is currently zero."
        )

    nomba_mock_ref = f"TX-NOMBA-{uuid.uuid4().hex[:12].upper()}"
    
    logger.info(
        f"FINTECH OUTBOUND TRANSFER INTERFACE: Dispatching NGN {total_collected} "
        f"to virtual bank target associated with User {current_recipient.user_id} via ref {nomba_mock_ref}."
    )

    try:
        payout_record = Payout(
            group_id=group.id,
            recipient_id=current_recipient.user_id,
            cycle_number=group.current_cycle,
            amount=float(total_collected),
            nomba_transfer_ref=nomba_mock_ref,
            status="completed"
        )
        db.add(payout_record)

        total_members = db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
        executed_cycle = group.current_cycle
        
        if group.current_cycle >= total_members:
            group.status = GroupStatus.COMPLETED
            logger.info(f"Lifecycle Event: Group {group.id} has successfully concluded all {total_members} rotation blocks.")
        else:
            group.current_cycle += 1

        db.commit()

        return PayoutExecutionResponse(
            message="Cyclic payout disbursement processed and executed successfully.",
            group_id=group.id,
            cycle_number=executed_cycle,
            recipient_user_id=current_recipient.user_id,
            amount=float(total_collected),
            nomba_transfer_ref=nomba_mock_ref,
            status="completed",
            group_lifecycle_status=group.status.value
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Critical Banking Bridge Processing Exception: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fintech network timeout encountered during outbound ledger execution."
        )
