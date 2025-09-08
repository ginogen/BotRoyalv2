#!/usr/bin/env python3
"""
🛡️ Aplicar Fix de Rate Limiting para Follow-up Spam
Script para aplicar las mejoras anti-spam al sistema de follow-ups
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('followup.fix')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no encontrado en variables de entorno")
    sys.exit(1)

def apply_rate_limit_migration():
    """Aplicar migración de rate limiting"""
    print("🛡️ APLICANDO MIGRACIÓN DE RATE LIMITING")
    print("=" * 60)
    
    try:
        # Leer el archivo de migración
        migration_file = "/Users/gino/BotRoyalv2/migrations/add_follow_up_rate_limits.sql"
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Aplicar migración
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(migration_sql)
                conn.commit()
                
        logger.info("✅ Migración de rate limiting aplicada exitosamente")
        return True
        
    except FileNotFoundError:
        logger.error(f"❌ No se encontró archivo de migración: {migration_file}")
        return False
    except Exception as e:
        logger.error(f"❌ Error aplicando migración: {e}")
        return False

def verify_tables_created():
    """Verificar que las tablas se crearon correctamente"""
    print("\n🔍 VERIFICANDO TABLAS CREADAS")
    print("-" * 40)
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar tablas creadas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('follow_up_rate_limits', 'follow_up_recovery_locks')
                    ORDER BY table_name
                """)
                
                tables = cursor.fetchall()
                
                if len(tables) == 2:
                    logger.info("✅ Ambas tablas creadas correctamente:")
                    for table in tables:
                        logger.info(f"   - {table['table_name']}")
                    return True
                else:
                    logger.error(f"❌ Solo {len(tables)} de 2 tablas encontradas")
                    return False
                
    except Exception as e:
        logger.error(f"❌ Error verificando tablas: {e}")
        return False

def test_rate_limit_functions():
    """Test básico de las funciones de rate limiting"""
    print("\n🧪 TESTING FUNCIONES DE RATE LIMITING")
    print("-" * 40)
    
    try:
        # Importar el scheduler para probar las funciones
        from royal_agents.follow_up import FollowUpScheduler
        
        scheduler = FollowUpScheduler(DATABASE_URL)
        
        async def run_tests():
            test_user_id = "test_rate_limit_user"
            
            # Test 1: Usuario nuevo debe poder enviar
            logger.info("Test 1: Usuario nuevo")
            can_send = await scheduler._check_daily_rate_limit(test_user_id)
            if can_send:
                logger.info("✅ Usuario nuevo puede enviar follow-up")
            else:
                logger.error("❌ Usuario nuevo NO puede enviar follow-up")
                return False
            
            # Test 2: Incrementar contador
            logger.info("Test 2: Incrementar contador")
            increment_success = await scheduler._increment_daily_count(test_user_id)
            if increment_success:
                logger.info("✅ Contador incrementado exitosamente")
            else:
                logger.error("❌ Error incrementando contador")
                return False
            
            # Test 3: Usuario debe estar bloqueado después de 1 envío
            logger.info("Test 3: Rate limit después de envío")
            can_send_again = await scheduler._check_daily_rate_limit(test_user_id)
            if not can_send_again:
                logger.info("✅ Rate limit funcionando - usuario bloqueado")
            else:
                logger.error("❌ Rate limit NO funciona - usuario puede enviar otra vez")
                return False
            
            # Test 4: Lock system
            logger.info("Test 4: Sistema de locks")
            lock_acquired = await scheduler._acquire_recovery_lock(test_user_id, 'test', 1)
            if lock_acquired:
                logger.info("✅ Lock adquirido exitosamente")
                
                # Intentar adquirir lock otra vez (debe fallar)
                lock_acquired_again = await scheduler._acquire_recovery_lock(test_user_id, 'test', 1)
                if not lock_acquired_again:
                    logger.info("✅ Lock previene duplicados")
                else:
                    logger.error("❌ Sistema de locks NO funciona")
                    return False
                
                # Liberar lock
                await scheduler._release_recovery_lock(test_user_id)
                logger.info("✅ Lock liberado exitosamente")
            else:
                logger.error("❌ No se pudo adquirir lock")
                return False
            
            # Cleanup
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM follow_up_rate_limits WHERE user_id = %s", (test_user_id,))
                    cursor.execute("DELETE FROM follow_up_recovery_locks WHERE user_id = %s", (test_user_id,))
                    conn.commit()
                    
            logger.info("✅ Cleanup completado")
            return True
        
        return asyncio.run(run_tests())
        
    except Exception as e:
        logger.error(f"❌ Error en tests: {e}")
        return False

def investigate_problematic_user():
    """Investigar el usuario problemático 5493413418733"""
    print("\n🔍 INVESTIGANDO USUARIO PROBLEMÁTICO")
    print("-" * 40)
    
    PROBLEM_USER = "5493413418733"
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Contar jobs pendientes
                cursor.execute("""
                    SELECT COUNT(*) as count, status
                    FROM follow_up_jobs 
                    WHERE user_id LIKE %s OR phone = %s
                    GROUP BY status
                    ORDER BY count DESC
                """, (f"%{PROBLEM_USER}%", PROBLEM_USER))
                
                job_stats = cursor.fetchall()
                
                if job_stats:
                    logger.info(f"📊 Estado de jobs para {PROBLEM_USER}:")
                    for stat in job_stats:
                        logger.info(f"   {stat['status']}: {stat['count']} jobs")
                else:
                    logger.info(f"ℹ️ No se encontraron jobs para {PROBLEM_USER}")
                
                # Verificar rate limit
                cursor.execute("""
                    SELECT user_id, daily_count, last_followup_sent, reset_date
                    FROM follow_up_rate_limits 
                    WHERE user_id LIKE %s
                """, (f"%{PROBLEM_USER}%",))
                
                rate_limit = cursor.fetchone()
                if rate_limit:
                    logger.info(f"🛡️ Rate limit para {PROBLEM_USER}:")
                    logger.info(f"   Daily count: {rate_limit['daily_count']}")
                    logger.info(f"   Last sent: {rate_limit['last_followup_sent']}")
                    logger.info(f"   Reset date: {rate_limit['reset_date']}")
                else:
                    logger.info(f"ℹ️ No hay registro de rate limit para {PROBLEM_USER}")
                
                return True
                
    except Exception as e:
        logger.error(f"❌ Error investigando usuario problemático: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Iniciando aplicación de fix anti-spam para follow-ups...")
    
    success_steps = 0
    total_steps = 4
    
    # Step 1: Aplicar migración
    if apply_rate_limit_migration():
        success_steps += 1
    
    # Step 2: Verificar tablas
    if verify_tables_created():
        success_steps += 1
    
    # Step 3: Test funciones
    if test_rate_limit_functions():
        success_steps += 1
    
    # Step 4: Investigar usuario problemático
    if investigate_problematic_user():
        success_steps += 1
    
    print(f"\n📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"Steps completados: {success_steps}/{total_steps}")
    
    if success_steps == total_steps:
        print("✅ FIX APLICADO EXITOSAMENTE")
        print("\n🎯 PRÓXIMOS PASOS:")
        print("1. Reiniciar el servidor para aplicar cambios")
        print("2. Monitorear endpoint: /api/followup/spam-detection")  
        print("3. Verificar que no hay más follow-ups múltiples")
        print("4. Rate limit: máximo 1 follow-up por día por usuario")
    else:
        print("❌ ALGUNOS PASOS FALLARON")
        print("Revisar logs arriba para detalles")

if __name__ == "__main__":
    main()