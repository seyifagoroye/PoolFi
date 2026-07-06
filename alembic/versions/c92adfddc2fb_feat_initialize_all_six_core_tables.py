"""feat: initialize all six core tables

Revision ID: c92adfddc2fb
Revises:
Create Date: 2026-07-01 21:08:52.953795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c92adfddc2fb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. USERS TABLE
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('coordinator', 'member', name='userrole'), nullable=False),
        sa.Column('bank_account_number', sa.String(20), nullable=False),
        sa.Column('bank_code', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_phone', 'users', ['phone'])

    # 2. GROUPS TABLE
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('coordinator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contribution_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('cycle_frequency', sa.Enum('weekly', 'monthly', name='cyclefrequency'), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('current_cycle', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('active', 'completed', 'paused', name='groupstatus'), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_groups_coordinator', 'groups', ['coordinator_id'])
    op.create_index('idx_groups_status', 'groups', ['status'])

    # 3. GROUP_MEMBERS TABLE
    op.create_table(
        'group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('rotation_position', sa.Integer, nullable=False),
        sa.Column('virtual_account_number', sa.String(20), nullable=True),
        sa.Column('virtual_account_ref', sa.String(255), unique=True, nullable=False),
        sa.Column('joined_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_group_members_group', 'group_members', ['group_id'])
    op.create_index('idx_group_members_user', 'group_members', ['user_id'])
    op.create_index('idx_group_members_virtual_account', 'group_members', ['virtual_account_number'])

    # 4. CONTRIBUTIONS TABLE
    op.create_table(
        'contributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('cycle_number', sa.Integer, nullable=False),
        sa.Column('expected_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.Enum('paid', 'underpaid', 'overpaid', 'unpaid', name='contributionstatus'), nullable=False, server_default='unpaid'),
        sa.Column('transaction_id', sa.String(255), unique=True, nullable=True),
        sa.Column('paid_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_contributions_group', 'contributions', ['group_id'])
    op.create_index('idx_contributions_member', 'contributions', ['member_id'])
    op.create_index('idx_contributions_cycle', 'contributions', ['cycle_number'])
    op.create_index('idx_contributions_status', 'contributions', ['status'])
    op.create_index('idx_contributions_transaction', 'contributions', ['transaction_id'])

    # 5. PAYOUTS TABLE
    op.create_table(
        'payouts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('cycle_number', sa.Integer, nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', name='payoutstatus'), nullable=False, server_default='pending'),
        sa.Column('nomba_transfer_ref', sa.String(255), nullable=True),
        sa.Column('initiated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_payouts_group', 'payouts', ['group_id'])
    op.create_index('idx_payouts_recipient', 'payouts', ['recipient_id'])
    op.create_index('idx_payouts_status', 'payouts', ['status'])
    op.create_index('idx_payouts_cycle', 'payouts', ['cycle_number'])
    op.create_index('idx_payouts_ref', 'payouts', ['nomba_transfer_ref'])

    # 6. WEBHOOK_EVENTS TABLE
    op.create_table(
        'webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('nomba_request_id', sa.String(255), unique=True, nullable=False),
        sa.Column('transaction_id', sa.String(255), nullable=False),
        sa.Column('raw_payload', sa.JSON, nullable=False),
        sa.Column('processed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('received_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_webhook_events_type', 'webhook_events', ['event_type'])
    op.create_index('idx_webhook_events_request', 'webhook_events', ['nomba_request_id'])
    op.create_index('idx_webhook_events_transaction', 'webhook_events', ['transaction_id'])
    op.create_index('idx_webhook_events_processed', 'webhook_events', ['processed'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('webhook_events')
    op.drop_table('payouts')
    op.drop_table('contributions')
    op.drop_table('group_members')
    op.drop_table('groups')
    op.drop_table('users')

    op.execute('DROP TYPE IF EXISTS payoutstatus')
    op.execute('DROP TYPE IF EXISTS contributionstatus')
    op.execute('DROP TYPE IF EXISTS groupstatus')
    op.execute('DROP TYPE IF EXISTS cyclefrequency')
    op.execute('DROP TYPE IF EXISTS userrole')
