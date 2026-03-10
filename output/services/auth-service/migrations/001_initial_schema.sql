-- Initial database schema for Auth Service
-- Generated: 2026-01-04

-- Create auth_service table
CREATE TABLE IF NOT EXISTS auth_service (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_auth_service_name ON auth_service(name);
CREATE INDEX IF NOT EXISTS idx_auth_service_created_at ON auth_service(created_at);
CREATE INDEX IF NOT EXISTS idx_auth_service_metadata ON auth_service USING gin(metadata);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_auth_service_updated_at
    BEFORE UPDATE ON auth_service
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
