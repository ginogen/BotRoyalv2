#!/usr/bin/env python3
"""
Script para limpiar mensajes con source='followup' inválido
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtener conexión a PostgreSQL"""
    try:
        database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:ngYpnFNDfDsaqyLzVsxsjoLowpOxnhjy@postgres.railway.internal:5432/railway')
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        return None

def investigate_followup_messages():
    """Investigar mensajes con source='followup'"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Contar mensajes con source='followup'
        cursor.execute("SELECT COUNT(*) as count FROM message_queue WHERE source = 'followup'")
        count_result = cursor.fetchone()
        followup_count = count_result['count'] if count_result else 0
        
        logger.info(f"🔍 Mensajes con source='followup': {followup_count}")
        
        if followup_count > 0:
            # Obtener algunos ejemplos
            cursor.execute("""
                SELECT id, user_id, message_content, status, created_at, metadata 
                FROM message_queue 
                WHERE source = 'followup' 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            examples = cursor.fetchall()
            logger.info("📋 Ejemplos de mensajes 'followup':")
            for msg in examples:
                logger.info(f"  - ID: {msg['id']}, User: {msg['user_id']}, Status: {msg['status']}")
                logger.info(f"    Content: {msg['message_content'][:100]}...")
                logger.info(f"    Created: {msg['created_at']}")
        
        # Verificar también estados de estos mensajes
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM message_queue 
            WHERE source = 'followup' 
            GROUP BY status
        """)
        
        status_counts = cursor.fetchall()
        if status_counts:
            logger.info("📊 Estados de mensajes 'followup':")
            for status_row in status_counts:
                logger.info(f"  - {status_row['status']}: {status_row['count']}")
        
        return followup_count
        
    except Exception as e:
        logger.error(f"❌ Error investigando mensajes: {e}")
        return 0
    finally:
        conn.close()

def clean_followup_messages(action='convert'):
    """
    Limpiar mensajes con source='followup'
    action: 'convert' (a 'system') o 'delete'
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        if action == 'convert':
            # Convertir 'followup' a 'system'
            cursor.execute("""
                UPDATE message_queue 
                SET source = 'system' 
                WHERE source = 'followup'
            """)
            affected_rows = cursor.rowcount
            conn.commit()
            logger.info(f"✅ Convertidos {affected_rows} mensajes de 'followup' a 'system'")
            
        elif action == 'delete':
            # Eliminar mensajes 'followup'
            cursor.execute("DELETE FROM message_queue WHERE source = 'followup'")
            affected_rows = cursor.rowcount
            conn.commit()
            logger.info(f"🗑️ Eliminados {affected_rows} mensajes con source='followup'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error limpiando mensajes: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_cleanup():
    """Verificar que no queden mensajes 'followup'"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM message_queue WHERE source = 'followup'")
        count_result = cursor.fetchone()
        remaining_count = count_result['count'] if count_result else 0
        
        if remaining_count == 0:
            logger.info("✅ No quedan mensajes con source='followup'")
            return True
        else:
            logger.warning(f"⚠️ Still {remaining_count} messages with source='followup'")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verificando limpieza: {e}")
        return False
    finally:
        conn.close()

def main():
    """Función principal"""
    logger.info("🔧 Iniciando limpieza de mensajes 'followup'...")
    
    # 1. Investigar
    logger.info("\n1️⃣ INVESTIGANDO MENSAJES 'FOLLOWUP'...")
    followup_count = investigate_followup_messages()
    
    if followup_count == 0:
        logger.info("✅ No hay mensajes con source='followup' para limpiar")
        return
    
    # 2. Acción automática (convertir a 'system')
    logger.info(f"\n❓ Se encontraron {followup_count} mensajes con source='followup'")
    logger.info("🔄 Convirtiendo automáticamente a 'system'...")
    
    # 3. Ejecutar acción
    logger.info("\n2️⃣ CONVIRTIENDO MENSAJES...")
    success = clean_followup_messages('convert')
    
    # 4. Verificar
    if success:
        logger.info("\n3️⃣ VERIFICANDO LIMPIEZA...")
        verify_cleanup()
        logger.info("\n✅ Limpieza completada. Reinicia el servidor para aplicar cambios.")
    else:
        logger.error("❌ Error durante la limpieza")

if __name__ == "__main__":
    main()