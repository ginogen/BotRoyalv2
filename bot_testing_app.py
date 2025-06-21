#!/usr/bin/env python3
"""
🎯 BOT ROYAL - INTERFACE DE TESTING Y FEEDBACK
Interfaz visual para que el cliente pruebe, evalúe y mejore el bot
"""

import streamlit as st
import sqlite3
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
import os
from typing import List, Dict, Any
import uuid
import nest_asyncio  # Para manejar event loops anidados

# Configurar página
st.set_page_config(
    page_title="🤖 Bot Royal - Testing Interface",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports del bot
try:
    from royal_agents import run_contextual_conversation_sync
    from royal_agents.conversation_context import context_manager
    
    # Permitir event loops anidados para compatibilidad con Streamlit
    nest_asyncio.apply()
    
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    st.error("⚠️ Bot no disponible. Verificar instalación.")
except Exception as e:
    BOT_AVAILABLE = False
    st.error(f"⚠️ Error configurando bot: {e}")

# Base de datos para feedback
def init_database():
    """Inicializa la base de datos de feedback"""
    conn = sqlite3.connect('bot_feedback.db')
    cursor = conn.cursor()
    
    # Tabla de conversaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            message TEXT,
            bot_response TEXT,
            timestamp DATETIME,
            session_id TEXT,
            rating INTEGER,
            feedback_text TEXT,
            category TEXT
        )
    ''')
    
    # Tabla de feedback general
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS general_feedback (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            feedback_type TEXT,
            title TEXT,
            description TEXT,
            priority TEXT,
            status TEXT,
            timestamp DATETIME,
            session_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_conversation(user_id: str, message: str, bot_response: str, session_id: str):
    """Guarda una conversación en la BD"""
    conn = sqlite3.connect('bot_feedback.db')
    cursor = conn.cursor()
    
    conversation_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO conversations 
        (id, user_id, message, bot_response, timestamp, session_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (conversation_id, user_id, message, bot_response, datetime.now(), session_id))
    
    conn.commit()
    conn.close()
    return conversation_id

def save_feedback(conversation_id: str, rating: int, feedback_text: str, category: str):
    """Guarda feedback de una conversación"""
    conn = sqlite3.connect('bot_feedback.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE conversations 
        SET rating = ?, feedback_text = ?, category = ?
        WHERE id = ?
    ''', (rating, feedback_text, category, conversation_id))
    
    conn.commit()
    conn.close()

def save_general_feedback(user_id: str, feedback_type: str, title: str, description: str, priority: str, session_id: str):
    """Guarda feedback general"""
    conn = sqlite3.connect('bot_feedback.db')
    cursor = conn.cursor()
    
    feedback_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO general_feedback 
        (id, user_id, feedback_type, title, description, priority, status, timestamp, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (feedback_id, user_id, feedback_type, title, description, priority, 'pendiente', datetime.now(), session_id))
    
    conn.commit()
    conn.close()

def get_conversations_data():
    """Obtiene datos de conversaciones para análisis"""
    conn = sqlite3.connect('bot_feedback.db')
    df = pd.read_sql_query('SELECT * FROM conversations', conn)
    conn.close()
    return df

def get_feedback_data():
    """Obtiene datos de feedback general"""
    conn = sqlite3.connect('bot_feedback.db')
    df = pd.read_sql_query('SELECT * FROM general_feedback', conn)
    conn.close()
    return df

# Función helper para ejecutar conversaciones en Streamlit
def run_bot_conversation_safe(user_id: str, user_input: str) -> str:
    """
    Ejecuta la conversación con el bot de manera segura para Streamlit
    """
    try:
        # Método 1: Usar run_contextual_conversation_sync directamente
        return run_contextual_conversation_sync(user_id, user_input)
        
    except RuntimeError as e:
        error_str = str(e) if e else ""
        if error_str and hasattr(error_str, 'lower') and "event loop" in error_str.lower():
            # Método 2: Si hay problemas con event loop, usar asyncio.run
            try:
                import asyncio
                from royal_agents.royal_agent_contextual import run_contextual_conversation
                
                # Crear nuevo event loop para esta conversación
                return asyncio.run(run_contextual_conversation(user_id, user_input))
                
            except Exception as e2:
                st.error(f"❌ Error ejecutando conversación: {e2}")
                return "Hubo un problema técnico. Por favor, intenta de nuevo."
        else:
            raise e
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        return "Hubo un problema procesando tu mensaje. Por favor, intenta de nuevo."

# Interfaz principal
def main():
    """Función principal de la interfaz"""
    
    # Inicializar BD
    init_database()
    
    # Inicializar session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "cliente_tester"
    
    # Header principal
    st.title("🤖 Bot Royal - Interface de Testing")
    st.markdown("### 🎯 Prueba, evalúa y mejora el bot de manera visual")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Info de sesión
        st.info(f"**Sesión:** {st.session_state.session_id[:8]}...")
        
        # Usuario  
        user_id = st.text_input("👤 Tu nombre:", value=st.session_state.user_id)
        if user_id != st.session_state.user_id:
            st.session_state.user_id = user_id
        
        st.divider()
        
        # Navegación
        st.header("📋 Navegación")
        page = st.selectbox(
            "Selecciona una sección:",
            ["💬 Chat de Pruebas", "🔍 Transparencia del Bot", "📊 Dashboard de Feedback", "📝 Feedback General"]
        )
        
        st.divider()
        
        # Controles de sesión
        st.header("🔄 Controles")
        
        if st.button("🧹 Nueva Sesión"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
            if BOT_AVAILABLE:
                # Limpiar contexto del bot
                if st.session_state.user_id in context_manager.active_contexts:
                    del context_manager.active_contexts[st.session_state.user_id]
            st.rerun()
    
    # Contenido principal según página seleccionada
    if page == "💬 Chat de Pruebas":
        chat_interface()
    elif page == "🔍 Transparencia del Bot":
        transparency_interface()
    elif page == "📊 Dashboard de Feedback":
        dashboard_interface()
    elif page == "📝 Feedback General":
        general_feedback_interface()

def chat_interface():
    """Interfaz principal de chat"""
    
    st.header("💬 Chat de Pruebas")
    st.markdown("Prueba el bot y proporciona feedback inmediato sobre cada respuesta")
    
    if not BOT_AVAILABLE:
        st.error("🚫 El bot no está disponible. Verificar configuración.")
        return
    
    # Área de chat
    chat_container = st.container()
    
    with chat_container:
        # Mostrar historial
        for i, (user_msg, bot_msg, conv_id) in enumerate(st.session_state.chat_history):
            
            # Mensaje del usuario
            with st.chat_message("user"):
                st.write(user_msg)
            
            # Respuesta del bot
            with st.chat_message("assistant"):
                st.write(bot_msg)
                
                # Panel de feedback para cada respuesta
                with st.expander(f"📝 Feedback para respuesta #{i+1}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        rating = st.select_slider(
                            "⭐ Calificación:",
                            options=[1, 2, 3, 4, 5],
                            value=3,
                            key=f"rating_{conv_id}"
                        )
                    
                    with col2:
                        category = st.selectbox(
                            "🏷️ Categoría:",
                            ["Correcta", "Confusa", "Incompleta", "Incorrecta", "Tono inadecuado"],
                            key=f"category_{conv_id}"
                        )
                    
                    feedback_text = st.text_area(
                        "💭 ¿Qué está mal y cómo debería mejorar?",
                        placeholder="Describe específicamente qué debería cambiar...",
                        key=f"feedback_{conv_id}"
                    )
                    
                    if st.button("💾 Guardar Feedback", key=f"save_{conv_id}"):
                        # Asegurar tipos correctos
                        rating_int = rating if isinstance(rating, int) else rating[0] if isinstance(rating, tuple) else 3
                        category_str = category if category is not None else "Sin categoría"
                        save_feedback(conv_id, rating_int, feedback_text, category_str)
                        st.success("✅ Feedback guardado")
    
    # Botones de prueba rápida
    st.divider()
    st.subheader("🚀 Pruebas Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Emprendimiento", use_container_width=True):
            user_input = "Quiero empezar a vender, ¿qué me recomendás?"
            st.session_state.quick_test_input = user_input
            
    with col2:
        if st.button("📦 Productos", use_container_width=True):
            user_input = "¿Tenés anillos de plata?"
            st.session_state.quick_test_input = user_input
            
    with col3:
        if st.button("🚚 Envíos", use_container_width=True):
            user_input = "¿Cómo son los envíos?"
            st.session_state.quick_test_input = user_input
    
    # Chat input fluido (permite Enter para enviar)
    user_input = st.chat_input("💬 Escribe tu mensaje y presiona Enter...")
    
    # Procesar input de pruebas rápidas
    if 'quick_test_input' in st.session_state:
        user_input = st.session_state.quick_test_input
        del st.session_state.quick_test_input
    
    # Procesar mensaje
    if user_input and user_input.strip():
        with st.spinner("🤖 Pablo está respondiendo..."):
            try:
                # Obtener respuesta del bot
                bot_response = run_bot_conversation_safe(st.session_state.user_id, user_input)
                
                # Guardar en BD
                conv_id = save_conversation(st.session_state.user_id, user_input, bot_response, st.session_state.session_id)
                
                # Agregar al historial
                st.session_state.chat_history.append((user_input, bot_response, conv_id))
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {e}")

def transparency_interface():
    """Interfaz de transparencia - mostrar system prompts"""
    
    st.header("🔍 Transparencia del Bot")
    st.markdown("Ve las 'entrañas' del bot: prompts, herramientas y lógica interna")
    
    # Mostrar system prompt actual
    st.subheader("📝 System Prompt Principal")
    
    # Prompt principal del bot
    main_prompt = """
Sos Pablo, el asistente virtual de Royal Company (mayorista de bijou, relojes, maquillaje).

PERSONALIDAD Y TONO:
- Hablás en argentino informal pero profesional
- Sos entusiasta, confiable y orientado a ayudar
- Usás emojis moderadamente 
- Sos experto en ayudar emprendedores

FUNCIONES PRINCIPALES:
1. Ayudar a emprendedores a elegir productos 
2. Responder sobre catálogo, precios, stock
3. Brindar información de envíos y pagos
4. Detectar frustración y escalar a humanos cuando sea necesario

REGLAS CRÍTICAS:
- NUNCA inventés precios o información que no tenés
- Cuando no sepas algo, activá protocolo HITL (Human In The Loop)
- Usá las herramientas MCP para obtener datos reales
- Mantené memoria de productos mostrados para referencias futuras
- Si detectás frustración, escalá inmediatamente

INFORMACIÓN BÁSICA:
- Ubicación: Buenos Aires, Argentina
- Envíos: Todo el país via OCA/Andreani
- Mínimo de compra: $40,000
- Pagos: Efectivo, transferencia, tarjetas
- Catálogo: https://royalmayorista.com.ar/shop/
"""
    
    st.code(main_prompt, language="text")
    
    with st.expander("💡 Sugerir mejoras al prompt"):
        suggestion = st.text_area(
            "¿Cómo mejorarías este prompt?",
            placeholder="Sugiere cambios específicos para mejorar las respuestas del bot..."
        )
        
        if st.button("📤 Enviar Sugerencia"):
            if suggestion:
                save_general_feedback(
                    st.session_state.user_id,
                    "system_prompt",
                    "Mejora de System Prompt",
                    suggestion,
                    "alta",
                    st.session_state.session_id
                )
                st.success("✅ Sugerencia enviada")
    
    st.divider()
    
    # Mostrar herramientas disponibles
    st.subheader("🛠️ Herramientas Disponibles")
    
    tools_info = {
        "🔍 get_product_info_with_context": "Busca productos en WooCommerce y los guarda en memoria",
        "🚀 get_combos_with_context": "Obtiene combos emprendedores específicos",
        "💳 process_purchase_intent": "Procesa cuando el usuario quiere comprar",
        "😤 detect_user_frustration": "Detecta frustración y activa protocolo HITL",
        "🆘 handle_missing_information_hitl": "Maneja información faltante",
        "📋 get_context_summary": "Obtiene resumen del contexto actual",
        "👤 update_user_profile": "Actualiza perfil del usuario (emprendedor, etc.)",
        "💡 get_recommendations_with_context": "Genera recomendaciones personalizadas"
    }
    
    for tool, description in tools_info.items():
        with st.expander(tool):
            st.write(f"**Función:** {description}")
            
            feedback = st.text_input(
                f"💭 Feedback para {tool}:",
                placeholder="¿Esta herramienta funciona bien? ¿Qué mejorarías?",
                key=f"tool_feedback_{tool}"
            )
            
            if st.button(f"📤 Enviar", key=f"send_tool_{tool}"):
                if feedback:
                    save_general_feedback(
                        st.session_state.user_id,
                        "tool",
                        f"Feedback: {tool}",
                        feedback,
                        "media",
                        st.session_state.session_id
                    )
                    st.success("✅ Feedback enviado")

def dashboard_interface():
    """Dashboard de análisis de feedback"""
    
    st.header("📊 Dashboard de Feedback")
    st.markdown("Análisis completo de las pruebas y feedback recibido")
    
    # Obtener datos
    conversations_df = get_conversations_data()
    feedback_df = get_feedback_data()
    
    if conversations_df.empty:
        st.info("🤷‍♂️ Aún no hay conversaciones. ¡Comienza probando el bot!")
        return
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💬 Total Conversaciones", len(conversations_df))
    
    with col2:
        rated_convs = conversations_df[conversations_df['rating'].notna()]
        avg_rating = rated_convs['rating'].mean() if not rated_convs.empty else 0
        st.metric("⭐ Rating Promedio", f"{avg_rating:.1f}/5")
    
    with col3:
        st.metric("📝 Feedback Recibido", len(feedback_df))
    
    with col4:
        unique_sessions = conversations_df['session_id'].nunique()
        st.metric("🎯 Sesiones de Prueba", unique_sessions)
    
    st.divider()
    
    # Gráficos de análisis
    if not conversations_df.empty:
        
        # Gráfico de ratings
        if not rated_convs.empty:
            st.subheader("⭐ Distribución de Ratings")
            
            rating_counts = rated_convs['rating'].value_counts().sort_index()
            fig_rating = px.bar(
                x=rating_counts.index,
                y=rating_counts.values,
                title="Distribución de Calificaciones",
                labels={'x': 'Rating', 'y': 'Cantidad'}
            )
            st.plotly_chart(fig_rating, use_container_width=True)
        
        # Gráfico de categorías de feedback
        categorized = conversations_df[conversations_df['category'].notna()]
        if not categorized.empty:
            st.subheader("🏷️ Categorías de Feedback")
            
            category_counts = categorized['category'].value_counts()
            fig_category = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="Distribución de Categorías de Feedback"
            )
            st.plotly_chart(fig_category, use_container_width=True)
    
    # Tabla de feedback detallado
    st.subheader("📋 Feedback Detallado")
    
    if not conversations_df.empty:
        feedback_detailed = conversations_df[
            (conversations_df['feedback_text'].notna()) & 
            (conversations_df['feedback_text'] != '')
        ][['timestamp', 'user_id', 'message', 'rating', 'category', 'feedback_text']]
        
        if not feedback_detailed.empty:
            st.dataframe(feedback_detailed, use_container_width=True)
        else:
            st.info("No hay feedback textual aún")

def general_feedback_interface():
    """Interfaz para feedback general del sistema"""
    
    st.header("📝 Feedback General")
    st.markdown("Proporciona feedback general sobre el bot, sugerencias de mejora y reporta problemas")
    
    # Formulario de feedback general
    with st.form("general_feedback_form"):
        st.subheader("💭 Nuevo Feedback")
        
        col1, col2 = st.columns(2)
        
        with col1:
            feedback_type = st.selectbox(
                "🏷️ Tipo de Feedback:",
                ["Sugerencia de mejora", "Reporte de bug", "Funcionalidad faltante", "Mejora de UX", "Otro"]
            )
        
        with col2:
            priority = st.selectbox(
                "⚡ Prioridad:",
                ["Baja", "Media", "Alta", "Crítica"]
            )
        
        title = st.text_input(
            "📌 Título:",
            placeholder="Resumen breve del feedback..."
        )
        
        description = st.text_area(
            "📝 Descripción detallada:",
            placeholder="Describe en detalle tu sugerencia, problema o mejora...",
            height=150
        )
        
        submit_feedback = st.form_submit_button("📤 Enviar Feedback")
        
        if submit_feedback and title and description:
            # Asegurar que feedback_type no sea None
            feedback_type_str = feedback_type if feedback_type is not None else "Otro"
            save_general_feedback(
                st.session_state.user_id,
                feedback_type_str,
                title,
                description,
                priority.lower(),
                st.session_state.session_id
            )
            st.success("✅ Feedback enviado correctamente")
    
    st.divider()
    
    # Mostrar feedback existente
    st.subheader("📋 Feedback Enviado")
    
    feedback_df = get_feedback_data()
    
    if not feedback_df.empty:
        # Mostrar feedback
        for _, row in feedback_df.iterrows():
            with st.expander(f"🎯 {row['title']} - {row['priority'].upper()}"):
                st.write(f"**Tipo:** {row['feedback_type']}")
                st.write(f"**Estado:** {row['status']}")
                st.write(f"**Fecha:** {row['timestamp']}")
                st.write(f"**Descripción:**")
                st.write(row['description'])
    else:
        st.info("No hay feedback general aún")

if __name__ == "__main__":
    main() 