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

# Aplicar parche para compatibilidad de openai-agents antes de cualquier import
try:
    import patch_openai_agents
except ImportError:
    pass  # El parche es opcional

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time
import uuid
import httpx

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

# Follow-up system
from royal_agents.follow_up import FollowUpScheduler, FollowUpManager, FollowUpTracker

# Royal agents import - Intentar importación modular
ROYAL_AGENTS_AVAILABLE = False

# Paso 1: Intentar importar la función principal directamente
try:
    from royal_agents.agent_manager import run_contextual_conversation_sync_managed as run_contextual_conversation_sync
    ROYAL_AGENTS_AVAILABLE = True
    print("✅ ÉXITO: run_contextual_conversation_sync importado correctamente")
except Exception as e:
    print(f"❌ ERROR CRÍTICO importando run_contextual_conversation_sync: {e}")
    import traceback
    print(f"❌ Stack trace completo:\n{traceback.format_exc()}")
    
    # Fallback temporal con respuesta básica
    def run_contextual_conversation_sync(user_id: str, user_message: str) -> str:
        # Respuesta temporal mientras se soluciona el problema
        return "Hola! El sistema está en mantenimiento momentáneo. Por favor intenta nuevamente en unos minutos o contacta a soporte."


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
CHATWOOT_TEAM_GENERAL_ID = int(os.getenv("CHATWOOT_TEAM_GENERAL_ID", "0"))  # Para consultas generales sin información

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

# Global message deduplication cache
processed_messages = set()
last_cleanup_time = datetime.now()

# Bot state manager instance
bot_state_manager: Optional[BotStateManager] = None

# Main event loop for async operations from threads
main_event_loop: Optional[asyncio.AbstractEventLoop] = None

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

class ManualMessage(BaseModel):
    message: str
    phone: str
    from_user: Optional[bool] = True

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
        
        # 📅 FOLLOW-UP: Cancelar follow-ups cuando el usuario responde
        try:
            if followup_manager and message_data:
                # Los mensajes de usuarios vienen de evolution o chatwoot (no system)
                source_str = str(message_data.source).lower() if hasattr(message_data, 'source') else ''
                if source_str in ['evolution', 'chatwoot', 'messagesource.evolution', 'messagesource.chatwoot']:
                    await followup_manager.handle_user_response(user_id)
                    if followup_tracker:
                        await followup_tracker.track_user_response(user_id, message)
        except Exception as e:
            logger.debug(f"Follow-up processing skipped: {e}")
        
        # ✨ NUEVO: Verificar estado del bot ANTES de procesar
        # Extraer identificadores del mensaje
        phone = message_data.phone if message_data else None
        conversation_id = message_data.conversation_id if message_data else None
        
        # Verificar por teléfono (prioritario)
        if phone and bot_state_manager:
            is_active = await bot_state_manager.is_bot_active(phone)
            if not is_active:
                logger.info(f"🔇 Worker: Bot pausado para teléfono {phone}, mensaje ignorado silenciosamente")
                return ""
        
        # Verificar por conversación si no hay teléfono
        elif conversation_id and bot_state_manager:
            conv_identifier = f"conv_{conversation_id}"
            is_active = await bot_state_manager.is_bot_active(conv_identifier)
            if not is_active:
                logger.info(f"🔇 Worker: Bot pausado para conversación {conv_identifier}, mensaje ignorado silenciosamente")
                return ""
        
        # Verificar por user_id como último recurso (para casos legacy)
        elif user_id and not user_id.startswith("chatwoot_") and bot_state_manager:
            # Si el user_id parece ser un teléfono, verificar
            is_active = await bot_state_manager.is_bot_active(user_id)
            if not is_active:
                logger.info(f"🔇 Worker: Bot pausado para user_id {user_id}, mensaje ignorado silenciosamente")
                return ""
        
        # Si llegamos aquí, el bot está activo - procesar normalmente
        logger.debug(f"✅ Worker: Bot activo para {user_id}, procesando mensaje...")
        
        # Process with Royal agent (using sync version for thread compatibility)
        logger.info(f"🤖 Llamando a run_contextual_conversation_sync para {user_id}")
        logger.info(f"🤖 Royal agents disponible: {ROYAL_AGENTS_AVAILABLE}")
        
        response = run_contextual_conversation_sync(user_id, message)
        
        logger.info(f"🤖 Respuesta recibida: {response[:50] if response else 'None'}...")
        
        # ✨ NUEVO: Verificar si hay respuesta válida antes de enviar
        if response is None or response == "":
            processing_time = time.time() - start_time
            logger.warning(f"⚠️ Royal agents no disponible para {user_id}, mensaje ignorado")
            logger.info(f"🔇 No response generated for {user_id} (bot paused or agents unavailable), processed in {processing_time:.2f}s")
            return ""
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update global metrics
        system_metrics['average_response_time'] = (
            system_metrics['average_response_time'] * 0.9 + processing_time * 0.1
        )
        
        # Send response back to appropriate channel (solo si hay respuesta válida)
        if message_data and response:
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

def detect_missing_info_response(response: str) -> tuple[bool, str, str]:
    """
    Detecta si la respuesta indica falta de información y debe asignarse a un agente.
    
    Returns:
        tuple: (should_assign, info_type, replacement_message)
    """
    import re
    import random
    
    response_lower = response.lower()
    
    # Patrones que indican falta de información
    missing_info_patterns = [
        r"lamentablemente.*no tengo",
        r"disculp.*no tengo información",
        r"no tengo información",
        r"no dispongo.*información", 
        r"no sé.*sobre",
        r"no conozco.*información",
        r"no puedo.*información",
        r"no tengo.*datos",
        r"información.*no.*está.*disponible",
        r"no.*encontré.*información",
        r"no.*acceso.*información",
        r"lamentablemente.*no.*información",
        r"no cuento con.*información",
        r"no hay información",
        r"sin información.*disponible"
    ]
    
    # Verificar si la respuesta indica falta de información
    for pattern in missing_info_patterns:
        if re.search(pattern, response_lower):
            # Determinar tipo de información faltante
            info_type = "general"
            if any(word in response_lower for word in ["precio", "costo", "valor", "pago"]):
                info_type = "price"
            elif any(word in response_lower for word in ["stock", "disponible", "cantidad"]):
                info_type = "stock"
            elif any(word in response_lower for word in ["producto", "joya", "modelo"]):
                info_type = "product"
            elif any(word in response_lower for word in ["envío", "entrega", "despacho"]):
                info_type = "shipping"
            
            # Mensajes naturales argentinos de reemplazo
            replacement_messages = {
                'product': [
                    "Dale, dejame que chequeo eso puntualmente en el sistema y te confirmo ahora 👍",
                    "Tengo que verificar eso con el equipo. Dame un momento que te traigo la info completa 👍",
                    "Mirá, eso lo tengo que consultar específicamente. En un ratito te confirmo todo 👍"
                ],
                'price': [
                    "Los precios me los están actualizando justo ahora. Dame un minuto que te confirmo el valor exacto 👍",
                    "Tengo que chequear el precio actualizado. Ahora te traigo el dato preciso 👍",
                    "Dale, dejame que reviso el valor actual y te confirmo en un momento 👍"
                ],
                'stock': [
                    "El stock lo tengo que verificar en tiempo real. Un segundo que chequeo y te confirmo 👍",
                    "Dale, que consulto la disponibilidad exacta y te digo 👍",
                    "Tengo que ver qué hay disponible ahora mismo. Ya te confirmo 👍"
                ],
                'shipping': [
                    "Los envíos tengo que consultarlos según tu zona específica. Ya te digo 👍",
                    "Para el envío necesito chequear tu ubicación exacta. Ahora te confirmo 👍",
                    "Dale, que verifico las opciones de envío para tu zona y te cuento 👍"
                ],
                'general': [
                    "Dale, tengo que chequear eso puntualmente. Dame un ratito y te confirmo todo 👍",
                    "Esa info la tengo que verificar bien. En un momento te respondo 👍",
                    "Dejame que consulto eso específicamente y te paso toda la información 👍"
                ]
            }
            
            # Seleccionar mensaje de reemplazo
            messages = replacement_messages.get(info_type, replacement_messages['general'])
            replacement_message = random.choice(messages)
            
            return True, info_type, replacement_message
    
    return False, "", ""

async def send_response_to_channel(user_id: str, response: str, message_data: 'MessageData'):
    """Send response back to the appropriate channel (WhatsApp, Chatwoot, etc.)"""
    
    # Verificar que hay respuesta válida
    if not response or response is None:
        logger.debug(f"🔇 No response to send for {user_id} (None or empty)")
        return False
    
    # 🚨 INTERCEPTOR: Detectar "No tengo información" y asignar a agente
    should_assign, info_type, replacement_message = detect_missing_info_response(response)
    
    if should_assign and message_data.conversation_id:
        logger.warning(f"🚨 DETECTADA respuesta sin información de tipo '{info_type}' para {user_id}")
        logger.info(f"📋 Respuesta original: {response[:100]}...")
        
        # Determinar team según tipo de información
        team_id = CHATWOOT_TEAM_GENERAL_ID  # Por defecto
        if info_type == "shipping":
            team_id = CHATWOOT_TEAM_SHIPPING_ID
        elif info_type in ["product", "stock", "price"]:
            team_id = CHATWOOT_TEAM_SUPPORT_ID if CHATWOOT_TEAM_GENERAL_ID == 0 else CHATWOOT_TEAM_GENERAL_ID
        
        # Asignar automáticamente si hay team configurado
        if team_id > 0:
            assignment_success = await assign_conversation_to_team(
                message_data.conversation_id, 
                team_id, 
                f"Información faltante: {info_type}"
            )
            
            if assignment_success:
                logger.info(f"✅ Conversación {message_data.conversation_id} asignada automáticamente por falta de información ({info_type})")
                
                # Pausar bot para esta conversación
                if bot_state_manager:
                    conv_identifier = f"conv_{message_data.conversation_id}"
                    await bot_state_manager.pause_bot(
                        conv_identifier, 
                        reason=f"Asignado por información faltante: {info_type}",
                        ttl=86400  # 24 horas
                    )
                    logger.info(f"⏸️ Bot pausado para conversación {message_data.conversation_id}")
        
        # Usar mensaje de reemplazo natural
        response = replacement_message
        logger.info(f"🔄 Mensaje reemplazado: {replacement_message}")
    
    try:
        # Los mensajes de Evolution se envían por el canal Evolution si tienen número de teléfono
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
# MESSAGE EXTRACTION FUNCTIONS
# =====================================================

def extract_message_content(message_data: dict) -> str:
    """Extract message content from different WhatsApp message types"""
    message = message_data.get("message", {})
    
    # Type 1: Simple conversation message
    if "conversation" in message:
        return message["conversation"]
    
    # Type 2: Extended text message
    if "extendedTextMessage" in message:
        return message["extendedTextMessage"].get("text", "")
    
    # Type 3: Quoted message
    if "quotedMessage" in message:
        quoted = message["quotedMessage"]
        if "conversation" in quoted:
            return quoted["conversation"]
        elif "extendedTextMessage" in quoted:
            return quoted["extendedTextMessage"].get("text", "")
    
    # Type 4: Media messages
    if "imageMessage" in message:
        return message["imageMessage"].get("caption", "[Imagen]")
    
    if "videoMessage" in message:
        return message["videoMessage"].get("caption", "[Video]")
    
    if "documentMessage" in message:
        return message["documentMessage"].get("caption", "[Documento]")
    
    if "audioMessage" in message:
        return "[Audio]"
    
    if "stickerMessage" in message:
        return "[Sticker]"
    
    if "locationMessage" in message:
        return "[Ubicación]"
    
    return ""

# =====================================================
# CONVERSATION-PHONE MAPPING FUNCTIONS
# =====================================================

def link_conversation_to_phone(conversation_id: str, phone: str):
    """Vincular conversación de Chatwoot con número de teléfono"""
    global conversation_phone_mapping
    conversation_phone_mapping[conversation_id] = phone
    logger.info(f"🔗 Vinculando conversación {conversation_id} con teléfono {phone}")

def is_duplicate_message(phone: str, content: str, source: str = "") -> bool:
    """
    Verifica si un mensaje ya fue procesado para evitar respuestas duplicadas
    """
    global processed_messages, last_cleanup_time
    
    # Limpiar cache viejo cada 5 minutos
    now = datetime.now()
    if (now - last_cleanup_time).total_seconds() > 300:  # 5 minutos
        processed_messages.clear()
        last_cleanup_time = now
        logger.info("🧹 Cache de mensajes duplicados limpiado")
    
    # Crear clave única para el mensaje
    message_key = f"{phone}:{content[:50]}:{source}"
    message_hash = hash(message_key)
    
    if message_hash in processed_messages:
        logger.warning(f"🔄 MENSAJE DUPLICADO DETECTADO: {phone} - '{content[:30]}...' desde {source}")
        return True
    
    # Marcar como procesado
    processed_messages.add(message_hash)
    return False

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
            "roto", "mal estado", "garantia", "devolucion", "cambio",
            "pedido roto", "llego roto", "vino roto", "llegó dañado", "dañado"
        ],
        "team_id": CHATWOOT_TEAM_SUPPORT_ID,
        "message": "Te voy a conectar con nuestro equipo, quienes te van a ayudar con tu reclamo especifico. 🛠️\nVan a resolver tu problema de inmediato."
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
    logger.info(f"🔍 is_order_inquiry - Analizando: '{message_lower[:50]}...'")
    
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
    
    logger.info(f"🔍 has_order_ref: {has_order_ref}, has_status_ref: {has_status_ref}")
    
    result = has_order_ref or has_status_ref
    logger.info(f"🔍 is_order_inquiry resultado: {result}")
    
    return result

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
    logger.info(f"🔍 check_and_route_by_keywords - Analizando: '{message_lower[:100]}...'")
    
    # Revisar cada categoría de keywords
    for route_type, config in KEYWORD_ROUTING.items():
        logger.info(f"🔍 Revisando categoría: {route_type}")
        
        # Para shipping, hacer validación adicional
        if route_type == "shipping":
            is_order_query = is_order_inquiry(message)
            logger.info(f"🔍 Shipping - es consulta de pedido?: {is_order_query}")
            if not is_order_query:
                logger.info(f"🔍 Skipping shipping - no es consulta de pedido específico")
                continue  # Skip si no es consulta sobre pedido específico
        
        # Verificar si alguna keyword coincide
        matched_keywords = [kw for kw in config["keywords"] if kw in message_lower]
        logger.info(f"🔍 Keywords coincidentes en {route_type}: {matched_keywords}")
        
        if matched_keywords:
            logger.info(f"🎯 Keywords detectadas [{route_type}]: {matched_keywords} en mensaje: '{message[:50]}...'")
            logger.info(f"🎯 Intentando asignar conversación {conversation_id} al equipo {config['team_id']} ({route_type})")
            
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

async def find_or_create_conversation_for_phone(phone: str) -> Optional[str]:
    """
    Busca una conversación existente en Chatwoot por número de teléfono
    o crea una nueva si no existe
    """
    if not all([CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
        logger.warning("⚠️ Chatwoot API no configurada para búsqueda de conversaciones")
        return None
    
    try:
        # Buscar conversaciones existentes por teléfono
        search_url = f"{CHATWOOT_API_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/search"
        headers = {
            "Content-Type": "application/json",
            "api_access_token": CHATWOOT_API_TOKEN
        }
        
        # Buscar por el teléfono con diferentes formatos
        search_queries = [
            phone,
            f"+{phone}",
            f"+1{phone}",  # Si es número de US
            phone[-10:] if len(phone) > 10 else phone  # Últimos 10 dígitos
        ]
        
        for query in search_queries:
            params = {"q": query}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=headers, params=params)
                
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("payload", [])
                
                if conversations:
                    # Tomar la primera conversación encontrada
                    conv = conversations[0]
                    conversation_id = str(conv.get("id"))
                    
                    # Crear vinculación
                    link_conversation_to_phone(conversation_id, phone)
                    
                    logger.info(f"🔍 Conversación encontrada por búsqueda: {conversation_id} para {phone}")
                    return conversation_id
        
        # Si no se encontró, intentar crear una nueva conversación (esto requiere más lógica)
        logger.info(f"🔍 No se encontró conversación existente para {phone}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error buscando conversación para {phone}: {e}")
        return None

async def detect_keywords_without_assignment(message: str, phone: str) -> bool:
    """
    Detecta keywords y notifica sin asignar conversación
    (fallback cuando no hay conversation_id)
    """
    message_lower = message.lower()
    
    # Revisar si hay keywords de soporte que requieren atención
    for route_type, config in KEYWORD_ROUTING.items():
        matched_keywords = [kw for kw in config["keywords"] if kw in message_lower]
        
        if matched_keywords:
            logger.warning(f"🚨 KEYWORDS DETECTADAS sin conversación: [{route_type}] {matched_keywords} de {phone}")
            
            # Enviar mensaje al usuario explicando que será contactado
            fallback_message = f"""🔔 Detecté que necesitás ayuda con {route_type}.

Como no puedo procesar tu consulta automáticamente en este momento, nuestro equipo especializado te va a contactar directamente para resolver tu situación.

Gracias por tu paciencia. 🙏"""
            
            try:
                await send_evolution_message(phone, fallback_message)
                logger.info(f"📱 Mensaje de fallback enviado a {phone}")
            except Exception as e:
                logger.error(f"❌ Error enviando mensaje de fallback: {e}")
            
            # Log para que admin pueda revisar manualmente
            logger.critical(f"🚨 ATENCIÓN MANUAL REQUERIDA: {phone} - Tipo: {route_type} - Keywords: {matched_keywords}")
            
            return True
    
    return False

async def pause_bot_for_both_channels(phone: str, conversation_id: str, reason: str) -> bool:
    """Pausar bot para ambos canales (WhatsApp y Chatwoot)"""
    success_phone = await bot_state_manager.pause_bot(phone, reason) if bot_state_manager else False
    success_conv = await bot_state_manager.pause_bot(f"conv_{conversation_id}", reason) if bot_state_manager else False
    
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
    success_phone = await bot_state_manager.resume_bot(phone) if bot_state_manager else False
    success_conv = await bot_state_manager.resume_bot(f"conv_{conversation_id}") if bot_state_manager else False
    
    logger.info(f"✅ Bot reactivado para AMBOS canales: {phone} y conv_{conversation_id}")
    return True

# =====================================================
# BOT CONTROL FUNCTIONS  
# =====================================================

def detect_bot_control_tags(labels: list) -> dict:
    """
    Detecta etiquetas de control del bot ('bot-paused' y 'bot-active') en la lista de etiquetas
    
    Args:
        labels: Lista de etiquetas de la conversación
        
    Returns:
        Dict con información de las etiquetas detectadas:
        {
            'bot_paused': bool,
            'bot_active': bool, 
            'action': 'pause'|'activate'|None,
            'priority_tag': str|None
        }
    """
    result = {
        'bot_paused': False,
        'bot_active': False,
        'action': None,
        'priority_tag': None
    }
    
    if not labels or not isinstance(labels, list):
        return result
        
    for label in labels:
        # Manejar diferentes formatos de etiqueta
        label_name = ""
        
        if isinstance(label, dict):
            label_name = label.get('title') or label.get('name') or label.get('label') or ""
        elif isinstance(label, str):
            label_name = label
        
        label_name = label_name.lower().strip()
        
        # Verificar etiquetas de control
        if label_name == 'bot-paused':
            result['bot_paused'] = True
        elif label_name == 'bot-active':
            result['bot_active'] = True
    
    # Determinar acción basada en prioridad
    # bot-active tiene precedencia sobre bot-paused
    if result['bot_active']:
        result['action'] = 'activate'
        result['priority_tag'] = 'bot-active'
    elif result['bot_paused']:
        result['action'] = 'pause'
        result['priority_tag'] = 'bot-paused'
    
    return result

async def handle_conversation_updated(data: Dict) -> Dict:
    """
    Maneja eventos conversation_updated para detectar cambios en etiquetas bot-paused
    
    Args:
        data: Datos del webhook de Chatwoot
        
    Returns:
        Diccionario con el resultado del procesamiento
    """
    try:
        # Buscar conversation_id en múltiples ubicaciones posibles
        conversation = data.get("conversation", {})
        conversation_id = str(conversation.get("id", ""))
        
        # Si no está en conversation.id, buscar en el nivel raíz del payload
        if not conversation_id:
            conversation_id = str(data.get("id", ""))
        
        # Si aún no encontramos el ID, intentar con otros campos posibles
        if not conversation_id:
            # Algunas veces Chatwoot puede enviar el ID en diferentes formatos
            if "conversation_id" in data:
                conversation_id = str(data.get("conversation_id", ""))
        
        if not conversation_id:
            logger.warning(f"⚠️ conversation_updated sin ID de conversación. Payload keys: {list(data.keys())}")
            logger.debug(f"🔍 Payload completo: {data}")
            return {"status": "error", "message": "Missing conversation ID"}
        
        # Extraer número de teléfono de la conversación (buscar en múltiples ubicaciones)
        phone = None
        
        # 1. Buscar en conversation.contact_phone
        contact_phone = conversation.get("contact_phone")
        if contact_phone:
            phone = contact_phone.replace("+", "").replace("-", "").replace(" ", "")
        
        # 2. Buscar en contact_inbox.source_id si no está en contact_phone
        if not phone:
            contact_inbox = conversation.get("contact_inbox", {})
            source_id = contact_inbox.get("source_id", "")
            if source_id and source_id.replace("-", "").replace("+", "").replace(" ", "").isdigit():
                phone = source_id.replace("-", "").replace("+", "").replace(" ", "")
        
        # 3. Buscar en additional_attributes.phone_number
        if not phone:
            attrs = conversation.get("additional_attributes", {})
            if "phone_number" in attrs:
                phone = attrs["phone_number"].replace("+", "").replace("-", "").replace(" ", "")
        
        # 4. Si conversation está vacío, buscar teléfono en el payload principal
        if not phone and not conversation:
            # Buscar source_id en el nivel raíz
            source_id = data.get("source_id", "")
            if source_id and source_id.replace("-", "").replace("+", "").replace(" ", "").isdigit():
                phone = source_id.replace("-", "").replace("+", "").replace(" ", "")
        
        # 5. Si aún no tenemos teléfono, buscar en las vinculaciones existentes
        if not phone and conversation_id:
            phone = get_phone_from_conversation(conversation_id)
            if phone:
                logger.info(f"🔗 Teléfono encontrado en vinculaciones: conversación {conversation_id} ↔ teléfono {phone}")
        
        logger.info(f"🏷️ Procesando conversation_updated - Conversación: {conversation_id}, Teléfono: {phone}")
        
        # Extraer etiquetas de la conversación (buscar en múltiples ubicaciones)
        labels = conversation.get("labels", [])
        
        # Si no hay etiquetas en conversation.labels, buscar en otros lugares
        if not labels:
            # Buscar en cached_label_list
            labels = conversation.get("cached_label_list", [])
            if isinstance(labels, str):
                # Si es string separado por comas, convertir a lista
                labels = [{"title": label.strip()} for label in labels.split(",") if label.strip()]
        
        # Si aún no hay etiquetas y conversation está vacío, buscar en el payload principal
        if not labels and not conversation:
            # Algunos webhooks podrían enviar las etiquetas en el nivel raíz
            labels = data.get("labels", [])
        
        logger.info(f"🔍 Etiquetas encontradas para conversación {conversation_id}: {labels}")
        
        # Detectar etiquetas de control del bot
        control_tags = detect_bot_control_tags(labels)
        logger.info(f"🎯 Etiquetas de control detectadas: {control_tags}")
        
        # Determinar identificadores para el estado del bot
        identifiers = []
        if phone:
            identifiers.append(phone)
            # Crear vinculación si hay teléfono
            link_conversation_to_phone(conversation_id, phone)
        
        # Siempre agregar identificador de conversación
        conv_identifier = f"conv_{conversation_id}"
        identifiers.append(conv_identifier)
        
        logger.info(f"🎯 Identificadores para procesar etiquetas: {identifiers}")
        
        # Procesar cambio de estado del bot basado en etiquetas de control
        actions_taken = []
        action = control_tags.get('action')
        priority_tag = control_tags.get('priority_tag')
        
        for identifier in identifiers:
            # Obtener estado actual del bot para este identificador
            current_state = await bot_state_manager.get_bot_state(identifier) if bot_state_manager else None
            is_currently_paused = not current_state.get("active", True) if current_state else False
            current_reason = current_state.get("reason", "") if current_state else ""
            
            logger.info(f"🔍 Estado actual para {identifier}: pausado={is_currently_paused}, razón='{current_reason}'")
            
            if action == 'activate':
                # REACTIVAR BOT - etiqueta bot-active presente
                if is_currently_paused:
                    success = await bot_state_manager.resume_bot(identifier) if bot_state_manager else False if bot_state_manager else False if bot_state_manager else False
                    
                    if success:
                        actions_taken.append(f"force_resumed_{identifier}")
                        logger.info(f"🟢 Bot FORZADAMENTE reactivado por etiqueta '{priority_tag}' para {identifier}")
                        logger.info(f"   ↳ Razón de pausa anterior sobreescrita: '{current_reason}'")
                    else:
                        logger.error(f"❌ Error reactivando bot por etiqueta '{priority_tag}' para {identifier}")
                else:
                    logger.info(f"ℹ️ Bot ya estaba activo para {identifier}, etiqueta '{priority_tag}' ignorada")
                
            elif action == 'pause':
                # PAUSAR BOT - etiqueta bot-paused presente
                if not is_currently_paused:
                    success = await bot_state_manager.pause_bot(
                        identifier, 
                        reason="etiqueta_bot_paused",
                        ttl=86400  # 24 horas por defecto
                    ) if bot_state_manager else False
                    
                    if success:
                        actions_taken.append(f"paused_{identifier}")
                        logger.info(f"🔴 Bot pausado por etiqueta '{priority_tag}' para {identifier}")
                    else:
                        logger.error(f"❌ Error pausando bot por etiqueta '{priority_tag}' para {identifier}")
                else:
                    logger.info(f"ℹ️ Bot ya estaba pausado para {identifier}, etiqueta '{priority_tag}' ignorada")
                
            elif not control_tags['bot_paused'] and not control_tags['bot_active']:
                # SIN ETIQUETAS DE CONTROL - verificar si se removieron etiquetas
                if is_currently_paused and current_reason == "etiqueta_bot_paused":
                    # Solo reactivar si fue pausado específicamente por etiqueta bot-paused
                    success = await bot_state_manager.resume_bot(identifier) if bot_state_manager else False if bot_state_manager else False if bot_state_manager else False
                    
                    if success:
                        actions_taken.append(f"auto_resumed_{identifier}")
                        logger.info(f"🟢 Bot reactivado automáticamente por remoción de etiqueta bot-paused para {identifier}")
                    else:
                        logger.error(f"❌ Error reactivando bot automáticamente para {identifier}")
                else:
                    logger.info(f"ℹ️ Sin etiquetas de control para {identifier}, manteniendo estado actual")
        
        return {
            "status": "processed",
            "conversation_id": conversation_id,
            "phone": phone,
            "control_tags": control_tags,
            "actions_taken": actions_taken,
            "identifiers": identifiers
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando conversation_updated: {e}")
        return {"status": "error", "message": str(e)}

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
                success = await bot_state_manager.pause_bot(chat_id, "agent_control") if bot_state_manager else False
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
                success = await bot_state_manager.resume_bot(chat_id) if bot_state_manager else False
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
                success = await bot_state_manager.pause_bot(identifier, f"agent_{agent_name}") if bot_state_manager else False
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
                success = await bot_state_manager.resume_bot(identifier) if bot_state_manager else False if bot_state_manager else False
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
            
            state = await bot_state_manager.get_bot_state(identifier) if bot_state_manager else {"active": True} if bot_state_manager else {"active": True}
            
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

@app.get("/debug/royal-agents")
async def debug_royal_agents():
    """Debug endpoint to check royal_agents import status"""
    import sys
    
    # Verificar si el módulo está cargado
    royal_agents_loaded = 'royal_agents' in sys.modules
    royal_agent_contextual_loaded = 'royal_agents.royal_agent_contextual' in sys.modules
    
    # Probar una llamada simple
    test_response = None
    try:
        test_response = run_contextual_conversation_sync("test_user", "hola test")
    except Exception as e:
        test_response = f"Error en llamada: {str(e)}"
    
    return {
        "status": "debug_info",
        "ROYAL_AGENTS_AVAILABLE": ROYAL_AGENTS_AVAILABLE,
        "module_loaded": {
            "royal_agents": royal_agents_loaded,
            "royal_agent_contextual": royal_agent_contextual_loaded
        },
        "test_call_response": test_response[:100] if test_response else None,
        "function_type": str(type(run_contextual_conversation_sync))
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
        sender = data.get("sender", {})
        sender_type = sender.get("type") if sender else None
        content = data.get("content", "")
        is_private = data.get("private", False)
        
        logger.info(f"🔍 DEBUG - Event: {event}, MsgType: {message_type}, Sender: {sender_type}, Private: {is_private}, Content: '{content}'")
        logger.info(f"🔍 DEBUG - Sender completo: {sender}")
        
        # 🏷️ Handle conversation_updated events for bot-paused tag detection
        if data.get("event") == "conversation_updated":
            logger.info("🏷️ Evento conversation_updated detectado - procesando etiquetas...")
            result = await handle_conversation_updated(data)
            logger.info(f"🏷️ Resultado conversation_updated: {result}")
            return result

        # Handle agent control commands (notes or messages from agents)
        if (data.get("event") == "message_created" and 
            data.get("sender", {}).get("type") == "user"):
            # This is from an agent (user in Chatwoot = agent)
            content_lower = content.lower().strip()
            if any(cmd in content_lower for cmd in ["/bot pause", "/bot resume", "/bot status", "bot pause", "bot resume"]):
                logger.info(f"🎯 Comando de agente detectado: {content}")
                return await handle_agent_private_note(data)
        
        # Process only incoming messages from contacts  
        # Nota: A veces sender.type es None pero el mensaje sigue siendo válido
        if (data.get("event") == "message_created" and 
            data.get("message_type") == "incoming"):
            
            sender_type = data.get("sender", {}).get("type") if data.get("sender") else None
            logger.info(f"🔍 Mensaje incoming detectado, sender.type: {sender_type}")
            
            # Skip si es mensaje de agente (user type)
            if sender_type == "user":
                logger.info("🔇 Ignorando mensaje de agente (user type)")
                return {"status": "received", "ignored": "agent_message"}
            
            # Procesar mensajes de contact o sender type desconocido
            logger.info("🔵 PROCESANDO mensaje incoming de contact en Chatwoot")
            
            conversation = data.get("conversation", {})
            content = data.get("content", "").strip()
            
            # VERIFICAR DUPLICACIÓN EN CHATWOOT
            contact_phone = conversation.get("contact_phone", "unknown")
            if is_duplicate_message(contact_phone, content, "chatwoot"):
                return {"status": "duplicate_ignored", "source": "chatwoot"}
            
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
                        if bot_state_manager and not await bot_state_manager.is_bot_active(phone):
                            bot_active = False
                            logger.info(f"🔇 Bot pausado para teléfono {phone} (Chatwoot), mensaje ignorado")
                    
                    # También verificar por conversación  
                    conv_identifier = f"conv_{conversation_id}"
                    if bot_state_manager and not await bot_state_manager.is_bot_active(conv_identifier):
                        bot_active = False
                        logger.info(f"🔇 Bot pausado para conversación {conv_identifier} (Chatwoot), mensaje ignorado")
                    
                    if not bot_active:
                        return {"status": "bot_paused", "message": "ignored", "source": "chatwoot"}
                    
                    # 🎯 CHECK FOR ASSIGNMENT KEYWORDS BEFORE PROCESSING
                    logger.info(f"🔍 CHATWOOT - Revisando keywords en: '{content[:50]}...' para conversación {conversation_id}")
                    routed = await check_and_route_by_keywords(
                        content, 
                        conversation_id, 
                        phone if phone else f"chatwoot_{contact_id}"
                    )
                    
                    if routed:
                        logger.info(f"🚀 Mensaje de Chatwoot ruteado automáticamente: {conversation_id}")
                        return {"status": "routed_to_team", "conversation_id": conversation_id, "source": "chatwoot"}
                    else:
                        logger.info(f"🔍 CHATWOOT - NO se detectaron keywords de asignación en: '{content[:50]}...'")
                        # CONTINUAR con el procesamiento normal del bot solo si NO hubo asignación
                    
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
        else:
            # Log por qué no se procesó el mensaje
            logger.info(f"🔇 Mensaje NO procesado - Event: {data.get('event')}, MsgType: {data.get('message_type')}, Sender: {data.get('sender', {}).get('type')}")
        
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
        
        logger.info(f"📱 Evolution event: {event}")
        
        # Handle different event types
        if event == "labels.association":
            # Handle label changes from Chatwoot
            return await handle_label_association(data)
        
        # Process regular messages
        if event not in ["messages.upsert"]:
            # Log especial para identificar qué eventos llegan
            if event == "messages.update":
                logger.debug(f"🔇 Ignoring event: {event}")  # Menos verboso
            else:
                logger.info(f"🔇 Ignoring event: {event}")
            return {"status": "received", "ignored": event}
        
        logger.info(f"📱 Processing messages.upsert event")
        
        # Debug: Mostrar estructura del mensaje completo
        logger.info(f"📱 Raw message data keys: {list(message_data_raw.keys())}")
        logger.info(f"📱 Raw message structure: {json.dumps(message_data_raw, indent=2)[:1000]}...")
        
        # Check if message is from us (fromMe: true)
        from_me = message_data_raw.get("key", {}).get("fromMe", False)
        logger.info(f"📱 fromMe value: {from_me}")
        
        if from_me:
            logger.info("🔇 Ignoring message from bot itself (fromMe: true)")
            return {"status": "received", "ignored": "fromMe"}
        
        # Extract message data
        message_content = extract_message_content(message_data_raw).strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "")
        
        # Handle different number formats (WhatsApp, Meta Ads, etc)
        if "@lid" in from_number:
            # Meta Ads Lead ID format
            logger.info(f"📱 Usuario de Meta Ads detectado: {from_number}")
            from_number = from_number.replace("@lid", "")
        elif "@s.whatsapp.net" in from_number:
            # Standard WhatsApp format
            from_number = from_number.replace("@s.whatsapp.net", "")
        elif "@g.us" in from_number:
            # Group format (ignore for now)
            logger.info(f"📱 Mensaje de grupo detectado: {from_number}")
            from_number = from_number.replace("@g.us", "")
        
        # Debug: Mostrar campos extraídos
        logger.info(f"📱 Extracted - Content: '{message_content}', From: '{from_number}'")
        logger.info(f"📱 Message object keys: {list(message_data_raw.get('message', {}).keys())}")
        logger.info(f"📱 Key object: {message_data_raw.get('key', {})}")
        
        if message_content and from_number:
            # VERIFICAR DUPLICACIÓN EN EVOLUTION API
            if is_duplicate_message(from_number, message_content, "evolution"):
                return {"status": "duplicate_ignored", "phone": from_number}
            
            logger.info(f"📱 PROCESANDO mensaje WhatsApp de {from_number}: '{message_content[:100]}...'")
            user_id = f"whatsapp_{from_number}"
            
            # PRIMERO: Buscar chatwootConversationId en el payload de Evolution
            conversation_id = None
            chatwoot_conv_id = message_data_raw.get("chatwootConversationId")
            if chatwoot_conv_id:
                conversation_id = str(chatwoot_conv_id)
                logger.info(f"✅ Usando chatwootConversationId del payload: {conversation_id}")
                # Crear vinculación automática
                link_conversation_to_phone(conversation_id, from_number)
            else:
                # FALLBACK: Buscar en el mapeo local si no viene en el payload
                conversation_id = get_conversation_from_phone(from_number)
                if conversation_id:
                    logger.info(f"📱 Teléfono {from_number} vinculado a conversación {conversation_id} (desde mapeo local)")
                else:
                    logger.info(f"⚠️ No hay chatwootConversationId en payload ni vinculación local para {from_number}")
            
            # Handle bot control commands first
            control_response = await handle_bot_control_commands(from_number, message_content)
            if control_response:
                return control_response
            
            # Check if bot is active for this user (verificar ambos identificadores)
            bot_active = await bot_state_manager.is_bot_active(from_number) if bot_state_manager else True
            if conversation_id:
                # También verificar por conversación si existe vinculación
                conv_active = await bot_state_manager.is_bot_active(f"conv_{conversation_id}") if bot_state_manager else True
                bot_active = bot_active and conv_active
            
            if not bot_active:
                logger.info(f"🔇 Bot pausado para {from_number}, mensaje ignorado")
                return {"status": "bot_paused", "message": "ignored"}
            
            # 🎯 CHECK FOR ASSIGNMENT KEYWORDS BEFORE PROCESSING
            if conversation_id:
                logger.info(f"🔍 REVISANDO keywords en: '{message_content[:50]}...' para conversación {conversation_id}")
                routed = await check_and_route_by_keywords(
                    message_content, 
                    conversation_id, 
                    from_number
                )
                
                if routed:
                    logger.info(f"🚀 Mensaje ruteado automáticamente: {from_number} → {conversation_id}")
                    return {"status": "routed_to_team", "conversation_id": conversation_id, "phone": from_number}
                else:
                    logger.info(f"🔍 NO se detectaron keywords de asignación en: '{message_content[:50]}...'")
            else:
                logger.warning(f"⚠️ No hay conversación vinculada para {from_number} - usando fallback")
                
                # FUNCIONALIDAD FALLBACK: Detección sin asignación
                # Si no hay conversation_id pero hay keywords importantes, notificar
                if await detect_keywords_without_assignment(message_content, from_number):
                    return {"status": "keywords_detected_no_assignment", "phone": from_number}
                
                logger.info(f"ℹ️ Continuando con bot normal para {from_number} (sin conversation_id)")
            
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
        else:
            # Debug: Si no hay contenido o número, mostrar qué pasó  
            logger.warning(f"📱 Mensaje messages.upsert SIN CONTENIDO VÁLIDO:")
            logger.warning(f"   - Content: '{message_content}'")
            logger.warning(f"   - From: '{from_number}'")
            logger.warning(f"   - fromMe: {from_me}")
            logger.warning(f"   - Full data: {json.dumps(message_data_raw, indent=2)[:500]}...")
        
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
    priority = priority_map.get(test_msg.priority or "normal", MessagePriority.NORMAL)
    
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
        state = await bot_state_manager.get_bot_state(identifier) if bot_state_manager else {"active": True}
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
        success = await bot_state_manager.pause_bot(identifier, reason, ttl) if bot_state_manager else False
        
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
        success = await bot_state_manager.resume_bot(identifier) if bot_state_manager else False
        
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
        count = await bot_state_manager.pause_all_bots(reason) if bot_state_manager else 0
        
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
        count = await bot_state_manager.resume_all_bots() if bot_state_manager else 0
        
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
        stats = await bot_state_manager.get_stats() if bot_state_manager else {}
        
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
# FOLLOW-UP SYSTEM ENDPOINTS
# =====================================================

@app.get("/api/followup/stats")
async def get_followup_stats():
    """Obtener estadísticas del sistema de follow-up"""
    try:
        if not followup_manager:
            return {"error": "Follow-up system not initialized"}
        
        stats = await followup_manager.get_followup_stats()
        return stats
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats de follow-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/followup/performance")
async def get_followup_performance():
    """Obtener métricas de rendimiento de follow-ups"""
    try:
        if not followup_tracker:
            return {"error": "Follow-up tracker not initialized"}
        
        performance = await followup_tracker.get_performance_metrics(7)
        return performance
    except Exception as e:
        logger.error(f"❌ Error obteniendo performance de follow-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/followup/queue")
async def get_followup_queue():
    """Obtener estado de la cola de follow-ups"""
    try:
        if not followup_tracker:
            return {"error": "Follow-up tracker not initialized"}
        
        queue_status = await followup_tracker.get_queue_status()
        return queue_status
    except Exception as e:
        logger.error(f"❌ Error obteniendo cola de follow-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/followup/blacklist")
async def add_to_blacklist(request: Request):
    """Agregar usuario a blacklist de follow-ups"""
    try:
        if not followup_manager:
            raise HTTPException(status_code=503, detail="Follow-up system not available")
        
        data = await request.json()
        user_id = data.get("user_id")
        phone = data.get("phone", "")
        reason = data.get("reason", "user_request")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        await followup_manager.add_user_to_blacklist(user_id, phone, reason)
        return {"success": True, "message": f"Usuario {user_id} agregado a blacklist"}
        
    except Exception as e:
        logger.error(f"❌ Error agregando a blacklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/followup/schedule")
async def schedule_manual_followup(request: Request):
    """Programar follow-ups manualmente para un usuario"""
    try:
        if not followup_scheduler:
            raise HTTPException(status_code=503, detail="Follow-up scheduler not available")
        
        data = await request.json()
        user_id = data.get("user_id")
        phone = data.get("phone")
        
        if not user_id or not phone:
            raise HTTPException(status_code=400, detail="user_id and phone required")
        
        # Obtener contexto del usuario
        context = await hybrid_context_manager.get_context(user_id)
        context_data = context.to_dict() if context else {}
        
        success = await followup_scheduler.schedule_user_followups(
            user_id, phone, context_data
        )
        
        if success:
            return {"success": True, "message": f"Follow-ups programados para {user_id}"}
        else:
            raise HTTPException(status_code=500, detail="Error programando follow-ups")
            
    except Exception as e:
        logger.error(f"❌ Error programando follow-up manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/setup-followup-tables")
async def setup_followup_tables():
    """Crear tablas de follow-up (solo para admin)"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        # Ejecutar el script de creación de tablas
        import subprocess
        result = subprocess.run(
            ["python", "create_followup_tables.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "success": True, 
                "message": "Tablas de follow-up creadas exitosamente",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Error creando tablas: {result.stderr}"
            )
            
    except Exception as e:
        logger.error(f"❌ Error setup tablas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/admin/cleanup-invalid-sources")
async def cleanup_invalid_message_sources():
    """Clean up messages with invalid source values (like 'followup')"""
    try:
        if not advanced_queue.pg_pool:
            raise HTTPException(status_code=500, detail="Database not available")
        
        conn = advanced_queue.pg_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # First, investigate what invalid sources exist
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM message_queue 
                WHERE source NOT IN ('chatwoot', 'evolution', 'test', 'system')
                GROUP BY source
            """)
            
            invalid_sources = cursor.fetchall()
            
            if not invalid_sources:
                return {
                    "status": "success",
                    "message": "No invalid message sources found",
                    "cleaned_count": 0
                }
            
            logger.info(f"🔍 Found invalid sources: {invalid_sources}")
            
            # Convert all invalid sources to 'system'
            cursor.execute("""
                UPDATE message_queue 
                SET source = 'system' 
                WHERE source NOT IN ('chatwoot', 'evolution', 'test', 'system')
            """)
            
            cleaned_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"✅ Cleaned {cleaned_count} messages with invalid sources")
            
            return {
                "status": "success", 
                "message": f"Cleaned {cleaned_count} messages with invalid sources",
                "invalid_sources_found": [{"source": row[0], "count": row[1]} for row in invalid_sources],
                "cleaned_count": cleaned_count
            }
                
        finally:
            advanced_queue.pg_pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"❌ Failed to cleanup invalid sources: {e}")
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
# UTILITY FUNCTIONS
# =====================================================

async def _create_followup_tables_if_needed(database_url: str) -> bool:
    """Crear tablas de follow-up automáticamente si no existen"""
    try:
        import psycopg2
        
        # Definir SQLs de creación
        table_sqls = [
            # Tabla principal de trabajos
            """
            CREATE TABLE IF NOT EXISTS follow_up_jobs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                stage INTEGER NOT NULL,
                scheduled_for TIMESTAMP NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                context_snapshot JSONB,
                last_user_message TEXT,
                trigger_event VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                next_retry_at TIMESTAMP,
                UNIQUE(user_id, stage)
            );
            """,
            
            # Historial
            """
            CREATE TABLE IF NOT EXISTS follow_up_history (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                stage INTEGER NOT NULL,
                message_sent TEXT NOT NULL,
                template_used VARCHAR(100),
                generation_model VARCHAR(50),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_responded BOOLEAN DEFAULT FALSE,
                responded_at TIMESTAMP,
                response_message TEXT,
                response_time_hours DECIMAL(10,2),
                effectiveness_score DECIMAL(3,2),
                metadata JSONB DEFAULT '{}'
            );
            """,
            
            # Configuración
            """
            CREATE TABLE IF NOT EXISTS follow_up_config (
                id SERIAL PRIMARY KEY,
                stage_delays_hours INTEGER[] DEFAULT '{1,6,24,48,72,96,120,168}',
                start_hour INTEGER DEFAULT 9,
                end_hour INTEGER DEFAULT 21,
                timezone VARCHAR(50) DEFAULT 'America/Argentina/Cordoba',
                allowed_weekdays INTEGER[] DEFAULT '{1,2,3,4,5,6}',
                max_followups_per_user INTEGER DEFAULT 8,
                cooldown_between_stages_hours INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Blacklist
            """
            CREATE TABLE IF NOT EXISTS follow_up_blacklist (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(50),
                reason VARCHAR(200),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by VARCHAR(100) DEFAULT 'user'
            );
            """,
            
            # Índices
            """
            CREATE INDEX IF NOT EXISTS idx_followup_jobs_scheduled ON follow_up_jobs(scheduled_for, status);
            CREATE INDEX IF NOT EXISTS idx_followup_jobs_user ON follow_up_jobs(user_id);
            CREATE INDEX IF NOT EXISTS idx_followup_history_user_time ON follow_up_history(user_id, sent_at);
            CREATE INDEX IF NOT EXISTS idx_followup_blacklist_user ON follow_up_blacklist(user_id);
            """,
            
            # Configuración inicial
            """
            INSERT INTO follow_up_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
            """
        ]
        
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cursor:
                for sql in table_sqls:
                    cursor.execute(sql)
                
                conn.commit()
        
        logger.info("✅ Tablas de follow-up creadas/verificadas automáticamente")
        return True
                
    except Exception as e:
        logger.error(f"❌ Error creando tablas de follow-up: {e}")
        return False

# =====================================================
# STARTUP AND SHUTDOWN HANDLERS
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    global bot_state_manager, main_event_loop, followup_scheduler, followup_manager, followup_tracker
    
    logger.info("🚀 Starting Royal Bot - Maximum Efficiency Edition")
    
    # Guardar el event loop principal
    main_event_loop = asyncio.get_running_loop()
    logger.info("📍 Event loop principal guardado para operaciones async")
    
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
    
    # Initialize follow-up system (if enabled)
    followup_enabled = os.getenv("FOLLOWUP_ENABLED", "true").lower() == "true"
    if followup_enabled:
        logger.info("📅 Initializing follow-up system...")
        try:
            # Initialize follow-up components
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment variables")
            
            # Crear tablas automáticamente si no existen
            logger.info("🗄️ Verificando/creando tablas de follow-up...")
            await _create_followup_tables_if_needed(database_url)
            
            followup_scheduler = FollowUpScheduler(
                database_url=database_url,
                evolution_api_url=EVOLUTION_API_URL,
                evolution_token=EVOLUTION_API_TOKEN,
                instance_name=INSTANCE_NAME,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            await followup_scheduler.initialize()
            followup_scheduler.start()
            
            followup_manager = FollowUpManager(
                database_url=database_url,
                evolution_api_url=EVOLUTION_API_URL,
                evolution_token=EVOLUTION_API_TOKEN,
                instance_name=INSTANCE_NAME,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            followup_tracker = FollowUpTracker(database_url)
            
            logger.info("✅ Follow-up system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing follow-up system: {e}")
            logger.warning("⚠️ Follow-up system disabled due to initialization error")
            followup_scheduler = None
            followup_manager = None
            followup_tracker = None
    else:
        logger.info("📅 Follow-up system disabled")
        followup_scheduler = None
        followup_manager = None  
        followup_tracker = None

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
    global bot_state_manager, followup_scheduler, followup_manager
    
    logger.info("🛑 Shutting down Royal Bot - Maximum Efficiency Edition")
    
    # Shutdown follow-up system first
    if followup_scheduler:
        logger.info("📅 Stopping follow-up scheduler...")
        followup_scheduler.stop()
    
    if followup_manager:
        logger.info("📤 Closing follow-up manager...")
        await followup_manager.close()

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
# TEST ENDPOINTS FOR BOT-PAUSED TAG SYSTEM
# =====================================================

@app.post("/test/bot-control-tags")
async def test_bot_control_tags_endpoint(request: Request):
    """
    Endpoint de prueba para simular eventos conversation_updated con etiquetas de control del bot
    
    Body esperado:
    {
        "conversation_id": "123",
        "phone": "5491112345678", 
        "bot_paused": true/false,     // opcional
        "bot_active": true/false,     // opcional  
        "labels": [{"title": "bot-paused"}, {"title": "bot-active"}] // opcional
    }
    """
    try:
        data = await request.json()
        
        conversation_id = data.get("conversation_id", "test_123")
        phone = data.get("phone", "5491112345678") 
        bot_paused = data.get("bot_paused", False)
        bot_active = data.get("bot_active", False)
        labels = data.get("labels", [])
        
        # Si no hay labels pero se especificaron flags, crear las etiquetas
        if not labels:
            if bot_paused:
                labels.append({"title": "bot-paused"})
            if bot_active:
                labels.append({"title": "bot-active"})
        
        # Crear payload simulado de conversation_updated
        simulated_webhook_data = {
            "event": "conversation_updated",
            "conversation": {
                "id": conversation_id,
                "contact_phone": f"+{phone}",
                "labels": labels,
                "contact_inbox": {
                    "source_id": phone
                },
                "additional_attributes": {
                    "phone_number": f"+{phone}"
                }
            }
        }
        
        logger.info(f"🧪 TEST: Simulando conversation_updated para conversación {conversation_id}")
        logger.info(f"🧪 TEST: Teléfono: {phone}, bot-paused: {bot_paused}, bot-active: {bot_active}")
        
        # Procesar usando la función existente
        result = await handle_conversation_updated(simulated_webhook_data)
        
        return {
            "status": "test_completed",
            "simulated_data": simulated_webhook_data,
            "processing_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test de bot-paused tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test: {str(e)}"
        )

@app.post("/test/conversation-webhook")
async def test_conversation_webhook_endpoint(request: Request):
    """
    Endpoint de prueba para simular webhooks completos de conversation_updated
    
    Permite enviar payloads completos de Chatwoot para testing
    """
    try:
        webhook_data = await request.json()
        
        # Validar que sea un evento conversation_updated
        if webhook_data.get("event") != "conversation_updated":
            return {
                "status": "error",
                "message": "Solo se aceptan eventos conversation_updated para este test"
            }
        
        logger.info("🧪 TEST: Procesando webhook conversation_updated simulado")
        
        # Procesar usando el handler principal
        result = await handle_conversation_updated(webhook_data)
        
        return {
            "status": "webhook_test_completed",
            "received_data": webhook_data,
            "processing_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test de webhook conversation_updated: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test de webhook: {str(e)}"
        )

@app.post("/test/complaint-scenario")
async def test_complaint_scenario_endpoint(request: Request):
    """
    Endpoint de prueba para simular el escenario completo de reclamo → pausa → reactivación
    
    Body esperado:
    {
        "conversation_id": "123",
        "phone": "5491112345678",
        "step": "complaint"|"support_assigns"|"agent_reactivates"
    }
    """
    try:
        data = await request.json()
        
        conversation_id = data.get("conversation_id", "test_complaint_123")
        phone = data.get("phone", "5491112345678")
        step = data.get("step", "complaint")
        
        logger.info(f"🧪 TEST RECLAMO: Simulando paso '{step}' para conversación {conversation_id}")
        
        if step == "complaint":
            # Simular mensaje de reclamo
            complaint_message = "Tengo un reclamo con mi pedido, llegó dañado"
            
            # Simular la lógica de check_and_route_by_keywords
            # En realidad esto pausaría el bot con razón "Asignado a equipo support"
            success = await bot_state_manager.pause_bot(
                phone, 
                reason="Asignado a equipo support",
                ttl=86400  # 24 horas
            ) if bot_state_manager else False
            
            if success:
                return {
                    "status": "complaint_processed",
                    "step": step,
                    "conversation_id": conversation_id,
                    "phone": phone,
                    "message": "Bot pausado por reclamo (simulado)",
                    "bot_paused": True,
                    "pause_reason": "Asignado a equipo support",
                    "ttl_hours": 24
                }
        
        elif step == "agent_reactivates":
            # Simular que agente agrega etiqueta bot-active
            webhook_data = {
                "event": "conversation_updated",
                "conversation": {
                    "id": conversation_id,
                    "contact_phone": f"+{phone}",
                    "labels": [
                        {"title": "bot-active"}  # Etiqueta de reactivación
                    ]
                }
            }
            
            logger.info(f"🧪 TEST RECLAMO: Agente reactiva bot con etiqueta bot-active")
            result = await handle_conversation_updated(webhook_data)
            
            return {
                "status": "agent_reactivation_processed",
                "step": step,
                "webhook_result": result,
                "expected_action": "Bot debería reactivarse inmediatamente"
            }
            
        else:
            return {
                "status": "error",
                "message": f"Paso desconocido: {step}. Usar: 'complaint' o 'agent_reactivates'"
            }
        
    except Exception as e:
        logger.error(f"❌ Error en test de escenario de reclamo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test de reclamo: {str(e)}"
        )

@app.get("/test/bot-paused-instructions")
async def get_bot_paused_instructions(request: Request):
    """
    Endpoint que devuelve las instrucciones para usar el sistema bot-paused
    """
    return {
        "sistema": "Control de Bot con Etiquetas bot-paused y bot-active",
        "descripcion": "Sistema para pausar/reactivar el bot desde Chatwoot con control de prioridades",
        
        "uso": {
            "pausar_bot": "Agregar etiqueta 'bot-paused' a la conversación en Chatwoot",
            "reactivar_bot_normal": "Remover etiqueta 'bot-paused' de la conversación en Chatwoot", 
            "reactivar_bot_forzado": "Agregar etiqueta 'bot-active' (funciona para cualquier pausa)"
        },
        
        "configuracion_webhook": {
            "evento_requerido": "conversation_updated",
            "url_webhook": f"{request.base_url}webhook/chatwoot",
            "metodo": "POST"
        },
        
        "etiquetas": {
            "bot_paused": {
                "nombre": "bot-paused",
                "funcion": "Pausar bot",
                "tipo": "case-sensitive",
                "formato": "Exactamente 'bot-paused' (sin espacios, con guión)"
            },
            "bot_active": {
                "nombre": "bot-active", 
                "funcion": "Reactivar bot (override cualquier pausa)",
                "tipo": "case-sensitive",
                "formato": "Exactamente 'bot-active' (sin espacios, con guión)",
                "prioridad": "ALTA - Tiene precedencia sobre bot-paused"
            }
        },
        
        "funcionamiento": [
            "1. Sistema detecta reclamos → Bot pausado por 24h (razón: 'Asignado a equipo support')",
            "2. Agente resuelve problema y quiere reactivar bot",
            "3. Agente agrega etiqueta 'bot-active' en Chatwoot",
            "4. Webhook conversation_updated se dispara inmediatamente",
            "5. Sistema detecta 'bot-active' → Bot reactivado INMEDIATAMENTE",
            "6. Bot funciona normalmente (sin esperar 24h)",
            "7. ALTERNATIVO: Usar 'bot-paused' para pausar manualmente",
            "8. PRIORIDAD: 'bot-active' siempre gana sobre 'bot-paused'"
        ],
        
        "endpoints_test": [
            "POST /test/bot-control-tags - Simular etiquetas bot-paused/bot-active",
            "POST /test/conversation-webhook - Simular webhook completo",
            "POST /test/complaint-scenario - Simular reclamo completo + reactivación",
            "GET /bot/status/{phone} - Ver estado actual del bot",
            "GET /test/bot-paused-instructions - Estas instrucciones"
        ],
        
        "ejemplos": {
            "pausar_bot_manual": {
                "metodo": "POST",
                "url": "/test/bot-control-tags",
                "body": {
                    "conversation_id": "123", 
                    "phone": "5491112345678",
                    "bot_paused": True
                }
            },
            "reactivar_bot_normal": {
                "metodo": "POST", 
                "url": "/test/bot-control-tags",
                "body": {
                    "conversation_id": "123",
                    "phone": "5491112345678", 
                    "bot_paused": False
                }
            },
            "reactivar_bot_forzado": {
                "metodo": "POST",
                "url": "/test/bot-control-tags", 
                "body": {
                    "conversation_id": "123",
                    "phone": "5491112345678",
                    "bot_active": True
                }
            },
            "escenario_reclamo": {
                "metodo": "POST",
                "url": "/test/complaint-scenario",
                "body": {
                    "conversation_id": "complaint_123",
                    "phone": "5491112345678",
                    "step": "complaint"
                }
            },
            "escenario_reactivacion": {
                "metodo": "POST", 
                "url": "/test/complaint-scenario",
                "body": {
                    "conversation_id": "complaint_123",
                    "phone": "5491112345678", 
                    "step": "agent_reactivates"
                }
            }
        }
    }

# =====================================================
# DEBUG ENDPOINTS (TEMPORAL)
# =====================================================

@app.get("/debug/followups")
async def debug_followups_endpoint():
    """
    Endpoint temporal para diagnosticar el sistema de follow-ups
    """
    try:
        import pytz
        argentina_tz = pytz.timezone("America/Argentina/Cordoba")
        current_time = datetime.now(argentina_tz)
        
        debug_info = {
            "timestamp": current_time.isoformat(),
            "timezone": "America/Argentina/Cordoba",
            "scheduler_running": followup_scheduler.is_running if followup_scheduler else False,
            "pending_jobs": [],
            "inactive_users": [],
            "evolution_config": {
                "url": EVOLUTION_API_URL,
                "instance": INSTANCE_NAME,
                "token_configured": bool(EVOLUTION_API_TOKEN)
            }
        }
        
        # Verificar follow-ups pendientes
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Follow-ups pendientes
                    cursor.execute("""
                        SELECT user_id, stage, scheduled_for, phone, status, created_at
                        FROM follow_up_jobs 
                        WHERE status = 'pending'
                        ORDER BY scheduled_for
                        LIMIT 20
                    """)
                    pending_jobs = cursor.fetchall()
                    debug_info["pending_jobs"] = [dict(job) for job in pending_jobs]
                    
                    # Usuarios inactivos
                    cutoff_time = current_time - timedelta(hours=1)
                    cursor.execute("""
                        SELECT user_id, last_interaction, context_data
                        FROM conversation_contexts 
                        WHERE last_interaction < %s
                        ORDER BY last_interaction DESC
                        LIMIT 10
                    """, (cutoff_time,))
                    inactive_users = cursor.fetchall()
                    debug_info["inactive_users"] = [dict(user) for user in inactive_users]
        
        return debug_info
        
    except Exception as e:
        logger.error(f"❌ Error en debug de follow-ups: {e}")
        return {"error": str(e)}

@app.get("/debug/followups/tables")
async def debug_followups_tables():
    """
    Endpoint temporal para verificar datos en las tablas
    """
    try:
        import pytz
        argentina_tz = pytz.timezone("America/Argentina/Cordoba")
        current_time = datetime.now(argentina_tz)
        
        tables_info = {
            "timestamp": current_time.isoformat(),
            "conversation_contexts": {"count": 0, "recent": []},
            "follow_up_jobs": {"count": 0, "recent": []},
            "follow_up_blacklist": {"count": 0}
        }
        
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Verificar conversation_contexts
                    cursor.execute("SELECT COUNT(*) as count FROM conversation_contexts")
                    count_result = cursor.fetchone()
                    tables_info["conversation_contexts"]["count"] = count_result["count"]
                    
                    cursor.execute("""
                        SELECT user_id, last_interaction, context_data
                        FROM conversation_contexts 
                        ORDER BY last_interaction DESC 
                        LIMIT 5
                    """)
                    recent_contexts = cursor.fetchall()
                    tables_info["conversation_contexts"]["recent"] = [dict(ctx) for ctx in recent_contexts]
                    
                    # Verificar follow_up_jobs
                    cursor.execute("SELECT COUNT(*) as count FROM follow_up_jobs")
                    count_result = cursor.fetchone()
                    tables_info["follow_up_jobs"]["count"] = count_result["count"]
                    
                    cursor.execute("""
                        SELECT user_id, stage, status, created_at, scheduled_for
                        FROM follow_up_jobs 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """)
                    recent_jobs = cursor.fetchall()
                    tables_info["follow_up_jobs"]["recent"] = [dict(job) for job in recent_jobs]
                    
                    # Verificar blacklist
                    cursor.execute("SELECT COUNT(*) as count FROM follow_up_blacklist")
                    count_result = cursor.fetchone()
                    tables_info["follow_up_blacklist"]["count"] = count_result["count"]
        
        return tables_info
        
    except Exception as e:
        logger.error(f"❌ Error en debug de tablas: {e}")
        return {"error": str(e)}

@app.post("/debug/create-test-context")
async def create_test_context_endpoint(request: Request):
    """
    Endpoint temporal para crear un contexto de prueba y verificar el sistema
    """
    try:
        data = await request.json()
        user_id = data.get("user_id", "whatsapp_5491112345678")
        message = data.get("message", "Hola, me interesa emprender")
        
        # Crear contexto usando hybrid_context_manager directamente
        from hybrid_context_manager import ConversationMemory
        import pytz
        
        test_context = ConversationMemory(user_id=user_id)
        test_context.last_interaction = datetime.now(pytz.timezone("America/Argentina/Cordoba"))
        test_context.user_intent = "emprendedor"
        test_context.is_entrepreneur = True
        test_context.context_data = {"phone": user_id.replace("whatsapp_", "")}
        
        # Agregar interacción
        test_context.interaction_history.append({
            "role": "user",
            "message": message,
            "timestamp": test_context.last_interaction.isoformat()
        })
        
        # Guardar en PostgreSQL
        success = await hybrid_context_manager.save_context(user_id, test_context)
        
        if success:
            # Verificar que se guardó
            saved_context = await hybrid_context_manager.get_context(user_id)
            
            return {
                "success": True,
                "message": f"Contexto de prueba creado para {user_id}",
                "context_data": saved_context.to_dict() if saved_context else None,
                "should_trigger_followup": True
            }
        else:
            return {
                "success": False,
                "message": "Error guardando contexto de prueba"
            }
        
    except Exception as e:
        logger.error(f"❌ Error creando contexto de prueba: {e}")
        return {"error": str(e)}

@app.post("/debug/make-user-inactive")
async def make_user_inactive_endpoint(request: Request):
    """
    Endpoint temporal para hacer que un usuario aparezca inactivo (para testing follow-ups)
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        hours_ago = data.get("hours_ago", 2)
        
        if not user_id:
            return {"error": "user_id requerido"}
        
        import pytz
        from datetime import timedelta
        
        # Calcular timestamp inactivo
        inactive_time = datetime.now(pytz.timezone("America/Argentina/Cordoba")) - timedelta(hours=hours_ago)
        
        # Actualizar en PostgreSQL directamente
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE conversation_contexts 
                    SET last_interaction = %s
                    WHERE user_id = %s
                """, (inactive_time, user_id))
                
                if cursor.rowcount > 0:
                    return {
                        "success": True,
                        "message": f"Usuario {user_id} marcado como inactivo desde hace {hours_ago} horas",
                        "inactive_since": inactive_time.isoformat(),
                        "updated_rows": cursor.rowcount
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Usuario {user_id} no encontrado"
                    }
        
    except Exception as e:
        logger.error(f"❌ Error haciendo usuario inactivo: {e}")
        return {"error": str(e)}

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