#!/usr/bin/env python3
"""
🚀 INSTALADOR AUTOMÁTICO - Interface de Testing Bot Royal
Instala y configura todo lo necesario para la interfaz de pruebas
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}:")
        print(f"   {e.stderr}")
        return False

def check_python_version():
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} - Se requiere Python 3.8+")
        return False

def install_dependencies():
    """Instala las dependencias necesarias"""
    print("\n📦 INSTALANDO DEPENDENCIAS...")
    
    # Dependencias específicas para la interfaz
    dependencies = [
        "streamlit==1.28.1",
        "plotly==5.17.0", 
        "pandas==2.1.4",
        "sqlite3"  # Viene con Python por defecto
    ]
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"Instalando {dep}"):
            return False
    
    return True

def create_startup_script():
    """Crea script de inicio fácil"""
    script_content = '''#!/bin/bash
# 🚀 SCRIPT DE INICIO - Interface de Testing Bot Royal

echo "🤖 Iniciando Interface de Testing Bot Royal..."
echo "📱 Se abrirá automáticamente en tu navegador"
echo ""
echo "🔗 URL: http://localhost:8501"
echo "⏹️  Para detener: Ctrl+C"
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "🐍 Activando entorno virtual..."
    source .venv/bin/activate
fi

# Iniciar Streamlit
streamlit run bot_testing_app.py --server.port 8501 --server.headless false
'''
    
    with open('start_testing_interface.sh', 'w') as f:
        f.write(script_content)
    
    # Hacer ejecutable
    os.chmod('start_testing_interface.sh', 0o755)
    
    print("✅ Script de inicio creado: start_testing_interface.sh")

def create_windows_startup():
    """Crea script de inicio para Windows"""
    script_content = '''@echo off
REM 🚀 SCRIPT DE INICIO - Interface de Testing Bot Royal

echo 🤖 Iniciando Interface de Testing Bot Royal...
echo 📱 Se abrirá automáticamente en tu navegador
echo.
echo 🔗 URL: http://localhost:8501
echo ⏹️  Para detener: Ctrl+C
echo.

REM Activar entorno virtual si existe
if exist ".venv\\Scripts\\activate.bat" (
    echo 🐍 Activando entorno virtual...
    call .venv\\Scripts\\activate.bat
)

REM Iniciar Streamlit
streamlit run bot_testing_app.py --server.port 8501 --server.headless false

pause
'''
    
    with open('start_testing_interface.bat', 'w') as f:
        f.write(script_content)
    
    print("✅ Script de inicio para Windows creado: start_testing_interface.bat")

def create_readme():
    """Crea README con instrucciones"""
    readme_content = '''# 🤖 Bot Royal - Interface de Testing

## 🎯 ¿Qué es esto?

Esta es una **interfaz visual completa** para que puedas:

- 💬 **Probar el bot** con conversaciones reales
- 📝 **Dar feedback** sobre cada respuesta 
- 🔍 **Ver las "entrañas"** del bot (system prompts)
- 📊 **Analizar métricas** de rendimiento
- 🎯 **Sugerir mejoras** específicas

## 🚀 Cómo usar

### Opción 1: Script automático (RECOMENDADO)

```bash
# En Mac/Linux
./start_testing_interface.sh

# En Windows
start_testing_interface.bat
```

### Opción 2: Manual

```bash
streamlit run bot_testing_app.py
```

## 📋 Secciones disponibles

### 💬 Chat de Pruebas
- Chatea con el bot en tiempo real
- Califica cada respuesta (1-5 estrellas)
- Categoriza problemas (confusa, incorrecta, etc.)
- Deja feedback específico sobre qué mejorar

### 🔍 Transparencia del Bot  
- Ve el system prompt completo
- Entiende qué herramientas usa
- Sugiere mejoras al prompt
- Comprende la lógica interna

### 📊 Dashboard de Feedback
- Métricas de rendimiento
- Gráficos de calificaciones
- Análisis de categorías de problemas
- Timeline de actividad

### 📝 Feedback General
- Reporta bugs o problemas
- Sugiere nuevas funcionalidades
- Marca prioridades (baja/media/alta/crítica)
- Todo queda registrado para mejoras

## 🎯 Consejos para Testing Efectivo

1. **Prueba escenarios reales** - Simula conversaciones típicas
2. **Sé específico en el feedback** - Di exactamente qué cambiarías
3. **Usa las pruebas rápidas** - Botones para casos comunes
4. **Revisa la transparencia** - Entiende por qué responde así
5. **Marca prioridades** - Enfócate en lo más importante

## 🔧 Solución de Problemas

### El bot no responde
- Verificar que `OPENAI_API_KEY` esté configurado
- Revisar conexión a internet
- Verificar que el bot esté instalado

### Error de base de datos
- Se crea automáticamente (`bot_feedback.db`)
- Si hay problemas, eliminar el archivo y reiniciar

### Interface no carga
- Verificar que Streamlit esté instalado: `pip install streamlit`
- Probar puerto alternativo: `streamlit run bot_testing_app.py --server.port 8502`

## 📞 Soporte

Si encuentras problemas:

1. Revisar este README
2. Verificar configuración de variables de entorno
3. Contactar al desarrollador con el error específico

---

¡Todo el feedback que proporciones será usado para mejorar el bot al máximo! 🚀
'''
    
    with open('README_TESTING_INTERFACE.md', 'w') as f:
        f.write(readme_content)
    
    print("✅ README creado: README_TESTING_INTERFACE.md")

def main():
    """Función principal del instalador"""
    print("🚀" + "="*60 + "🚀")
    print("    BOT ROYAL - INSTALADOR DE INTERFACE DE TESTING")
    print("🚀" + "="*60 + "🚀")
    print()
    
    # Verificar Python
    if not check_python_version():
        print("\n❌ INSTALACIÓN CANCELADA")
        sys.exit(1)
    
    # Instalar dependencias
    if not install_dependencies():
        print("\n❌ ERROR EN INSTALACIÓN DE DEPENDENCIAS")
        sys.exit(1)
    
    # Crear scripts de inicio
    print("\n📝 CREANDO SCRIPTS DE INICIO...")
    create_startup_script()
    create_windows_startup()
    create_readme()
    
    # Verificar archivos necesarios
    print("\n🔍 VERIFICANDO ARCHIVOS...")
    required_files = [
        'bot_testing_app.py',
        'royal_agents/__init__.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️  ARCHIVOS FALTANTES: {', '.join(missing_files)}")
        print("   Asegurate de estar en el directorio correcto del proyecto")
    
    # Instrucciones finales
    print("\n🎉 ¡INSTALACIÓN COMPLETADA!")
    print("\n🚀 PARA INICIAR LA INTERFACE:")
    print("   Mac/Linux: ./start_testing_interface.sh")
    print("   Windows:   start_testing_interface.bat")
    print("   Manual:    streamlit run bot_testing_app.py")
    print()
    print("🔗 Se abrirá en: http://localhost:8501")
    print("📖 Lee README_TESTING_INTERFACE.md para más detalles")
    print()

if __name__ == "__main__":
    main() 