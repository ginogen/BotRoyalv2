-- =====================================================
-- 📅 SISTEMA DE FOLLOW-UP - ROYAL BOT V2
-- Tablas para seguimiento automático de usuarios inactivos
-- =====================================================

-- Tabla principal de trabajos de follow-up programados
CREATE TABLE IF NOT EXISTS follow_up_jobs (
    id SERIAL PRIMARY KEY,
    
    -- Identificación del usuario
    user_id VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    
    -- Configuración del follow-up
    stage INTEGER NOT NULL,                    -- 1-8 (etapas del follow-up)
    scheduled_for TIMESTAMP NOT NULL,          -- Cuándo enviar el mensaje
    
    -- Estado del trabajo
    status VARCHAR(50) DEFAULT 'pending',      -- pending, sent, cancelled, failed
    attempts INTEGER DEFAULT 0,               -- Número de intentos de envío
    max_attempts INTEGER DEFAULT 3,           -- Máximo de reintentos
    
    -- Contexto y metadata
    context_snapshot JSONB,                   -- Snapshot del contexto del usuario
    last_user_message TEXT,                   -- Último mensaje del usuario
    trigger_event VARCHAR(100),               -- Qué disparó el follow-up
    
    -- Control de tiempo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    
    -- Evitar duplicados por usuario y etapa
    UNIQUE(user_id, stage)
);

-- Historial completo de follow-ups enviados
CREATE TABLE IF NOT EXISTS follow_up_history (
    id SERIAL PRIMARY KEY,
    
    -- Identificación
    user_id VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    stage INTEGER NOT NULL,
    
    -- Contenido del follow-up
    message_sent TEXT NOT NULL,
    template_used VARCHAR(100),
    generation_model VARCHAR(50),
    
    -- Timing y respuesta
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_responded BOOLEAN DEFAULT FALSE,
    responded_at TIMESTAMP,
    response_message TEXT,
    
    -- Métricas
    response_time_hours DECIMAL(10,2),       -- Horas hasta respuesta
    effectiveness_score DECIMAL(3,2),        -- Score 0-1 de efectividad
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Configuración global del sistema de follow-up
CREATE TABLE IF NOT EXISTS follow_up_config (
    id SERIAL PRIMARY KEY,
    
    -- Configuración de timing
    stage_delays_hours INTEGER[] DEFAULT '{1,6,24,48,72,96,120,168}', -- Delays en horas
    
    -- Horarios permitidos
    start_hour INTEGER DEFAULT 9,            -- 9 AM
    end_hour INTEGER DEFAULT 21,             -- 9 PM
    timezone VARCHAR(50) DEFAULT 'America/Argentina/Cordoba',
    
    -- Días de la semana permitidos (1-7, donde 1=lunes)
    allowed_weekdays INTEGER[] DEFAULT '{1,2,3,4,5,6}', -- Lunes a sábado
    
    -- Configuración de límites
    max_followups_per_user INTEGER DEFAULT 8,
    cooldown_between_stages_hours INTEGER DEFAULT 1,
    
    -- Control de activación
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blacklist de usuarios que no quieren follow-ups
CREATE TABLE IF NOT EXISTS follow_up_blacklist (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    reason VARCHAR(200),                     -- Razón del opt-out
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by VARCHAR(100) DEFAULT 'user'      -- user, admin, system
);

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices para follow_up_jobs
CREATE INDEX IF NOT EXISTS idx_followup_jobs_scheduled ON follow_up_jobs(scheduled_for, status);
CREATE INDEX IF NOT EXISTS idx_followup_jobs_user ON follow_up_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_followup_jobs_status ON follow_up_jobs(status);
CREATE INDEX IF NOT EXISTS idx_followup_jobs_stage ON follow_up_jobs(stage);

-- Índices para follow_up_history
CREATE INDEX IF NOT EXISTS idx_followup_history_user_time ON follow_up_history(user_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_followup_history_stage ON follow_up_history(stage);
CREATE INDEX IF NOT EXISTS idx_followup_history_responded ON follow_up_history(user_responded);
CREATE INDEX IF NOT EXISTS idx_followup_history_sent_at ON follow_up_history(sent_at);

-- Índices para follow_up_blacklist
CREATE INDEX IF NOT EXISTS idx_followup_blacklist_user ON follow_up_blacklist(user_id);
CREATE INDEX IF NOT EXISTS idx_followup_blacklist_phone ON follow_up_blacklist(phone);

-- =====================================================
-- FUNCIONES DE UTILIDAD
-- =====================================================

-- Función para limpiar trabajos antiguos (más de 30 días)
CREATE OR REPLACE FUNCTION cleanup_old_followup_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM follow_up_jobs 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
    AND status IN ('sent', 'cancelled', 'failed');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE 'plpgsql';

-- Función para cancelar follow-ups de un usuario específico
CREATE OR REPLACE FUNCTION cancel_user_followups(target_user_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    cancelled_count INTEGER;
BEGIN
    UPDATE follow_up_jobs 
    SET status = 'cancelled', processed_at = CURRENT_TIMESTAMP
    WHERE user_id = target_user_id 
    AND status = 'pending';
    
    GET DIAGNOSTICS cancelled_count = ROW_COUNT;
    RETURN cancelled_count;
END;
$$ LANGUAGE 'plpgsql';

-- =====================================================
-- DATOS INICIALES
-- =====================================================

-- Insertar configuración por defecto
INSERT INTO follow_up_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- VISTAS PARA MONITOREO
-- =====================================================

-- Vista de estadísticas de follow-up
CREATE OR REPLACE VIEW follow_up_stats AS
SELECT 
    stage,
    COUNT(*) as total_sent,
    COUNT(CASE WHEN user_responded THEN 1 END) as responses,
    ROUND(COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2) as response_rate,
    AVG(response_time_hours) as avg_response_time_hours
FROM follow_up_history 
WHERE sent_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY stage
ORDER BY stage;

-- Vista de trabajos pendientes
CREATE OR REPLACE VIEW follow_up_queue AS
SELECT 
    user_id,
    stage,
    scheduled_for,
    EXTRACT(EPOCH FROM (scheduled_for - CURRENT_TIMESTAMP))/3600 as hours_until_send,
    attempts,
    created_at
FROM follow_up_jobs 
WHERE status = 'pending'
ORDER BY scheduled_for;

-- Comentarios para documentación
COMMENT ON TABLE follow_up_jobs IS 'Trabajos programados de follow-up para reactivar conversaciones';
COMMENT ON TABLE follow_up_history IS 'Historial completo de follow-ups enviados y sus resultados';
COMMENT ON TABLE follow_up_config IS 'Configuración global del sistema de follow-up';
COMMENT ON TABLE follow_up_blacklist IS 'Usuarios que no desean recibir follow-ups';

-- Versión del schema de follow-up
INSERT INTO schema_version (version, description) 
VALUES (2, 'Follow-up system tables for conversation reactivation')
ON CONFLICT (version) DO NOTHING;