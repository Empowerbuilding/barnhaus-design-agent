-- setup_db.sql — Frank agent database bootstrap
-- Run this against a fresh Frank Supabase project to create all required tables.
-- Schema matches the live production DB (stlvgflkgqhtxfxuorvf).
--
-- After running this, seed unit_costs by running:
--   python3 automation/seed_unit_costs.py
--
-- NOTE: Never reference BudgetBuilder in live operations. All unit costs live
--       in the unit_costs table below. BudgetBuilder is READ-ONLY for seeding only.

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── projects ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                text NOT NULL,
    address             text,
    description         text,
    plan_files          jsonb DEFAULT '[]'::jsonb,
    status              text DEFAULT 'active',
    discord_channel_id  text,
    takeoffs_synced_at  timestamptz,
    plan_summary        text,
    plan_context        jsonb DEFAULT '{}'::jsonb,
    created_at          timestamptz DEFAULT now()
);

-- ─── subcontractors ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcontractors (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name    text NOT NULL,
    trade           text,
    email           text,
    phone           text,
    contact_name    text,
    city            text,
    region          text,
    notes           text,
    active          boolean DEFAULT true,
    preferred       boolean DEFAULT false,
    avg_bid_price   numeric,
    last_bid_date   date,
    source          text DEFAULT 'manual',
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subcontractors_trade  ON subcontractors(trade);
CREATE INDEX IF NOT EXISTS idx_subcontractors_email  ON subcontractors(email);
CREATE INDEX IF NOT EXISTS idx_subcontractors_active ON subcontractors(active);

-- ─── takeoffs ────────────────────────────────────────────────────────────────
-- NOTE: Column names are item_type and quantity (NOT type_name/count — those
--       are the OLD incorrect names). Schema matches live DB exactly.
CREATE TABLE IF NOT EXISTS takeoffs (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid REFERENCES projects(id) ON DELETE CASCADE,
    category    text,
    item_type   text,           -- e.g. "Wall 2x6 Ext Stucco", "Door — 3068 Single"
    description text,           -- human-readable line description
    quantity    numeric,        -- count (EA), area (SF), length (LF), etc.
    unit        text,           -- "EA", "SF", "LF", "CY", etc.
    notes       text,
    trade       text,           -- e.g. "Wood Framing", "Roofing", "Drywall"
    source      text DEFAULT 'revit_bridge',
    created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_takeoffs_project_id ON takeoffs(project_id);
CREATE INDEX IF NOT EXISTS idx_takeoffs_category   ON takeoffs(category);
CREATE INDEX IF NOT EXISTS idx_takeoffs_trade       ON takeoffs(trade);

-- ─── unit_costs ──────────────────────────────────────────────────────────────
-- Frank's own unit cost library — seeded from BB via seed_unit_costs.py.
-- All cost lookups in live operations MUST use this table only.
CREATE TABLE IF NOT EXISTS unit_costs (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item             text NOT NULL,
    category         text,
    unit             text,
    unit_cost        numeric,
    actual_unit_cost numeric,
    multiplier       numeric DEFAULT 1,
    code             text,
    source           text DEFAULT 'budget_builder',
    created_at       timestamptz DEFAULT now(),
    updated_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_unit_costs_item     ON unit_costs(item);
CREATE INDEX IF NOT EXISTS idx_unit_costs_category ON unit_costs(category);

-- ─── rfqs ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rfqs (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid REFERENCES projects(id) ON DELETE CASCADE,
    subcontractor_id  uuid REFERENCES subcontractors(id),
    trade             text NOT NULL,
    sent_at           timestamptz DEFAULT now(),
    status            text DEFAULT 'sent',   -- sent | responded | declined | awarded
    email_message_id  text
);

CREATE INDEX IF NOT EXISTS idx_rfqs_project_id       ON rfqs(project_id);
CREATE INDEX IF NOT EXISTS idx_rfqs_subcontractor_id ON rfqs(subcontractor_id);
CREATE INDEX IF NOT EXISTS idx_rfqs_trade            ON rfqs(trade);

-- ─── bids ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bids (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rfq_id            uuid REFERENCES rfqs(id) ON DELETE CASCADE,
    project_id        uuid REFERENCES projects(id),
    subcontractor_id  uuid REFERENCES subcontractors(id),
    trade             text,
    amount            numeric,
    notes             text,
    received_at       timestamptz DEFAULT now(),
    status            text DEFAULT 'received'  -- received | accepted | rejected
);

CREATE INDEX IF NOT EXISTS idx_bids_project_id ON bids(project_id);
CREATE INDEX IF NOT EXISTS idx_bids_rfq_id     ON bids(rfq_id);

-- ─── bid_questions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bid_questions (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bid_id            uuid REFERENCES bids(id) ON DELETE CASCADE,
    question          text,
    answer            text,
    created_at        timestamptz DEFAULT now()
);
