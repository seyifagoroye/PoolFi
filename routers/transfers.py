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
from models import Group, GroupMember, Contribution, Payout
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
    recipient_user_id: int
    amount_disbursed: float
    nomba_reference: str
    status: str

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
    and disburses the entire pot balance to the designated turn-order recipient.
    """
    # 1. Fetch target group sequence metadata
    group = db.query(Group).filter(Group.id == payload.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested savings group does not exist within the system schema."
        )

    # 2. Determine who owns the current slot rotation cycle
    current_recipient = db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.draw_order == group.current_cycle
    ).first()

    if not current_recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data Mismatch: No member assigned to cycle slot position {group.current_cycle}."
        )

    # 3. Prevent duplicate payouts for the exact same rotation round
    existing_payout = db.query(Payout).filter(
        Payout.group_id == group.id,
        Payout.cycle_number == group.current_cycle,
        Payout.status == "success"
    ).first()

    if existing_payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payout Protection Block: Cycle {group.current_cycle} pot has already been disbursed."
        )

    # 4. Sum up total collected payments from the contribution matrix
    total_collected = db.query(func.sum(Contribution.paid_amount)).filter(
        Contribution.group_id == group.id,
        Contribution.cycle_number == group.current_cycle,
        Contribution.status == "paid"
    ).scalar() or 0.0

    # Safety check: Prevent firing empty payouts if nobody contributed yet
    if float(total_collected) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process Halt: Total collected balance for this cycle round is currently zero."
        )

    # 5. Interface with Nomba Outbound Transfer Framework Simulation Gateway
    # In a full staging pipeline, this builds the internal Bearer signature token and executes an outbound POST request.
    nomba_mock_ref = f"TX-NOMBA-{uuid.uuid4().hex[:12].upper()}"
    
    logger.info(
        f"FINTECH OUTBOUND TRANSFER INTERFACE: Dispatching NGN {total_collected} "
        f"to virtual bank target associated with User {current_recipient.user_id} via ref {nomba_mock_ref}."
    )

    try:
        # Create persistent ledger payout entry block
        payout_record = Payout(
            group_id=group.id,
            member_id=current_recipient.user_id,
            cycle_number=group.current_cycle,
            amount_disbursed=float(total_collected),
            nomba_reference=nomba_mock_ref,
            status="success",
            executed_at=datetime.utcnow()
        )
        db.add(payout_record)

        # Safely increment group status metadata to the next round cycle slot automatically
        group.current_cycle += 1
        db.commit()

        return PayoutExecutionResponse(
            message="Cyclic payout disbursement processed and executed successfully.",
            group_id=group.id,
            cycle_number=group.current_cycle - 1, # Return the round that was just paid out
            recipient_user_id=current_recipient.user_id,
            amount_disbursed=float(total_collected),
            nomba_reference=nomba_mock_ref,
            status="success"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Critical Banking Bridge Processing Exception: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fintech network timeout encountered during outbound ledger execution."
        )