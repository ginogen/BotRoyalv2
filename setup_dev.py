#!/usr/bin/env python3
"""
Script de setup para desarrollo del Royal Bot
Automatiza la configuración inicial del entorno
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description=""):
    """Ejecuta un comando y maneja errores"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Error: {e.stderr}")
        return False

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ es requerido")
        print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detectado")
    return True

def setup_virtual_environment():
    """Configura el entorno virtual"""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ Entorno virtual ya existe")
        return True
    
    print("🔧 Creando entorno virtual...")
    if not run_command("python -m venv .venv", "Creando entorno virtual"):
        return False
    
    return True

def activate_and_install():
    """Activa el entorno virtual e instala dependencias"""
    print("🔧 Instalando dependencias...")
    
    # Comando de activación según el OS
    if os.name == 'nt':  # Windows
        activate_cmd = ".venv\\Scripts\\activate"
        pip_path = ".venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        activate_cmd = "source .venv/bin/activate"
        pip_path = ".venv/bin/pip"
    
    # Instalar dependencias
    install_cmd = f"{pip_path} install -r requirements.txt"
    return run_command(install_cmd, "Instalando dependencias Python")

def setup_environment_file():
    """Configura el archivo de variables de entorno"""
    env_example = Path("config.env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ Archivo .env ya existe")
        return True
    
    if not env_example.exists():
        print("❌ Archivo config.env.example no encontrado")
        return False
    
    print("🔧 Copiando archivo de configuración...")
    shutil.copy(env_example, env_file)
    
    print("⚠️  IMPORTANTE: Editá el archivo .env con tu OpenAI API Key")
    print("   Archivo copiado: .env")
    return True

def check_openai_key():
    """Verifica si la OpenAI API Key está configurada"""
    # Revisar variables de entorno
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OPENAI_API_KEY encontrada en variables de entorno")
        return True
    
    # Revisar archivo .env
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY=sk-" in content and "your-openai-api-key-here" not in content:
                print("✅ OPENAI_API_KEY configurada en .env")
                return True
    
    print("⚠️  OPENAI_API_KEY no configurada")
    print("   1. Obtené tu API key de: https://platform.openai.com/api-keys")
    print("   2. Agregala al archivo .env o como variable de entorno")
    print("   3. Ejemplo: export OPENAI_API_KEY=sk-tu-clave-aqui")
    return False

def test_basic_imports():
    """Prueba las importaciones básicas"""
    print("🔧 Verificando importaciones...")
    
    try:
        # Test básico sin importar OpenAI agents aún
        import asyncio
        import json
        import redis
        print("✅ Dependencias básicas importadas correctamente")
        return True
    except ImportError as e:
        print(f"❌ Error importando dependencias: {e}")
        return False

def main():
    """Función principal de setup"""
    print("🏆 ROYAL BOT - SETUP DE DESARROLLO")
    print("=" * 50)
    
    # Verificaciones previas
    if not check_python_version():
        sys.exit(1)
    
    # Setup paso a paso
    steps = [
        ("Configurando entorno virtual", setup_virtual_environment),
        ("Instalando dependencias", activate_and_install),
        ("Configurando archivo .env", setup_environment_file),
        ("Verificando importaciones", test_basic_imports)
    ]
    
    for description, func in steps:
        print(f"\n🚀 {description}...")
        if not func():
            print(f"❌ Error en: {description}")
            sys.exit(1)
    
    # Verificaciones finales
    print(f"\n🔍 VERIFICACIONES FINALES")
    print("-" * 30)
    
    check_openai_key()
    
    print(f"\n🎉 SETUP COMPLETADO!")
    print("=" * 50)
    print("📝 PRÓXIMOS PASOS:")
    print("1. Configurá tu OPENAI_API_KEY en .env")
    print("2. Activá el entorno virtual:")
    
    if os.name == 'nt':
        print("   .venv\\Scripts\\activate")
    else:
        print("   source .venv/bin/activate")
    
    print("3. Probá el bot:")
    print("   python test_chat.py")
    print("4. O iniciá el servidor:")
    print("   python server.py")
    
    print(f"\n🔗 ENLACES ÚTILES:")
    print("- OpenAI API Keys: https://platform.openai.com/api-keys")
    print("- Documentación: README.md")
    print("- Test API: http://localhost:8000 (cuando esté corriendo)")

if __name__ == "__main__":
    main() 