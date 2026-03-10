-- Initial database schema for Outreach Service
-- Generated: 2026-01-04

-- Create outreach_service table
CREATE TABLE IF NOT EXISTS outreach_service (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_outreach_service_name ON outreach_service(name);
CREATE INDEX IF NOT EXISTS idx_outreach_service_created_at ON outreach_service(created_at);
CREATE INDEX IF NOT EXISTS idx_outreach_service_metadata ON outreach_service USING gin(metadata);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_outreach_service_updated_at
    BEFORE UPDATE ON outreach_service
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
