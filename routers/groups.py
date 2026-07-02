"""
PoolFi Groups Router
Handles all core lifecycle endpoints for rotating savings groups (Ajo/Esusu),
restricted strictly to authenticated users with the 'coordinator' role.
"""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Core dependency and utility imports assumed from app architecture
from database import get_db
from auth import get_current_user
from models import Group, User, UserRole
from schemas import GroupCreate, GroupResponse

# Initialize logging for the groups infrastructure
logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/api/groups",
    tags=["Groups Management"]
)


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new rotating savings group"
)
async def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initializes a new Ajo/Esusu savings pool.
    
    Validates that the authenticated user possesses the coordinator ('oga') role 
    before committing the new group structural parameters to the database ledger.
    """
    # Security Requirement: Verify coordinator role via JWT claims
    if current_user.role != UserRole.COORDINATOR:
        logger.warning(
            f"Unauthorized group creation attempt by user {current_user.id} with role {current_user.role}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only coordinators can initialize savings groups."
        )

    try:
        new_group = Group(
            name=payload.name,
            coordinator_id=current_user.id,
            contribution_amount=payload.contribution_amount,
            cycle_frequency=payload.cycle_frequency,
            start_date=payload.start_date,
            current_cycle=1,
            status="active"
        )
        
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        logger.info(f"Group '{new_group.name}' successfully initialized by coordinator {current_user.id}")
        return new_group

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize savings group. Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while creating the group."
        )


@router.get(
    "",
    response_model=List[GroupResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all groups managed by the coordinator"
)
async def get_coordinator_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches all rotating savings groups owned explicitly by the authenticated coordinator.
    """
    if current_user.role != UserRole.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only coordinators can view managed groups."
        )

    try:
        groups = db.query(Group).filter(Group.coordinator_id == current_user.id).all()
        return groups

    except Exception as e:
        logger.error(f"Error querying coordinator groups for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching your groups ledger."
        )


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed structural mapping of a single group"
)
async def get_group_details(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves metadata details for a specific pool context.
    Strictly verifies ownership boundaries to prevent information leakage across separate coordinators.
    """
    if current_user.role != UserRole.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only coordinators can review group profiles."
        )

    group = db.query(Group).filter(Group.id == str(group_id)).first()
    
    if not group:
        logger.info(f"Coordinator {current_user.id} requested non-existent group metadata context: {group_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested savings group does not exist inside our records."
        )

    # Security Requirement: Strictly verify ownership boundary
    if group.coordinator_id != current_user.id:
        logger.warning(
            f"Cross-tenant data access violation attempt by coordinator {current_user.id} on group {group.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. You do not possess structural ownership permissions over this group."
        )

    return group