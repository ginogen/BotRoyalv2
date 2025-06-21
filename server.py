#!/usr/bin/env python3
"""
Servidor web para el Royal Bot
Maneja webhooks de Chatwoot y Evolution API
"""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import hmac
import hashlib

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis
import requests
from dotenv import load_dotenv

from agents import Runner
from royal_agents.royal_agent import royal_consultation_agent

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv(".env")

# Configuración
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHATWOOT_WEBHOOK_SECRET = os.getenv("CHATWOOT_WEBHOOK_SECRET")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_TOKEN = os.getenv("EVOLUTION_API_TOKEN")

# Inicializar FastAPI
app = FastAPI(
    title="Royal Bot API",
    description="Bot de consultas para Royal Company",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Redis
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("✅ Conexión a Redis establecida")
except Exception as e:
    logger.error(f"❌ Error conectando a Redis: {e}")
    redis_client = None

# Modelos de datos
class ChatwootMessage(BaseModel):
    message_type: str
    content: str
    sender_type: str
    conversation_id: int
    contact_id: int
    account_id: int

class EvolutionMessage(BaseModel):
    key: Dict[str, Any]
    message: Dict[str, Any]
    messageTimestamp: int
    pushName: str

class TestMessage(BaseModel):
    message: str
    client_id: Optional[str] = None

# Utilidades
def verify_chatwoot_signature(payload: bytes, signature: str) -> bool:
    """Verifica la firma del webhook de Chatwoot"""
    if not CHATWOOT_WEBHOOK_SECRET:
        return True  # Si no hay secret configurado, aceptar
    
    expected_signature = hmac.new(
        CHATWOOT_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

def get_client_context(client_id: str) -> Dict[str, Any]:
    """Obtiene el contexto del cliente desde Redis"""
    if not redis_client:
        return {}
    
    try:
        context_key = f"client_context:{client_id}"
        context_data = redis_client.get(context_key)
        return json.loads(context_data) if context_data else {}
    except Exception as e:
        logger.error(f"Error obteniendo contexto del cliente {client_id}: {e}")
        return {}

def save_client_context(client_id: str, context: Dict[str, Any]) -> None:
    """Guarda el contexto del cliente en Redis"""
    if not redis_client:
        return
    
    try:
        context_key = f"client_context:{client_id}"
        # Mantener solo los últimos 10 mensajes para optimizar memoria
        if "conversation_history" in context:
            context["conversation_history"] = context["conversation_history"][-10:]
        
        redis_client.setex(
            context_key, 
            86400,  # 24 horas de TTL
            json.dumps(context, ensure_ascii=False)
        )
    except Exception as e:
        logger.error(f"Error guardando contexto del cliente {client_id}: {e}")

async def process_message_with_agent(message: str, client_id: str) -> str:
    """Procesa un mensaje con el agente Royal"""
    try:
        # Obtener contexto del cliente
        context = get_client_context(client_id)
        
        # Agregar mensaje actual al historial
        if "conversation_history" not in context:
            context["conversation_history"] = []
        
        context["conversation_history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ejecutar el agente
        logger.info(f"🤖 Procesando mensaje para cliente {client_id}: {message[:50]}...")
        
        result = await Runner.run(
            royal_consultation_agent,
            message,
            context={
                "client_id": client_id,
                "conversation_history": context["conversation_history"][-5:]  # Últimos 5 mensajes
            }
        )
        
        agent_response = result.final_output
        
        # Agregar respuesta al historial
        context["conversation_history"].append({
            "role": "assistant", 
            "content": agent_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Guardar contexto actualizado
        save_client_context(client_id, context)
        
        logger.info(f"✅ Respuesta generada para cliente {client_id}")
        return agent_response
        
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        return "Disculpá, hubo un problema técnico. Probá de nuevo en un momento 🔧"

def send_to_chatwoot(conversation_id: int, message: str) -> bool:
    """Envía un mensaje a Chatwoot"""
    try:
        # Implementar envío a Chatwoot API
        # Esta función se completará con los datos específicos de tu instancia
        logger.info(f"📤 Enviando a Chatwoot conversación {conversation_id}: {message[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando a Chatwoot: {e}")
        return False

def send_to_evolution(phone: str, message: str) -> bool:
    """Envía un mensaje vía Evolution API"""
    try:
        if not EVOLUTION_API_URL or not EVOLUTION_API_TOKEN:
            logger.warning("Evolution API no configurada")
            return False
            
        headers = {
            "Authorization": f"Bearer {EVOLUTION_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": phone,
            "text": message
        }
        
        response = requests.post(
            f"{EVOLUTION_API_URL}/message/sendText",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"📤 Mensaje enviado via Evolution a {phone}")
            return True
        else:
            logger.error(f"❌ Error Evolution API: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando via Evolution: {e}")
        return False

# Endpoints

@app.get("/")
async def root():
    """Endpoint de salud"""
    return {
        "status": "active",
        "service": "Royal Bot API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Chequeo de salud del servicio"""
    redis_status = "connected" if redis_client else "disconnected"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook para recibir mensajes de Chatwoot"""
    try:
        # Verificar firma si está configurada
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        if CHATWOOT_WEBHOOK_SECRET and not verify_chatwoot_signature(body, signature):
            raise HTTPException(status_code=401, detail="Firma inválida")
        
        # Procesar mensaje
        data = await request.json()
        logger.info(f"📨 Webhook Chatwoot recibido: {data.get('event', 'unknown')}")
        
        # Solo procesar mensajes de entrada de contactos
        if (data.get("event") == "message_created" and 
            data.get("message_type") == "incoming" and
            data.get("sender_type") == "contact"):
            
            message_content = data.get("content", "").strip()
            conversation_id = data.get("conversation", {}).get("id")
            contact_id = data.get("sender", {}).get("id")
            
            if message_content and conversation_id:
                # Procesar en background
                background_tasks.add_task(
                    process_chatwoot_message,
                    message_content,
                    conversation_id,
                    contact_id
                )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Chatwoot: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook para recibir mensajes de Evolution API"""
    try:
        data = await request.json()
        logger.info(f"📨 Webhook Evolution recibido")
        
        # Extraer información del mensaje
        message_data = data.get("data", {})
        message_type = message_data.get("messageType")
        
        if message_type == "conversation":
            message_content = message_data.get("message", {}).get("conversation", "").strip()
            from_number = message_data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
            
            if message_content and from_number:
                # Procesar en background
                background_tasks.add_task(
                    process_evolution_message,
                    message_content,
                    from_number
                )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Evolution: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

@app.post("/test/message")
async def test_message(test_msg: TestMessage):
    """Endpoint para probar el agente directamente"""
    try:
        client_id = test_msg.client_id or "test_user"
        
        response = await process_message_with_agent(
            test_msg.message,
            client_id
        )
        
        return {
            "status": "success",
            "response": response,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test message: {e}")
        raise HTTPException(status_code=500, detail="Error procesando mensaje")

# Funciones de background
async def process_chatwoot_message(message: str, conversation_id: int, contact_id: int):
    """Procesa mensaje de Chatwoot en background"""
    try:
        client_id = f"chatwoot_{contact_id}"
        response = await process_message_with_agent(message, client_id)
        
        # Enviar respuesta a Chatwoot
        send_to_chatwoot(conversation_id, response)
        
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje Chatwoot: {e}")

async def process_evolution_message(message: str, phone: str):
    """Procesa mensaje de Evolution API en background"""
    try:
        client_id = f"whatsapp_{phone}"
        response = await process_message_with_agent(message, client_id)
        
        # Enviar respuesta via Evolution
        send_to_evolution(phone, response)
        
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje Evolution: {e}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando Royal Bot Server...")
    logger.info(f"🌐 Servidor corriendo en http://{HOST}:{PORT}")
    
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=os.getenv("ENVIRONMENT") == "development"
    ) 