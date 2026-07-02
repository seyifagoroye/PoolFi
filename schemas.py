from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from models import UserRole, CycleFrequency, GroupStatus, ContributionStatus, PayoutStatus

# ==========================================
# USER SCHEMAS
# ==========================================

class UserBase(BaseModel):
    name: str = Field(..., max_length=255, description="Full legal name of the participant")
    phone: str = Field(..., description="Phone number in international or localized format")
    email: EmailStr
    role: UserRole
    bank_account_number: str = Field(..., min_length=10, max_length=10, description="10-digit Nigerian NUBAN account number")
    bank_code: str = Field(..., description="Standard Central Bank of Nigeria bank routing code")

    @field_validator("bank_account_number")
    @classmethod
    def validate_nuban(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Bank account number must contain only numeric digits")
        return value

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext password, minimum 8 characters for security compliance")

class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# GROUP SCHEMAS
# ==========================================

class GroupBase(BaseModel):
    name: str = Field(..., max_length=255, description="The public name of the savings circle")
    contribution_amount: Decimal = Field(..., gt=0, description="The fixed baseline amount contributed per cycle per member")
    cycle_frequency: CycleFrequency
    start_date: date

class GroupCreate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: UUID
    coordinator_id: UUID
    current_cycle: int
    status: GroupStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# GROUP MEMBER SCHEMAS
# ==========================================

class GroupMemberBase(BaseModel):
    user_id: UUID
    rotation_position: int = Field(..., gt=0, description="Assigned collection sequence slot within the cycle pool")

class GroupMemberCreate(GroupMemberBase):
    pass

class GroupMemberResponse(GroupMemberBase):
    id: UUID
    group_id: UUID
    virtual_account_number: Optional[str] = None
    virtual_account_ref: str
    joined_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# CONTRIBUTION SCHEMAS
# ==========================================

class ContributionResponse(BaseModel):
    id: UUID
    group_id: UUID
    member_id: UUID
    cycle_number: int
    expected_amount: Decimal
    paid_amount: Decimal
    status: ContributionStatus
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# PAYOUT SCHEMAS
# ==========================================

class PayoutResponse(BaseModel):
    id: UUID
    group_id: UUID
    recipient_id: UUID
    cycle_number: int
    amount: Decimal
    status: PayoutStatus
    nomba_transfer_ref: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# WEBHOOK EVENT SCHEMAS
# ==========================================

class WebhookEventResponse(BaseModel):
    id: UUID
    event_type: str
    nomba_request_id: str
    transaction_id: str
    raw_payload: Dict[str, Any]
    processed: bool
    received_at: datetime

    class Config:
        from_attributes = True
        from pydantic import BaseModel, Field
from uuid import UUID

class MemberInviteSchema(BaseModel):
    user_id: UUID
    rotation_position: int = Field(..., gt=0, description="Position in the rotation order")