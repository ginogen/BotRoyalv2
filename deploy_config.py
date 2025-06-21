#!/usr/bin/env python3
"""
🚀 CONFIGURACIÓN DE DEPLOY - BOT ROYAL TESTING INTERFACE
Configuraciones específicas para producción
"""

import os
import streamlit as st

def configure_for_production():
    """Configuraciones específicas para deploy en producción"""
    
    # Configurar página para producción
    st.set_page_config(
        page_title="🤖 Bot Royal - Interface de Testing",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://royalmayorista.com.ar',
            'Report a bug': None,
            'About': """
            # Bot Royal Testing Interface
            
            Interfaz profesional para testing y feedback del bot de Royal Company.
            
            **Funcionalidades:**
            - Chat interactivo con feedback en tiempo real
            - Dashboard de métricas y análisis
            - Transparencia completa del sistema
            - Reportes de bugs y mejoras
            
            Desarrollado para optimizar la experiencia del bot de ventas.
            """
        }
    )

def check_environment_variables():
    """Verifica que todas las variables de entorno estén configuradas"""
    
    required_vars = [
        'OPENAI_API_KEY',
        'WOOCOMMERCE_URL', 
        'WOOCOMMERCE_CONSUMER_KEY',
        'WOOCOMMERCE_CONSUMER_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        st.error(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        st.stop()
    
    return True

def get_production_database_path():
    """Ruta de la base de datos para producción"""
    
    # En Railway, usar directorio persistente
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return '/app/data/bot_feedback.db'
    
    # En Streamlit Cloud, usar directorio temporal
    elif os.getenv('STREAMLIT_SHARING'):
        return 'bot_feedback.db'
    
    # Local development
    else:
        return 'bot_feedback.db'

def setup_production_logging():
    """Configurar logging para producción"""
    
    import logging
    
    # Nivel de logging según entorno
    if os.getenv('ENVIRONMENT') == 'production':
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Reducir logs verbosos en producción
    if os.getenv('ENVIRONMENT') == 'production':
        logging.getLogger('httpx').setLevel(logging.ERROR)
        logging.getLogger('streamlit').setLevel(logging.ERROR)

def get_app_url():
    """Obtiene la URL de la aplicación según el entorno"""
    
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Railway genera URL automáticamente
        return f"https://{os.getenv('RAILWAY_STATIC_URL', 'app.railway.app')}"
    
    elif os.getenv('STREAMLIT_SHARING'):
        # Streamlit Cloud
        return "https://share.streamlit.io"
    
    else:
        # Local
        return "http://localhost:8501"

# Configuración automática al importar
if __name__ != "__main__":
    setup_production_logging() 