#!/usr/bin/env python3

"""
🧹 LIMPIAR Y RECREAR TABLAS AUTOMÁTICAMENTE
Script para eliminar todas las tablas y permitir que se recreen automáticamente
"""

import os
import psycopg2
import logging
from database_persistent import DatabaseManager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def clean_postgresql_tables():
    """Elimina todas las tablas de PostgreSQL"""
    
    print("🧹 LIMPIANDO TABLAS POSTGRESQL")
    print("=" * 50)
    
    # Verificar si hay DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ No hay DATABASE_URL configurada")
        print("💡 Ejecuta: export DATABASE_URL='tu_url_aqui'")
        return False
    
    try:
        print("🔗 Conectando a PostgreSQL...")
        connection = psycopg2.connect(database_url)
        connection.autocommit = True
        cursor = connection.cursor()
        
        # Listar todas las tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('conversations', 'general_feedback', 'bot_metrics', 'feedback')
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("✅ No hay tablas para eliminar")
            return True
        
        print(f"📋 Tablas encontradas: {', '.join(tables)}")
        
        # Eliminar tablas en orden (por las foreign keys)
        table_order = ['feedback', 'bot_metrics', 'general_feedback', 'conversations']
        
        for table in table_order:
            if table in tables:
                print(f"🗑️ Eliminando tabla: {table}")
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"✅ Tabla {table} eliminada")
        
        # Verificar que se eliminaron
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('conversations', 'general_feedback', 'bot_metrics', 'feedback')
        """)
        
        remaining = cursor.fetchall()
        
        if remaining:
            print(f"⚠️ Algunas tablas no se eliminaron: {remaining}")
        else:
            print("✅ Todas las tablas eliminadas exitosamente")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error eliminando tablas: {e}")
        return False

def test_automatic_recreation():
    """Prueba que las tablas se recreen automáticamente"""
    
    print("\n🔄 PROBANDO RECREACIÓN AUTOMÁTICA")
    print("=" * 50)
    
    try:
        # Crear nueva instancia - esto debería crear las tablas automáticamente
        print("🏗️ Creando instancia de DatabaseManager...")
        db = DatabaseManager()
        
        if db.db_type != 'postgresql':
            print("⚠️ No se está usando PostgreSQL, usando SQLite")
            return True
        
        print("✅ DatabaseManager creado")
        
        # Intentar guardar una conversación de prueba
        print("💾 Guardando conversación de prueba...")
        
        conversation_id = db.save_conversation(
            user_id="test_recreate",
            message="Probando recreación automática de tablas",
            bot_response="¡Las tablas se recrearon automáticamente!",
            session_id="test_session_123"
        )
        
        print(f"✅ Conversación guardada: {conversation_id}")
        
        # Probar feedback
        print("⭐ Guardando feedback...")
        db.save_feedback(conversation_id, 5, "Test recreación", "auto")
        
        print("✅ Feedback guardado")
        
        # Verificar datos
        print("📊 Verificando datos...")
        conversations = db.get_conversations_data()
        
        print(f"✅ Datos recuperados: {len(conversations)} conversaciones")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en recreación automática: {e}")
        return False

def main():
    """Función principal"""
    
    print("🚀 SCRIPT DE LIMPIEZA Y RECREACIÓN AUTOMÁTICA")
    print("=" * 60)
    
    # Paso 1: Limpiar tablas existentes
    if not clean_postgresql_tables():
        print("\n❌ Error en la limpieza. Verifica tu DATABASE_URL")
        return False
    
    # Paso 2: Probar recreación automática
    if not test_automatic_recreation():
        print("\n❌ Error en la recreación automática")
        return False
    
    print("\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
    print("✅ Tablas eliminadas y recreadas automáticamente")
    print("🎯 Tu aplicación ahora creará las tablas cuando las necesite")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n💡 INSTRUCCIONES:")
        print("1. Asegúrate de tener DATABASE_URL configurada")
        print("2. Ejecuta: export DATABASE_URL='postgresql://usuario:password@host:port/database'")
        print("3. Vuelve a ejecutar este script")
        exit(1)
    
    print("\n🎯 PRÓXIMOS PASOS:")
    print("1. Haz deploy de tu aplicación")
    print("2. Las tablas se crearán automáticamente al guardar datos")
    print("3. No necesitas intervención manual") 