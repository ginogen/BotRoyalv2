#!/usr/bin/env python3
"""
🔧 SERVIDOR DEBUG MÍNIMO
Para verificar que Railway funciona sin dependencias complejas
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Royal Bot Debug", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "Royal Bot Debug Server",
        "status": "working",
        "message": "✅ Railway está funcionando correctamente",
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
        "server": "debug_server",
        "message": "Debug server funcionando"
    }

@app.post("/test/simple")
async def test_simple():
    return {
        "status": "success",
        "message": "Servidor debug respondiendo correctamente",
        "test": "✅ OK"
    }

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """Webhook para recibir mensajes de Evolution API"""
    try:
        data = await request.json()
        
        # Log del webhook recibido
        print(f"📨 Webhook Evolution recibido: {json.dumps(data, indent=2)}")
        
        # Extraer información básica
        message_data_raw = data.get("data", {})
        message_content = message_data_raw.get("message", {}).get("conversation", "").strip()
        from_number = message_data_raw.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        print(f"📱 Mensaje de {from_number}: {message_content}")
        
        # Por ahora, solo responder que se recibió
        # En producción, aquí procesarías el mensaje con el bot
        
        return {
            "status": "received",
            "message": "Webhook recibido correctamente",
            "from": from_number,
            "content": message_content[:50] + "..." if len(message_content) > 50 else message_content
        }
        
    except Exception as e:
        print(f"❌ Error en webhook Evolution: {e}")
        return {
            "status": "error",
            "message": f"Error procesando webhook: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("debug_server:app", host="0.0.0.0", port=port) 