#!/usr/bin/env python3
"""
Script para limpiar contexto, jobs y follow-ups de un usuario específico
Uso: python cleanup_user.py <user_id>
"""

import asyncio
import psycopg2
import sys
import os
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar configuración
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def cleanup_user(user_id: str):
    """Limpiar todos los datos de un usuario específico"""
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                
                # 1. Cancelar todos los follow-up jobs pendientes
                cursor.execute("""
                    UPDATE follow_up_jobs 
                    SET status = 'cancelled', processed_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND status = 'pending'
                """, (user_id,))
                cancelled_jobs = cursor.rowcount
                logger.info(f"✅ Cancelados {cancelled_jobs} follow-up jobs pendientes")
                
                # 2. Opción: Eliminar TODOS los jobs del usuario (históricos también)
                # Descomenta si quieres eliminar todo el historial
                # cursor.execute("""
                #     DELETE FROM follow_up_jobs WHERE user_id = %s
                # """, (user_id,))
                # deleted_jobs = cursor.rowcount
                # logger.info(f"🗑️ Eliminados {deleted_jobs} follow-up jobs en total")
                
                # 3. Limpiar contexto de conversación
                cursor.execute("""
                    DELETE FROM conversation_contexts 
                    WHERE user_id = %s
                """, (user_id,))
                if cursor.rowcount > 0:
                    logger.info(f"✅ Contexto de conversación eliminado")
                
                # 4. Limpiar historial de interacciones
                cursor.execute("""
                    DELETE FROM user_interactions 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_interactions = cursor.rowcount
                logger.info(f"✅ Eliminadas {deleted_interactions} interacciones")
                
                # 5. Verificar si está en blacklist
                cursor.execute("""
                    SELECT 1 FROM follow_up_blacklist 
                    WHERE user_id = %s
                """, (user_id,))
                
                if cursor.fetchone():
                    logger.info(f"ℹ️ Usuario está en blacklist de follow-ups")
                
                # 6. Mostrar resumen de follow-up history
                cursor.execute("""
                    SELECT COUNT(*) as total, 
                           COUNT(CASE WHEN user_responded THEN 1 END) as responded
                    FROM follow_up_history 
                    WHERE user_id = %s
                """, (user_id,))
                
                history = cursor.fetchone()
                if history and history[0] > 0:
                    logger.info(f"📊 Historial: {history[0]} follow-ups enviados, {history[1]} respondidos")
                
                conn.commit()
                logger.info(f"✅ Limpieza completa para usuario: {user_id}")
                
    except Exception as e:
        logger.error(f"❌ Error limpiando datos del usuario: {e}")
        raise

async def add_to_blacklist(user_id: str, reason: str = "manual_cleanup"):
    """Agregar usuario a blacklist de follow-ups"""
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Extraer phone si está en formato whatsapp_
                phone = user_id.replace('whatsapp_', '') if user_id.startswith('whatsapp_') else ''
                
                cursor.execute("""
                    INSERT INTO follow_up_blacklist (user_id, phone, reason)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        added_at = CURRENT_TIMESTAMP
                """, (user_id, phone, reason))
                
                conn.commit()
                logger.info(f"✅ Usuario agregado a blacklist: {user_id}")
                
    except Exception as e:
        logger.error(f"❌ Error agregando a blacklist: {e}")

async def show_user_status(user_id: str):
    """Mostrar estado actual del usuario"""
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                print(f"\n📊 ESTADO DEL USUARIO: {user_id}\n")
                
                # Follow-up jobs
                cursor.execute("""
                    SELECT stage, status, scheduled_for, attempts 
                    FROM follow_up_jobs 
                    WHERE user_id = %s
                    ORDER BY stage
                """, (user_id,))
                
                jobs = cursor.fetchall()
                if jobs:
                    print("📅 FOLLOW-UP JOBS:")
                    for stage, status, scheduled, attempts in jobs:
                        print(f"  Stage {stage}: {status} - Programado: {scheduled} - Intentos: {attempts}")
                else:
                    print("📅 Sin follow-up jobs")
                
                # Contexto
                cursor.execute("""
                    SELECT last_interaction, current_state, is_entrepreneur 
                    FROM conversation_contexts 
                    WHERE user_id = %s
                """, (user_id,))
                
                context = cursor.fetchone()
                if context:
                    print(f"\n💬 CONTEXTO:")
                    print(f"  Última interacción: {context[0]}")
                    print(f"  Estado: {context[1]}")
                    print(f"  Es emprendedor: {context[2]}")
                else:
                    print("\n💬 Sin contexto de conversación")
                
                # Blacklist
                cursor.execute("""
                    SELECT reason, added_at 
                    FROM follow_up_blacklist 
                    WHERE user_id = %s
                """, (user_id,))
                
                blacklist = cursor.fetchone()
                if blacklist:
                    print(f"\n🚫 EN BLACKLIST:")
                    print(f"  Razón: {blacklist[0]}")
                    print(f"  Desde: {blacklist[1]}")
                
    except Exception as e:
        logger.error(f"❌ Error mostrando estado: {e}")

async def main():
    if len(sys.argv) < 2:
        print("""
Uso: python cleanup_user.py <user_id> [opciones]

Opciones:
  --show         Solo mostrar estado del usuario
  --blacklist    Agregar a blacklist después de limpiar
  --all          Eliminar TODO (incluye historial)

Ejemplos:
  python cleanup_user.py whatsapp_5491123456789
  python cleanup_user.py whatsapp_5491123456789 --show
  python cleanup_user.py whatsapp_5491123456789 --blacklist
        """)
        return
    
    user_id = sys.argv[1]
    show_only = "--show" in sys.argv
    add_blacklist = "--blacklist" in sys.argv
    
    if show_only:
        await show_user_status(user_id)
    else:
        await show_user_status(user_id)
        
        print(f"\n⚠️  ¿Limpiar todos los datos de {user_id}? (s/n): ", end="")
        confirm = input().lower()
        
        if confirm == 's':
            await cleanup_user(user_id)
            
            if add_blacklist:
                await add_to_blacklist(user_id)
            
            print("\n📊 ESTADO DESPUÉS DE LIMPIEZA:")
            await show_user_status(user_id)
        else:
            print("❌ Cancelado")

if __name__ == "__main__":
    asyncio.run(main())