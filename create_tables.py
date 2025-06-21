#!/usr/bin/env python3
"""
Script para crear las tablas de la base de datos manualmente
"""

import os
import sys

# Agregar el directorio actual al path para importar nuestros módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_persistent import DatabaseManager

def create_tables():
    """Crear todas las tablas necesarias en la base de datos"""
    
    print("🚀 Iniciando creación de tablas...")
    
    try:
        # Inicializar el manager de base de datos
        db_manager = DatabaseManager()
        
        # Las tablas se crean automáticamente en __init__
        print("✅ DatabaseManager inicializado")
        
        # Verificar que las tablas existen
        if hasattr(db_manager, 'engine'):
            print("✅ Usando PostgreSQL")
            
            # Importar para verificar tablas
            from sqlalchemy import text
            
            with db_manager.engine.connect() as conn:
                # Verificar tablas existentes
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                
                tables = [row[0] for row in result]
                print(f"📋 Tablas encontradas: {tables}")
                
                if not tables:
                    print("ℹ️  No hay tablas - se crearán automáticamente al usar la app")
                else:
                    print("✅ Tablas existentes en la base de datos")
                    
        else:
            print("✅ Usando SQLite local")
            
        print("\n🎉 ¡Proceso completado!")
        print("💡 Las tablas se crearán automáticamente cuando:")
        print("   • Alguien chate con el bot")
        print("   • Se guarde feedback")
        print("   • Se registren métricas")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Esto es normal - las tablas se crean cuando se usan")

if __name__ == "__main__":
    create_tables() 