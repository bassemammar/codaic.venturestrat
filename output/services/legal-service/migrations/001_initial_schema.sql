-- Initial database schema for Legal Service
-- Generated: 2026-01-04

-- Create legal_service table
CREATE TABLE IF NOT EXISTS legal_service (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_legal_service_name ON legal_service(name);
CREATE INDEX IF NOT EXISTS idx_legal_service_created_at ON legal_service(created_at);
CREATE INDEX IF NOT EXISTS idx_legal_service_metadata ON legal_service USING gin(metadata);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_legal_service_updated_at
    BEFORE UPDATE ON legal_service
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
