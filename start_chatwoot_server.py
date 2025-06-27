#!/usr/bin/env python3
"""
🚀 SCRIPT DE INICIO - ROYAL BOT CHATWOOT SERVER
Facilita el inicio del servidor con verificaciones automáticas
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def print_banner():
    """Mostrar banner de inicio"""
    print("=" * 60)
    print("🤖 ROYAL BOT - SERVIDOR CHATWOOT")
    print("   Optimizado para múltiples conversaciones")
    print("=" * 60)
    print()

def check_requirements():
    """Verificar que las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    
    try:
        import fastapi
        import uvicorn
        import httpx
        import royal_agents
        print("   ✅ FastAPI, Uvicorn, HTTPX")
        print("   ✅ Royal Agents")
        return True
    except ImportError as e:
        print(f"   ❌ Falta dependencia: {e}")
        print("   📦 Instalar con: pip install -r requirements.txt")
        return False

def check_env_file():
    """Verificar archivo de configuración"""
    print("🔍 Verificando configuración...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("   ⚠️  Archivo .env no encontrado")
        print("   📋 Copia config.chatwoot.env.example como .env")
        
        # Crear .env básico si no existe
        with open(".env", "w") as f:
            f.write("# Configuración básica Royal Bot\n")
            f.write("PORT=8000\n")
            f.write("WORKER_POOL_SIZE=3\n")
            f.write("MAX_CONCURRENT_USERS=5\n")
            f.write("\n# Completa estas variables para Chatwoot:\n")
            f.write("# CHATWOOT_API_URL=https://tu-chatwoot.com\n")
            f.write("# CHATWOOT_API_TOKEN=tu_token\n")
            f.write("# CHATWOOT_ACCOUNT_ID=123\n")
        
        print("   ✅ Archivo .env básico creado")
        return False
    
    print("   ✅ Archivo .env encontrado")
    return True

def check_chatwoot_config():
    """Verificar configuración de Chatwoot"""
    print("🔍 Verificando configuración Chatwoot...")
    
    load_dotenv()
    
    chatwoot_url = os.getenv("CHATWOOT_API_URL")
    chatwoot_token = os.getenv("CHATWOOT_API_TOKEN") 
    chatwoot_account = os.getenv("CHATWOOT_ACCOUNT_ID")
    
    if not chatwoot_url:
        print("   ⚠️  CHATWOOT_API_URL no configurado")
        return False
    
    if not chatwoot_token:
        print("   ⚠️  CHATWOOT_API_TOKEN no configurado")
        return False
        
    if not chatwoot_account:
        print("   ⚠️  CHATWOOT_ACCOUNT_ID no configurado")
        return False
    
    print("   ✅ Configuración Chatwoot completa")
    return True

def check_evolution_config():
    """Verificar configuración de Evolution API"""
    print("🔍 Verificando configuración Evolution API...")
    
    evolution_url = os.getenv("EVOLUTION_API_URL")
    evolution_token = os.getenv("EVOLUTION_API_TOKEN")
    
    if not evolution_url or not evolution_token:
        print("   ⚠️  Evolution API no configurado (opcional)")
        print("   📱 Solo Chatwoot funcionará")
        return False
    
    print("   ✅ Evolution API configurado")
    return True

def show_startup_info():
    """Mostrar información de inicio"""
    port = os.getenv("PORT", "8000")
    workers = os.getenv("WORKER_POOL_SIZE", "3")
    max_users = os.getenv("MAX_CONCURRENT_USERS", "5")
    
    print()
    print("🚀 CONFIGURACIÓN DE INICIO:")
    print(f"   📊 Puerto: {port}")
    print(f"   👥 Workers: {workers}")
    print(f"   🔄 Usuarios concurrentes: {max_users}")
    print()
    print("📡 ENDPOINTS DISPONIBLES:")
    print(f"   🏠 Principal: http://localhost:{port}/")
    print(f"   ❤️  Health: http://localhost:{port}/health")
    print(f"   🧪 Test: http://localhost:{port}/test/message")
    print(f"   📊 Stats: http://localhost:{port}/stats")
    print()
    print("🔗 WEBHOOKS:")
    print(f"   📥 Chatwoot: http://localhost:{port}/webhook/chatwoot")
    print(f"   📱 Evolution: http://localhost:{port}/webhook/evolution")
    print()

def main():
    """Función principal"""
    print_banner()
    
    # Verificaciones previas
    if not check_requirements():
        sys.exit(1)
    
    env_exists = check_env_file()
    chatwoot_ok = check_chatwoot_config() if env_exists else False
    evolution_ok = check_evolution_config() if env_exists else False
    
    if not env_exists:
        print()
        print("🔧 CONFIGURACIÓN REQUERIDA:")
        print("   1. Edita el archivo .env que se creó")
        print("   2. Completa las variables de Chatwoot")
        print("   3. Opcionalmente configura Evolution API")
        print("   4. Ejecuta este script de nuevo")
        print()
        print("📖 Ver config.chatwoot.env.example para ayuda")
        sys.exit(1)
    
    if not chatwoot_ok:
        print()
        print("⚠️  ADVERTENCIA: Chatwoot no configurado")
        print("   El servidor iniciará pero necesitarás configurar:")
        print("   - CHATWOOT_API_URL")
        print("   - CHATWOOT_API_TOKEN") 
        print("   - CHATWOOT_ACCOUNT_ID")
        print()
        response = input("¿Continuar sin Chatwoot? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    show_startup_info()
    
    # Preguntar modo de inicio
    print("🎯 MODOS DE INICIO:")
    print("   1. Desarrollo (con recarga automática)")
    print("   2. Producción (optimizado)")
    print("   3. Test (solo verificar)")
    print()
    
    while True:
        try:
            mode = input("Selecciona modo (1-3): ").strip()
            if mode in ['1', '2', '3']:
                break
            print("Por favor selecciona 1, 2 o 3")
        except KeyboardInterrupt:
            print("\n👋 Cancelado")
            sys.exit(0)
    
    print()
    print("🚀 Iniciando servidor...")
    print("   (Presiona Ctrl+C para detener)")
    print()
    
    try:
        if mode == '1':
            # Modo desarrollo
            subprocess.run([
                sys.executable, "-m", "uvicorn",
                "royal_chatwoot_server:app",
                "--host", "0.0.0.0",
                "--port", os.getenv("PORT", "8000"),
                "--reload",
                "--log-level", "info"
            ])
        elif mode == '2':
            # Modo producción
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "royal_chatwoot_server:app",
                "--host", "0.0.0.0",
                "--port", os.getenv("PORT", "8000"),
                "--workers", "1",
                "--log-level", "warning"
            ])
        elif mode == '3':
            # Modo test
            print("🧪 Ejecutando tests básicos...")
            subprocess.run([
                sys.executable, "-c",
                "import royal_chatwoot_server; print('✅ Servidor importado correctamente')"
            ])
            print("✅ Tests básicos completados")
            
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
    except Exception as e:
        print(f"\n❌ Error iniciando servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 