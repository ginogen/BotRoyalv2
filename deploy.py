#!/usr/bin/env python3
"""
🚀 SCRIPT DE DEPLOY AUTOMATIZADO
Bot Royal Testing Interface - Deploy a diferentes plataformas
"""

import os
import subprocess
import sys
from pathlib import Path

def check_prerequisites():
    """Verifica que todo esté listo para deploy"""
    
    print("🔍 Verificando prerequisitos...")
    
    # Verificar que bot_testing_app.py existe
    if not Path("bot_testing_app.py").exists():
        print("❌ bot_testing_app.py no encontrado")
        return False
    
    # Verificar requirements.txt
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt no encontrado")
        return False
    
    # Verificar variables de entorno críticas
    required_vars = ['OPENAI_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"⚠️ Variables de entorno faltantes: {missing}")
        print("   Configurar antes del deploy")
    
    print("✅ Prerequisitos verificados")
    return True

def deploy_to_railway():
    """Deploy a Railway"""
    
    print("🚂 Deploying a Railway...")
    
    # Verificar si Railway CLI está instalado
    try:
        subprocess.run(["railway", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI no instalado")
        print("   Instalar desde: https://railway.app/cli")
        return False
    
    try:
        # Login si es necesario
        subprocess.run(["railway", "login"], check=True)
        
        # Deploy
        subprocess.run(["railway", "up"], check=True)
        
        print("✅ Deploy a Railway completado")
        print("🔗 URL: railway logs para ver la URL generada")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en deploy a Railway: {e}")
        return False

def deploy_to_streamlit_cloud():
    """Instrucciones para deploy a Streamlit Cloud"""
    
    print("☁️ Deploy a Streamlit Cloud (Manual):")
    print()
    print("1️⃣ Subir código a GitHub:")
    print("   git add .")
    print("   git commit -m 'Deploy bot testing interface'")
    print("   git push origin main")
    print()
    print("2️⃣ Ir a https://share.streamlit.io")
    print("3️⃣ Conectar repositorio GitHub")
    print("4️⃣ Configurar:")
    print("   - Main file: bot_testing_app.py")
    print("   - Python version: 3.11")
    print()
    print("5️⃣ Agregar secrets (variables de entorno):")
    print("   - OPENAI_API_KEY")
    print("   - WOOCOMMERCE_URL")
    print("   - WOOCOMMERCE_CONSUMER_KEY") 
    print("   - WOOCOMMERCE_CONSUMER_SECRET")
    print()
    print("6️⃣ Deploy automático en unos minutos")

def create_production_env_example():
    """Crea ejemplo de variables de entorno para producción"""
    
    env_content = """# 🚀 VARIABLES DE ENTORNO PARA PRODUCCIÓN
# Copiar y completar en la plataforma de deploy

# OpenAI
OPENAI_API_KEY=sk-...

# WooCommerce
WOOCOMMERCE_URL=https://royalmayorista.com.ar
WOOCOMMERCE_CONSUMER_KEY=ck_...
WOOCOMMERCE_CONSUMER_SECRET=cs_...

# Configuración
ENVIRONMENT=production
PORT=8501
HOST=0.0.0.0

# Opcional: Configuraciones adicionales
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
"""
    
    with open("production.env.example", "w") as f:
        f.write(env_content)
    
    print("📝 Creado: production.env.example")
    print("   Usar como referencia para configurar variables en producción")

def prepare_for_deploy():
    """Prepara archivos para deploy"""
    
    print("📦 Preparando archivos para deploy...")
    
    # Crear archivo de configuración de producción
    create_production_env_example()
    
    # Verificar que .gitignore excluye archivos sensibles
    gitignore_content = """
# Environments
.env
.env.local
.env.production
config.env
*.env

# Database
*.db
*.sqlite3

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.venv/
venv/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content.strip())
    
    print("✅ Archivos preparados")

def main():
    """Función principal"""
    
    print("🚀 BOT ROYAL - DEPLOY AUTOMATIZADO")
    print("=" * 40)
    
    if not check_prerequisites():
        sys.exit(1)
    
    print("\n📋 Opciones de Deploy:")
    print("1️⃣ Railway (Automático)")
    print("2️⃣ Streamlit Cloud (Manual)")
    print("3️⃣ Preparar archivos solamente")
    print("0️⃣ Salir")
    
    while True:
        choice = input("\n🎯 Selecciona opción (1-3, 0 para salir): ").strip()
        
        if choice == "0":
            print("👋 ¡Hasta luego!")
            break
            
        elif choice == "1":
            prepare_for_deploy()
            deploy_to_railway()
            break
            
        elif choice == "2":
            prepare_for_deploy()
            deploy_to_streamlit_cloud()
            break
            
        elif choice == "3":
            prepare_for_deploy()
            print("✅ Archivos preparados para deploy manual")
            break
            
        else:
            print("❌ Opción inválida. Intenta de nuevo.")

if __name__ == "__main__":
    main() 