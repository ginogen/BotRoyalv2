#!/usr/bin/env python3
"""
Servidor debug mínimo para probar healthcheck
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Debug Health Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "Debug Health Server",
        "status": "working",
        "message": "✅ Servidor funcionando",
        "port": os.getenv("PORT", "not_set"),
        "host": "0.0.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server": "debug_health_server",
        "message": "Health endpoint funcionando",
        "port": os.getenv("PORT", "not_set")
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Iniciando servidor debug en puerto {port}")
    uvicorn.run("debug_health_server:app", host="0.0.0.0", port=port, log_level="info")
