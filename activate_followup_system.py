#!/usr/bin/env python3
"""
📅 Activador del Sistema de Follow-up - Royal Bot v2
Script para crear las tablas e inicializar el sistema de follow-up
"""

import asyncio
import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('followup.activator')

async def create_followup_tables():
    """Crear tablas de follow-up en PostgreSQL"""
    try:
        # Obtener URL de la base de datos
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL no encontrada en variables de entorno")
            return False
        
        logger.info("🗄️ Conectando a PostgreSQL...")
        
        # Leer script SQL
        sql_file = "/Users/gino/BotRoyalv2/migrations/add_followup_tables.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Ejecutar script
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_script)
                logger.info("✅ Tablas de follow-up creadas exitosamente")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        return False

async def verify_system():
    """Verificar que el sistema esté correctamente configurado"""
    try:
        logger.info("🔍 Verificando configuración...")
        
        # Variables requeridas
        required_vars = [
            "DATABASE_URL",
            "EVOLUTION_API_URL", 
            "EVOLUTION_API_TOKEN",
            "INSTANCE_NAME",
            "OPENAI_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
            return False
        
        # Verificar conexión a DB
        database_url = os.getenv("DATABASE_URL")
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar que las tablas existan
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'follow_up%'
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                expected_tables = [
                    'follow_up_jobs', 
                    'follow_up_history', 
                    'follow_up_config',
                    'follow_up_blacklist'
                ]
                
                missing_tables = [t for t in expected_tables if t not in tables]
                if missing_tables:
                    logger.error(f"❌ Tablas faltantes: {', '.join(missing_tables)}")
                    return False
        
        logger.info("✅ Sistema verificado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verificando sistema: {e}")
        return False

async def show_system_status():
    """Mostrar estado del sistema de follow-up"""
    try:
        database_url = os.getenv("DATABASE_URL")
        
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Contar trabajos pendientes
                cursor.execute("SELECT COUNT(*) as count FROM follow_up_jobs WHERE status = 'pending'")
                pending_jobs = cursor.fetchone()['count']
                
                # Contar usuarios en blacklist
                cursor.execute("SELECT COUNT(*) as count FROM follow_up_blacklist")
                blacklisted = cursor.fetchone()['count']
                
                # Follow-ups enviados en últimos 7 días
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM follow_up_history 
                    WHERE sent_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                """)
                recent_sent = cursor.fetchone()['count']
                
                print("\n" + "="*50)
                print("📅 ESTADO DEL SISTEMA DE FOLLOW-UP")
                print("="*50)
                print(f"📋 Trabajos pendientes: {pending_jobs}")
                print(f"🚫 Usuarios en blacklist: {blacklisted}")
                print(f"📤 Enviados últimos 7 días: {recent_sent}")
                print(f"⏰ Sistema activado: {datetime.now()}")
                print("="*50)
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado: {e}")

async def main():
    """Función principal de activación"""
    logger.info("🚀 Iniciando activación del sistema de follow-up...")
    
    # Paso 1: Crear tablas
    logger.info("📊 Paso 1: Creando tablas de base de datos...")
    if not await create_followup_tables():
        logger.error("❌ Falló creación de tablas")
        return
    
    # Paso 2: Verificar configuración
    logger.info("🔧 Paso 2: Verificando configuración...")
    if not await verify_system():
        logger.error("❌ Falló verificación del sistema")
        return
    
    # Paso 3: Mostrar estado
    logger.info("📈 Paso 3: Mostrando estado del sistema...")
    await show_system_status()
    
    logger.info("✅ Sistema de follow-up activado exitosamente!")
    logger.info("🚀 Para usar:")
    logger.info("   1. Configura las variables de entorno en Railway")
    logger.info("   2. Reinicia tu servicio")
    logger.info("   3. Verifica en: /api/followup/stats")

if __name__ == "__main__":
    asyncio.run(main())