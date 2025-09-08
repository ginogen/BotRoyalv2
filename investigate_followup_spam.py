#!/usr/bin/env python3
"""
Investigación del problema de follow-up spam para usuario 5493413418733
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz
import json

# Configuración de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no encontrado en variables de entorno")
    sys.exit(1)

# Usuario problemático
PROBLEM_USER = "5493413418733"

def investigate_user_followups():
    """Investigar el estado de follow-ups del usuario problemático"""
    
    print(f"🔍 INVESTIGACIÓN DE FOLLOW-UP SPAM")
    print(f"=" * 60)
    print(f"Usuario: {PROBLEM_USER}")
    print(f"Fecha investigación: {datetime.now()}")
    print()
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # 1. REVISAR JOBS DE FOLLOW-UP
                print("📋 1. JOBS DE FOLLOW-UP EXISTENTES:")
                print("-" * 40)
                
                cursor.execute("""
                    SELECT 
                        user_id, phone, stage, status, 
                        scheduled_for, created_at, processed_at,
                        attempts, last_error
                    FROM follow_up_jobs 
                    WHERE user_id LIKE %s OR phone = %s
                    ORDER BY created_at DESC
                """, (f"%{PROBLEM_USER}%", PROBLEM_USER))
                
                jobs = cursor.fetchall()
                print(f"Total jobs encontrados: {len(jobs)}")
                print()
                
                if jobs:
                    for job in jobs:
                        print(f"  📌 Stage {job['stage']}: {job['status']}")
                        print(f"     User ID: {job['user_id']}")
                        print(f"     Phone: {job['phone']}")
                        print(f"     Scheduled: {job['scheduled_for']}")
                        print(f"     Created: {job['created_at']}")
                        print(f"     Processed: {job['processed_at']}")
                        print(f"     Attempts: {job['attempts']}")
                        if job['last_error']:
                            print(f"     Error: {job['last_error'][:100]}...")
                        print()
                
                # 2. REVISAR CONTEXTO DE CONVERSACIÓN
                print("💬 2. CONTEXTO DE CONVERSACIÓN:")
                print("-" * 40)
                
                # Buscar por diferentes variantes del user_id
                user_variants = [
                    PROBLEM_USER,
                    f"whatsapp_{PROBLEM_USER}",
                    f"evolution_{PROBLEM_USER}",
                    f"chatwoot_{PROBLEM_USER}"
                ]
                
                context_found = False
                for user_variant in user_variants:
                    cursor.execute("""
                        SELECT user_id, last_interaction, context_data
                        FROM conversation_contexts 
                        WHERE user_id = %s
                    """, (user_variant,))
                    
                    context = cursor.fetchone()
                    if context:
                        context_found = True
                        print(f"  ✅ Contexto encontrado para: {user_variant}")
                        print(f"     Última interacción: {context['last_interaction']}")
                        
                        context_data = context['context_data'] or {}
                        interaction_history = context_data.get('interaction_history', [])
                        print(f"     Interacciones en historial: {len(interaction_history)}")
                        
                        # Verificar si tiene conversación real
                        has_real_conversation = len([
                            i for i in interaction_history 
                            if i.get('role') in ['user', 'assistant'] 
                            and i.get('message', '').strip()
                            and not any(skip in i.get('message', '').lower() for skip in [
                                'escalado a humano', 'información faltante', 'necesita asistencia'
                            ])
                        ]) >= 2
                        
                        print(f"     ¿Conversación real?: {has_real_conversation}")
                        print(f"     Últimas 3 interacciones:")
                        
                        for i, interaction in enumerate(interaction_history[-3:], 1):
                            role = interaction.get('role', 'unknown')
                            message = interaction.get('message', '')[:80]
                            timestamp = interaction.get('timestamp', 'N/A')
                            print(f"       {i}. {role}: {message}... [{timestamp}]")
                        print()
                
                if not context_found:
                    print(f"  ❌ No se encontró contexto para ninguna variante del usuario")
                    print()
                
                # 3. REVISAR BLACKLIST
                print("🚫 3. ESTADO DE BLACKLIST:")
                print("-" * 40)
                
                cursor.execute("""
                    SELECT user_id, reason, created_at
                    FROM follow_up_blacklist 
                    WHERE user_id LIKE %s
                """, (f"%{PROBLEM_USER}%",))
                
                blacklist = cursor.fetchall()
                if blacklist:
                    for entry in blacklist:
                        print(f"  🚫 En blacklist: {entry['user_id']}")
                        print(f"     Razón: {entry['reason']}")
                        print(f"     Desde: {entry['created_at']}")
                        print()
                else:
                    print(f"  ✅ Usuario NO está en blacklist")
                    print()
                
                # 4. BUSCAR JOBS RECIENTES (últimas 24 horas)
                print("⏰ 4. ACTIVIDAD RECIENTE (últimas 24 horas):")
                print("-" * 40)
                
                yesterday = datetime.now() - timedelta(hours=24)
                
                cursor.execute("""
                    SELECT 
                        user_id, stage, status, created_at, processed_at,
                        scheduled_for
                    FROM follow_up_jobs 
                    WHERE (user_id LIKE %s OR phone = %s)
                    AND created_at > %s
                    ORDER BY created_at DESC
                """, (f"%{PROBLEM_USER}%", PROBLEM_USER, yesterday))
                
                recent_jobs = cursor.fetchall()
                print(f"Jobs creados en las últimas 24h: {len(recent_jobs)}")
                
                if recent_jobs:
                    print("\nDetalle por hora de creación:")
                    for job in recent_jobs:
                        created_hour = job['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                        scheduled_hour = job['scheduled_for'].strftime('%Y-%m-%d %H:%M:%S') if job['scheduled_for'] else 'N/A'
                        processed_hour = job['processed_at'].strftime('%Y-%m-%d %H:%M:%S') if job['processed_at'] else 'Pendiente'
                        
                        print(f"  🕐 Stage {job['stage']} - {job['status']}")
                        print(f"     Creado: {created_hour}")
                        print(f"     Programado: {scheduled_hour}")
                        print(f"     Procesado: {processed_hour}")
                        print()
                
                # 5. ESTADÍSTICAS GENERALES
                print("📊 5. ESTADÍSTICAS:")
                print("-" * 40)
                
                # Contar por estado
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM follow_up_jobs 
                    WHERE user_id LIKE %s OR phone = %s
                    GROUP BY status
                """, (f"%{PROBLEM_USER}%", PROBLEM_USER))
                
                stats = cursor.fetchall()
                for stat in stats:
                    print(f"  {stat['status']}: {stat['count']} jobs")
                
                print()
                
                # Contar por stage
                cursor.execute("""
                    SELECT stage, COUNT(*) as count
                    FROM follow_up_jobs 
                    WHERE user_id LIKE %s OR phone = %s
                    GROUP BY stage
                    ORDER BY stage
                """, (f"%{PROBLEM_USER}%", PROBLEM_USER))
                
                stage_stats = cursor.fetchall()
                print("Por etapa:")
                for stat in stage_stats:
                    print(f"  Stage {stat['stage']}: {stat['count']} jobs")
                
    except Exception as e:
        print(f"❌ Error durante investigación: {e}")
        import traceback
        traceback.print_exc()

def suggest_fixes():
    """Sugerir correcciones basadas en los hallazgos"""
    print(f"\n🔧 SUGERENCIAS DE CORRECCIÓN:")
    print(f"=" * 60)
    print("1. Si hay múltiples jobs pendientes del mismo stage: CANCELAR DUPLICADOS")
    print("2. Si jobs fueron creados al mismo tiempo: BUG EN RECOVERY SYSTEM")  
    print("3. Si usuario no tiene conversación real: MEJORAR DETECCIÓN")
    print("4. Si hay jobs con scheduled_for muy cercanos: IMPLEMENTAR RATE LIMITING")
    print("5. Si hay muchos jobs 'failed': REVISAR SISTEMA DE ENVÍO")
    print("\nAcciones inmediatas:")
    print("- Cancelar jobs pendientes duplicados")
    print("- Agregar rate limiting (1 follow-up por día máximo)")
    print("- Mejorar protecciones en recovery systems")

if __name__ == "__main__":
    investigate_user_followups()
    suggest_fixes()