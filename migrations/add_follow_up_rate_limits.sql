-- 🛡️ FOLLOW-UP RATE LIMITS TABLE
-- Prevenir spam de follow-ups: máximo 1 por día por usuario

-- Tabla para control de rate limiting de follow-ups
CREATE TABLE IF NOT EXISTS follow_up_rate_limits (
    user_id VARCHAR(255) PRIMARY KEY,
    last_followup_sent TIMESTAMP WITH TIME ZONE,
    daily_count INTEGER DEFAULT 0,
    reset_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_follow_up_rate_limits_reset_date ON follow_up_rate_limits(reset_date);
CREATE INDEX IF NOT EXISTS idx_follow_up_rate_limits_last_sent ON follow_up_rate_limits(last_followup_sent);

-- Tabla para locks de recovery operations (prevenir race conditions)
CREATE TABLE IF NOT EXISTS follow_up_recovery_locks (
    user_id VARCHAR(255) PRIMARY KEY,
    last_recovery_attempt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    recovery_type VARCHAR(50), -- 'critical', 'emergency', 'manual'
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para cleanup de locks expirados
CREATE INDEX IF NOT EXISTS idx_follow_up_recovery_locks_expired ON follow_up_recovery_locks(locked_until);

-- Constraint adicional para prevenir jobs duplicados (mismo usuario, mismo stage, pendientes)
-- Solo se puede agregar si la tabla follow_up_jobs ya existe
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'follow_up_jobs') THEN
        -- Intentar agregar constraint si no existe
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'unique_pending_job_per_user_stage'
        ) THEN
            ALTER TABLE follow_up_jobs 
            ADD CONSTRAINT unique_pending_job_per_user_stage 
            UNIQUE (user_id, stage) 
            DEFERRABLE INITIALLY DEFERRED;
        END IF;
    END IF;
END $$;

-- Function para limpiar rate limits diariamente (auto-reset)
CREATE OR REPLACE FUNCTION reset_daily_follow_up_limits() RETURNS void AS $$
BEGIN
    UPDATE follow_up_rate_limits 
    SET daily_count = 0, reset_date = CURRENT_DATE 
    WHERE reset_date < CURRENT_DATE;
    
    DELETE FROM follow_up_recovery_locks 
    WHERE locked_until < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Trigger para auto-update updated_at
CREATE OR REPLACE FUNCTION update_follow_up_rate_limits_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_follow_up_rate_limits_updated_at
    BEFORE UPDATE ON follow_up_rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_follow_up_rate_limits_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE follow_up_rate_limits IS '🛡️ Rate limiting para follow-ups: máximo 1 por día por usuario';
COMMENT ON TABLE follow_up_recovery_locks IS '🔒 Locks para prevenir race conditions en recovery systems';
COMMENT ON FUNCTION reset_daily_follow_up_limits() IS '🔄 Reset automático de rate limits diarios y cleanup de locks';