#!/usr/bin/env python3
"""
Script para activar la limpieza de mensajes inválidos vía endpoint
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def trigger_cleanup(server_url):
    """Activar limpieza de mensajes con sources inválidos"""
    
    try:
        logger.info(f"🔧 Activando limpieza en: {server_url}")
        
        response = requests.post(
            f"{server_url}/admin/cleanup-invalid-sources",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Limpieza completada:")
            logger.info(f"   - Mensajes limpiados: {data.get('cleaned_count', 0)}")
            logger.info(f"   - Sources inválidos encontrados: {data.get('invalid_sources_found', [])}")
            return True
        else:
            logger.error(f"❌ Error en limpieza: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ No se puede conectar al servidor: {e}")
        return False

def main():
    """Función principal"""
    # Intentar con la URL de Railway primero
    railway_url = "https://botroyalv2-production.up.railway.app"
    local_url = "http://localhost:8000"
    
    logger.info("🚀 Iniciando limpieza de sources inválidos...")
    
    # Intentar Railway primero
    logger.info("\n1️⃣ Intentando con Railway...")
    success = trigger_cleanup(railway_url)
    
    if not success:
        logger.info("\n2️⃣ Intentando localmente...")
        success = trigger_cleanup(local_url)
    
    if success:
        logger.info("\n✅ LIMPIEZA COMPLETADA")
        logger.info("💡 Los errores de 'followup' deberían desaparecer ahora")
    else:
        logger.info("\n❌ NO SE PUDO EJECUTAR LA LIMPIEZA")
        logger.info("💡 Asegúrate de que el servidor esté corriendo")

if __name__ == "__main__":
    main()