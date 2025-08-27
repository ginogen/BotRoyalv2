#!/usr/bin/env python3
"""
🔄 ROYAL BOT - ACTIVADOR DEL SISTEMA UNIFICADO
Script para activar el sistema unificado de forma segura
con rollback automático en caso de problemas.
"""

import os
import logging
import time
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_current_server():
    """Hacer backup del servidor actual"""
    try:
        server_path = "/Users/gino/BotRoyalv2/royal_server_optimized.py"
        backup_path = "/Users/gino/BotRoyalv2/royal_server_optimized.py.backup"
        
        # Leer servidor actual
        with open(server_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # Guardar backup
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(current_content)
            
        logger.info(f"✅ Backup created: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}")
        return False

def modify_server_imports():
    """Modificar las importaciones del servidor para usar AgentManager"""
    try:
        server_path = "/Users/gino/BotRoyalv2/royal_server_optimized.py"
        
        # Leer contenido actual
        with open(server_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Modificar la importación
        old_import = "from royal_agents.royal_agent_contextual import run_contextual_conversation_sync"
        new_import = "from royal_agents.agent_manager import run_contextual_conversation_sync_managed as run_contextual_conversation_sync"
        
        if old_import in content:
            content = content.replace(old_import, new_import)
            
            # Escribir el archivo modificado
            with open(server_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✅ Server imports updated to use AgentManager")
            return True
        else:
            logger.warning("⚠️ Original import not found - manual integration may be needed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error modifying server imports: {e}")
        return False

def test_integration():
    """Test que la integración funcione correctamente"""
    try:
        # Importar la nueva función
        from royal_agents.agent_manager import run_contextual_conversation_sync_managed
        
        # Test básico
        start_time = time.time()
        test_response = run_contextual_conversation_sync_managed("test_integration", "¿Cuál es el mínimo?")
        response_time = time.time() - start_time
        
        # Validar respuesta
        if test_response and len(test_response) > 10:
            logger.info(f"✅ Integration test PASSED ({response_time:.2f}s)")
            logger.info(f"✅ Test response length: {len(test_response)} chars")
            return True
        else:
            logger.error("❌ Integration test FAILED - Empty or short response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test FAILED: {e}")
        return False

def rollback_server():
    """Rollback al servidor original"""
    try:
        server_path = "/Users/gino/BotRoyalv2/royal_server_optimized.py"
        backup_path = "/Users/gino/BotRoyalv2/royal_server_optimized.py.backup"
        
        if Path(backup_path).exists():
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            
            with open(server_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
                
            logger.info("🔄 Server rolled back to original version")
            return True
        else:
            logger.error("❌ No backup found for rollback")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during rollback: {e}")
        return False

def enable_unified_agent():
    """Habilitar el agente unificado a través de feature flags"""
    try:
        from royal_agents.agent_manager import switch_to_unified_agent
        
        success = switch_to_unified_agent()
        if success:
            logger.info("✅ Unified agent ENABLED")
            return True
        else:
            logger.error("❌ Failed to enable unified agent")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enabling unified agent: {e}")
        return False

def main():
    """Activación principal del sistema unificado"""
    print("🚀 ROYAL BOT - UNIFIED SYSTEM ACTIVATOR")
    print("="*50)
    
    # Paso 1: Backup del servidor actual
    print("\n📦 Step 1: Creating backup...")
    if not backup_current_server():
        print("❌ FAILED: Cannot create backup. Aborting.")
        return 1
    
    # Paso 2: Modificar importaciones del servidor
    print("\n🔧 Step 2: Updating server imports...")
    if not modify_server_imports():
        print("❌ FAILED: Cannot modify server imports. Aborting.")
        return 1
    
    # Paso 3: Test de integración básica
    print("\n🧪 Step 3: Testing integration...")
    if not test_integration():
        print("❌ FAILED: Integration test failed. Rolling back...")
        rollback_server()
        return 1
    
    # Paso 4: Habilitar agente unificado (opcional)
    print("\n🎯 Step 4: Enabling unified agent...")
    print("⚠️  This step is OPTIONAL. The system will work with original agents by default.")
    print("⚠️  Only enable if you want to test the unified agent immediately.")
    
    enable_unified = input("Enable unified agent? (y/N): ").lower().strip()
    
    if enable_unified == 'y':
        if enable_unified_agent():
            print("✅ Unified agent enabled!")
        else:
            print("⚠️  Failed to enable unified agent, but integration is still active")
    else:
        print("ℹ️  Unified agent NOT enabled. System will use original agents.")
    
    # Resultado final
    print("\n🎉 SUCCESS! System is now integrated with AgentManager")
    print("\n📋 NEXT STEPS:")
    print("1. Restart your server to activate the new integration")
    print("2. Monitor logs for any issues")  
    print("3. Use agent_manager functions to control agent selection")
    print("4. Run tests with: python test_unified_agent.py")
    
    return 0

if __name__ == "__main__":
    exit(main())