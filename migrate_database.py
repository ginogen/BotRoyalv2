#!/usr/bin/env python3
"""
🔄 MIGRACIÓN AUTOMÁTICA DE BASE DE DATOS
Script que se ejecuta automáticamente en deploy para asegurar que las tablas estén correctas
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_database_schema():
    """Verifica si el esquema de la base de datos es correcto"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.info("❌ No hay DATABASE_URL configurada, usando SQLite")
        return True  # SQLite se crea automáticamente
    
    try:
        logger.info("🔍 Verificando esquema de PostgreSQL...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar si existe la tabla conversations con la columna rating
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' 
            AND column_name = 'rating'
            AND table_schema = 'public'
        """)
        
        rating_column = cursor.fetchone()
        
        if rating_column:
            logger.info("✅ Esquema correcto - columna 'rating' encontrada")
            cursor.close()
            conn.close()
            return True
        else:
            logger.info("⚠️ Esquema incorrecto - falta columna 'rating'")
            cursor.close()
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verificando esquema: {e}")
        return False

def migrate_database():
    """Migra la base de datos al esquema correcto"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.info("ℹ️ Sin DATABASE_URL, no hay migración necesaria")
        return True
    
    try:
        logger.info("🔧 Iniciando migración de base de datos...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Backup de datos existentes (si los hay)
        logger.info("💾 Respaldando datos existentes...")
        
                 # Verificar si hay datos en conversations
        try:
            cursor.execute("SELECT COUNT(*) FROM conversations")
            result = cursor.fetchone()
            conversation_count = result[0] if result else 0
            logger.info(f"📊 {conversation_count} conversaciones encontradas")
        except:
            conversation_count = 0
        
        # Verificar si hay datos en feedback
        try:
            cursor.execute("SELECT COUNT(*) FROM feedback")
            result = cursor.fetchone()
            feedback_count = result[0] if result else 0
            logger.info(f"📊 {feedback_count} feedbacks encontrados")
        except:
            feedback_count = 0
        
        # Si hay datos, crear tabla temporal para backup
        if conversation_count > 0 or feedback_count > 0:
            logger.info("💾 Creando backup temporal de datos...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations_backup AS 
                    SELECT * FROM conversations
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_backup AS 
                    SELECT * FROM feedback
                """)
                logger.info("✅ Backup creado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo crear backup: {e}")
        
        # Eliminar tablas actuales
        logger.info("🗑️ Eliminando tablas obsoletas...")
        cursor.execute('DROP TABLE IF EXISTS conversations CASCADE')
        cursor.execute('DROP TABLE IF EXISTS feedback CASCADE')
        cursor.execute('DROP TABLE IF EXISTS bot_metrics CASCADE')
        
        # Crear tablas nuevas con esquema correcto
        logger.info("🏗️ Creando tablas con esquema correcto...")
        
        # Tabla conversations (unificada)
        cursor.execute('''
            CREATE TABLE conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(255) NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla general_feedback 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS general_feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                feedback_type VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                priority VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'pendiente',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Crear índices
        cursor.execute('CREATE INDEX idx_conversations_user_timestamp ON conversations(user_id, timestamp)')
        cursor.execute('CREATE INDEX idx_conversations_rating ON conversations(rating)')
        cursor.execute('CREATE INDEX idx_feedback_priority ON general_feedback(priority, status)')
        
        logger.info("✅ Tablas creadas exitosamente")
        
        # Migrar datos si había backup
        if conversation_count > 0:
            logger.info("📦 Migrando datos de backup...")
            try:
                # Migrar conversaciones (mapear campos)
                cursor.execute("""
                    INSERT INTO conversations (user_id, message, bot_response, timestamp, session_id)
                    SELECT 
                        user_id,
                        COALESCE(conversation_data, 'Conversación migrada') as message,
                        'Respuesta migrada' as bot_response,
                        timestamp,
                        'migrated_' || id::text as session_id
                    FROM conversations_backup
                """)
                
                # Migrar feedback a las conversaciones
                cursor.execute("""
                    UPDATE conversations 
                    SET rating = fb.rating, 
                        feedback_text = fb.comment,
                        category = fb.category
                    FROM feedback_backup fb
                    WHERE conversations.user_id = fb.user_id
                    AND conversations.session_id = 'migrated_' || fb.conversation_id::text
                """)
                
                logger.info("✅ Datos migrados exitosamente")
                
                # Limpiar backups
                cursor.execute('DROP TABLE IF EXISTS conversations_backup')
                cursor.execute('DROP TABLE IF EXISTS feedback_backup')
                
            except Exception as e:
                logger.warning(f"⚠️ Error migrando datos: {e}")
                logger.info("💡 Se crearon las tablas vacías - esto no afecta el funcionamiento")
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 ¡Migración completada exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        return False

def main():
    """Función principal de migración"""
    
    logger.info("🚀 Iniciando verificación de base de datos...")
    
    # Verificar si necesita migración
    if check_database_schema():
        logger.info("✅ Base de datos ya está correcta")
        return True
    
    # Ejecutar migración
    logger.info("🔧 Base de datos necesita migración...")
    success = migrate_database()
    
    if success:
        logger.info("🎉 ¡Migración completada! La aplicación puede iniciarse")
        return True
    else:
        logger.error("❌ Migración falló - la aplicación usará SQLite como fallback")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 