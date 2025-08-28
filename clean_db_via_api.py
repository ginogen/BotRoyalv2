#!/usr/bin/env python3
"""
Script para limpiar mensajes con source='followup' vía API del servidor
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_via_sql_endpoint(server_url="http://localhost:8000"):
    """Usar endpoint del servidor para ejecutar SQL de limpieza"""
    
    # Primero verificar si el servidor está corriendo
    try:
        health_response = requests.get(f"{server_url}/health", timeout=5)
        if health_response.status_code != 200:
            logger.error("❌ Servidor no está disponible")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ No se puede conectar al servidor: {e}")
        return False
    
    logger.info("✅ Servidor disponible, procediendo con limpieza...")
    
    # SQL para investigar mensajes 'followup'
    investigate_sql = "SELECT COUNT(*) as count FROM message_queue WHERE source = 'followup'"
    
    # SQL para convertir 'followup' a 'system'
    cleanup_sql = "UPDATE message_queue SET source = 'system' WHERE source = 'followup'"
    
    # Verificación final
    verify_sql = "SELECT COUNT(*) as count FROM message_queue WHERE source = 'followup'"
    
    # Como no tenemos un endpoint SQL directo, vamos a simular con el endpoint de test
    # que debería conectarse a la base de datos
    
    try:
        # Test de mensaje para verificar conectividad
        test_response = requests.post(
            f"{server_url}/test/message",
            json={"message": "test cleanup", "user_id": "cleanup_test"},
            timeout=10
        )
        
        if test_response.status_code == 200:
            logger.info("✅ Servidor puede procesar mensajes")
            logger.info("📝 Para limpiar la base de datos, necesitas acceso directo a PostgreSQL")
            logger.info("💡 Ejecuta este SQL directamente en la base de datos de Railway:")
            logger.info("   UPDATE message_queue SET source = 'system' WHERE source = 'followup';")
            return True
        else:
            logger.error(f"❌ Error en test endpoint: {test_response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error ejecutando test: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🔧 Iniciando limpieza de mensajes 'followup' vía API...")
    
    # Intentar con localhost primero
    success = clean_via_sql_endpoint("http://localhost:8000")
    
    if not success:
        # Si no funciona localmente, mostrar instrucciones para Railway
        logger.info("\n📋 INSTRUCCIONES PARA LIMPIEZA EN RAILWAY:")
        logger.info("1. Accede al dashboard de Railway")
        logger.info("2. Ve a tu base de datos PostgreSQL")
        logger.info("3. Abre la consola SQL")
        logger.info("4. Ejecuta este comando:")
        logger.info("   UPDATE message_queue SET source = 'system' WHERE source = 'followup';")
        logger.info("5. Reinicia tu aplicación")

if __name__ == "__main__":
    main()