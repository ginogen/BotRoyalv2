-- 🚨 MIGRACIÓN CRÍTICA DE TIMEZONE - Script SQL Directo
-- Ejecutar directamente en la base de datos

-- Función auxiliar para convertir timestamps
CREATE OR REPLACE FUNCTION fix_timestamp_to_argentina(input_timestamp TEXT)
RETURNS TIMESTAMPTZ AS $$
BEGIN
    -- Si ya tiene timezone Argentina (-03:00), devolverlo tal como está
    IF input_timestamp LIKE '%-03:00' THEN
        RETURN input_timestamp::TIMESTAMPTZ;
    END IF;
    
    -- Si termina con Z (UTC), convertir a Argentina
    IF input_timestamp LIKE '%Z' THEN
        RETURN (REPLACE(input_timestamp, 'Z', '+00:00')::TIMESTAMPTZ) AT TIME ZONE 'America/Argentina/Cordoba';
    END IF;
    
    -- Si tiene otro timezone, convertir
    IF input_timestamp ~ '.*[+-]\d{2}:\d{2}$' THEN
        RETURN (input_timestamp::TIMESTAMPTZ) AT TIME ZONE 'America/Argentina/Cordoba';
    END IF;
    
    -- Sin timezone, asumir UTC y convertir a Argentina
    RETURN (input_timestamp::TIMESTAMP AT TIME ZONE 'UTC') AT TIME ZONE 'America/Argentina/Cordoba';
    
EXCEPTION WHEN OTHERS THEN
    -- En caso de error, usar timestamp actual menos 1 hora (fallback)
    RETURN (NOW() - INTERVAL '1 hour') AT TIME ZONE 'America/Argentina/Cordoba';
END;
$$ LANGUAGE plpgsql;

-- Migrar conversation_contexts
UPDATE conversation_contexts 
SET 
    last_interaction = fix_timestamp_to_argentina(last_interaction::TEXT),
    context_data = COALESCE(context_data, '{}'::JSONB) || 
                   jsonb_build_object('last_interaction', 
                       fix_timestamp_to_argentina(last_interaction::TEXT)::TEXT
                   )
WHERE last_interaction IS NOT NULL;

-- Migrar follow_up_jobs  
UPDATE follow_up_jobs
SET 
    scheduled_for = fix_timestamp_to_argentina(scheduled_for::TEXT),
    context_snapshot = CASE 
        WHEN context_snapshot IS NOT NULL AND context_snapshot ? 'last_interaction' THEN
            context_snapshot || jsonb_build_object(
                'last_interaction', 
                fix_timestamp_to_argentina((context_snapshot->>'last_interaction'))::TEXT
            )
        ELSE context_snapshot
    END
WHERE scheduled_for IS NOT NULL;

-- Activar modo migración por 24 horas
INSERT INTO follow_up_config (config_key, config_value)
VALUES ('migration_mode_until', (NOW() + INTERVAL '24 hours')::TEXT)
ON CONFLICT (config_key) DO UPDATE SET 
    config_value = EXCLUDED.config_value;

-- Limpiar función auxiliar
DROP FUNCTION fix_timestamp_to_argentina(TEXT);

-- Mostrar resumen
SELECT 'MIGRATION COMPLETED' as status,
       (SELECT COUNT(*) FROM conversation_contexts) as total_contexts_migrated,
       (SELECT COUNT(*) FROM follow_up_jobs) as total_jobs_migrated,
       (SELECT config_value FROM follow_up_config WHERE config_key = 'migration_mode_until') as migration_mode_until;