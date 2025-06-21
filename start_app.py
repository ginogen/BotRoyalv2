#!/usr/bin/env python3
"""
🚀 SCRIPT DE INICIO DE APLICACIÓN
Ejecuta migración de base de datos y luego inicia la aplicación
"""

import os
import sys
import subprocess
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración de base de datos"""
    
    logger.info("🔄 Ejecutando migración de base de datos...")
    
    try:
        # Ejecutar migración
        result = subprocess.run([
            sys.executable, 'migrate_database.py'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("✅ Migración completada exitosamente")
            logger.info(result.stdout)
            return True
        else:
            logger.error("❌ Error en migración:")
            logger.error(result.stderr)
            logger.warning("⚠️ Continuando con SQLite como fallback...")
            return True  # Continuar aunque falle (usará SQLite)
            
    except subprocess.TimeoutExpired:
        logger.error("⏰ Timeout en migración - continuando con SQLite")
        return True
    except Exception as e:
        logger.error(f"❌ Error ejecutando migración: {e}")
        logger.warning("⚠️ Continuando con SQLite como fallback...")
        return True

def start_streamlit():
    """Inicia la aplicación Streamlit"""
    
    logger.info("🚀 Iniciando aplicación Streamlit...")
    
    # Configurar puerto
    port = os.getenv('PORT', '8080')
    
    # Comando para iniciar Streamlit
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'bot_testing_app.py',
        '--server.port', port,
        '--server.address', '0.0.0.0',
        '--server.headless', 'true',
        '--server.runOnSave', 'false'
    ]
    
    logger.info(f"📡 Iniciando en puerto {port}")
    
    try:
        # Ejecutar Streamlit
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error iniciando Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⏹️ Aplicación detenida por el usuario")
        sys.exit(0)

def main():
    """Función principal"""
    
    logger.info("🏁 Iniciando proceso de arranque...")
    
    # Paso 1: Migración de base de datos
    if not run_migration():
        logger.error("❌ Migración crítica falló - abortando inicio")
        sys.exit(1)
    
    # Paso 2: Iniciar aplicación
    start_streamlit()

if __name__ == "__main__":
    main() 