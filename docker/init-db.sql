-- Initialize PacketArch database
-- This script runs when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom enum types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sequencetype') THEN
        CREATE TYPE sequencetype AS ENUM (
            'startup', 'shutdown', 'poll_cycle', 'write_sequence',
            'error_recovery', 'state_transition', 'heartbeat', 'alarm'
        );
    END IF;
END$$;

-- TimescaleDB should already be available from the base image
-- but we ensure it's enabled
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create schema for better organization (optional)
-- CREATE SCHEMA IF NOT EXISTS packetarch;

-- Grant permissions (for development)
GRANT ALL PRIVILEGES ON DATABASE packetarch TO packetarch;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PacketArch database initialized successfully';
END $$;
