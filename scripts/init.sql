-- ===========================================
-- Script de inicialización de AI Engine
-- ===========================================

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsquedas de texto

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE 'Base de datos AI Engine inicializada correctamente';
END $$;
