import enum
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, 
    String, 
    Integer, 
    Numeric, 
    Boolean, 
    DateTime, 
    Date, 
    ForeignKey, 
    Enum, 
    JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

# ==========================================
# ENUMERATED TYPES (Strict Type Safety)
# ==========================================

class UserRole(str, enum.Enum):
    COORDINATOR = "coordinator"
    MEMBER = "member"

class CycleFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class GroupStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"

class ContributionStatus(str, enum.Enum):
    PAID = "paid"
    UNDERPAID = "underpaid"
    OVERPAID = "overpaid"
    UNPAID = "unpaid"

class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

# ==========================================
# DATABASE MODELS
# ==========================================

class User(Base):
    """
    Represents an authenticated participant on the platform.
    Can act as a group coordinator (Oga) or an individual group member.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    bank_account_number = Column(String(20), nullable=False)
    bank_code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    managed_groups = relationship("Group", back_populates="coordinator")
    group_memberships = relationship("GroupMember", back_populates="user")
    contributions = relationship("Contribution", back_populates="member")
    payouts = relationship("Payout", back_populates="recipient")


class Group(Base):
    """
    Represents an active or historical digital rotating Ajo/Esusu savings group.
    """
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    coordinator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    contribution_amount = Column(Numeric(12, 2), nullable=False)
    cycle_frequency = Column(Enum(CycleFrequency), nullable=False)
    start_date = Column(Date, nullable=False)
    current_cycle = Column(Integer, default=1, nullable=False)
    status = Column(Enum(GroupStatus), default=GroupStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    coordinator = relationship("User", back_populates="managed_groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    contributions = relationship("Contribution", back_populates="group", cascade="all, delete-orphan")
    payouts = relationship("Payout", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """
    Intersection table mapping users explicitly to instances of savings groups.
    Captures the specific dynamic infrastructure parameters mapping to Nomba Sub-Accounts.
    """
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    rotation_position = Column(Integer, nullable=False)
    virtual_account_number = Column(String(20), nullable=True, index=True)
    virtual_account_ref = Column(String(255), unique=True, nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class Contribution(Base):
    """
    Tracks cycle ledger entries evaluating incoming user bank transfers.
    Provides direct infrastructure safeguards against double-ledger accounting entries.
    """
    __tablename__ = "contributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False, index=True)
    expected_amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    status = Column(Enum(ContributionStatus), default=ContributionStatus.UNPAID, nullable=False, index=True)
    transaction_id = Column(String(255), unique=True, nullable=True, index=True) # Idempotency ledger check
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    group = relationship("Group", back_populates="contributions")
    member = relationship("User", back_populates="contributions")


class Payout(Base):
    """
    Logs outward fund settlement movements generated via Nomba Transfers API.
    """
    __tablename__ = "payouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(PayoutStatus), default=PayoutStatus.PENDING, nullable=False, index=True)
    nomba_transfer_ref = Column(String(255), nullable=True, index=True) # Maps to unique API outbounds
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    group = relationship("Group", back_populates="payouts")
    recipient = relationship("User", back_populates="payouts")


class WebhookEvent(Base):
    """
    Audit ledger tracking unique webhooks inbound from Nomba payment routers.
    Guarantees absolute immediate ingestion and post-transaction validation tracking.
    """
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    nomba_request_id = Column(String(255), unique=True, nullable=False, index=True) # Main validation identity
    transaction_id = Column(String(255), nullable=False, index=True)
    raw_payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)