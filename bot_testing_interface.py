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
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    st.error("⚠️ Bot no disponible. Verificar instalación.")

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
    
    # Tabla de system prompts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_prompts (
            id TEXT PRIMARY KEY,
            prompt_name TEXT,
            prompt_content TEXT,
            version TEXT,
            timestamp DATETIME,
            active BOOLEAN
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
        
        if st.button("💾 Descargar Datos"):
            # Generar reporte
            conversations_df = get_conversations_data()
            feedback_df = get_feedback_data()
            
            with st.expander("📊 Datos para descargar"):
                st.write("**Conversaciones:**", conversations_df.shape[0])
                st.write("**Feedback:**", feedback_df.shape[0])
    
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
                        save_feedback(conv_id, rating, feedback_text, category)
                        st.success("✅ Feedback guardado")
    
    # Input para nuevo mensaje
    st.divider()
    
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_area(
                "💬 Escribe tu mensaje:",
                placeholder="Prueba preguntando sobre productos, emprendimiento, envíos, etc.",
                height=100
            )
        
        with col2:
            st.write("") # Spacing
            submit_button = st.form_submit_button("▶️ Enviar", use_container_width=True)
            
            # Botones de prueba rápida
            st.write("**Pruebas rápidas:**")
            if st.form_submit_button("🚀 Emprendimiento", use_container_width=True):
                user_input = "Quiero empezar a vender, ¿qué me recomendás?"
                submit_button = True
            if st.form_submit_button("📦 Productos", use_container_width=True):
                user_input = "¿Tenés anillos de plata?"
                submit_button = True
            if st.form_submit_button("🚚 Envíos", use_container_width=True):
                user_input = "¿Cómo son los envíos?"
                submit_button = True
    
    # Procesar mensaje
    if submit_button and user_input.strip():
        with st.spinner("🤖 Pablo está respondiendo..."):
            try:
                # Obtener respuesta del bot
                bot_response = run_contextual_conversation_sync(st.session_state.user_id, user_input)
                
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
    
    # Tabs para diferentes aspectos
    tab1, tab2, tab3, tab4 = st.tabs(["📝 System Prompts", "🛠️ Herramientas", "🧠 Contexto Actual", "⚙️ Configuración"])
    
    with tab1:
        st.subheader("📝 System Prompts Actuales")
        
        # Mostrar los prompts del sistema
        try:
            with open('royal_agents/royal_agent_with_mcp.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extraer el system prompt principal
                if 'instructions=' in content:
                    start = content.find('instructions=') + len('instructions=')
                    end = content.find('",', start)
                    if end == -1:
                        end = content.find('"""', start + 3)
                    prompt = content[start:end].strip().replace('"""', '').replace('"', '')
                    
                    st.code(prompt, language="text")
                    
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
                
        except Exception as e:
            st.error(f"No se pudo cargar el system prompt: {e}")
    
    with tab2:
        st.subheader("🛠️ Herramientas Disponibles")
        
        # Listar herramientas disponibles
        tools_info = {
            "🔍 get_product_info_with_context": "Busca productos y los guarda en memoria",
            "🚀 get_combos_with_context": "Obtiene combos emprendedores",
            "💳 process_purchase_intent": "Procesa intenciones de compra",
            "😤 detect_user_frustration": "Detecta frustración del usuario",
            "🆘 handle_missing_information_hitl": "Maneja información faltante",
            "📋 get_context_summary": "Obtiene resumen del contexto",
            "👤 update_user_profile": "Actualiza perfil del usuario",
            "💡 get_recommendations_with_context": "Genera recomendaciones personalizadas"
        }
        
        for tool, description in tools_info.items():
            with st.expander(tool):
                st.write(description)
                
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
    
    with tab3:
        st.subheader("🧠 Contexto Actual del Usuario")
        
        if BOT_AVAILABLE:
            try:
                # Obtener contexto actual
                context = context_manager.get_or_create_context(st.session_state.user_id)
                conv = context.conversation
                
                # Mostrar información del contexto
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("👤 Usuario", st.session_state.user_id)
                    st.metric("🔄 Estado", conv.current_state)
                    st.metric("📦 Productos en memoria", len(conv.recent_products))
                    st.metric("💬 Interacciones", len(conv.interaction_history))
                
                with col2:
                    st.metric("🚀 Es emprendedor", "Sí" if conv.is_entrepreneur else "No")
                    if conv.experience_level:
                        st.metric("📈 Nivel", conv.experience_level)
                    if conv.budget_range:
                        st.metric("💰 Presupuesto", conv.budget_range)
                
                # Productos en memoria
                if conv.recent_products:
                    st.subheader("📦 Productos en Memoria")
                    for i, product in enumerate(conv.recent_products[-5:], 1):
                        st.write(f"{i}. **{product.name}** - ${product.price}")
                
                # Historial de interacciones
                if conv.interaction_history:
                    st.subheader("💬 Últimas Interacciones")
                    for interaction in conv.interaction_history[-5:]:
                        role = "👤 Usuario" if interaction["role"] == "user" else "🤖 Pablo"
                        st.write(f"{role}: {interaction['message'][:100]}...")
                
            except Exception as e:
                st.error(f"Error obteniendo contexto: {e}")
        else:
            st.warning("Bot no disponible")
    
    with tab4:
        st.subheader("⚙️ Configuración del Sistema")
        
        # Variables de entorno
        env_vars = {
            "OPENAI_API_KEY": "🔑 API Key de OpenAI",
            "WOOCOMMERCE_CONSUMER_KEY": "🛒 WooCommerce Consumer Key", 
            "WOOCOMMERCE_CONSUMER_SECRET": "🛒 WooCommerce Consumer Secret"
        }
        
        for var, description in env_vars.items():
            status = "✅ Configurado" if os.getenv(var) else "❌ NO configurado"
            st.write(f"{description}: {status}")

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
                labels={'x': 'Rating', 'y': 'Cantidad'},
                color=rating_counts.values,
                color_continuous_scale='RdYlGn'
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
        
        # Timeline de conversaciones
        st.subheader("📈 Timeline de Actividad")
        
        conversations_df['timestamp'] = pd.to_datetime(conversations_df['timestamp'])
        daily_counts = conversations_df.groupby(conversations_df['timestamp'].dt.date).size()
        
        fig_timeline = px.line(
            x=daily_counts.index,
            y=daily_counts.values,
            title="Conversaciones por Día",
            labels={'x': 'Fecha', 'y': 'Número de Conversaciones'}
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
    
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
            save_general_feedback(
                st.session_state.user_id,
                feedback_type,
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
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            filter_type = st.multiselect(
                "Filtrar por tipo:",
                options=feedback_df['feedback_type'].unique(),
                default=feedback_df['feedback_type'].unique()
            )
        
        with col2:
            filter_priority = st.multiselect(
                "Filtrar por prioridad:",
                options=feedback_df['priority'].unique(),
                default=feedback_df['priority'].unique()
            )
        
        # Aplicar filtros
        filtered_feedback = feedback_df[
            (feedback_df['feedback_type'].isin(filter_type)) &
            (feedback_df['priority'].isin(filter_priority))
        ]
        
        # Mostrar feedback
        for _, row in filtered_feedback.iterrows():
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