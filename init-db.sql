-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear esquema principal
CREATE SCHEMA IF NOT EXISTS public;
