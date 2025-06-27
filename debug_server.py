#!/usr/bin/env python3
"""
🔧 SERVIDOR DEBUG MÍNIMO
Para verificar que Railway funciona sin dependencias complejas
"""

import os
from fastapi import FastAPI
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("debug_server:app", host="0.0.0.0", port=port) 