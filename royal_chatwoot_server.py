#!/usr/bin/env python3
"""
🤖 ROYAL BOT - SERVIDOR OPTIMIZADO PARA CHATWOOT
Implementación simplificada pero robusta basada en el sistema Node.js
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
import threading
from queue import PriorityQueue, Empty
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Imports del bot
from royal_agents import run_contextual_conversation_sync

# Configuración
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
PORT = int(os.getenv("PORT", 8000))
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_TOKEN = os.getenv("EVOLUTION_API_TOKEN")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "F1_Retencion")

# Configuración del sistema
WORKER_POOL_SIZE = int(os.getenv("WORKER_POOL_SIZE", 3))
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", 5))

@dataclass
class MessageData:
    user_id: str
    message: str
    source: str
    conversation_id: Optional[str] = None
    phone: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: int = 1

class MessageQueue:
    def __init__(self):
        self.queue = PriorityQueue()
        self.processed_messages = defaultdict(set)
        self.lock = threading.Lock()
    
    def add_message(self, message_data: MessageData) -> bool:
        with self.lock:
            message_key = f"{hash(message_data.message)}-{message_data.user_id}"
            
            if message_key in self.processed_messages[message_data.user_id]:
                return False
                
            self.processed_messages[message_data.user_id].add(message_key)
            
            # Limpiar mensajes antiguos
            if len(self.processed_messages[message_data.user_id]) > 10:
                old_messages = list(self.processed_messages[message_data.user_id])[:5]
                for old_msg in old_messages:
                    self.processed_messages[message_data.user_id].discard(old_msg)
            
            self.queue.put((message_data.priority, message_data.timestamp, message_data))
            return True
    
    def get_next_message(self, timeout: float = 1.0) -> Optional[MessageData]:
        try:
            priority, timestamp, message_data = self.queue.get(timeout=timeout)
            return message_data
        except Empty:
            return None

class WorkerPool:
    def __init__(self, pool_size: int):
        self.executor = ThreadPoolExecutor(max_workers=pool_size)
        self.active_workers = 0
        self.lock = threading.Lock()
    
    async def process_message(self, message_data: MessageData) -> Dict[str, Any]:
        with self.lock:
            self.active_workers += 1
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._process_sync,
                message_data
            )
            return result
        finally:
            with self.lock:
                self.active_workers -= 1
    
    def _process_sync(self, message_data: MessageData) -> Dict[str, Any]:
        try:
            logger.info(f"🤖 Procesando: {message_data.user_id}")
            
            response = run_contextual_conversation_sync(
                message_data.user_id, 
                message_data.message
            )
            
            return {
                "success": True,
                "response": response
            }
        except Exception as e:
            logger.error(f"❌ Error procesando: {e}")
            return {
                "success": False,
                "response": "Hubo un problema técnico. Un agente te contactará pronto."
            }

class ChatwootService:
    def __init__(self):
        self.session = None
    
    async def initialize(self):
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(self, conversation_id: str, message: str) -> bool:
        if not all([CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]) or not self.session:
            return False
            
        try:
            headers = {
                "api_access_token": CHATWOOT_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            payload = {
                "content": message,
                "message_type": "outgoing"
            }
            
            response = await self.session.post(
                f"{CHATWOOT_API_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages",
                headers=headers,
                json=payload
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"❌ Error enviando a Chatwoot: {e}")
            return False

class EvolutionService:
    def __init__(self):
        self.session = None
    
    async def initialize(self):
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(self, phone: str, message: str) -> bool:
        if not all([EVOLUTION_API_URL, EVOLUTION_API_TOKEN]) or not self.session:
            return False
            
        try:
            headers = {
                "apikey": EVOLUTION_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            payload = {
                "number": phone,
                "textMessage": {"text": message}
            }
            
            response = await self.session.post(
                f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}",
                headers=headers,
                json=payload
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Error enviando via Evolution: {e}")
            return False

# Instancias globales
app = FastAPI(title="Royal Bot Chatwoot", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

message_queue = MessageQueue()
worker_pool = WorkerPool(WORKER_POOL_SIZE)
chatwoot_service = ChatwootService()
evolution_service = EvolutionService()

processing_active = True

async def message_processor():
    """Procesador principal de mensajes"""
    logger.info("🚀 Procesador de mensajes iniciado")
    
    while processing_active:
        try:
            message_data = message_queue.get_next_message(timeout=1.0)
            
            if not message_data:
                continue
            
            # Procesar mensaje
            result = await worker_pool.process_message(message_data)
            
            if result["success"]:
                # Enviar respuesta
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
                
                logger.info(f"✅ Mensaje procesado: {message_data.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error en procesador: {e}")
            await asyncio.sleep(1.0)

# Modelos
class TestMessage(BaseModel):
    message: str
    user_id: Optional[str] = "test_user"

# Endpoints
@app.get("/")
async def root():
    return {
        "service": "Royal Bot Chatwoot",
        "version": "2.0.0",
        "status": "active",
        "features": [
            "✅ Conexión con Chatwoot",
            "✅ Sistema de workers paralelos", 
            "✅ Cola de mensajes optimizada",
            "✅ Integration WhatsApp via Evolution"
        ]
    }

@app.get("/health")
async def health_check():
    """Chequeo de salud del servicio"""
    return {
        "status": "healthy",
        "service": "Royal Bot Chatwoot",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "workers": {
            "active": worker_pool.active_workers,
            "total": WORKER_POOL_SIZE
        },
        "queue": {
            "pending": message_queue.queue.qsize() if hasattr(message_queue.queue, 'qsize') else 0
        }
    }



@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    try:
        data = await request.json()
        
        if (data.get("event") == "message_created" and 
            data.get("message_type") == "incoming" and
            data.get("sender", {}).get("type") == "contact"):
            
            conversation = data.get("conversation", {})
            content = data.get("content", "").strip()
            
            if content and conversation.get("id"):
                contact_id = data.get("sender", {}).get("id")
                
                if contact_id is not None:
                    message_data = MessageData(
                        user_id=f"chatwoot_{str(contact_id)}",
                        message=content,
                        source="chatwoot",
                        conversation_id=str(conversation["id"])
                    )
                    
                    if message_queue.add_message(message_data):
                        logger.info(f"📥 Mensaje Chatwoot agregado: {contact_id}")
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Error webhook Chatwoot: {e}")
        raise HTTPException(status_code=500, detail="Error procesando webhook")

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    try:
        data = await request.json()
        
        message_data_raw = data.get("data", {})
        message_content = message_data_raw.get("message", {}).get("conversation", "").strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        if message_content and from_number:
            message_data = MessageData(
                user_id=f"whatsapp_{from_number}",
                message=message_content,
                source="evolution",
                phone=from_number
            )
            
            if message_queue.add_message(message_data):
                logger.info(f"📥 Mensaje WhatsApp agregado: {from_number}")
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Error webhook Evolution: {e}")
        raise HTTPException(status_code=500, detail="Error procesando webhook")

@app.post("/test/message")
async def test_message(test_msg: TestMessage):
    try:
        message_data = MessageData(
            user_id=test_msg.user_id,
            message=test_msg.message,
            source="test",
            priority=1
        )
        
        result = await worker_pool.process_message(message_data)
        
        return {
            "status": "success" if result["success"] else "error",
            "response": result["response"],
            "user_id": test_msg.user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error test message: {e}")
        raise HTTPException(status_code=500, detail="Error procesando mensaje")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando Royal Bot Chatwoot...")
    
    await chatwoot_service.initialize()
    await evolution_service.initialize()
    
    # Iniciar procesador
    asyncio.create_task(message_processor())
    
    logger.info("✅ Servidor inicializado")

@app.on_event("shutdown")
async def shutdown_event():
    global processing_active
    processing_active = False
    
    if chatwoot_service.session:
        await chatwoot_service.session.aclose()
    if evolution_service.session:
        await evolution_service.session.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("royal_chatwoot_server:app", host="0.0.0.0", port=PORT, log_level="info") 