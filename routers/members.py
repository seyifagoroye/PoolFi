import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import Group, GroupMember, User, UserRole
from schemas import MemberInviteSchema
from nomba_client import nomba_service

logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/api/groups",
    tags=["Members Management"]
)

@router.post(
    "/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a group and provision a Nomba virtual account"
)
async def add_member_to_group(
    group_id: UUID,
    payload: MemberInviteSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.COORDINATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    group = db.query(Group).filter(Group.id == str(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    if group.coordinator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not manage this group.")

    target_member = db.query(User).filter(User.id == str(payload.user_id)).first()
    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    already_member = db.query(GroupMember).filter(
        GroupMember.group_id == str(group_id),
        GroupMember.user_id == str(payload.user_id)
    ).first()
    if already_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already in this group.")

    account_ref = f"REF_{str(group_id).replace('-','')[:8].upper()}_{str(payload.user_id).replace('-','')[:8].upper()}"

    try:
        logger.info(f"Initiating Nomba virtual account allocation for user {target_member.id} in group {group_id}")
        nomba_va_response = await nomba_service.create_virtual_account(
            account_ref=account_ref,
            account_name=f"PoolFi/{target_member.name}",
        )
        logger.info(f"Full Nomba VA response: {nomba_va_response}")
        va_data = nomba_va_response.get("data", {})
        account_number = va_data.get("bankAccountNumber")
        if not account_number:
            raise ValueError("Nomba response did not return a valid account number.")
    except Exception as e:
        logger.error(f"Nomba Virtual Account generation failure: {str(e)}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to provision banking infrastructure from provider gateway.")

    try:
        new_enrollment = GroupMember(
            group_id=str(group_id),
            user_id=str(target_member.id),
            rotation_position=payload.rotation_position,
            virtual_account_number=account_number,
            virtual_account_ref=account_ref
        )
        db.add(new_enrollment)
        db.commit()
        db.refresh(new_enrollment)
        logger.info(f"User {target_member.id} successfully bound to pool {group_id} via account {account_number}")
        return {
            "status": "success",
            "message": "Member successfully added to group",
            "data": {
                "member_id": str(target_member.id),
                "group_id": str(group_id),
                "virtual_bank_name": va_data.get("bankName", "Nombank MFB"),
                "virtual_account_number": account_number,
                "rotation_position": new_enrollment.rotation_position
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Internal database enrollment commit crash: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record membership.")
