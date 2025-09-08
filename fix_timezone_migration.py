#!/usr/bin/env python3
"""
🚨 MIGRACIÓN CRÍTICA: Corrección de Timezone para Follow-ups
Corrige todos los timestamps existentes para usar timezone Argentina consistentemente
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import pytz
from datetime import datetime, timedelta
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Timezone Argentina
ARGENTINA_TZ = pytz.timezone("America/Argentina/Cordoba")

def fix_timestamp(timestamp_input):
    """Convertir cualquier timestamp a Argentina timezone"""
    try:
        if isinstance(timestamp_input, str):
            # Si ya tiene timezone Argentina, mantenerlo
            if '-03:00' in timestamp_input:
                return datetime.fromisoformat(timestamp_input)
            
            # Si termina con Z (UTC)
            if timestamp_input.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_input.replace('Z', '+00:00'))
                return dt.astimezone(ARGENTINA_TZ)
            
            # Si tiene otro timezone
            if '+' in timestamp_input or '-' in timestamp_input[-6:]:
                dt = datetime.fromisoformat(timestamp_input)
                return dt.astimezone(ARGENTINA_TZ)
            
            # Sin timezone - asumir UTC y convertir a Argentina
            dt = datetime.fromisoformat(timestamp_input)
            utc = pytz.UTC.localize(dt)
            return utc.astimezone(ARGENTINA_TZ)
            
        elif isinstance(timestamp_input, datetime):
            if timestamp_input.tzinfo is None:
                # Sin timezone - asumir UTC
                utc = pytz.UTC.localize(timestamp_input)
                return utc.astimezone(ARGENTINA_TZ)
            else:
                return timestamp_input.astimezone(ARGENTINA_TZ)
                
        else:
            logger.error(f"Tipo de timestamp no soportado: {type(timestamp_input)}")
            return None
            
    except Exception as e:
        logger.error(f"Error procesando timestamp {timestamp_input}: {e}")
        return None

def migrate_conversation_contexts():
    """Migrar conversation_contexts para timezone consistente"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL no encontrada")
        return False
    
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                logger.info("🔍 Buscando conversation_contexts para migrar...")
                
                cursor.execute("""
                    SELECT user_id, context_data, last_interaction, created_at, updated_at
                    FROM conversation_contexts
                """)
                
                contexts = cursor.fetchall()
                logger.info(f"📊 Encontrados {len(contexts)} contextos para migrar")
                
                migrated_count = 0
                
                for context in contexts:
                    try:
                        user_id = context['user_id']
                        context_data = context['context_data'] or {}
                        last_interaction = context['last_interaction']
                        
                        # Corregir last_interaction
                        fixed_last_interaction = fix_timestamp(last_interaction)
                        if not fixed_last_interaction:
                            logger.warning(f"⚠️ No se pudo corregir timestamp para {user_id}")
                            continue
                        
                        # Corregir context_data.last_interaction si existe
                        if isinstance(context_data, dict):
                            if 'last_interaction' in context_data:
                                fixed_context_timestamp = fix_timestamp(context_data['last_interaction'])
                                if fixed_context_timestamp:
                                    context_data['last_interaction'] = fixed_context_timestamp.isoformat()
                            else:
                                # Agregar timestamp corregido al context_data
                                context_data['last_interaction'] = fixed_last_interaction.isoformat()
                        
                        # Actualizar en BD
                        cursor.execute("""
                            UPDATE conversation_contexts 
                            SET context_data = %s, last_interaction = %s
                            WHERE user_id = %s
                        """, (Json(context_data), fixed_last_interaction, user_id))
                        
                        migrated_count += 1
                        logger.info(f"✅ Migrado {user_id}: {fixed_last_interaction}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error migrando {context.get('user_id', 'unknown')}: {e}")
                
                conn.commit()
                logger.info(f"🎉 Migración completada: {migrated_count} contextos actualizados")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error en migración de contextos: {e}")
        return False

def migrate_follow_up_jobs():
    """Migrar follow_up_jobs para timezone consistente"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL no encontrada")
        return False
    
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                logger.info("🔍 Buscando follow_up_jobs para migrar...")
                
                cursor.execute("""
                    SELECT user_id, stage, scheduled_for, created_at, context_snapshot
                    FROM follow_up_jobs
                """)
                
                jobs = cursor.fetchall()
                logger.info(f"📊 Encontrados {len(jobs)} jobs para migrar")
                
                migrated_count = 0
                
                for job in jobs:
                    try:
                        user_id = job['user_id']
                        stage = job['stage']
                        scheduled_for = job['scheduled_for']
                        context_snapshot = job['context_snapshot'] or {}
                        
                        # Corregir scheduled_for
                        fixed_scheduled_for = fix_timestamp(scheduled_for)
                        if not fixed_scheduled_for:
                            logger.warning(f"⚠️ No se pudo corregir scheduled_for para {user_id} stage {stage}")
                            continue
                        
                        # Corregir timestamps en context_snapshot
                        if isinstance(context_snapshot, dict):
                            if 'last_interaction' in context_snapshot:
                                fixed_context_timestamp = fix_timestamp(context_snapshot['last_interaction'])
                                if fixed_context_timestamp:
                                    context_snapshot['last_interaction'] = fixed_context_timestamp.isoformat()
                        
                        # Actualizar en BD
                        cursor.execute("""
                            UPDATE follow_up_jobs 
                            SET scheduled_for = %s, context_snapshot = %s
                            WHERE user_id = %s AND stage = %s
                        """, (fixed_scheduled_for, Json(context_snapshot), user_id, stage))
                        
                        migrated_count += 1
                        logger.info(f"✅ Migrado job {user_id} stage {stage}: {fixed_scheduled_for}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error migrando job {job.get('user_id', 'unknown')}: {e}")
                
                conn.commit()
                logger.info(f"🎉 Migración de jobs completada: {migrated_count} jobs actualizados")
                
                # 🛡️ ACTIVAR MODO MIGRACIÓN por 24 horas para prevenir duplicación
                migration_until = datetime.now(ARGENTINA_TZ) + timedelta(hours=24)
                cursor.execute("""
                    INSERT INTO follow_up_config (config_key, config_value)
                    VALUES ('migration_mode_until', %s)
                    ON CONFLICT (config_key) DO UPDATE SET 
                        config_value = EXCLUDED.config_value
                """, (migration_until.isoformat(),))
                logger.info(f"🛡️ Modo protección anti-duplicación activo hasta: {migration_until}")
                
                conn.commit()
                return True
                
    except Exception as e:
        logger.error(f"❌ Error en migración de jobs: {e}")
        return False

def find_users_missing_followups():
    """Encontrar usuarios que deberían tener follow-ups pero no los tienen"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL no encontrada")
        return []
    
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT cc.user_id, cc.last_interaction, cc.context_data
                    FROM conversation_contexts cc
                    LEFT JOIN follow_up_blacklist bl ON cc.user_id = bl.user_id
                    WHERE bl.user_id IS NULL  -- No en blacklist
                    AND cc.last_interaction < %s  -- Inactivo por más de 1 hora
                    AND NOT EXISTS (  -- Sin follow-ups pendientes
                        SELECT 1 FROM follow_up_jobs fj 
                        WHERE fj.user_id = cc.user_id 
                        AND fj.status = 'pending'
                    )
                    ORDER BY cc.last_interaction ASC
                """, (datetime.now(ARGENTINA_TZ) - timedelta(hours=1),))
                
                missing_users = cursor.fetchall()
                logger.info(f"🚨 Encontrados {len(missing_users)} usuarios sin follow-ups que los necesitan")
                
                return missing_users
                
    except Exception as e:
        logger.error(f"❌ Error buscando usuarios faltantes: {e}")
        return []

def main():
    """Función principal de migración"""
    logger.info("🚨 INICIANDO MIGRACIÓN CRÍTICA DE TIMEZONE")
    logger.info("=" * 60)
    
    # Paso 1: Migrar conversation_contexts
    logger.info("📋 PASO 1: Migrando conversation_contexts...")
    if not migrate_conversation_contexts():
        logger.error("❌ Falló migración de conversation_contexts")
        return False
    
    # Paso 2: Migrar follow_up_jobs
    logger.info("📋 PASO 2: Migrando follow_up_jobs...")
    if not migrate_follow_up_jobs():
        logger.error("❌ Falló migración de follow_up_jobs")
        return False
    
    # Paso 3: Encontrar usuarios que necesitan follow-ups
    logger.info("📋 PASO 3: Identificando usuarios sin follow-ups...")
    missing_users = find_users_missing_followups()
    
    if missing_users:
        logger.warning(f"⚠️ {len(missing_users)} usuarios necesitan follow-ups programados")
        logger.info("💡 Ejecuta el scheduler para que los detecte automáticamente")
        
        # Mostrar primeros 10 usuarios
        for i, user in enumerate(missing_users[:10]):
            logger.info(f"  {i+1}. {user['user_id']} - inactive since {user['last_interaction']}")
    
    logger.info("=" * 60)
    logger.info("🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
    logger.info("📝 El sistema de follow-ups ahora debería funcionar correctamente")
    logger.info("🔄 Reinicia el scheduler para aplicar los cambios")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)