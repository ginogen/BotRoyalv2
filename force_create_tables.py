#!/usr/bin/env python3
"""
🔧 FORZAR CREACIÓN DE TABLAS
Script para diagnosticar y forzar la creación correcta de tablas en PostgreSQL
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configurar logging detallado
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def diagnose_database():
    """Diagnostica la base de datos PostgreSQL"""
    
    print("🔍 DIAGNÓSTICO DE BASE DE DATOS")
    print("=" * 50)
    
    # Verificar variables de entorno
    database_url = os.getenv('DATABASE_URL')
    postgres_url = os.getenv('POSTGRES_URL')
    
    print(f"📊 VARIABLES DE ENTORNO:")
    print(f"   DATABASE_URL: {'✅ Configurado' if database_url else '❌ No encontrado'}")
    print(f"   POSTGRES_URL: {'✅ Configurado' if postgres_url else '❌ No encontrado'}")
    
    if not database_url and not postgres_url:
        print("❌ No hay URL de base de datos configurada")
        return False
    
    db_url = database_url or postgres_url
    if db_url and len(db_url) > 40:
        print(f"   URL a usar: {db_url[:30]}***{db_url[-10:]}")
    else:
        print(f"   URL a usar: ***")
    
    try:
        # Intentar conectar
        print("\n🔗 PROBANDO CONEXIÓN...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        
        print("✅ Conexión exitosa a PostgreSQL")
        
        # Verificar tablas existentes
        print("\n📋 VERIFICANDO TABLAS EXISTENTES...")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name IN ('conversations', 'general_feedback')
            ORDER BY table_name, ordinal_position
        """)
        
        tables_info = cursor.fetchall()
        
        if not tables_info:
            print("⚠️  No se encontraron tablas 'conversations' o 'general_feedback'")
            return conn
        else:
            print("📋 ESTRUCTURA DE TABLAS:")
            current_table = None
            for row in tables_info:
                if current_table != row['table_name']:
                    current_table = row['table_name']
                    print(f"\n  🗂️  Tabla: {current_table}")
                print(f"     • {row['column_name']}: {row['data_type']} ({'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Verificar si la columna rating existe específicamente
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' 
            AND column_name = 'rating'
            AND table_schema = 'public'
        """)
        
        rating_column = cursor.fetchone()
        if rating_column:
            print(f"\n✅ Columna 'rating' encontrada en tabla 'conversations'")
        else:
            print(f"\n❌ Columna 'rating' NO encontrada en tabla 'conversations'")
        
        cursor.close()
        return conn
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        return False

def force_create_tables(conn):
    """Fuerza la creación correcta de tablas"""
    
    print("\n🔨 FORZANDO CREACIÓN DE TABLAS")
    print("=" * 50)
    
    cursor = conn.cursor()
    
    try:
        # PRIMERO: Eliminar tablas existentes si están corruptas
        print("⚠️  Eliminando tablas existentes (si existen)...")
        cursor.execute('DROP TABLE IF EXISTS conversations CASCADE')
        cursor.execute('DROP TABLE IF EXISTS general_feedback CASCADE')
        
        print("✅ Tablas eliminadas")
        
        # SEGUNDO: Crear tabla de conversaciones
        print("\n📋 Creando tabla 'conversations'...")
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
        
        print("✅ Tabla 'conversations' creada")
        
        # TERCERO: Crear tabla de feedback general
        print("\n📋 Creando tabla 'general_feedback'...")
        cursor.execute('''
            CREATE TABLE general_feedback (
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
        
        print("✅ Tabla 'general_feedback' creada")
        
        # CUARTO: Crear índices
        print("\n🔍 Creando índices...")
        cursor.execute('CREATE INDEX idx_conversations_user_timestamp ON conversations(user_id, timestamp)')
        cursor.execute('CREATE INDEX idx_conversations_rating ON conversations(rating)')
        cursor.execute('CREATE INDEX idx_feedback_priority ON general_feedback(priority, status)')
        
        print("✅ Índices creados")
        
        # QUINTO: Verificar estructura final
        print("\n🔍 VERIFICANDO ESTRUCTURA FINAL...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'conversations' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("📋 Columnas en tabla 'conversations':")
        for col_name, data_type, nullable in columns:
            print(f"   • {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
        
        # Verificar específicamente la columna rating
        rating_exists = any(col[0] == 'rating' for col in columns)
        if rating_exists:
            print("\n✅ ¡Columna 'rating' creada correctamente!")
        else:
            print("\n❌ ¡ERROR! Columna 'rating' no se creó")
            
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        cursor.close()
        return False

def test_insert_and_update():
    """Prueba las operaciones de inserción y actualización"""
    
    print("\n🧪 PROBANDO OPERACIONES DE BASE DE DATOS")
    print("=" * 50)
    
    try:
        # Usar el DatabaseManager existente
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_persistent import DatabaseManager
        
        # Crear nueva instancia para forzar reconexión
        db_manager = DatabaseManager()
        
        if db_manager.db_type != 'postgresql':
            print(f"⚠️  DatabaseManager está usando {db_manager.db_type}, no PostgreSQL")
            print("   Esto indica que aún hay un problema de conexión")
            return False
        
        print("✅ DatabaseManager conectado a PostgreSQL")
        
        # Probar inserción
        print("\n📝 Probando inserción de conversación...")
        conversation_id = db_manager.save_conversation(
            user_id="test_user_123",
            message="Mensaje de prueba",
            bot_response="Respuesta de prueba",
            session_id="test_session_123"
        )
        
        print(f"✅ Conversación guardada con ID: {conversation_id}")
        
        # Probar actualización con rating
        print("\n⭐ Probando actualización de rating...")
        db_manager.save_feedback(
            conversation_id=conversation_id,
            rating=5,
            feedback_text="Excelente servicio de prueba",
            category="test"
        )
        
        print("✅ Rating guardado correctamente")
        
        # Verificar datos
        print("\n🔍 Verificando datos guardados...")
        data = db_manager.get_conversations_data()
        
        if data and len(data) > 0:
            last_record = data[0]  # Más reciente
            print(f"   ID: {last_record.get('id')}")
            print(f"   Usuario: {last_record.get('user_id')}")
            print(f"   Rating: {last_record.get('rating')}")
            print(f"   Feedback: {last_record.get('feedback_text')}")
            
            if last_record.get('rating') == 5:
                print("✅ ¡TODO FUNCIONA CORRECTAMENTE!")
                return True
            else:
                print("❌ El rating no se guardó correctamente")
                return False
        else:
            print("❌ No se pudieron recuperar los datos")
            return False
            
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        return False

def main():
    """Función principal"""
    
    print("🚀 SCRIPT DE DIAGNÓSTICO Y REPARACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    # Paso 1: Diagnóstico
    conn = diagnose_database()
    if not conn:
        print("\n❌ No se pudo conectar a la base de datos")
        sys.exit(1)
    
    # Paso 2: Forzar creación de tablas
    if not force_create_tables(conn):
        print("\n❌ No se pudieron crear las tablas")
        conn.close()
        sys.exit(1)
    
    conn.close()
    
    # Paso 3: Probar operaciones
    if not test_insert_and_update():
        print("\n❌ Las operaciones de base de datos fallan")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 ¡ÉXITO! La base de datos está funcionando correctamente")
    print("=" * 60)
    print("💡 Ahora tu aplicación debería funcionar sin problemas")
    print("💾 Los datos se guardarán en PostgreSQL en lugar de SQLite")

if __name__ == "__main__":
    main() 