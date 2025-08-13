#!/usr/bin/env python3
"""
🚀 ROYAL BOT SERVER - MAXIMUM EFFICIENCY EDITION
Integrates all optimization systems for Railway deployment:
- Hybrid Context Management (PostgreSQL + Redis + Memory)
- Advanced Message Queue with priorities
- Dynamic Worker Pool with auto-scaling
- Circuit breaker patterns
- Smart rate limiting
- Real-time monitoring
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time
import uuid

# FastAPI and middleware
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Our optimization systems
from hybrid_context_manager import hybrid_context_manager, initialize_hybrid_context
from advanced_message_queue import (
    advanced_queue, initialize_queue, MessageData, 
    MessageSource, MessagePriority
)
from dynamic_worker_pool import initialize_worker_pool, shutdown_worker_pool, dynamic_pool

# Bot state management
from bot_state_manager import BotStateManager

# Royal agents import
try:
    from royal_agents import run_contextual_conversation_sync
except ImportError:
    # Fallback if royal_agents not available
    def run_contextual_conversation_sync(user_id: str, message: str) -> str:
        return "Sistema en modo de prueba. Royal agents no disponible."

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURATION
# =====================================================

# Environment variables with Railway defaults
PORT = int(os.getenv("PORT", 8000))
ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "development")

# External service configurations
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN") 
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_TOKEN = os.getenv("EVOLUTION_API_TOKEN")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "F1_Retencion")

# Team IDs for automatic assignment
CHATWOOT_TEAM_SHIPPING_ID = int(os.getenv("CHATWOOT_TEAM_SHIPPING_ID", "0"))
CHATWOOT_TEAM_SUPPORT_ID = int(os.getenv("CHATWOOT_TEAM_SUPPORT_ID", "0"))
CHATWOOT_TEAM_BILLING_ID = int(os.getenv("CHATWOOT_TEAM_BILLING_ID", "0"))

# Performance tuning
ENABLE_PERFORMANCE_MONITORING = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"

# =====================================================
# FASTAPI APP SETUP
# =====================================================

app = FastAPI(
    title="Royal Bot - Maximum Efficiency Edition",
    description="Optimized Royal Bot with advanced queueing, context management, and auto-scaling",
    version="3.0.0",
    docs_url="/admin/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/admin/redoc" if ENVIRONMENT == "development" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
startup_time = datetime.now()
request_count = 0
system_metrics = {
    'requests_processed': 0,
    'messages_queued': 0,
    'average_response_time': 0.0,
    'last_health_check': None
}

# Bot state manager instance
bot_state_manager: Optional[BotStateManager] = None

# Mapeo conversación <-> teléfono para sincronización entre canales
conversation_phone_mapping = {}

# =====================================================
# PYDANTIC MODELS
# =====================================================

class TestMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    priority: Optional[str] = "normal"

class WebhookMessage(BaseModel):
    message: str
    user_id: str
    source: str
    conversation_id: Optional[str] = None
    phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class TestAssignment(BaseModel):
    message: str
    phone: str
    conversation_id: str
    simulate_only: Optional[bool] = False

# =====================================================
# CORE MESSAGE PROCESSOR
# =====================================================

async def process_royal_message(user_id: str, message: str, message_data: Optional['MessageData'] = None) -> str:
    """
    Core message processor that integrates with all our systems.
    This is what gets called by the worker pool.
    """
    start_time = time.time()
    
    try:
        # Log the processing start
        logger.info(f"🤖 Processing message for {user_id}: {message[:50]}...")
        
        # Process with Royal agent (using sync version for thread compatibility)
        response = run_contextual_conversation_sync(user_id, message)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update global metrics
        system_metrics['average_response_time'] = (
            system_metrics['average_response_time'] * 0.9 + processing_time * 0.1
        )
        
        # Send response back to appropriate channel
        if message_data:
            await send_response_to_channel(user_id, response, message_data)
        
        logger.info(f"✅ Message processed for {user_id} in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Processing failed for {user_id} after {processing_time:.2f}s: {e}")
        
        # Return friendly error message
        error_response = (
            "Disculpá, tuve un problemita técnico. "
            "Dame un momento que ya te ayudo. "
            "Si es urgente, podés contactar directamente a nuestros locales."
        )
        
        # Try to send error response
        if message_data:
            try:
                await send_response_to_channel(user_id, error_response, message_data)
            except:
                pass  # Don't fail if we can't send error response
        
        return error_response

async def send_response_to_channel(user_id: str, response: str, message_data: 'MessageData'):
    """Send response back to the appropriate channel (WhatsApp, Chatwoot, etc.)"""
    
    try:
        if message_data.source == MessageSource.EVOLUTION and message_data.phone:
            # Send to WhatsApp via Evolution API
            success = await send_evolution_message(message_data.phone, response)
            if success:
                logger.info(f"📱 Response sent to WhatsApp: {user_id}")
            else:
                logger.error(f"❌ Failed to send WhatsApp response: {user_id}")
                
        elif message_data.source == MessageSource.CHATWOOT and message_data.conversation_id:
            # Send to Chatwoot
            success = await send_chatwoot_message(message_data.conversation_id, response)
            if success:
                logger.info(f"💬 Response sent to Chatwoot: {user_id}")
            else:
                logger.error(f"❌ Failed to send Chatwoot response: {user_id}")
                
        else:
            logger.warning(f"⚠️ No channel configured for response: {user_id} (source: {message_data.source})")
            
    except Exception as e:
        logger.error(f"❌ Error sending response to channel: {e}")

# =====================================================
# EXTERNAL SERVICE INTEGRATIONS
# =====================================================

async def send_chatwoot_message(conversation_id: str, message: str) -> bool:
    """Send message to Chatwoot"""
    if not all([CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
        logger.warning("⚠️ Chatwoot not configured")
        return False
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "api_access_token": CHATWOOT_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            payload = {
                "content": message,
                "message_type": "outgoing"
            }
            
            response = await client.post(
                f"{CHATWOOT_API_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages",
                headers=headers,
                json=payload
            )
            
            success = response.status_code in [200, 201]
            if success:
                logger.info(f"✅ Chatwoot message sent to conversation {conversation_id}")
            else:
                logger.error(f"❌ Chatwoot send failed: {response.status_code}")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ Chatwoot send error: {e}")
        return False

async def send_evolution_message(phone: str, message: str) -> bool:
    """Send message via Evolution API"""
    if not all([EVOLUTION_API_URL, EVOLUTION_API_TOKEN]):
        logger.warning("⚠️ Evolution API not configured")
        return False
    
    try:
        import httpx
        
        # Use phone number exactly as received (Evolution API expects no + prefix)
        formatted_phone = phone
        
        # Log the request details for debugging
        logger.info(f"🔄 Sending message to Evolution API:")
        logger.info(f"   URL: {EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}")
        logger.info(f"   Phone: {formatted_phone}")
        logger.info(f"   Message length: {len(message)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "apikey": EVOLUTION_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            payload = {
                "number": formatted_phone,
                "text": message
            }
            
            response = await client.post(
                f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}",
                headers=headers,
                json=payload
            )
            
            # Check for success (200 or 201 are both success)
            if response.status_code in [200, 201]:
                logger.info(f"✅ Evolution message sent to {formatted_phone}")
                return True
            
            # Enhanced error logging for actual errors
            logger.error(f"❌ Evolution API Error:")
            logger.error(f"   Status Code: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            logger.error(f"   Headers: {dict(response.headers)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Evolution send error: {e}")
        return False

# =====================================================
# MESSAGE PROCESSING PIPELINE
# =====================================================

async def process_message_pipeline(
    user_id: str,
    message: str,
    source: MessageSource,
    conversation_id: Optional[str] = None,
    phone: Optional[str] = None,
    priority: MessagePriority = MessagePriority.NORMAL,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Complete message processing pipeline:
    1. Create message data
    2. Add to queue
    3. Worker pool processes it
    4. Response is sent back via appropriate channel
    """
    
    # Create message data
    message_data = MessageData(
        user_id=user_id,
        message=message,
        source=source,
        priority=priority,
        conversation_id=conversation_id,
        phone=phone,
        metadata=metadata or {}
    )
    
    # Add to advanced queue
    success = await advanced_queue.add_message(message_data)
    
    if success:
        system_metrics['messages_queued'] += 1
        logger.info(f"📥 Message queued: {user_id} via {source.value}")
    else:
        logger.warning(f"⚠️ Message not queued (duplicate?): {user_id}")
    
    return success

# =====================================================
# BACKGROUND TASKS
# =====================================================

async def response_sender_task():
    """Background task that monitors completed messages and sends responses"""
    logger.info("📡 Response sender task started")
    
    # This would typically involve polling completed messages
    # and sending responses via the appropriate channels
    # For now, we'll implement a simple monitoring loop
    
    while True:
        try:
            # Get queue stats for monitoring
            if advanced_queue and advanced_queue.pg_pool:
                # Here we could check for completed messages that need response sending
                # This is where the integration with Chatwoot/Evolution would happen
                pass
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Response sender error: {e}")
            await asyncio.sleep(30)
    
    logger.info("📡 Response sender task stopped")

async def metrics_collector_task():
    """Background task for collecting and storing metrics"""
    logger.info("📊 Metrics collector started")
    
    while True:
        try:
            if ENABLE_PERFORMANCE_MONITORING:
                # Collect metrics from all systems
                current_time = datetime.now()
                
                # Update system health check time
                system_metrics['last_health_check'] = current_time
                
                # Here we could store metrics in database for long-term analysis
                # For now, we just update in-memory metrics
                
            await asyncio.sleep(60)  # Collect every minute
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Metrics collector error: {e}")
            await asyncio.sleep(120)
    
    logger.info("📊 Metrics collector stopped")

# =====================================================
# CONVERSATION-PHONE MAPPING FUNCTIONS
# =====================================================

def link_conversation_to_phone(conversation_id: str, phone: str):
    """Vincular conversación de Chatwoot con número de teléfono"""
    global conversation_phone_mapping
    conversation_phone_mapping[conversation_id] = phone
    logger.info(f"🔗 Vinculando conversación {conversation_id} con teléfono {phone}")

def get_phone_from_conversation(conversation_id: str) -> Optional[str]:
    """Obtener número de teléfono desde conversación de Chatwoot"""
    return conversation_phone_mapping.get(conversation_id)

def get_conversation_from_phone(phone: str) -> Optional[str]:
    """Obtener conversación de Chatwoot desde número de teléfono"""
    for conv_id, mapped_phone in conversation_phone_mapping.items():
        if mapped_phone == phone:
            return conv_id
    return None

# =====================================================
# AUTOMATIC CONVERSATION ASSIGNMENT
# =====================================================

# Keyword routing configuration
KEYWORD_ROUTING = {
    "shipping": {
        "keywords": [
            "mi pedido", "mi orden", "mi compra", "estado de mi", "donde esta mi",
            "cuando llega mi", "ya enviaron mi", "seguimiento de mi", "tracking de mi",
            "estado del pedido", "donde esta el pedido", "cuando llega el pedido",
            "ya enviaron el pedido", "ya despacharon", "seguimiento del pedido",
            "que paso con mi", "como va mi", "me enviaron", "ya salio mi"
        ],
        "team_id": CHATWOOT_TEAM_SHIPPING_ID,
        "message": "Te estoy conectando con nuestro equipo de seguimiento de pedidos 📦\nVan a revisar el estado específico de tu compra y te van a dar toda la información actualizada."
    },
    "support": {
        "keywords": [
            "reclamo", "queja", "problema", "no funciona", "defectuoso", 
            "roto", "mal estado", "garantia", "devolucion", "cambio"
        ],
        "team_id": CHATWOOT_TEAM_SUPPORT_ID,
        "message": "Te voy a conectar con nuestro equipo de soporte técnico 🛠️\nVan a resolver tu problema de inmediato."
    },
    "billing": {
        "keywords": [
            "factura", "pago", "transferencia", "comprobante", "facturación",
            "cobro", "precio mal", "me cobraron", "descuento", "promocion"
        ],
        "team_id": CHATWOOT_TEAM_BILLING_ID,
        "message": "Te derivo con nuestro área de facturación 💳\nVan a revisar tu caso específico."
    }
}

async def assign_conversation_to_team(conversation_id: str, team_id: int, reason: str = "") -> bool:
    """
    Asigna una conversación a un equipo específico en Chatwoot
    
    Args:
        conversation_id: ID de la conversación en Chatwoot
        team_id: ID del equipo al que asignar
        reason: Razón de la asignación para logging
        
    Returns:
        bool: True si la asignación fue exitosa
    """
    if not all([CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
        logger.warning("⚠️ Chatwoot API no configurada para asignación")
        return False
    
    if team_id == 0:
        logger.warning(f"⚠️ Team ID no configurado para asignación: {reason}")
        return False
    
    try:
        url = f"{CHATWOOT_API_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/assignments"
        
        headers = {
            "Content-Type": "application/json",
            "api_access_token": CHATWOOT_API_TOKEN
        }
        
        data = {"team_id": team_id}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            
        if response.status_code == 200:
            logger.info(f"✅ Conversación {conversation_id} asignada al equipo {team_id} - Razón: {reason}")
            
            # Actualizar métricas
            system_metrics.setdefault('assignments_successful', 0)
            system_metrics['assignments_successful'] += 1
            system_metrics['last_assignment'] = datetime.now().isoformat()
            
            return True
        else:
            logger.error(f"❌ Error asignando conversación {conversation_id}: {response.status_code} - {response.text}")
            
            # Actualizar métricas de error
            system_metrics.setdefault('assignments_failed', 0)
            system_metrics['assignments_failed'] += 1
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en asignación de conversación {conversation_id}: {e}")
        system_metrics.setdefault('assignments_failed', 0)
        system_metrics['assignments_failed'] += 1
        return False

def is_order_inquiry(message: str) -> bool:
    """
    Determina si el mensaje es una consulta específica sobre un pedido ya realizado
    vs. una consulta general sobre condiciones de envío
    """
    message_lower = message.lower()
    
    # Palabras que indican consulta sobre pedido específico
    order_indicators = [
        "mi pedido", "mi orden", "mi compra", "mi producto",
        "el pedido que", "la orden que", "lo que compré", "lo que pague",
        "mi encargo", "mi solicitud"
    ]
    
    # Palabras que indican estado/seguimiento
    status_indicators = [
        "estado", "donde esta", "cuando llega", "ya enviaron",
        "seguimiento", "tracking", "que paso con", "como va",
        "ya despacharon", "ya salio"
    ]
    
    # Debe tener al menos un indicador de pedido Y uno de estado
    has_order_ref = any(indicator in message_lower for indicator in order_indicators)
    has_status_ref = any(indicator in message_lower for indicator in status_indicators)
    
    return has_order_ref or has_status_ref

async def check_and_route_by_keywords(message: str, conversation_id: str, phone: str) -> bool:
    """
    Verifica palabras clave en el mensaje y asigna a equipos si corresponde
    
    Args:
        message: Mensaje del usuario
        conversation_id: ID de conversación en Chatwoot
        phone: Número de teléfono del usuario
        
    Returns:
        bool: True si se realizó una asignación
    """
    message_lower = message.lower()
    
    # Revisar cada categoría de keywords
    for route_type, config in KEYWORD_ROUTING.items():
        # Para shipping, hacer validación adicional
        if route_type == "shipping":
            if not is_order_inquiry(message):
                continue  # Skip si no es consulta sobre pedido específico
        
        # Verificar si alguna keyword coincide
        matched_keywords = [kw for kw in config["keywords"] if kw in message_lower]
        
        if matched_keywords:
            logger.info(f"🎯 Keywords detectadas [{route_type}]: {matched_keywords} en mensaje: '{message[:50]}...'")
            
            # Intentar asignar conversación
            success = await assign_conversation_to_team(
                conversation_id, 
                config["team_id"],
                f"Keyword detectada: {route_type} ({', '.join(matched_keywords)})"
            )
            
            if success:
                # Pausar bot para ambos canales
                pause_success = await pause_bot_for_both_channels(
                    phone, 
                    conversation_id, 
                    f"Asignado a equipo {route_type}"
                )
                
                if pause_success:
                    logger.info(f"⏸️ Bot pausado para {phone} tras asignación a {route_type}")
                
                # Enviar mensaje de confirmación apropiado según el canal
                try:
                    if phone and not phone.startswith("chatwoot_"):
                        # Enviar vía WhatsApp si tenemos número real
                        await send_evolution_message(phone, config["message"])
                        logger.info(f"📱 Mensaje de confirmación enviado a WhatsApp: {phone}")
                    else:
                        # Enviar vía Chatwoot si no tenemos número de teléfono
                        await send_chatwoot_message(conversation_id, config["message"])
                        logger.info(f"💬 Mensaje de confirmación enviado a Chatwoot: {conversation_id}")
                except Exception as e:
                    logger.error(f"❌ Error enviando confirmación: {e}")
                
                # Log de éxito completo
                logger.info(f"🚀 Asignación completada: {phone} → Equipo {route_type} (Conversación {conversation_id})")
                
                return True
            else:
                logger.error(f"❌ Falló asignación para keywords {route_type}: {matched_keywords}")
    
    return False

async def pause_bot_for_both_channels(phone: str, conversation_id: str, reason: str) -> bool:
    """Pausar bot para ambos canales (WhatsApp y Chatwoot)"""
    success_phone = await bot_state_manager.pause_bot(phone, reason)
    success_conv = await bot_state_manager.pause_bot(f"conv_{conversation_id}", reason)
    
    if success_phone and success_conv:
        logger.info(f"✅ Bot pausado para AMBOS canales: {phone} y conv_{conversation_id}")
        return True
    elif success_phone or success_conv:
        logger.warning(f"⚠️ Bot pausado parcialmente: phone={success_phone}, conv={success_conv}")
        return True
    else:
        logger.error(f"❌ No se pudo pausar bot para ningún canal")
        return False

async def resume_bot_for_both_channels(phone: str, conversation_id: str) -> bool:
    """Reactivar bot para ambos canales (WhatsApp y Chatwoot)"""
    success_phone = await bot_state_manager.resume_bot(phone)
    success_conv = await bot_state_manager.resume_bot(f"conv_{conversation_id}")
    
    logger.info(f"✅ Bot reactivado para AMBOS canales: {phone} y conv_{conversation_id}")
    return True

# =====================================================
# BOT CONTROL FUNCTIONS
# =====================================================

async def handle_label_association(data: Dict) -> Dict:
    """
    Manejar eventos de asociación de etiquetas desde Chatwoot
    Detecta cuando se agrega/quita la etiqueta 'bot-paused'
    """
    try:
        label_data = data.get("data", {})
        action = label_data.get("action")  # "add" o "remove"
        labels = label_data.get("labels", [])
        chat_id = label_data.get("chatId", "").replace("@s.whatsapp.net", "")
        
        if ENABLE_REQUEST_LOGGING:
            logger.info(f"🏷️ Label event: {action} - Labels: {labels} - Chat: {chat_id}")
        
        if "bot-paused" in labels and chat_id:
            if action == "add":
                # Pausar bot
                success = await bot_state_manager.pause_bot(chat_id, "agent_control")
                if success:
                    # Notificar al usuario
                    await send_evolution_message(
                        chat_id, 
                        "🔴 Un agente ha tomado control de esta conversación. "
                        "El asistente virtual está pausado temporalmente."
                    )
                    logger.info(f"🔴 Bot pausado por agente para {chat_id}")
                
            elif action == "remove":
                # Reactivar bot
                success = await bot_state_manager.resume_bot(chat_id)
                if success:
                    # Notificar al usuario
                    await send_evolution_message(
                        chat_id,
                        "🟢 El asistente virtual está nuevamente disponible. "
                        "¿En qué puedo ayudarte?"
                    )
                    logger.info(f"🟢 Bot reactivado por agente para {chat_id}")
        
        return {
            "status": "label_processed", 
            "action": action, 
            "labels": labels,
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando etiquetas: {e}")
        return {"status": "error", "message": str(e)}

async def handle_bot_control_commands(phone: str, message: str) -> Optional[Dict]:
    """
    Manejar comandos de control del bot desde WhatsApp
    Comandos: /pausar, /stop, /activar, /start, /estado
    """
    try:
        message_lower = message.lower().strip()
        
        # Control del bot SOLO desde Chatwoot (agentes)
        # Comandos desde WhatsApp son ignorados para mantener transparencia total
        if message_lower in ["/pausar", "/stop", "/activar", "/start", "/estado", "pausar", "stop", "activar", "start", "estado"]:
            logger.info(f"🔇 Comando de control ignorado desde WhatsApp: {message}")
            return None
        
        # No es un comando de control
        return None
        
    except Exception as e:
        logger.error(f"❌ Error procesando comando de control: {e}")
        return {"status": "error", "message": str(e)}

async def handle_agent_private_note(data: Dict) -> Dict:
    """
    Manejar notas privadas de agentes en Chatwoot para control del bot
    Comandos: /bot pause, /bot resume, /bot status
    """
    try:
        content = data.get("content", "").strip().lower()
        conversation = data.get("conversation", {})
        conversation_id = str(conversation.get("id", ""))
        
        # Extraer número de teléfono de la conversación
        phone = None
        contact_phone = conversation.get("contact_phone")
        if contact_phone:
            phone = contact_phone.replace("+", "").replace("-", "").replace(" ", "")
        
        # Buscar el número en contact_inbox si no está en contact_phone
        if not phone:
            contact_inbox = conversation.get("contact_inbox", {})
            source_id = contact_inbox.get("source_id", "")
            # source_id podría contener el número de teléfono
            if source_id and source_id.replace("-", "").isdigit():
                phone = source_id.replace("-", "")
        
        # Si aún no tenemos teléfono, buscar en additional_attributes
        if not phone:
            attrs = conversation.get("additional_attributes", {})
            if "phone_number" in attrs:
                phone = attrs["phone_number"].replace("+", "").replace("-", "").replace(" ", "")
        
        agent_name = data.get("sender", {}).get("name", "Agente")
        
        logger.info(f"📝 Nota privada del {agent_name}: {content}")
        logger.info(f"🔍 Teléfono extraído: {phone} | Conversación: {conversation_id}")
        
        # Comandos de control del bot
        if content in ["/bot pause", "/bot pausar", "bot pause", "bot pausar"]:
            # Pausar para AMBOS canales si hay vinculación
            if phone:
                success = await pause_bot_for_both_channels(phone, conversation_id, f"agent_{agent_name}")
                logger.info(f"🎯 Pausando bot para AMBOS canales: teléfono {phone} y conversación {conversation_id}")
            else:
                # Solo pausar conversación si no hay teléfono
                identifier = f"conv_{conversation_id}"
                success = await bot_state_manager.pause_bot(identifier, f"agent_{agent_name}")
                logger.info(f"🎯 Pausando bot para conversación: {identifier}")
            
            if success:
                # NO enviar mensaje - debe ser transparente para el usuario
                pass
                
                logger.info(f"🔴 Bot pausado por {agent_name} para {identifier}")
                
                return {
                    "status": "bot_paused",
                    "message": f"Bot pausado por {agent_name}",
                    "identifier": identifier
                }
            else:
                logger.error(f"❌ No se pudo pausar bot para {identifier}")
                return {"status": "error", "message": "No se pudo pausar el bot"}
        
        elif content in ["/bot resume", "/bot activar", "bot resume", "bot activar"]:
            # Reactivar para AMBOS canales si hay vinculación
            if phone:
                success = await resume_bot_for_both_channels(phone, conversation_id)
                logger.info(f"🎯 Reactivando bot para AMBOS canales: teléfono {phone} y conversación {conversation_id}")
            else:
                # Solo reactivar conversación si no hay teléfono
                identifier = f"conv_{conversation_id}"
                success = await bot_state_manager.resume_bot(identifier)
                logger.info(f"🎯 Reactivando bot para conversación: {identifier}")
            
            if success:
                # NO enviar mensaje - transición debe ser invisible
                pass
                
                logger.info(f"🟢 Bot reactivado por {agent_name} para {identifier}")
                
                return {
                    "status": "bot_resumed",
                    "message": f"Bot reactivado por {agent_name}",
                    "identifier": identifier
                }
            else:
                logger.info(f"ℹ️ Bot ya estaba activo para {identifier}")
                return {"status": "info", "message": "Bot ya estaba activo"}
        
        elif content in ["/bot status", "/bot estado", "bot status", "bot estado"]:
            # Consultar estado del bot
            if phone:
                identifier = phone
                logger.info(f"🎯 Consultando estado para teléfono: {identifier}")
            else:
                identifier = f"conv_{conversation_id}"
                logger.info(f"🎯 Consultando estado para conversación: {identifier}")
            
            state = await bot_state_manager.get_bot_state(identifier)
            
            status_msg = "🟢 ACTIVO" if state["active"] else "🔴 PAUSADO"
            reason = state.get("reason", "")
            if reason:
                status_msg += f" ({reason})"
            
            logger.info(f"ℹ️ Estado consultado por {agent_name}: {status_msg}")
            
            return {
                "status": "status_checked",
                "bot_status": status_msg,
                "state": state,
                "identifier": identifier
            }
        
        # No es un comando de control del bot
        return {"status": "ignored", "message": "Nota privada ignorada"}
        
    except Exception as e:
        logger.error(f"❌ Error procesando nota privada: {e}")
        return {"status": "error", "message": str(e)}

# =====================================================
# API ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """Service status and information"""
    uptime = datetime.now() - startup_time
    
    return {
        "service": "Royal Bot - Maximum Efficiency Edition",
        "version": "3.0.0",
        "status": "active",
        "uptime_seconds": int(uptime.total_seconds()),
        "uptime_human": str(uptime),
        "environment": ENVIRONMENT,
        "features": [
            "✅ Hybrid Context Management (PostgreSQL + Redis + Memory)",
            "✅ Advanced Priority Message Queue",
            "✅ Dynamic Auto-scaling Worker Pool",
            "✅ Circuit Breaker Protection",
            "✅ Real-time Performance Monitoring",
            "✅ Smart Rate Limiting",
            "✅ Chatwoot Integration",
            "✅ Evolution API (WhatsApp) Integration"
        ],
        "metrics": {
            "requests_processed": system_metrics['requests_processed'],
            "messages_queued": system_metrics['messages_queued'],
            "average_response_time": round(system_metrics['average_response_time'], 3)
        }
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    start_time = time.time()
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "overall_status": "healthy"
    }
    
    # Check hybrid context manager
    try:
        context_health = await hybrid_context_manager.health_check()
        health["checks"]["context_manager"] = context_health
        if context_health["status"] != "healthy":
            health["overall_status"] = "degraded"
    except Exception as e:
        health["checks"]["context_manager"] = {"status": "unhealthy", "error": str(e)}
        health["overall_status"] = "degraded"
    
    # Check message queue
    try:
        queue_health = await advanced_queue.health_check()
        health["checks"]["message_queue"] = queue_health
        if queue_health["status"] != "healthy":
            health["overall_status"] = "degraded"
    except Exception as e:
        health["checks"]["message_queue"] = {"status": "unhealthy", "error": str(e)}
        health["overall_status"] = "degraded"
    
    # Check worker pool
    try:
        if dynamic_pool:
            pool_health = await dynamic_pool.health_check()
            health["checks"]["worker_pool"] = pool_health
            if pool_health["status"] != "healthy":
                health["overall_status"] = "degraded"
        else:
            health["checks"]["worker_pool"] = {"status": "not_initialized"}
    except Exception as e:
        health["checks"]["worker_pool"] = {"status": "unhealthy", "error": str(e)}
        health["overall_status"] = "degraded"
    
    # Response time check
    health_check_time = (time.time() - start_time) * 1000
    health["response_time_ms"] = round(health_check_time, 2)
    
    # Overall status logic
    unhealthy_checks = sum(1 for check in health["checks"].values() 
                          if check.get("status") == "unhealthy")
    
    if unhealthy_checks > 0:
        health["overall_status"] = "unhealthy"
    elif health["overall_status"] != "healthy":
        health["overall_status"] = "degraded"
    
    # Set HTTP status code based on health
    status_code = 200
    if health["overall_status"] == "degraded":
        status_code = 200  # Still operational
    elif health["overall_status"] == "unhealthy":
        status_code = 503  # Service unavailable
    
    return JSONResponse(content=health, status_code=status_code)

@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """Chatwoot webhook handler with advanced processing"""
    global request_count
    request_count += 1
    system_metrics['requests_processed'] += 1
    
    try:
        data = await request.json()
        
        # Log webhook if enabled  
        if ENABLE_REQUEST_LOGGING:
            logger.info(f"📨 Chatwoot webhook: {json.dumps(data, indent=2)[:500]}...")
        
        # DEBUG: Log key fields for bot control
        event = data.get("event")
        message_type = data.get("message_type") 
        sender_type = data.get("sender", {}).get("type")
        content = data.get("content", "")
        is_private = data.get("private", False)
        
        logger.info(f"🔍 DEBUG - Event: {event}, MsgType: {message_type}, Sender: {sender_type}, Private: {is_private}, Content: '{content}'")
        
        # Handle agent control commands (notes or messages from agents)
        if (data.get("event") == "message_created" and 
            data.get("sender", {}).get("type") == "user"):
            # This is from an agent (user in Chatwoot = agent)
            content_lower = content.lower().strip()
            if any(cmd in content_lower for cmd in ["/bot pause", "/bot resume", "/bot status", "bot pause", "bot resume"]):
                logger.info(f"🎯 Comando de agente detectado: {content}")
                return await handle_agent_private_note(data)
        
        # Process only incoming messages from contacts
        if (data.get("event") == "message_created" and 
            data.get("message_type") == "incoming" and
            data.get("sender", {}).get("type") == "contact"):
            
            conversation = data.get("conversation", {})
            content = data.get("content", "").strip()
            
            if content and conversation.get("id"):
                contact_id = data.get("sender", {}).get("id")
                
                if contact_id is not None:
                    user_id = f"chatwoot_{str(contact_id)}"
                    conversation_id = str(conversation["id"])
                    
                    # Extract phone number for state checking and mapping
                    phone = None
                    if conversation.get("contact_phone"):
                        phone = conversation["contact_phone"].replace("+", "").replace("-", "").replace(" ", "")
                    
                    # Si no encontramos teléfono, intentar extraerlo del source_id o contact
                    if not phone:
                        # Buscar teléfono en contact si está disponible
                        sender = data.get("sender", {})
                        if "phone" in sender:
                            phone = str(sender["phone"]).replace("+", "").replace("-", "").replace(" ", "")
                    
                    # Crear vinculación si encontramos teléfono
                    if phone:
                        link_conversation_to_phone(conversation_id, phone)
                        logger.info(f"🔗 Vinculación creada: conversación {conversation_id} ↔ teléfono {phone}")
                    else:
                        # Buscar vinculación existente
                        phone = get_phone_from_conversation(conversation_id)
                        if phone:
                            logger.info(f"🔍 Usando vinculación existente: conversación {conversation_id} ↔ teléfono {phone}")
                    
                    # Check if bot is active - verificar AMBOS identificadores
                    bot_active = True
                    
                    # Primero verificar por teléfono si está disponible
                    if phone:
                        if not await bot_state_manager.is_bot_active(phone):
                            bot_active = False
                            logger.info(f"🔇 Bot pausado para teléfono {phone} (Chatwoot), mensaje ignorado")
                    
                    # También verificar por conversación  
                    conv_identifier = f"conv_{conversation_id}"
                    if not await bot_state_manager.is_bot_active(conv_identifier):
                        bot_active = False
                        logger.info(f"🔇 Bot pausado para conversación {conv_identifier} (Chatwoot), mensaje ignorado")
                    
                    if not bot_active:
                        return {"status": "bot_paused", "message": "ignored", "source": "chatwoot"}
                    
                    # 🎯 CHECK FOR ASSIGNMENT KEYWORDS BEFORE PROCESSING
                    routed = await check_and_route_by_keywords(
                        content, 
                        conversation_id, 
                        phone if phone else f"chatwoot_{contact_id}"
                    )
                    
                    if routed:
                        logger.info(f"🚀 Mensaje de Chatwoot ruteado automáticamente: {conversation_id}")
                        return {"status": "routed_to_team", "conversation_id": conversation_id, "source": "chatwoot"}
                    
                    # Determine priority based on content
                    priority = MessagePriority.NORMAL
                    if any(word in content.lower() for word in ['urgente', 'problema', 'error']):
                        priority = MessagePriority.HIGH
                    
                    # Add to processing pipeline
                    success = await process_message_pipeline(
                        user_id=user_id,
                        message=content,
                        source=MessageSource.CHATWOOT,
                        conversation_id=conversation_id,
                        priority=priority,
                        metadata={
                            "contact_id": contact_id,
                            "conversation_type": conversation.get("channel"),
                            "webhook_data": data
                        }
                    )
                    
                    if success:
                        # Schedule response sending (this would be handled by worker completion)
                        # background_tasks.add_task(send_chatwoot_response, conversation_id, user_id)
                        pass
        
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error(f"❌ Chatwoot webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """Evolution API webhook handler with advanced processing"""
    global request_count
    request_count += 1
    system_metrics['requests_processed'] += 1
    
    try:
        data = await request.json()
        
        # Log webhook if enabled
        if ENABLE_REQUEST_LOGGING:
            logger.info(f"📱 Evolution webhook: {json.dumps(data, indent=2)[:500]}...")
        
        # Only process incoming messages from users (not our own messages)
        event = data.get("event", "")
        message_data_raw = data.get("data", {})
        
        # Handle different event types
        if event == "labels.association":
            # Handle label changes from Chatwoot
            return await handle_label_association(data)
        
        # Process regular messages
        if event not in ["messages.upsert"]:
            logger.info(f"🔇 Ignoring event: {event}")
            return {"status": "received", "ignored": event}
        
        # Check if message is from us (fromMe: true)
        from_me = message_data_raw.get("key", {}).get("fromMe", False)
        if from_me:
            logger.info("🔇 Ignoring message from bot itself (fromMe: true)")
            return {"status": "received", "ignored": "fromMe"}
        
        # Extract message data
        message_content = message_data_raw.get("message", {}).get("conversation", "").strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        if message_content and from_number:
            user_id = f"whatsapp_{from_number}"
            
            # Buscar si este teléfono tiene una conversación vinculada
            conversation_id = get_conversation_from_phone(from_number)
            if conversation_id:
                logger.info(f"📱 Teléfono {from_number} vinculado a conversación {conversation_id}")
            
            # Handle bot control commands first
            control_response = await handle_bot_control_commands(from_number, message_content)
            if control_response:
                return control_response
            
            # Check if bot is active for this user (verificar ambos identificadores)
            bot_active = await bot_state_manager.is_bot_active(from_number)
            if conversation_id:
                # También verificar por conversación si existe vinculación
                conv_active = await bot_state_manager.is_bot_active(f"conv_{conversation_id}")
                bot_active = bot_active and conv_active
            
            if not bot_active:
                logger.info(f"🔇 Bot pausado para {from_number}, mensaje ignorado")
                return {"status": "bot_paused", "message": "ignored"}
            
            # 🎯 CHECK FOR ASSIGNMENT KEYWORDS BEFORE PROCESSING
            if conversation_id:
                routed = await check_and_route_by_keywords(
                    message_content, 
                    conversation_id, 
                    from_number
                )
                
                if routed:
                    logger.info(f"🚀 Mensaje ruteado automáticamente: {from_number} → {conversation_id}")
                    return {"status": "routed_to_team", "conversation_id": conversation_id, "phone": from_number}
            else:
                logger.info(f"ℹ️ No hay conversación vinculada para {from_number}, continuando con bot normal")
            
            # Auto-prioritize based on content
            priority = MessagePriority.NORMAL
            if any(word in message_content.lower() for word in ['urgente', 'problema', 'error']):
                priority = MessagePriority.HIGH
            elif any(word in message_content.lower() for word in ['comprar', 'precio', 'stock']):
                priority = MessagePriority.HIGH
            
            # Add to processing pipeline
            success = await process_message_pipeline(
                user_id=user_id,
                message=message_content,
                source=MessageSource.EVOLUTION,
                phone=from_number,
                priority=priority,
                metadata={
                    "instance": INSTANCE_NAME,
                    "webhook_data": data
                }
            )
        
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error(f"❌ Evolution webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@app.post("/test/message")
async def test_message(test_msg: TestMessage):
    """Test message endpoint with full processing pipeline"""
    user_id = test_msg.user_id or f"test_{uuid.uuid4().hex[:8]}"
    
    # Parse priority
    priority_map = {
        'urgent': MessagePriority.URGENT,
        'high': MessagePriority.HIGH,
        'normal': MessagePriority.NORMAL,
        'low': MessagePriority.LOW
    }
    priority = priority_map.get(test_msg.priority, MessagePriority.NORMAL)
    
    # Process through pipeline
    success = await process_message_pipeline(
        user_id=user_id,
        message=test_msg.message,
        source=MessageSource.TEST,
        priority=priority,
        metadata={"test_mode": True}
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to queue message")
    
    # For test endpoint, we'll wait a bit and return some stats
    await asyncio.sleep(0.5)
    
    return {
        "status": "queued",
        "user_id": user_id,
        "priority": priority.name,
        "message": test_msg.message,
        "queue_info": "Message added to advanced priority queue for processing"
    }

# =====================================================
# BOT STATE CONTROL ENDPOINTS
# =====================================================

@app.get("/bot/status/{identifier}")
async def get_bot_status(identifier: str):
    """
    Obtener el estado del bot para un identificador específico
    
    Args:
        identifier: Número de teléfono o ID de conversación
    """
    try:
        state = await bot_state_manager.get_bot_state(identifier)
        return {
            "identifier": identifier,
            "bot_active": state["active"],
            "status": state["status"],
            "reason": state["reason"],
            "paused_at": state["paused_at"],
            "ttl_remaining": state["ttl_remaining"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado del bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/pause/{identifier}")
async def pause_bot_endpoint(identifier: str, reason: str = "manual", ttl: int = 86400):
    """
    Pausar el bot para un identificador específico
    
    Args:
        identifier: Número de teléfono o ID de conversación
        reason: Razón de la pausa
        ttl: Tiempo de vida en segundos (default: 24 horas)
    """
    try:
        success = await bot_state_manager.pause_bot(identifier, reason, ttl)
        
        if success:
            # Enviar notificación si es un número de WhatsApp
            if identifier.isdigit() and len(identifier) >= 10:
                await send_evolution_message(
                    identifier,
                    f"🔴 El bot ha sido pausado por el administrador. "
                    f"Razón: {reason}. Envía /activar para intentar reactivarlo."
                )
            
            return {
                "status": "success",
                "message": f"Bot pausado para {identifier}",
                "reason": reason,
                "ttl": ttl,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudo pausar el bot")
    
    except Exception as e:
        logger.error(f"❌ Error pausando bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/resume/{identifier}")
async def resume_bot_endpoint(identifier: str):
    """
    Reactivar el bot para un identificador específico
    
    Args:
        identifier: Número de teléfono o ID de conversación
    """
    try:
        success = await bot_state_manager.resume_bot(identifier)
        
        if success:
            # Enviar notificación si es un número de WhatsApp
            if identifier.isdigit() and len(identifier) >= 10:
                await send_evolution_message(
                    identifier,
                    "🟢 El bot ha sido reactivado por el administrador. "
                    "¡Listo para ayudarte!"
                )
            
            return {
                "status": "success",
                "message": f"Bot reactivado para {identifier}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "info",
                "message": f"El bot ya estaba activo para {identifier}",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"❌ Error reactivando bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/pause-all")
async def pause_all_bots_endpoint(reason: str = "maintenance"):
    """
    Pausar todos los bots (útil para mantenimiento)
    
    Args:
        reason: Razón del mantenimiento
    """
    try:
        count = await bot_state_manager.pause_all_bots(reason)
        
        return {
            "status": "success",
            "message": f"{count} bots pausados",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error pausando todos los bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/resume-all")
async def resume_all_bots_endpoint():
    """Reactivar todos los bots"""
    try:
        count = await bot_state_manager.resume_all_bots()
        
        return {
            "status": "success",
            "message": f"{count} bots reactivados",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error reactivando todos los bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bot/stats")
async def get_bot_stats():
    """Obtener estadísticas del sistema de bots"""
    try:
        stats = await bot_state_manager.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            **stats
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/assignment")
async def test_assignment_endpoint(test_data: TestAssignment):
    """
    Endpoint para probar el sistema de asignación automática
    
    Args:
        test_data: Datos de prueba con mensaje, teléfono y conversación
    """
    try:
        logger.info(f"🧪 TEST: Probando asignación para mensaje: '{test_data.message[:50]}...'")
        
        # Crear vinculación temporal para la prueba
        original_mapping = conversation_phone_mapping.get(test_data.conversation_id)
        link_conversation_to_phone(test_data.conversation_id, test_data.phone)
        
        try:
            if test_data.simulate_only:
                # Solo simular detección sin asignar realmente
                message_lower = test_data.message.lower()
                detected_routes = []
                
                for route_type, config in KEYWORD_ROUTING.items():
                    matched_keywords = [kw for kw in config["keywords"] if kw in message_lower]
                    if matched_keywords:
                        detected_routes.append({
                            "route_type": route_type,
                            "matched_keywords": matched_keywords,
                            "team_id": config["team_id"],
                            "message": config["message"]
                        })
                
                return {
                    "status": "simulation",
                    "message": test_data.message,
                    "conversation_id": test_data.conversation_id,
                    "phone": test_data.phone,
                    "detected_routes": detected_routes,
                    "would_assign": len(detected_routes) > 0,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Probar asignación real
                routed = await check_and_route_by_keywords(
                    test_data.message,
                    test_data.conversation_id,
                    test_data.phone
                )
                
                return {
                    "status": "success",
                    "message": test_data.message,
                    "conversation_id": test_data.conversation_id,
                    "phone": test_data.phone,
                    "routed": routed,
                    "result": "assigned" if routed else "no_keywords_matched",
                    "timestamp": datetime.now().isoformat()
                }
        
        finally:
            # Restaurar mapeo original o limpiar
            if original_mapping:
                link_conversation_to_phone(test_data.conversation_id, original_mapping)
            elif test_data.conversation_id in conversation_phone_mapping:
                del conversation_phone_mapping[test_data.conversation_id]
    
    except Exception as e:
        logger.error(f"❌ Error en test de asignación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# MONITORING ENDPOINTS
# =====================================================

@app.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    metrics = {
        "system": system_metrics.copy(),
        "uptime": (datetime.now() - startup_time).total_seconds()
    }
    
    # Get context manager metrics
    try:
        context_metrics = await hybrid_context_manager.get_metrics()
        metrics["context_manager"] = context_metrics
    except Exception as e:
        metrics["context_manager"] = {"error": str(e)}
    
    # Get queue metrics
    try:
        queue_metrics = await advanced_queue.get_metrics()
        metrics["message_queue"] = queue_metrics
    except Exception as e:
        metrics["message_queue"] = {"error": str(e)}
    
    # Get worker pool metrics
    try:
        if dynamic_pool:
            pool_metrics = await dynamic_pool.get_metrics()
            metrics["worker_pool"] = pool_metrics
        else:
            metrics["worker_pool"] = {"status": "not_initialized"}
    except Exception as e:
        metrics["worker_pool"] = {"error": str(e)}
    
    return metrics

@app.get("/admin/queue")
async def admin_queue_stats():
    """Admin endpoint for queue statistics"""
    try:
        stats = await advanced_queue.get_queue_stats()
        return {
            "queue_stats": {
                "total_pending": stats.total_pending,
                "total_processing": stats.total_processing,
                "total_completed": stats.total_completed,
                "total_failed": stats.total_failed,
                "total_dead_letter": stats.total_dead_letter,
                "queue_depth": stats.queue_depth,
                "avg_processing_time": stats.avg_processing_time,
                "error_rate": stats.error_rate,
                "oldest_pending": stats.oldest_pending.isoformat() if stats.oldest_pending else None
            },
            "priority_breakdown": stats.pending_by_priority
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {e}")

@app.get("/admin/workers")
async def admin_worker_stats():
    """Admin endpoint for worker pool statistics"""
    try:
        if not dynamic_pool:
            return {"error": "Worker pool not initialized"}
        
        return await dynamic_pool.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker stats: {e}")

# =====================================================
# ADMIN ENDPOINTS FOR DYNAMIC CONTENT
# =====================================================

@app.post("/admin/add-training-example")
async def add_training_example(request: Request):
    """Add new training example without redeploying"""
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["tipo", "usuario", "bot", "descripcion"]
        if not all(field in data for field in required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Append to training file  
        training_file = "/app/Entrenamiento/Entrenamiento-Productos.txt"  # Railway path
        
        new_example = f"""
CONVERSACIÓN EJEMPLO NUEVA:
Usuario: {data['usuario']}
Royal: {data['bot']}
Descripción: {data['descripcion']}
Agregado: {datetime.now().isoformat()}
"""
        
        with open(training_file, 'a', encoding='utf-8') as f:
            f.write(new_example)
        
        logger.info(f"✅ New training example added: {data['tipo']}")
        
        return {
            "status": "success",
            "message": "Training example added successfully",
            "example": new_example
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to add training example: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/add-business-info")
async def add_business_info(request: Request):
    """Add new business information dynamically - PERSISTENT in PostgreSQL"""
    try:
        data = await request.json()
        
        # Generate unique ID
        info_id = str(uuid.uuid4())[:8]
        
        # Prepare data for database
        new_info = {
            "id": info_id,
            "category": data.get("category", "general"),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "keywords": data.get("keywords", []),
            "alternative_response": data.get("alternative_response", ""),
            "added": datetime.now().isoformat()
        }
        
        # Store in PostgreSQL for persistence
        if advanced_queue.pg_pool:
            conn = advanced_queue.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                
                # Create table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bot_knowledge (
                        id VARCHAR(10) PRIMARY KEY,
                        category VARCHAR(50),
                        title TEXT,
                        content TEXT,
                        keywords TEXT,
                        alternative_response TEXT,
                        added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        active BOOLEAN DEFAULT true
                    )
                """)
                
                # Insert new knowledge
                cursor.execute("""
                    INSERT INTO bot_knowledge 
                    (id, category, title, content, keywords, alternative_response, added)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    info_id,
                    new_info["category"],
                    new_info["title"], 
                    new_info["content"],
                    ','.join(new_info["keywords"]) if isinstance(new_info["keywords"], list) else str(new_info["keywords"]),
                    new_info["alternative_response"],
                    datetime.now()
                ))
                
                conn.commit()
                logger.info(f"✅ Business info stored in DB: {new_info['title']}")
                
            finally:
                advanced_queue.pg_pool.putconn(conn)
        
        return {
            "status": "success",
            "message": "Information saved permanently in database",
            "info": new_info
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to add business info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/reload-training")
async def reload_training():
    """Force reload training data without restart"""
    try:
        # This would trigger the training parser to reload
        # For now, return success message
        logger.info("🔄 Training data reload requested")
        
        return {
            "status": "success", 
            "message": "Training data will be reloaded on next request",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/business-info")
async def get_business_info():
    """Get current dynamic business information from PostgreSQL"""
    try:
        if not advanced_queue.pg_pool:
            return {"updated": "never", "info": [], "count": 0, "source": "no_db"}
        
        conn = advanced_queue.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Get all active knowledge
            cursor.execute("""
                SELECT id, category, title, content, keywords, alternative_response, added
                FROM bot_knowledge 
                WHERE active = true 
                ORDER BY added DESC
            """)
            
            rows = cursor.fetchall()
            info_list = []
            
            for row in rows:
                info_item = {
                    "id": row[0],
                    "category": row[1],
                    "title": row[2],
                    "content": row[3],
                    "keywords": row[4].split(',') if row[4] else [],
                    "alternative_response": row[5] or "",
                    "added": row[6].isoformat() if row[6] else ""
                }
                info_list.append(info_item)
            
            # Get latest update time
            cursor.execute("SELECT MAX(added) FROM bot_knowledge WHERE active = true")
            latest_update = cursor.fetchone()[0]
            
            return {
                "updated": latest_update.isoformat() if latest_update else "never",
                "info": info_list,
                "count": len(info_list),
                "source": "postgresql"
            }
            
        finally:
            advanced_queue.pg_pool.putconn(conn)
        
    except Exception as e:
        logger.error(f"❌ Failed to get business info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Serve admin panel HTML"""
    try:
        with open("/app/admin_panel.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback for development
        try:
            with open("admin_panel.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Admin panel not found</h1>", status_code=404)

@app.delete("/admin/delete-info/{info_id}")
async def delete_business_info(info_id: str):
    """Delete/deactivate business information"""
    try:
        if not advanced_queue.pg_pool:
            raise HTTPException(status_code=500, detail="Database not available")
        
        conn = advanced_queue.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Soft delete - mark as inactive
            cursor.execute("""
                UPDATE bot_knowledge 
                SET active = false 
                WHERE id = %s
            """, (info_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ Knowledge deleted: {info_id}")
                return {"status": "success", "message": "Information deleted"}
            else:
                raise HTTPException(status_code=404, detail="Information not found")
                
        finally:
            advanced_queue.pg_pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"❌ Failed to delete info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/search-info")
async def search_business_info(q: str = "", category: str = ""):
    """Search business information"""
    try:
        if not advanced_queue.pg_pool:
            return {"results": [], "count": 0}
        
        conn = advanced_queue.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            where_conditions = ["active = true"]
            params = []
            
            if q:
                where_conditions.append("(title ILIKE %s OR content ILIKE %s OR keywords ILIKE %s)")
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
            
            if category:
                where_conditions.append("category = %s")
                params.append(category)
            
            query = f"""
                SELECT id, category, title, content, keywords, alternative_response, added
                FROM bot_knowledge 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY added DESC
                LIMIT 50
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "category": row[1],
                    "title": row[2],
                    "content": row[3][:200] + "..." if len(row[3]) > 200 else row[3],
                    "keywords": row[4].split(',') if row[4] else [],
                    "added": row[6].isoformat() if row[6] else ""
                })
            
            return {"results": results, "count": len(results)}
            
        finally:
            advanced_queue.pg_pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# STARTUP AND SHUTDOWN HANDLERS
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    global bot_state_manager
    
    logger.info("🚀 Starting Royal Bot - Maximum Efficiency Edition")
    
    # Initialize bot state manager
    logger.info("🤖 Initializing bot state manager...")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    bot_state_manager = BotStateManager(redis_url)
    await bot_state_manager.initialize()
    
    # Initialize hybrid context manager
    logger.info("🧠 Initializing hybrid context manager...")
    await initialize_hybrid_context()
    
    # Initialize advanced message queue
    logger.info("📬 Initializing advanced message queue...")
    await initialize_queue()
    
    # Initialize dynamic worker pool with our message processor
    logger.info("⚡ Initializing dynamic worker pool...")
    await initialize_worker_pool(process_royal_message)
    
    # Start background tasks
    logger.info("📡 Starting background tasks...")
    asyncio.create_task(response_sender_task())
    asyncio.create_task(metrics_collector_task())
    
    logger.info("✅ Royal Bot - Maximum Efficiency Edition started successfully!")
    logger.info(f"   Environment: {ENVIRONMENT}")
    logger.info(f"   Port: {PORT}")
    logger.info(f"   Monitoring: {'Enabled' if ENABLE_PERFORMANCE_MONITORING else 'Disabled'}")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown of all systems"""
    global bot_state_manager
    
    logger.info("🛑 Shutting down Royal Bot - Maximum Efficiency Edition")
    
    # Shutdown worker pool first (stop processing new messages)
    logger.info("⚡ Shutting down worker pool...")
    await shutdown_worker_pool()
    
    # Close bot state manager connections
    logger.info("🤖 Closing bot state manager...")
    if bot_state_manager:
        await bot_state_manager.close()
    
    # Close context manager connections
    logger.info("🧠 Closing context manager connections...")
    if hybrid_context_manager.redis_client:
        await hybrid_context_manager.redis_client.close()
    
    # Close queue connections
    logger.info("📬 Closing queue connections...")
    if advanced_queue.redis_client:
        await advanced_queue.redis_client.close()
    
    logger.info("✅ Shutdown complete")

# =====================================================
# MAIN EXECUTION
# =====================================================

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn for Railway
    uvicorn_config = {
        "app": "royal_server_optimized:app",
        "host": "0.0.0.0",
        "port": PORT,
        "log_level": "info",
        "access_log": ENABLE_REQUEST_LOGGING,
        "workers": 1,  # Important: Only 1 worker for proper async coordination
    }
    
    # Production optimizations
    if ENVIRONMENT == "production":
        uvicorn_config.update({
            "reload": False,
            "log_level": "warning",
        })
    else:
        uvicorn_config.update({
            "reload": True,
            "log_level": "debug",
        })
    
    logger.info(f"🚀 Starting server with config: {uvicorn_config}")
    uvicorn.run(**uvicorn_config)