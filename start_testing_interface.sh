#!/bin/bash
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