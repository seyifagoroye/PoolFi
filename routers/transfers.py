"""
PoolFi Payouts and Transfers Router
Manages outbound capital distribution from group pots to designated rotation 
recipients via Nomba's core Transfers API infrastructure.
"""

import logging
from uuid import uuid4, UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import Group, GroupMember, User, UserRole, Payout, Contribution
from nomba_client import nomba_service

logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/api/groups",
    tags=["Payouts Management"]
)


@router.post(
    "/{group_id}/payouts",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger the cycle pot payout to the next scheduled group member"
)
async def initiate_group_payout(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Consolidates accumulated cycle contributions and dispatches the total 
    sum to the member holding the active rotation sequence position.
    """
    # 1. Authority Validation
    if current_user.role != UserRole.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only coordinators can authorize pot distributions."
        )

    # 2. Structural Ownership Verification
    group = db.query(Group).filter(Group.id == str(group_id)).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The specified savings pool ledger does not exist."
        )

    if group.coordinator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. You do not manage this savings circle."
        )

    # 3. Locate Recipient via Rotation Order Matrix
    current_cycle = group.current_cycle
    recipient_mapping = db.query(GroupMember).filter(
        GroupMember.group_id == str(group_id),
        GroupMember.rotation_position == current_cycle
    ).first()

    if not recipient_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No member assigned to rotation position slot {current_cycle} for this cycle."
        )

    recipient_user = db.query(User).filter(User.id == recipient_mapping.user_id).first()
    if not recipient_user or not recipient_user.bank_account_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recipient settlement profile contains invalid or missing NUBAN parameters."
        )

    # 4. Check for duplicate payouts on this specific cycle
    duplicate_payout = db.query(Payout).filter(
        Payout.group_id == str(group_id),
        Payout.cycle_number == current_cycle,
        Payout.status == "completed"
    ).first()

    if duplicate_payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cycle {current_cycle} pot has already been fully disbursed to {recipient_user.name}."
        )

    # 5. Compute Consolidated Pot Aggregations
    # Count members to find full expected pot volume
    total_members = db.query(GroupMember).filter(GroupMember.group_id == str(group_id)).count()
    total_pot_amount = float(group.contribution_amount) * total_members

    # 6. Initialize Local Audit Ledger (Pending State)
    merchant_tx_ref = uuid4()
    payout_record = Payout(
        group_id=str(group_id),
        recipient_id=str(recipient_user.id),
        cycle_number=current_cycle,
        amount=total_pot_amount,
        status="pending",
        nomba_transfer_ref=str(merchant_tx_ref)
    )
    db.add(payout_record)
    db.commit()

    # 7. Execute Secure Outbound Nomba Transfer Call
    try:
        logger.info(f"Dispatching pot payout of {total_pot_amount} NGN to {recipient_user.name} via Nomba Gateway.")
        
        transfer_response = await nomba_service.initiate_payout(
            amount=total_pot_amount,
            account_number=recipient_user.bank_account_number,
            account_name=recipient_user.name,
            bank_code=recipient_user.bank_code,
            merchant_tx_ref=str(merchant_tx_ref),
            narration=f"PoolFi Payout Group {group.name[:10]} Cycle {current_cycle}"
        )
        
        # Parse gateway response streams
        response_data = transfer_response.get("data", {})
        gateway_status = response_data.get("status", "SUCCESS") # Handle default fallbacks gracefully

        if gateway_status in ["SUCCESS", "PENDING"]:
            payout_record.status = "completed"
            payout_record.completed_at = db.text('NOW()')
            
            # Auto-advance the group cycle structure forward
            group.current_cycle += 1
            db.commit()
            
            logger.info(f"Payout transfer successfully executed for transaction reference {merchant_tx_ref}.")
            return {
                "status": "payout_dispatched",
                "cycle_processed": current_cycle,
                "amount_distributed": total_pot_amount,
                "recipient": recipient_user.name,
                "next_cycle": group.current_cycle
            }
        else:
            payout_record.status = "failed"
            db.commit()
            raise ValueError(f"Nomba settlement sub-system rejected transfer payload: {response_data.get('message')}")

    except Exception as e:
        db.refresh(payout_record)
        payout_record.status = "failed"
        db.commit()
        
        logger.error(f"Critical Bank Transfer Exception on payout execution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Outbound network settlement gateway error: {str(e)}"
        )


@router.get(
    "/{group_id}/payouts",
    status_code=status.HTTP_200_OK,
    summary="Fetch all historic payouts logged under this group"
)
async def get_group_payout_history(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the distribution history for auditing.
    """
    if current_user.role != UserRole.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    payouts = db.query(Payout).filter(Payout.group_id == str(group_id)).all()
    return payouts