#!/usr/bin/env python3
"""
📊 Crear Tablas de Follow-up - Royal Bot v2
Script simple para crear las tablas necesarias
"""

import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('followup.setup')

def create_tables():
    """Crear tablas de follow-up"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL no encontrada")
            return False
        
        logger.info("🗄️ Conectando a PostgreSQL...")
        
        sql_commands = [
            # Tabla principal de trabajos
            """
            CREATE TABLE IF NOT EXISTS follow_up_jobs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                stage INTEGER NOT NULL,
                scheduled_for TIMESTAMP NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                context_snapshot JSONB,
                last_user_message TEXT,
                trigger_event VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                next_retry_at TIMESTAMP,
                UNIQUE(user_id, stage)
            );
            """,
            
            # Historial
            """
            CREATE TABLE IF NOT EXISTS follow_up_history (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                stage INTEGER NOT NULL,
                message_sent TEXT NOT NULL,
                template_used VARCHAR(100),
                generation_model VARCHAR(50),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_responded BOOLEAN DEFAULT FALSE,
                responded_at TIMESTAMP,
                response_message TEXT,
                response_time_hours DECIMAL(10,2),
                effectiveness_score DECIMAL(3,2),
                metadata JSONB DEFAULT '{}'
            );
            """,
            
            # Configuración
            """
            CREATE TABLE IF NOT EXISTS follow_up_config (
                id SERIAL PRIMARY KEY,
                stage_delays_hours INTEGER[] DEFAULT '{1,6,24,48,72,96,120,168}',
                start_hour INTEGER DEFAULT 9,
                end_hour INTEGER DEFAULT 21,
                timezone VARCHAR(50) DEFAULT 'America/Argentina/Cordoba',
                allowed_weekdays INTEGER[] DEFAULT '{1,2,3,4,5,6}',
                max_followups_per_user INTEGER DEFAULT 8,
                cooldown_between_stages_hours INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Blacklist
            """
            CREATE TABLE IF NOT EXISTS follow_up_blacklist (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(50),
                reason VARCHAR(200),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by VARCHAR(100) DEFAULT 'user'
            );
            """,
            
            # Índices
            """
            CREATE INDEX IF NOT EXISTS idx_followup_jobs_scheduled ON follow_up_jobs(scheduled_for, status);
            CREATE INDEX IF NOT EXISTS idx_followup_jobs_user ON follow_up_jobs(user_id);
            CREATE INDEX IF NOT EXISTS idx_followup_history_user_time ON follow_up_history(user_id, sent_at);
            CREATE INDEX IF NOT EXISTS idx_followup_blacklist_user ON follow_up_blacklist(user_id);
            """,
            
            # Configuración inicial
            """
            INSERT INTO follow_up_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
            """
        ]
        
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cursor:
                for sql in sql_commands:
                    cursor.execute(sql)
                    logger.info("✅ Comando SQL ejecutado")
                
                conn.commit()
        
        logger.info("🎉 Tablas de follow-up creadas exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creando tablas de follow-up...")
    success = create_tables()
    if success:
        print("✅ ¡Listo! Reinicia el servidor para activar el sistema.")
    else:
        print("❌ Error creando tablas. Revisa los logs.")