@echo off
REM 🚀 SCRIPT DE INICIO - Interface de Testing Bot Royal

echo 🤖 Iniciando Interface de Testing Bot Royal...
echo 📱 Se abrirá automáticamente en tu navegador
echo.
echo 🔗 URL: http://localhost:8501
echo ⏹️  Para detener: Ctrl+C
echo.

REM Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    echo 🐍 Activando entorno virtual...
    call .venv\Scripts\activate.bat
)

REM Iniciar Streamlit
streamlit run bot_testing_app.py --server.port 8501 --server.headless false

pause 