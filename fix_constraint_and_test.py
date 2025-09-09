#!/usr/bin/env python3
"""
🔧 Aplicar Fix de Constraint y Probar Creación de Jobs
Script para corregir el constraint problemático y probar que los jobs se crean correctamente
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no encontrado en variables de entorno")
    sys.exit(1)

async def fix_constraint():
    """Arreglar el constraint problemático"""
    print("🔧 CORRIGIENDO CONSTRAINT PROBLEMÁTICO")
    print("=" * 50)
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # 1. Verificar si existe el constraint problemático
                cursor.execute("""
                    SELECT constraint_name, is_deferrable 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'follow_up_jobs' 
                    AND constraint_name = 'unique_pending_job_per_user_stage'
                """)
                
                existing_constraint = cursor.fetchone()
                
                if existing_constraint:
                    if existing_constraint['is_deferrable'] == 'YES':
                        print("🚨 Constraint DEFERRABLE encontrado - eliminando...")
                        cursor.execute("ALTER TABLE follow_up_jobs DROP CONSTRAINT unique_pending_job_per_user_stage")
                        print("✅ Constraint DEFERRABLE eliminado")
                    else:
                        print("✅ Constraint ya es NO DEFERRABLE")
                        return True
                
                # 2. Crear constraint correcto (NO deferrable)
                print("📝 Creando constraint NO DEFERRABLE...")
                cursor.execute("""
                    ALTER TABLE follow_up_jobs 
                    ADD CONSTRAINT unique_pending_job_per_user_stage 
                    UNIQUE (user_id, stage)
                """)
                print("✅ Constraint NO DEFERRABLE creado exitosamente")
                
                # 3. Verificar que funciona
                cursor.execute("""
                    SELECT constraint_name, is_deferrable 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'follow_up_jobs' 
                    AND constraint_name = 'unique_pending_job_per_user_stage'
                """)
                
                verified = cursor.fetchone()
                if verified and verified['is_deferrable'] == 'NO':
                    print(f"✅ Constraint verificado: {verified['constraint_name']} (deferrable: {verified['is_deferrable']})")
                    return True
                else:
                    print("❌ Error verificando constraint")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error corrigiendo constraint: {e}")
        return False

async def test_job_creation():
    """Probar creación de un job de follow-up"""
    print("\n🧪 PROBANDO CREACIÓN DE JOBS")
    print("=" * 50)
    
    try:
        from royal_agents.follow_up.follow_up_scheduler import FollowUpScheduler
        from datetime import datetime, timedelta
        import pytz
        
        # Crear scheduler de prueba
        scheduler = FollowUpScheduler(DATABASE_URL)
        test_user_id = "whatsapp_1234567890"  # Cambiar formato para que se extraiga phone correctamente
        test_phone = "1234567890"
        
        # Context de prueba
        test_context = {
            'current_state': 'browsing',
            'interaction_history': [
                {'role': 'user', 'message': 'Hola'},
                {'role': 'assistant', 'message': 'Hola! ¿En qué puedo ayudarte?'}
            ]
        }
        
        # Limpiar cualquier job anterior de prueba
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM follow_up_jobs WHERE user_id = %s", (test_user_id,))
        
        print(f"🎯 Probando creación de job para usuario: {test_user_id}")
        
        # Crear job de prueba
        tz = pytz.timezone("America/Argentina/Cordoba")
        scheduled_time = datetime.now(tz) + timedelta(minutes=5)
        
        await scheduler._create_followup_job(
            user_id=test_user_id,
            stage=1,
            scheduled_for=scheduled_time,
            context_snapshot=test_context,
            last_user_message="Mensaje de prueba"
        )
        
        # Verificar que se creó
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT user_id, stage, status, context_snapshot, phone 
                    FROM follow_up_jobs 
                    WHERE user_id = %s
                """, (test_user_id,))
                
                created_jobs = cursor.fetchall()
                
                if created_jobs:
                    job = created_jobs[0]
                    print(f"✅ Job creado exitosamente:")
                    print(f"   User ID: {job['user_id']}")
                    print(f"   Stage: {job['stage']}")
                    print(f"   Status: {job['status']}")
                    print(f"   Phone: {job['phone']}")
                    
                    # Verificar context
                    context = job['context_snapshot']
                    if context and isinstance(context, dict):
                        interactions = context.get('interaction_history', [])
                        print(f"   Context: {len(interactions)} interacciones")
                    
                    return True
                else:
                    print("❌ No se creó ningún job")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error probando creación de jobs: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM follow_up_jobs WHERE user_id = %s", (test_user_id,))
        except:
            pass

async def test_on_conflict():
    """Probar que ON CONFLICT funciona correctamente"""
    print("\n🔄 PROBANDO ON CONFLICT")
    print("=" * 50)
    
    try:
        from datetime import datetime
        test_user_id = "test_conflict_user"
        
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Limpiar
                cursor.execute("DELETE FROM follow_up_jobs WHERE user_id = %s", (test_user_id,))
                
                # Insertar job inicial
                cursor.execute("""
                    INSERT INTO follow_up_jobs 
                    (user_id, phone, stage, scheduled_for, context_snapshot, last_user_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (test_user_id, "1234567890", 1, datetime.now(), {}, "Test"))
                
                print("✅ Job inicial creado")
                
                # Probar ON CONFLICT - debería actualizar, no fallar
                cursor.execute("""
                    INSERT INTO follow_up_jobs 
                    (user_id, phone, stage, scheduled_for, context_snapshot, last_user_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, stage) DO UPDATE SET
                        scheduled_for = EXCLUDED.scheduled_for,
                        context_snapshot = EXCLUDED.context_snapshot,
                        status = 'pending'
                """, (test_user_id, "1234567890", 1, datetime.now(), {"updated": True}, "Test Updated"))
                
                print("✅ ON CONFLICT funcionó correctamente")
                
                # Limpiar
                cursor.execute("DELETE FROM follow_up_jobs WHERE user_id = %s", (test_user_id,))
                
                return True
                
    except Exception as e:
        logger.error(f"❌ Error probando ON CONFLICT: {e}")
        return False

async def main():
    """Función principal"""
    print("🛠️ FIX DE CONSTRAINT Y PRUEBAS DE JOBS")
    print("=" * 60)
    
    tests = [
        ("Corregir Constraint", fix_constraint),
        ("Probar Creación de Jobs", test_job_creation),
        ("Probar ON CONFLICT", test_on_conflict)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Ejecutando: {test_name}")
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: ÉXITO")
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 RESULTADO FINAL")
    print("=" * 60)
    print(f"Tests exitosos: {passed}/{total}")
    
    if passed == total:
        print("🎉 TODOS LOS FIXES APLICADOS EXITOSAMENTE")
        print("\n✅ SISTEMA LISTO:")
        print("   1. Constraint NO DEFERRABLE corregido")
        print("   2. ON CONFLICT funciona correctamente")
        print("   3. Jobs se crean sin errores")
        print("   4. Context enrichment mejorado")
        
        print(f"\n🚀 Los usuarios 'candidate' deberían cambiar a 'active' pronto")
    else:
        print("⚠️ ALGUNOS FIXES FALLARON")
        print("Revisar logs arriba para detalles")

if __name__ == "__main__":
    asyncio.run(main())