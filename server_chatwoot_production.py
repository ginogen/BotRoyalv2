#!/usr/bin/env python3
"""
🤖 ROYAL BOT - SERVIDOR PRINCIPAL CON CHATWOOT
Servidor optimizado para múltiples conversaciones concurrentes
Replicando funcionalidades esenciales del sistema Node.js
"""

import asyncio
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import hmac
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import PriorityQueue, Queue, Empty
import signal
import sys

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Imports del bot
from royal_agents import run_contextual_conversation_sync
from database_persistent import DatabaseManager

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# ================================
# CONFIGURACIÓN PRINCIPAL
# ================================

# Servidor
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Chatwoot
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN") 
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")
CHATWOOT_WEBHOOK_SECRET = os.getenv("CHATWOOT_WEBHOOK_SECRET")

# Evolution API (WhatsApp)
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_TOKEN = os.getenv("EVOLUTION_API_TOKEN")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "F1_Retencion")

# Workers y concurrencia
WORKER_POOL_SIZE = int(os.getenv("WORKER_POOL_SIZE", 3))
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", 5))
MESSAGE_BUFFER_TIMEOUT = int(os.getenv("MESSAGE_BUFFER_TIMEOUT", 3000)) / 1000  # Convertir a segundos
MESSAGE_COOLDOWN = int(os.getenv("MESSAGE_COOLDOWN", 1000)) / 1000

# ================================
# ESTRUCTURAS DE DATOS
# ================================

@dataclass
class MessageData:
    """Estructura para mensajes en cola"""
    user_id: str
    message: str
    source: str  # 'chatwoot' o 'evolution'
    conversation_id: Optional[str] = None
    phone: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: int = 1  # 1=alta, 2=normal, 3=baja
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class UserState:
    """Estado de usuario para gestión de concurrencia"""
    last_message_time: float = 0
    is_processing: bool = False
    message_count: int = 0
    processed_messages: set = field(default_factory=set)

class PriorityMessageQueue:
    """Cola de prioridades thread-safe para mensajes"""
    
    def __init__(self):
        self.queue = PriorityQueue()
        self.user_states: Dict[str, UserState] = defaultdict(UserState)
        self.lock = threading.Lock()
    
    def add_message(self, message_data: MessageData) -> bool:
        """Agrega mensaje a la cola si no es duplicado"""
        with self.lock:
            user_state = self.user_states[message_data.user_id]
            
            # Verificar duplicados usando ID único del mensaje + contenido
            message_key = f"{message_data.message_id}-{hash(message_data.message)}"
            
            if message_key in user_state.processed_messages:
                logger.warning(f"🔄 Mensaje duplicado ignorado para {message_data.user_id}")
                return False
            
            # Agregar a procesados
            user_state.processed_messages.add(message_key)
            
            # Limpiar mensajes antiguos (mantener solo últimos 10)
            if len(user_state.processed_messages) > 10:
                old_messages = list(user_state.processed_messages)[:5]
                for old_msg in old_messages:
                    user_state.processed_messages.discard(old_msg)
            
            # Determinar prioridad
            now = time.time()
            if user_state.is_processing:
                message_data.priority = 2  # Normal si ya está procesando
            elif now - user_state.last_message_time < MESSAGE_COOLDOWN:
                message_data.priority = 3  # Baja si es muy seguido
            else:
                message_data.priority = 1  # Alta prioridad
            
            # Agregar a cola
            self.queue.put((message_data.priority, message_data.timestamp, message_data))
            user_state.message_count += 1
            
            logger.info(f"📥 Mensaje agregado a cola: {message_data.user_id} (prioridad {message_data.priority})")
            return True
    
    def get_next_message(self, timeout: float = 1.0) -> Optional[MessageData]:
        """Obtiene siguiente mensaje de la cola"""
        try:
            priority, timestamp, message_data = self.queue.get(timeout=timeout)
            return message_data
        except Empty:
            return None
    
    def mark_user_processing(self, user_id: str, processing: bool):
        """Marca usuario como en procesamiento"""
        with self.lock:
            self.user_states[user_id].is_processing = processing
            if processing:
                self.user_states[user_id].last_message_time = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas de la cola"""
        with self.lock:
            return {
                "queue_size": self.queue.qsize(),
                "active_users": len([u for u in self.user_states.values() if u.is_processing]),
                "total_users": len(self.user_states),
                "total_processed": sum(u.message_count for u in self.user_states.values())
            }

class WorkerPool:
    """Pool de workers para procesamiento paralelo"""
    
    def __init__(self, pool_size: int):
        self.pool_size = pool_size
        self.executor = ThreadPoolExecutor(max_workers=pool_size)
        self.active_workers = 0
        self.total_processed = 0
        self.lock = threading.Lock()
    
    async def process_message(self, message_data: MessageData) -> Dict[str, Any]:
        """Procesa mensaje usando el pool de workers"""
        with self.lock:
            self.active_workers += 1
        
        try:
            loop = asyncio.get_event_loop()
            
            # Ejecutar procesamiento en worker thread
            result = await loop.run_in_executor(
                self.executor,
                self._process_message_sync,
                message_data
            )
            
            with self.lock:
                self.total_processed += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en worker procesando mensaje: {e}")
            return {
                "success": False,
                "response": "Hubo un problema técnico. Un agente humano te contactará pronto.",
                "error": str(e)
            }
        finally:
            with self.lock:
                self.active_workers -= 1
    
    def _process_message_sync(self, message_data: MessageData) -> Dict[str, Any]:
        """Procesamiento sincrónico del mensaje"""
        try:
            logger.info(f"🤖 Worker procesando: {message_data.user_id} - {message_data.message[:50]}...")
            
            start_time = time.time()
            
            # Procesar con el bot
            response = run_contextual_conversation_sync(message_data.user_id, message_data.message)
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Procesamiento completado en {processing_time:.2f}s")
            
            return {
                "success": True,
                "response": response,
                "processing_time": processing_time,
                "worker_id": threading.current_thread().name
            }
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento: {e}")
            return {
                "success": False,
                "response": "Hubo un problema procesando tu mensaje. Por favor, intenta de nuevo.",
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del pool"""
        with self.lock:
            return {
                "pool_size": self.pool_size,
                "active_workers": self.active_workers,
                "idle_workers": self.pool_size - self.active_workers,
                "total_processed": self.total_processed,
                "utilization": (self.active_workers / self.pool_size) * 100
            }

# ================================
# SERVICIOS PRINCIPALES  
# ================================

class ChatwootService:
    """Servicio para comunicación con Chatwoot"""
    
    def __init__(self):
        self.api_url = CHATWOOT_API_URL
        self.api_token = CHATWOOT_API_TOKEN
        self.account_id = CHATWOOT_ACCOUNT_ID
        self.session = None
        
    async def initialize(self):
        """Inicializar servicio"""
        self.session = httpx.AsyncClient(timeout=30.0)
        
        if self.api_url and self.api_token:
            try:
                await self.test_connection()
                logger.info("✅ Chatwoot service inicializado")
            except Exception as e:
                logger.warning(f"⚠️ Problema conectando con Chatwoot: {e}")
    
    async def test_connection(self) -> bool:
        """Probar conexión con Chatwoot"""
        if not all([self.api_url, self.api_token, self.account_id]):
            return False
            
        try:
            headers = {"api_access_token": self.api_token}
            response = await self.session.get(
                f"{self.api_url}/api/v1/accounts/{self.account_id}/conversations",
                headers=headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Error probando Chatwoot: {e}")
            return False
    
    async def send_message(self, conversation_id: str, message: str) -> bool:
        """Enviar mensaje a conversación de Chatwoot"""
        if not all([self.api_url, self.api_token, self.account_id]):
            logger.warning("Chatwoot no configurado")
            return False
            
        try:
            headers = {
                "api_access_token": self.api_token,
                "Content-Type": "application/json"
            }
            
            payload = {
                "content": message,
                "message_type": "outgoing"
            }
            
            response = await self.session.post(
                f"{self.api_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"📤 Mensaje enviado a Chatwoot conversación {conversation_id}")
                return True
            else:
                logger.error(f"❌ Error Chatwoot: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando a Chatwoot: {e}")
            return False
    
    def extract_phone_from_conversation(self, conversation_data: Dict) -> Optional[str]:
        """Extraer número de teléfono de datos de conversación"""
        try:
            # Intentar diferentes ubicaciones del número
            meta = conversation_data.get("meta", {})
            sender = meta.get("sender", {})
            
            phone = sender.get("phone_number") or sender.get("identifier", "")
            
            # Handle different number formats
            if phone:
                if "@lid" in phone:
                    # Meta Ads Lead ID format
                    logger.info(f"📱 Usuario de Meta Ads detectado en Chatwoot: {phone}")
                    return phone.replace("@lid", "")
                elif "@s.whatsapp.net" in phone:
                    # Standard WhatsApp format
                    return phone.replace("@s.whatsapp.net", "")
                elif "@g.us" in phone:
                    # Group format
                    logger.info(f"📱 Mensaje de grupo detectado en Chatwoot: {phone}")
                    return phone.replace("@g.us", "")
            
            return phone if phone else None
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo teléfono: {e}")
            return None

class EvolutionService:
    """Servicio para comunicación con Evolution API (WhatsApp)"""
    
    def __init__(self):
        self.api_url = EVOLUTION_API_URL
        self.api_token = EVOLUTION_API_TOKEN
        self.instance_name = INSTANCE_NAME
        self.session = None
        
    async def initialize(self):
        """Inicializar servicio"""
        self.session = httpx.AsyncClient(timeout=30.0)
        logger.info("✅ Evolution service inicializado")
    
    async def send_message(self, phone: str, message: str) -> bool:
        """Enviar mensaje vía WhatsApp"""
        if not all([self.api_url, self.api_token, self.instance_name]):
            logger.warning("Evolution API no configurada")
            return False
            
        try:
            headers = {
                "apikey": self.api_token,
                "Content-Type": "application/json"
            }
            
            payload = {
                "number": phone,
                "textMessage": {
                    "text": message
                }
            }
            
            response = await self.session.post(
                f"{self.api_url}/message/sendText/{self.instance_name}",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"📤 Mensaje enviado via WhatsApp a {phone}")
                return True
            else:
                logger.error(f"❌ Error Evolution API: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando via Evolution: {e}")
            return False

# ================================
# INSTANCIAS GLOBALES
# ================================

# Inicializar FastAPI
app = FastAPI(
    title="Royal Bot Chatwoot Production",
    description="Bot optimizado para múltiples conversaciones con Chatwoot",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servicios y sistemas globales
message_queue = PriorityMessageQueue()
worker_pool = WorkerPool(WORKER_POOL_SIZE)
chatwoot_service = ChatwootService()
evolution_service = EvolutionService()
db_manager = None

# Variables de control
processing_active = True
stats = {
    "messages_processed": 0,
    "start_time": time.time(),
    "errors": 0
}

# ================================
# PROCESADOR DE MENSAJES PRINCIPAL
# ================================

async def message_processor():
    """Procesador principal de la cola de mensajes"""
    logger.info("🚀 Procesador de mensajes iniciado")
    
    while processing_active:
        try:
            # Obtener siguiente mensaje
            message_data = message_queue.get_next_message(timeout=1.0)
            
            if not message_data:
                continue
            
            # Verificar límite de usuarios concurrentes
            queue_stats = message_queue.get_stats()
            if queue_stats["active_users"] >= MAX_CONCURRENT_USERS:
                # Reencolar con menor prioridad
                message_data.priority = 3
                message_queue.queue.put((message_data.priority, time.time(), message_data))
                await asyncio.sleep(0.5)
                continue
            
            # Marcar usuario como en procesamiento
            message_queue.mark_user_processing(message_data.user_id, True)
            
            try:
                # Procesar mensaje con worker pool
                result = await worker_pool.process_message(message_data)
                
                if result["success"]:
                    # Enviar respuesta según el origen
                    if message_data.source == "chatwoot" and message_data.conversation_id:
                        await chatwoot_service.send_message(
                            message_data.conversation_id, 
                            result["response"]
                        )
                    elif message_data.source == "evolution" and message_data.phone:
                        await evolution_service.send_message(
                            message_data.phone, 
                            result["response"]
                        )
                    
                    stats["messages_processed"] += 1
                    
                    # Guardar en base de datos si está disponible
                    if db_manager:
                        try:
                            db_manager.save_conversation(
                                message_data.user_id,
                                message_data.message,
                                result["response"],
                                str(uuid.uuid4())
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ Error guardando en BD: {e}")
                else:
                    stats["errors"] += 1
                    logger.error(f"❌ Error procesando mensaje: {result.get('error', 'Unknown')}")
                    
            finally:
                # Liberar usuario
                message_queue.mark_user_processing(message_data.user_id, False)
                await asyncio.sleep(0.1)  # Pequeña pausa para evitar spam
                
        except Exception as e:
            logger.error(f"❌ Error en procesador de mensajes: {e}")
            await asyncio.sleep(1.0)

# ================================
# MODELOS DE DATOS
# ================================

class ChatwootWebhook(BaseModel):
    event: str
    message_type: Optional[str] = None
    conversation: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    content: Optional[str] = None

class EvolutionWebhook(BaseModel):
    data: Dict[str, Any]

class TestMessage(BaseModel):
    message: str
    user_id: Optional[str] = "test_user"

# ================================
# UTILIDADES
# ================================

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verificar firma del webhook"""
    if not CHATWOOT_WEBHOOK_SECRET:
        return True
        
    expected = hmac.new(
        CHATWOOT_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)

# ================================
# ENDPOINTS
# ================================

@app.get("/")
async def root():
    """Endpoint principal"""
    uptime = time.time() - stats["start_time"]
    
    return {
        "service": "Royal Bot Chatwoot Production",
        "version": "2.0.0",
        "status": "active",
        "uptime_seconds": uptime,
        "features": [
            "✅ Conexión bidireccional con Chatwoot",
            "✅ Sistema de workers paralelos",
            "✅ Cola de prioridades para mensajes", 
            "✅ Gestión de concurrencia optimizada",
            "✅ Rate limiting y detección de duplicados",
            "✅ Integration con Evolution API (WhatsApp)"
        ],
        "stats": {
            **stats,
            "queue": message_queue.get_stats(),
            "workers": worker_pool.get_stats()
        }
    }

@app.get("/health")
async def health_check():
    """Health check"""
    chatwoot_ok = await chatwoot_service.test_connection()
    
    return {
        "status": "healthy",
        "services": {
            "chatwoot": "connected" if chatwoot_ok else "disconnected",
            "evolution": "configured" if all([EVOLUTION_API_URL, EVOLUTION_API_TOKEN]) else "not_configured",
            "database": "connected" if db_manager else "not_configured"
        },
        "workers": worker_pool.get_stats(),
        "queue": message_queue.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    """Webhook para recibir mensajes de Chatwoot"""
    try:
        # Verificar firma si está configurada
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        if CHATWOOT_WEBHOOK_SECRET and not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Firma inválida")
        
        data = await request.json()
        
        # Procesar solo mensajes entrantes de contactos
        if (data.get("event") == "message_created" and 
            data.get("message_type") == "incoming" and
            data.get("sender", {}).get("type") == "contact"):
            
            conversation = data.get("conversation", {})
            content = data.get("content", "").strip()
            
            if content and conversation.get("id"):
                # Extraer información del contacto
                contact_id = data.get("sender", {}).get("id")
                phone = chatwoot_service.extract_phone_from_conversation(conversation)
                
                # Crear mensaje para la cola
                message_data = MessageData(
                    user_id=f"chatwoot_{contact_id}",
                    message=content,
                    source="chatwoot",
                    conversation_id=str(conversation["id"]),
                    phone=phone
                )
                
                # Agregar a cola
                if message_queue.add_message(message_data):
                    logger.info(f"📥 Mensaje de Chatwoot agregado a cola: {contact_id}")
                
        return {"status": "received", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Chatwoot: {e}")
        raise HTTPException(status_code=500, detail="Error procesando webhook")

@app.post("/webhook/evolution")  
async def evolution_webhook(request: Request):
    """Webhook para recibir mensajes de Evolution API"""
    try:
        data = await request.json()
        
        # Extraer mensaje y datos
        message_data_raw = data.get("data", {})
        message_content = message_data_raw.get("message", {}).get("conversation", "").strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        if message_content and from_number:
            # Crear mensaje para la cola
            message_data = MessageData(
                user_id=f"whatsapp_{from_number}",
                message=message_content,
                source="evolution",
                phone=from_number
            )
            
            # Agregar a cola
            if message_queue.add_message(message_data):
                logger.info(f"📥 Mensaje de WhatsApp agregado a cola: {from_number}")
        
        return {"status": "received", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Evolution: {e}")
        raise HTTPException(status_code=500, detail="Error procesando webhook")

@app.post("/test/message")
async def test_message(test_msg: TestMessage):
    """Endpoint para probar el bot directamente"""
    try:
        message_data = MessageData(
            user_id=test_msg.user_id,
            message=test_msg.message,
            source="test",
            priority=1  # Alta prioridad para tests
        )
        
        # Procesar directamente sin cola para respuesta inmediata
        result = await worker_pool.process_message(message_data)
        
        return {
            "status": "success" if result["success"] else "error",
            "response": result["response"],
            "user_id": test_msg.user_id,
            "processing_time": result.get("processing_time", 0),
            "worker_id": result.get("worker_id", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test message: {e}")
        raise HTTPException(status_code=500, detail="Error procesando mensaje de prueba")

@app.get("/stats")
async def get_stats():
    """Estadísticas detalladas del sistema"""
    uptime = time.time() - stats["start_time"]
    
    return {
        "system": {
            "uptime_seconds": uptime,
            "uptime_formatted": f"{uptime//3600:.0f}h {(uptime%3600)//60:.0f}m",
            "messages_per_minute": (stats["messages_processed"] / (uptime / 60)) if uptime > 0 else 0,
            "error_rate": (stats["errors"] / max(stats["messages_processed"], 1)) * 100
        },
        "processing": {
            **stats,
            "queue": message_queue.get_stats(),
            "workers": worker_pool.get_stats()
        },
        "configuration": {
            "worker_pool_size": WORKER_POOL_SIZE,
            "max_concurrent_users": MAX_CONCURRENT_USERS,
            "message_buffer_timeout": MESSAGE_BUFFER_TIMEOUT,
            "message_cooldown": MESSAGE_COOLDOWN
        },
        "services": {
            "chatwoot_configured": bool(all([CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID])),
            "evolution_configured": bool(all([EVOLUTION_API_URL, EVOLUTION_API_TOKEN])),
            "database_available": bool(db_manager)
        }
    }

@app.post("/admin/clear-queue")
async def clear_queue():
    """Limpiar cola de mensajes (admin)"""
    global message_queue
    message_queue = PriorityMessageQueue()
    
    return {
        "status": "success",
        "message": "Cola de mensajes limpiada",
        "timestamp": datetime.now().isoformat()
    }

# ================================
# INICIALIZACIÓN Y STARTUP
# ================================

@app.on_event("startup")
async def startup_event():
    """Inicialización del servidor"""
    global db_manager, processing_active
    
    logger.info("🚀 Iniciando Royal Bot Chatwoot Production...")
    
    # Inicializar base de datos
    try:
        db_manager = DatabaseManager()
        logger.info(f"✅ Base de datos inicializada: {db_manager.db_type}")
    except Exception as e:
        logger.warning(f"⚠️ Base de datos no disponible: {e}")
    
    # Inicializar servicios
    await chatwoot_service.initialize()
    await evolution_service.initialize()
    
    # Iniciar procesador de mensajes
    processing_active = True
    asyncio.create_task(message_processor())
    
    logger.info("✅ Servidor completamente inicializado")
    logger.info(f"📊 Configuración: {WORKER_POOL_SIZE} workers, {MAX_CONCURRENT_USERS} usuarios concurrentes")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar"""
    global processing_active
    
    logger.info("🛑 Cerrando servidor...")
    processing_active = False
    
    # Cerrar sesiones HTTP
    if chatwoot_service.session:
        await chatwoot_service.session.aclose()
    if evolution_service.session:
        await evolution_service.session.aclose()
    
    logger.info("✅ Servidor cerrado correctamente")

# ================================
# MANEJO DE SEÑALES
# ================================

def signal_handler(signum, frame):
    """Manejo de señales para cierre graceful"""
    global processing_active
    logger.info(f"🛑 Señal {signum} recibida, cerrando...")
    processing_active = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ================================
# PUNTO DE ENTRADA
# ================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando Royal Bot Chatwoot Production Server...")
    logger.info(f"🌐 Servidor en http://{HOST}:{PORT}")
    
    uvicorn.run(
        "server_chatwoot_production:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False  # Deshabilitar en producción
    ) 