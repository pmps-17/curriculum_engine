-- Initialize PostgreSQL for curriculum_engine
-- Note: appuser and curriculum_engine are already created by POSTGRES_USER and POSTGRES_DB env vars
-- Just enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
