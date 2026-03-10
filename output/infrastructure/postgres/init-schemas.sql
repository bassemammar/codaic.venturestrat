-- PostgreSQL Schema Initialization for VentureStrat
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Registry Schema (platform registry service - tenants, models, configs)
CREATE SCHEMA IF NOT EXISTS registry;

-- Auth Schema (authentication service - users, roles, sessions, permissions)
CREATE SCHEMA IF NOT EXISTS auth;

-- Shared Schema (multi-tenancy, global config)
CREATE SCHEMA IF NOT EXISTS shared;

-- Domain Schema (domain entities)
CREATE SCHEMA IF NOT EXISTS venturestrat;

-- Audit Schema (security audit logs)
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant all schemas to the platform user
DO $$
DECLARE
  schema_name TEXT;
BEGIN
  FOREACH schema_name IN ARRAY ARRAY['registry', 'auth', 'shared', 'venturestrat', 'audit']
  LOOP
    EXECUTE format('GRANT ALL PRIVILEGES ON SCHEMA %I TO venturestrat', schema_name);
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA %I TO venturestrat', schema_name);
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA %I TO venturestrat', schema_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT ALL ON TABLES TO venturestrat', schema_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT ALL ON SEQUENCES TO venturestrat', schema_name);
  END LOOP;
END $$;

-- Tenants Table (multi-tenancy SDK)
CREATE TABLE IF NOT EXISTS shared.tenant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default tenant
INSERT INTO shared.tenant (id, name, slug, status) VALUES
    ('00000000-0000-0000-0000-000000000000', 'Default', 'default', 'active')
ON CONFLICT (id) DO NOTHING;

-- Event Audit Table (event-monitor service)
CREATE TABLE IF NOT EXISTS shared.event_audit (
    id UUID PRIMARY KEY,
    correlation_id VARCHAR(36),
    trace_id VARCHAR(32),
    parent_event_id VARCHAR(36),
    topic VARCHAR(255) NOT NULL,
    event_key VARCHAR(255),
    event_id VARCHAR(36),
    producer_service VARCHAR(100),
    consumer_service VARCHAR(100),
    consumer_group VARCHAR(255),
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    action VARCHAR(50),
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'observed',
    duration_ms INTEGER,
    attempt INTEGER DEFAULT 1,
    payload JSONB,
    error_message TEXT,
    error_type VARCHAR(255),
    tenant_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ea_correlation ON shared.event_audit (correlation_id);
CREATE INDEX IF NOT EXISTS idx_ea_topic ON shared.event_audit (topic);
CREATE INDEX IF NOT EXISTS idx_ea_entity ON shared.event_audit (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ea_status ON shared.event_audit (status);
CREATE INDEX IF NOT EXISTS idx_ea_created ON shared.event_audit (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ea_service ON shared.event_audit (producer_service);

-- Forge Schema (requirements management service)
CREATE SCHEMA IF NOT EXISTS forge;

-- Forge Requirements Table
CREATE TABLE IF NOT EXISTS forge.requirement (
    id SERIAL PRIMARY KEY,
    requirement_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requirement_type VARCHAR(50) NOT NULL DEFAULT 'new_feature',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'draft',
    spec_content TEXT,
    spec_metadata JSONB DEFAULT '{}',
    adw_execution_id VARCHAR(8),
    execution_status VARCHAR(50),
    execution_started_at TIMESTAMPTZ,
    execution_completed_at TIMESTAMPTZ,
    execution_error TEXT,
    current_phase VARCHAR(50),
    plan_status VARCHAR(50), build_status VARCHAR(50), ship_status VARCHAR(50),
    plan_started_at TIMESTAMPTZ, plan_completed_at TIMESTAMPTZ,
    build_started_at TIMESTAMPTZ, build_completed_at TIMESTAMPTZ,
    ship_started_at TIMESTAMPTZ, ship_completed_at TIMESTAMPTZ,
    phase_error_message TEXT,
    submitter_id INTEGER,
    reviewer_id INTEGER,
    review_comments TEXT,
    retry_count INTEGER DEFAULT 0,
    intervention_log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    CONSTRAINT chk_req_type CHECK (requirement_type IN ('bug_fix', 'new_feature', 'enhancement', 'change_request')),
    CONSTRAINT chk_req_priority CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_req_status CHECK (status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'executing', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS forge.requirement_version (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER REFERENCES forge.requirement(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    spec_content TEXT,
    spec_metadata JSONB DEFAULT '{}',
    created_by INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forge.requirement_audit (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER REFERENCES forge.requirement(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    actor_id INTEGER,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_forge_req_status ON forge.requirement (status);
CREATE INDEX IF NOT EXISTS idx_forge_req_type ON forge.requirement (requirement_type);
CREATE INDEX IF NOT EXISTS idx_forge_req_created ON forge.requirement (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forge_req_exec ON forge.requirement (execution_status);
CREATE INDEX IF NOT EXISTS idx_forge_audit_req ON forge.requirement_audit (requirement_id);

-- Grant forge schema to platform user
GRANT ALL PRIVILEGES ON SCHEMA forge TO venturestrat;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA forge TO venturestrat;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA forge TO venturestrat;
ALTER DEFAULT PRIVILEGES IN SCHEMA forge GRANT ALL ON TABLES TO venturestrat;
ALTER DEFAULT PRIVILEGES IN SCHEMA forge GRANT ALL ON SEQUENCES TO venturestrat;

-- Set default search path
ALTER DATABASE venturestrat SET search_path TO shared, venturestrat, registry, auth, audit, forge, public;
