-- Migration 001: Mark initial schema as applied
-- This migration does nothing - schema.sql already created all tables.
-- Its purpose is to set user_version=1 so future migrations work correctly.
SELECT 1;
