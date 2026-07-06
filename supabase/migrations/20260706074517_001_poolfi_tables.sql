/*
# PoolFi Core Schema - Part 1: Tables and Basic Policies

Creates all six core tables for the PoolFi Ajo/Esusu platform:
a digital infrastructure for Nigerian rotating savings groups.

## Tables Created:
1. users - Platform participants (coordinators and members)
2. groups - Rotating savings circles
3. group_members - Membership junction table
4. contributions - Payment tracking ledger
5. payouts - Disbursement records
6. webhook_events - Payment webhook audit log

Basic RLS policies for self-referencing tables included.
Cross-table dependent policies added in Part 2.
*/

-- Enable uuid extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    phone text UNIQUE NOT NULL,
    email text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('coordinator', 'member')),
    bank_account_number text NOT NULL,
    bank_code text NOT NULL,
    created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_read_own" ON users;
CREATE POLICY "users_read_own" ON users FOR SELECT
    TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "users_update_own" ON users;
CREATE POLICY "users_update_own" ON users FOR UPDATE
    TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "users_insert_own" ON users;
CREATE POLICY "users_insert_own" ON users FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = id);

-- 2. GROUPS TABLE
CREATE TABLE IF NOT EXISTS groups (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    coordinator_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    contribution_amount numeric(12, 2) NOT NULL,
    cycle_frequency text NOT NULL CHECK (cycle_frequency IN ('weekly', 'monthly')),
    start_date date NOT NULL,
    current_cycle integer DEFAULT 1 NOT NULL,
    status text DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'completed', 'paused')),
    created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_groups_coordinator ON groups(coordinator_id);
CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status);

ALTER TABLE groups ENABLE ROW LEVEL SECURITY;

-- Temporary simple policies, will be updated in Part 2
DROP POLICY IF EXISTS "groups_select_coordinator" ON groups;
CREATE POLICY "groups_select_coordinator" ON groups FOR SELECT
    TO authenticated USING (coordinator_id = auth.uid());

DROP POLICY IF EXISTS "groups_insert_coordinator" ON groups;
CREATE POLICY "groups_insert_coordinator" ON groups FOR INSERT
    TO authenticated WITH CHECK (coordinator_id = auth.uid());

DROP POLICY IF EXISTS "groups_update_coordinator" ON groups;
CREATE POLICY "groups_update_coordinator" ON groups FOR UPDATE
    TO authenticated USING (coordinator_id = auth.uid()) WITH CHECK (coordinator_id = auth.uid());

-- 3. GROUP_MEMBERS TABLE
CREATE TABLE IF NOT EXISTS group_members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rotation_position integer NOT NULL,
    virtual_account_number text,
    virtual_account_ref text UNIQUE NOT NULL,
    joined_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_virtual_account ON group_members(virtual_account_number);

ALTER TABLE group_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "group_members_select_member" ON group_members;
CREATE POLICY "group_members_select_member" ON group_members FOR SELECT
    TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "group_members_insert_coordinator" ON group_members;
CREATE POLICY "group_members_insert_coordinator" ON group_members FOR INSERT
    TO authenticated WITH CHECK (
        EXISTS (
            SELECT 1 FROM groups WHERE groups.id = group_members.group_id AND groups.coordinator_id = auth.uid()
        )
    );

-- 4. CONTRIBUTIONS TABLE
CREATE TABLE IF NOT EXISTS contributions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE RESTRICT,
    member_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    cycle_number integer NOT NULL,
    expected_amount numeric(12, 2) NOT NULL,
    paid_amount numeric(12, 2) DEFAULT 0.00 NOT NULL,
    status text DEFAULT 'unpaid' NOT NULL CHECK (status IN ('paid', 'underpaid', 'overpaid', 'unpaid')),
    transaction_id text UNIQUE,
    paid_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_contributions_group ON contributions(group_id);
CREATE INDEX IF NOT EXISTS idx_contributions_member ON contributions(member_id);
CREATE INDEX IF NOT EXISTS idx_contributions_cycle ON contributions(cycle_number);
CREATE INDEX IF NOT EXISTS idx_contributions_status ON contributions(status);
CREATE INDEX IF NOT EXISTS idx_contributions_transaction ON contributions(transaction_id);

ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "contributions_select_member" ON contributions;
CREATE POLICY "contributions_select_member" ON contributions FOR SELECT
    TO authenticated USING (member_id = auth.uid());

DROP POLICY IF EXISTS "contributions_insert_coordinator" ON contributions;
CREATE POLICY "contributions_insert_coordinator" ON contributions FOR INSERT
    TO authenticated WITH CHECK (
        EXISTS (
            SELECT 1 FROM groups WHERE groups.id = contributions.group_id AND groups.coordinator_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "contributions_update_coordinator" ON contributions;
CREATE POLICY "contributions_update_coordinator" ON contributions FOR UPDATE
    TO authenticated USING (
        EXISTS (
            SELECT 1 FROM groups WHERE groups.id = contributions.group_id AND groups.coordinator_id = auth.uid()
        )
    );

-- 5. PAYOUTS TABLE
CREATE TABLE IF NOT EXISTS payouts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE RESTRICT,
    recipient_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    cycle_number integer NOT NULL,
    amount numeric(12, 2) NOT NULL,
    status text DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    nomba_transfer_ref text,
    initiated_at timestamptz DEFAULT now() NOT NULL,
    completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_payouts_group ON payouts(group_id);
CREATE INDEX IF NOT EXISTS idx_payouts_recipient ON payouts(recipient_id);
CREATE INDEX IF NOT EXISTS idx_payouts_status ON payouts(status);
CREATE INDEX IF NOT EXISTS idx_payouts_cycle ON payouts(cycle_number);
CREATE INDEX IF NOT EXISTS idx_payouts_ref ON payouts(nomba_transfer_ref);

ALTER TABLE payouts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "payouts_select_recipient" ON payouts;
CREATE POLICY "payouts_select_recipient" ON payouts FOR SELECT
    TO authenticated USING (recipient_id = auth.uid());

DROP POLICY IF EXISTS "payouts_insert_coordinator" ON payouts;
CREATE POLICY "payouts_insert_coordinator" ON payouts FOR INSERT
    TO authenticated WITH CHECK (
        EXISTS (
            SELECT 1 FROM groups WHERE groups.id = payouts.group_id AND groups.coordinator_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "payouts_update_coordinator" ON payouts;
CREATE POLICY "payouts_update_coordinator" ON payouts FOR UPDATE
    TO authenticated USING (
        EXISTS (
            SELECT 1 FROM groups WHERE groups.id = payouts.group_id AND groups.coordinator_id = auth.uid()
        )
    );

-- 6. WEBHOOK_EVENTS TABLE
CREATE TABLE IF NOT EXISTS webhook_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    nomba_request_id text UNIQUE NOT NULL,
    transaction_id text NOT NULL,
    raw_payload jsonb NOT NULL,
    processed boolean DEFAULT false NOT NULL,
    received_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_request ON webhook_events(nomba_request_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_transaction ON webhook_events(transaction_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON webhook_events(processed);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;