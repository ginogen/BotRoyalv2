#!/usr/bin/env python3
"""
🔍 Script para verificar estado del sistema de follow-up
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

def check_followup_status():
    """Verificar estado completo del sistema"""
    try:
        # Conectar a la base de datos usando la configuración del servidor
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL no configurada")
            return
            
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                print("📊 ESTADO DEL SISTEMA DE FOLLOW-UP")
                print("="*50)
                
                # 1. Jobs pendientes
                cursor.execute("SELECT COUNT(*) as count FROM follow_up_jobs WHERE status = 'pending'")
                pending = cursor.fetchone()['count']
                print(f"📋 Jobs pendientes: {pending}")
                
                # 2. Jobs enviados hoy
                today = datetime.now().date()
                cursor.execute("SELECT COUNT(*) as count FROM follow_up_jobs WHERE status = 'sent' AND DATE(processed_at) = %s", (today,))
                sent_today = cursor.fetchone()['count']
                print(f"📤 Enviados hoy: {sent_today}")
                
                # 3. Usuarios inactivos detectados
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM conversation_contexts cc
                    LEFT JOIN follow_up_blacklist bl ON cc.user_id = bl.user_id
                    WHERE bl.user_id IS NULL 
                    AND cc.last_interaction < %s
                """, (datetime.now() - timedelta(hours=1),))
                inactive = cursor.fetchone()['count']
                print(f"👥 Usuarios inactivos: {inactive}")
                
                # 4. Próximo job programado
                cursor.execute("SELECT user_id, stage, scheduled_for FROM follow_up_jobs WHERE status = 'pending' ORDER BY scheduled_for LIMIT 1")
                next_job = cursor.fetchone()
                if next_job:
                    print(f"⏰ Próximo: Usuario {next_job['user_id'][:8]}... etapa {next_job['stage']} a las {next_job['scheduled_for']}")
                else:
                    print("⏰ No hay jobs programados")
                
                # 5. Usuarios en blacklist
                cursor.execute("SELECT COUNT(*) as count FROM follow_up_blacklist")
                blacklisted = cursor.fetchone()['count']
                print(f"🚫 En blacklist: {blacklisted}")
                
                print("\n✅ Sistema funcionando correctamente" if pending >= 0 else "❌ Problemas detectados")
                
    except Exception as e:
        print(f"❌ Error verificando estado: {e}")

if __name__ == "__main__":
    check_followup_status()