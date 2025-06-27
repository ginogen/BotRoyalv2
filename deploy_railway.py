#!/usr/bin/env python3
"""
🚀 SCRIPT DE DESPLIEGUE RAILWAY
Automatiza la configuración para desplegar en Railway
"""

import os
import subprocess
import json
import requests
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("🚀 ROYAL BOT - CONFIGURACIÓN RAILWAY")
    print("   Automatiza el despliegue en producción")
    print("=" * 60)
    print()

def check_requirements():
    """Verificar herramientas necesarias"""
    print("🔍 Verificando herramientas...")
    
    # Verificar Git
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Git disponible")
        else:
            print("   ❌ Git no encontrado")
            return False
    except FileNotFoundError:
        print("   ❌ Git no instalado")
        return False
    
    # Verificar si estamos en un repo Git
    if not Path('.git').exists():
        print("   ⚠️  No estás en un repositorio Git")
        response = input("   ¿Inicializar repositorio Git? (y/N): ")
        if response.lower() == 'y':
            subprocess.run(['git', 'init'])
            print("   ✅ Repositorio Git inicializado")
        else:
            return False
    
    return True

def check_railway_cli():
    """Verificar Railway CLI"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Railway CLI disponible")
            return True
        else:
            print("   ⚠️  Railway CLI no encontrado")
            return False
    except FileNotFoundError:
        print("   ⚠️  Railway CLI no instalado")
        return False

def install_railway_cli():
    """Instalar Railway CLI"""
    print("📦 Instalando Railway CLI...")
    
    try:
        # Intentar instalar con npm
        result = subprocess.run(['npm', 'install', '-g', '@railway/cli'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Railway CLI instalado con npm")
            return True
        else:
            print("   ❌ Error instalando con npm")
            print("   💡 Instala manualmente: npm install -g @railway/cli")
            return False
    except FileNotFoundError:
        print("   ⚠️  npm no disponible")
        print("   💡 Instala Railway CLI manualmente desde: https://docs.railway.app/develop/cli")
        return False

def prepare_git():
    """Preparar repositorio Git"""
    print("📦 Preparando repositorio...")
    
    # Verificar si hay cambios sin commit
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    
    if result.stdout.strip():
        print("   📝 Hay cambios sin commit")
        print("   🔍 Archivos modificados:")
        print(result.stdout)
        
        response = input("   ¿Hacer commit de estos cambios? (y/N): ")
        if response.lower() == 'y':
            commit_msg = input("   Mensaje del commit (o Enter para default): ").strip()
            if not commit_msg:
                commit_msg = "🚀 Preparando despliegue en Railway"
            
            subprocess.run(['git', 'add', '.'])
            subprocess.run(['git', 'commit', '-m', commit_msg])
            print("   ✅ Commit realizado")
        else:
            print("   ⚠️  Continúando sin commit")
    
    # Verificar remote origin
    result = subprocess.run(['git', 'remote', '-v'], 
                          capture_output=True, text=True)
    
    if 'origin' not in result.stdout:
        print("   ⚠️  No hay remote 'origin' configurado")
        print("   📋 Configura tu repositorio en GitHub/GitLab")
        print("   💡 Luego ejecuta: git remote add origin <URL>")
        return False
    
    print("   ✅ Repositorio Git listo")
    return True

def collect_environment_vars():
    """Recopilar variables de entorno"""
    print("⚙️ Configurando variables de entorno...")
    print()
    
    vars_config = {}
    
    # Variables obligatorias
    print("📱 === EVOLUTION API (WhatsApp) ===")
    vars_config['EVOLUTION_API_URL'] = input("URL de Evolution API: ").strip()
    vars_config['EVOLUTION_API_TOKEN'] = input("Token de Evolution API: ").strip()
    vars_config['INSTANCE_NAME'] = input("Nombre de instancia WhatsApp: ").strip()
    
    print("\n🤖 === OPENAI ===")
    vars_config['OPENAI_API_KEY'] = input("OpenAI API Key: ").strip()
    
    print("\n⚡ === CONFIGURACIÓN DE RENDIMIENTO ===")
    vars_config['WORKER_POOL_SIZE'] = input("Workers (default 3): ").strip() or "3"
    vars_config['MAX_CONCURRENT_USERS'] = input("Usuarios concurrentes (default 5): ").strip() or "5"
    vars_config['PORT'] = "8000"
    
    # Variables opcionales
    print("\n📞 === CHATWOOT (Opcional) ===")
    chatwoot_url = input("Chatwoot URL (Enter para saltar): ").strip()
    if chatwoot_url:
        vars_config['CHATWOOT_API_URL'] = chatwoot_url
        vars_config['CHATWOOT_API_TOKEN'] = input("Chatwoot API Token: ").strip()
        vars_config['CHATWOOT_ACCOUNT_ID'] = input("Chatwoot Account ID: ").strip()
    
    return vars_config

def setup_railway_project(env_vars):
    """Configurar proyecto en Railway"""
    print("🚀 Configurando proyecto en Railway...")
    
    # Login a Railway
    print("   🔐 Iniciando sesión en Railway...")
    result = subprocess.run(['railway', 'login'], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("   ❌ Error en login de Railway")
        print("   💡 Ve manualmente a railway.app y crea el proyecto")
        return False
    
    # Inicializar proyecto
    print("   📦 Inicializando proyecto...")
    result = subprocess.run(['railway', 'init'], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("   ❌ Error inicializando proyecto")
        return False
    
    # Configurar variables
    print("   ⚙️ Configurando variables de entorno...")
    for key, value in env_vars.items():
        if value:  # Solo configurar si tiene valor
            result = subprocess.run(['railway', 'variables', 'set', f'{key}={value}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {key} configurado")
            else:
                print(f"   ⚠️ Error configurando {key}")
    
    return True

def deploy_to_railway():
    """Desplegar en Railway"""
    print("🚀 Desplegando en Railway...")
    
    result = subprocess.run(['railway', 'up', '--detach'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("   ✅ Despliegue iniciado")
        print("   📊 Ver progreso: railway logs --follow")
        return True
    else:
        print("   ❌ Error en despliegue")
        print(f"   Error: {result.stderr}")
        return False

def get_railway_url():
    """Obtener URL del proyecto"""
    print("🔗 Obteniendo URL del proyecto...")
    
    result = subprocess.run(['railway', 'domain'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        url = result.stdout.strip()
        print(f"   🌐 URL: {url}")
        return url
    else:
        print("   ⚠️ No se pudo obtener URL automáticamente")
        print("   💡 Ve a Railway Dashboard para obtener la URL")
        return None

def show_final_instructions(railway_url):
    """Mostrar instrucciones finales"""
    print("\n" + "=" * 60)
    print("✅ DESPLIEGUE COMPLETADO")
    print("=" * 60)
    
    if railway_url:
        print(f"🌐 Tu bot está en: {railway_url}")
        print()
        print("📡 ENDPOINTS DISPONIBLES:")
        print(f"   🏠 Principal: {railway_url}/")
        print(f"   ❤️ Health: {railway_url}/health")
        print(f"   🧪 Test: {railway_url}/test/message")
        print(f"   📊 Stats: {railway_url}/stats")
        print()
        print("🔗 WEBHOOK PARA EVOLUTION API:")
        print(f"   URL: {railway_url}/webhook/evolution")
        print("   Events: MESSAGES_UPSERT")
    
    print()
    print("🔧 PRÓXIMOS PASOS:")
    print("1. ✅ Configurar webhook en Evolution API")
    print("2. ✅ Probar con WhatsApp real")
    print("3. ✅ Monitorear logs: railway logs --follow")
    print()
    
    if railway_url:
        print("🧪 TEST RÁPIDO:")
        print(f'curl -X POST {railway_url}/test/message \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"message": "Hola", "user_id": "test"}\'')

def main():
    """Función principal"""
    print_banner()
    
    # Verificaciones previas
    if not check_requirements():
        print("❌ Verificaciones fallaron")
        return
    
    # Verificar/instalar Railway CLI
    if not check_railway_cli():
        install_railway = input("¿Instalar Railway CLI? (y/N): ")
        if install_railway.lower() == 'y':
            if not install_railway_cli():
                print("💡 Continúa manualmente en railway.app")
                return
        else:
            print("💡 Continúa manualmente en railway.app")
            return
    
    # Preparar Git
    if not prepare_git():
        print("❌ Problema con repositorio Git")
        return
    
    # Recopilar variables
    env_vars = collect_environment_vars()
    
    # Verificar variables críticas
    required_vars = ['EVOLUTION_API_URL', 'EVOLUTION_API_TOKEN', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not env_vars.get(var)]
    
    if missing_vars:
        print(f"❌ Variables faltantes: {', '.join(missing_vars)}")
        return
    
    print("\n🔄 ¿Continuar con Railway setup?")
    print("   Esto configurará el proyecto automáticamente")
    response = input("   (y/N): ")
    
    if response.lower() != 'y':
        print("📋 Variables recopiladas. Configura manualmente en railway.app:")
        for key, value in env_vars.items():
            if value:
                print(f"   {key}={value}")
        return
    
    # Setup en Railway
    if not setup_railway_project(env_vars):
        print("❌ Error en setup de Railway")
        return
    
    # Desplegar
    if not deploy_to_railway():
        print("❌ Error en despliegue")
        return
    
    # Obtener URL
    railway_url = get_railway_url()
    
    # Instrucciones finales
    show_final_instructions(railway_url)

if __name__ == "__main__":
    main() 