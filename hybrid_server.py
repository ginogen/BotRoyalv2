#!/usr/bin/env python3
"""
🤖 SERVIDOR HÍBRIDO - ROYAL BOT
Combina la estabilidad del debug_server con el procesamiento de IA
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Royal Bot Hybrid", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_TOKEN = os.getenv("EVOLUTION_API_TOKEN") 
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "F1_Retencion")

# Cliente HTTP global
http_client = None

@app.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("🚀 Servidor híbrido iniciado")

@app.on_event("shutdown") 
async def shutdown_event():
    global http_client
    if http_client:
        await http_client.aclose()

async def process_message_with_ai(user_id: str, message: str) -> str:
    """Procesa mensaje con IA - versión simplificada"""
    try:
        # Importar solo cuando se necesite para evitar errores de startup
        from royal_agents import run_contextual_conversation_sync
        
        logger.info(f"🤖 Procesando con IA: {user_id}")
        
        # Ejecutar en thread pool para no bloquear
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            run_contextual_conversation_sync,
            user_id, 
            message
        )
        
        logger.info(f"✅ IA respondió para {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error procesando con IA: {e}")
        return "Disculpá, tengo un problema técnico. Un agente te va a contactar pronto."

async def send_whatsapp_response(phone: str, message: str) -> bool:
    """Envía respuesta por WhatsApp"""
    try:
        if not all([EVOLUTION_API_URL, EVOLUTION_API_TOKEN, http_client]):
            logger.warning("Evolution API no configurada")
            return False
            
        headers = {
            "apikey": EVOLUTION_API_TOKEN,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": phone,
            "textMessage": {"text": message}
        }
        
        response = await http_client.post(
            f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            logger.info(f"📤 Respuesta enviada a {phone}")
            return True
        else:
            logger.error(f"❌ Error Evolution API: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando respuesta: {e}")
        return False

@app.get("/")
async def root():
    return {
        "service": "Royal Bot Hybrid Server",
        "status": "working", 
        "message": "✅ Servidor funcionando con IA",
        "version": "1.0.0",
        "features": [
            "✅ Recepción de webhooks",
            "✅ Procesamiento con IA", 
            "✅ Respuestas automáticas",
            "✅ Healthcheck estable"
        ],
        "environment_vars": {
            "PORT": os.getenv("PORT", "not_set"),
            "OPENAI_API_KEY": "✅ Set" if os.getenv("OPENAI_API_KEY") else "❌ Missing",
            "EVOLUTION_API_URL": "✅ Set" if os.getenv("EVOLUTION_API_URL") else "❌ Missing",
            "EVOLUTION_API_TOKEN": "✅ Set" if os.getenv("EVOLUTION_API_TOKEN") else "❌ Missing",
            "INSTANCE_NAME": os.getenv("INSTANCE_NAME", "not_set"),
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server": "hybrid_server",
        "message": "Servidor híbrido funcionando",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """Webhook para recibir mensajes de Evolution API con procesamiento IA"""
    try:
        data = await request.json()
        
        # Log del webhook recibido
        print(f"📨 Webhook Evolution recibido: {json.dumps(data, indent=2)}")
        
        # Extraer información básica
        message_data_raw = data.get("data", {})
        message_content = message_data_raw.get("message", {}).get("conversation", "").strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        print(f"📱 Mensaje de {from_number}: {message_content}")
        
        # Si hay mensaje y número, procesarlo con IA
        if message_content and from_number:
            # Procesar en background para no bloquear el webhook
            asyncio.create_task(process_and_respond(from_number, message_content))
            
            return {
                "status": "received",
                "message": "Mensaje recibido y procesando con IA",
                "from": from_number,
                "content": message_content[:50] + "..." if len(message_content) > 50 else message_content
            }
        else:
            return {
                "status": "received",
                "message": "Webhook recibido pero sin mensaje válido"
            }
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Evolution: {e}")
        return {
            "status": "error",
            "message": f"Error procesando webhook: {str(e)}"
        }

async def process_and_respond(phone: str, message: str):
    """Procesa mensaje y envía respuesta - ejecuta en background"""
    try:
        user_id = f"whatsapp_{phone}"
        
        # Procesar con IA
        ai_response = await process_message_with_ai(user_id, message)
        
        # Enviar respuesta
        await send_whatsapp_response(phone, ai_response)
        
    except Exception as e:
        logger.error(f"❌ Error en proceso completo para {phone}: {e}")

@app.post("/test/message")
async def test_message(request: Request):
    """Endpoint para probar el procesamiento de IA"""
    try:
        data = await request.json()
        message = data.get("message", "Hola")
        user_id = data.get("user_id", "test_user")
        
        response = await process_message_with_ai(user_id, message)
        
        return {
            "status": "success",
            "input": message,
            "output": response,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Iniciando servidor híbrido en puerto {port}")
    uvicorn.run("hybrid_server:app", host="0.0.0.0", port=port, log_level="info")
