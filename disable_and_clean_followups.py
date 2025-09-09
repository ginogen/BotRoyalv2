#!/usr/bin/env python3
"""
🧹 LIMPIEZA TOTAL Y DESACTIVACIÓN DE FOLLOW-UPS
Script para limpiar completamente el sistema de follow-ups y desactivarlo
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:ngYpnFNDfDsaqyLzVsxsjoLowpOxnhjy@nozomi.proxy.rlwy.net:39231/railway")

def clean_all_followup_data():
    """Limpiar TODOS los datos de follow-ups de la base de datos"""
    print("🧹 LIMPIANDO TODOS LOS DATOS DE FOLLOW-UPS")
    print("=" * 60)
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # Contar datos antes de limpiar
                tables_to_clean = [
                    'follow_up_jobs',
                    'follow_up_history', 
                    'follow_up_blacklist',
                    'follow_up_rate_limits',
                    'follow_up_recovery_locks'
                ]
                
                print("📊 DATOS ANTES DE LIMPIAR:")
                total_records = 0
                for table in tables_to_clean:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        print(f"   {table}: {count} registros")
                        total_records += count
                    except Exception as e:
                        print(f"   {table}: No existe o error - {e}")
                
                print(f"   TOTAL: {total_records} registros")
                
                if total_records == 0:
                    print("✅ Ya estaba limpio - no hay registros de follow-ups")
                    return True
                
                # Limpiar cada tabla
                print(f"\n🗑️ ELIMINANDO TODOS LOS REGISTROS:")
                cleaned_tables = 0
                
                for table in tables_to_clean:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        deleted = cursor.rowcount
                        if deleted > 0:
                            print(f"✅ {table}: {deleted} registros eliminados")
                            cleaned_tables += 1
                        else:
                            print(f"ℹ️ {table}: Ya estaba vacío")
                    except Exception as e:
                        print(f"⚠️ {table}: Error eliminando - {e}")
                
                # Resetear secuencias si existen
                print(f"\n🔄 RESETEANDO SECUENCIAS:")
                sequences = ['follow_up_jobs_id_seq', 'follow_up_history_id_seq']
                for seq in sequences:
                    try:
                        cursor.execute(f"SELECT setval('{seq}', 1, false)")
                        print(f"✅ Secuencia {seq} reseteada")
                    except Exception as e:
                        print(f"ℹ️ Secuencia {seq}: {e}")
                
                print(f"\n✅ LIMPIEZA COMPLETADA")
                print(f"   Tablas limpiadas: {cleaned_tables}/{len(tables_to_clean)}")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error limpiando datos de follow-ups: {e}")
        return False

def disable_followup_scheduler():
    """Desactivar el sistema de follow-ups en el código"""
    print("\n🔒 DESACTIVANDO SISTEMA DE FOLLOW-UPS")
    print("=" * 60)
    
    try:
        # Crear flag de desactivación en el servidor
        server_file = "/Users/gino/BotRoyalv2/royal_server_optimized.py"
        
        # Leer archivo actual
        with open(server_file, 'r') as f:
            content = f.read()
        
        # Buscar inicialización del scheduler
        if 'followup_scheduler = FollowUpScheduler(' in content:
            # Comentar la inicialización
            content = content.replace(
                'followup_scheduler = FollowUpScheduler(',
                '# FOLLOW-UPS DESACTIVADOS TEMPORALMENTE\n    # followup_scheduler = FollowUpScheduler('
            )
            print("✅ FollowUpScheduler initialization commented out")
            
            # También desactivar el start del scheduler
            content = content.replace(
                'followup_scheduler.start()',
                '# followup_scheduler.start()  # DESACTIVADO'
            )
            print("✅ FollowUpScheduler.start() commented out")
            
            # Escribir archivo modificado
            with open(server_file, 'w') as f:
                f.write(content)
            
            print("✅ Follow-up scheduler desactivado en royal_server_optimized.py")
            return True
        else:
            print("ℹ️ No se encontró inicialización de FollowUpScheduler activa")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error desactivando scheduler: {e}")
        return False

def create_disable_flag():
    """Crear flag para indicar que follow-ups están desactivados"""
    print("\n🚩 CREANDO FLAG DE DESACTIVACIÓN")
    print("=" * 60)
    
    try:
        flag_file = "/Users/gino/BotRoyalv2/FOLLOWUPS_DISABLED.txt"
        
        with open(flag_file, 'w') as f:
            f.write("""
🚫 SISTEMA DE FOLLOW-UPS DESACTIVADO

Fecha de desactivación: $(date)
Motivo: Limpieza y desactivación temporal por problemas técnicos

Para reactivar:
1. Eliminar este archivo
2. Descomentar código en royal_server_optimized.py
3. Reiniciar servidor

Estado actual:
- Todos los datos de follow-ups eliminados
- Scheduler desactivado
- Sistema completamente inactivo
""")
        
        print(f"✅ Flag creado: {flag_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando flag: {e}")
        return False

def verify_cleanup():
    """Verificar que la limpieza fue exitosa"""
    print("\n🔍 VERIFICANDO LIMPIEZA")
    print("=" * 60)
    
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # Verificar que las tablas estén vacías
                tables = ['follow_up_jobs', 'follow_up_history', 'follow_up_rate_limits']
                all_clean = True
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        if count == 0:
                            print(f"✅ {table}: Vacío (0 registros)")
                        else:
                            print(f"❌ {table}: Aún tiene {count} registros")
                            all_clean = False
                    except Exception as e:
                        print(f"ℹ️ {table}: {e}")
                
                return all_clean
                
    except Exception as e:
        logger.error(f"❌ Error verificando limpieza: {e}")
        return False

def main():
    """Función principal"""
    print("🚫 LIMPIEZA TOTAL Y DESACTIVACIÓN DE FOLLOW-UPS")
    print("=" * 70)
    print("⚠️ ESTA OPERACIÓN ELIMINARÁ TODOS LOS DATOS DE FOLLOW-UPS")
    print("=" * 70)
    
    # Auto-confirmar para ejecución no interactiva
    print("\n🚀 PROCEDIENDO CON LIMPIEZA AUTOMÁTICA...")
    
    steps = [
        ("Limpiar datos de BD", clean_all_followup_data),
        ("Desactivar scheduler", disable_followup_scheduler),
        ("Crear flag de desactivación", create_disable_flag),
        ("Verificar limpieza", verify_cleanup)
    ]
    
    completed = 0
    total = len(steps)
    
    for step_name, step_func in steps:
        try:
            print(f"\n🔄 Ejecutando: {step_name}")
            if step_func():
                completed += 1
                print(f"✅ {step_name}: COMPLETADO")
            else:
                print(f"❌ {step_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {step_name}: ERROR - {e}")
    
    print(f"\n🏁 RESULTADO FINAL")
    print("=" * 70)
    print(f"Pasos completados: {completed}/{total}")
    
    if completed == total:
        print("🎉 FOLLOW-UPS COMPLETAMENTE DESACTIVADOS Y LIMPIADOS")
        print("\n✅ ESTADO ACTUAL:")
        print("   • Todos los datos de follow-ups eliminados")
        print("   • Sistema de scheduler desactivado")
        print("   • No se crearán nuevos follow-ups")
        print("   • No se enviarán mensajes automáticos")
        
        print(f"\n🚀 PRÓXIMOS PASOS:")
        print("   1. Reiniciar el servidor para aplicar cambios")
        print("   2. Verificar que no aparecen errores de follow-up")
        print("   3. Dashboard debería mostrar 0 usuarios con follow-ups")
        
        print(f"\n🔄 PARA REACTIVAR EN EL FUTURO:")
        print("   1. Eliminar archivo FOLLOWUPS_DISABLED.txt")
        print("   2. Descomentar código en royal_server_optimized.py")
        print("   3. Reiniciar servidor")
        
    else:
        print("⚠️ ALGUNOS PASOS FALLARON")
        print("Revisar output arriba y ejecutar manualmente si es necesario")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()