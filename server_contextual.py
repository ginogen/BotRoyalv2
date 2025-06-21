# Servidor de ejemplo para Royal Bot v2 con capacidades de contexto
# Demuestra el uso del agente contextual con memoria persistente

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from royal_agents import (
    run_contextual_conversation_sync,
    run_contextual_conversation,
    cleanup_old_contexts
)
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Royal Bot Contextual API",
    description="API para Royal Bot con capacidades de memoria y contexto",
    version="2.0.0"
)

class ChatMessage(BaseModel):
    user_id: str
    message: str
    use_async: bool = False

class ChatResponse(BaseModel):
    user_id: str
    response: str
    context_info: Optional[Dict] = None

class ContextInfo(BaseModel):
    user_id: str

@app.get("/")
async def root():
    return {
        "message": "Royal Bot Contextual API v2.0",
        "features": [
            "Memoria persistente de conversaciones",
            "Contexto de productos mostrados",
            "Reconocimiento de referencias (el primero, el segundo)",
            "Perfiles de usuario (emprendedor, experiencia)",
            "Recomendaciones personalizadas"
        ],
        "endpoints": [
            "/chat - Enviar mensaje con contexto",
            "/context/{user_id} - Ver contexto del usuario", 
            "/context/{user_id}/clear - Limpiar contexto",
            "/cleanup - Limpiar contextos antiguos"
        ]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_context(chat_message: ChatMessage):
    """
    Endpoint principal para chat con contexto.
    Mantiene memoria de la conversación y productos mostrados.
    """
    
    logger.info(f"💬 Chat request para usuario: {chat_message.user_id}")
    logger.info(f"   Mensaje: {chat_message.message}")
    
    try:
        if chat_message.use_async:
            # Versión asíncrona
            response = await run_contextual_conversation(
                user_id=chat_message.user_id,
                user_message=chat_message.message
            )
        else:
            # Versión síncrona (más estable)
            response = run_contextual_conversation_sync(
                user_id=chat_message.user_id,
                user_message=chat_message.message
            )
        
        # Obtener info del contexto para debugging
        from royal_agents.conversation_context import context_manager
        context = context_manager.get_or_create_context(chat_message.user_id)
        
        context_info = {
            "state": context.conversation.current_state,
            "is_entrepreneur": context.conversation.is_entrepreneur,
            "recent_products_count": len(context.conversation.recent_products),
            "interaction_count": len(context.conversation.interaction_history)
        }
        
        logger.info(f"✅ Respuesta generada para: {chat_message.user_id}")
        
        return ChatResponse(
            user_id=chat_message.user_id,
            response=response,
            context_info=context_info
        )
        
    except Exception as e:
        logger.error(f"❌ Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando mensaje: {str(e)}")

@app.get("/context/{user_id}")
async def get_user_context(user_id: str):
    """
    Obtiene el contexto completo de un usuario para debugging.
    """
    
    try:
        from royal_agents.conversation_context import context_manager
        context = context_manager.get_or_create_context(user_id)
        conversation = context.conversation
        
        return {
            "user_id": user_id,
            "conversation_started": conversation.conversation_started.isoformat(),
            "last_interaction": conversation.last_interaction.isoformat(),
            "current_state": conversation.current_state,
            "user_intent": conversation.user_intent,
            "is_entrepreneur": conversation.is_entrepreneur,
            "experience_level": conversation.experience_level,
            "product_interests": conversation.product_interests,
            "budget_range": conversation.budget_range,
            "recent_products": [
                {
                    "name": p.name,
                    "price": p.price,
                    "category": p.category,
                    "shown_at": p.shown_at.isoformat()
                }
                for p in conversation.recent_products
            ],
            "interaction_history": conversation.interaction_history[-5:],  # Últimas 5
            "user_profile": conversation.user_profile
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo contexto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo contexto: {str(e)}")

@app.delete("/context/{user_id}/clear")
async def clear_user_context(user_id: str):
    """
    Limpia el contexto de un usuario específico.
    """
    
    try:
        from royal_agents.conversation_context import context_manager
        
        if user_id in context_manager.active_contexts:
            del context_manager.active_contexts[user_id]
            logger.info(f"🧹 Contexto limpiado para usuario: {user_id}")
            return {"message": f"Contexto limpiado para usuario {user_id}"}
        else:
            return {"message": f"No se encontró contexto para usuario {user_id}"}
            
    except Exception as e:
        logger.error(f"❌ Error limpiando contexto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error limpiando contexto: {str(e)}")

@app.post("/cleanup")
async def cleanup_old_contexts_endpoint():
    """
    Limpia contextos antiguos (más de 24 horas).
    """
    
    try:
        cleanup_old_contexts()
        return {"message": "Limpieza de contextos antiguos completada"}
        
    except Exception as e:
        logger.error(f"❌ Error en limpieza: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en limpieza: {str(e)}")

@app.get("/stats")
async def get_stats():
    """
    Obtiene estadísticas del sistema de contexto.
    """
    
    try:
        from royal_agents.conversation_context import context_manager
        
        active_contexts = len(context_manager.active_contexts)
        
        # Estadísticas por estado
        states = {}
        entrepreneurs = 0
        total_products = 0
        
        for context in context_manager.active_contexts.values():
            conv = context.conversation
            
            # Estados
            if conv.current_state in states:
                states[conv.current_state] += 1
            else:
                states[conv.current_state] = 1
                
            # Emprendedores
            if conv.is_entrepreneur:
                entrepreneurs += 1
                
            # Productos
            total_products += len(conv.recent_products)
        
        return {
            "active_contexts": active_contexts,
            "entrepreneurs": entrepreneurs,
            "states_distribution": states,
            "total_products_in_memory": total_products,
            "average_products_per_user": total_products / max(active_contexts, 1)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

if __name__ == "__main__":
    print("🚀 Iniciando Royal Bot Contextual Server...")
    print("📋 Características:")
    print("   • Memoria persistente de conversaciones")
    print("   • Contexto de productos mostrados") 
    print("   • Reconocimiento de referencias")
    print("   • Perfiles de usuario personalizados")
    print("")
    print("🔗 Endpoints disponibles:")
    print("   • POST /chat - Chat con contexto")
    print("   • GET /context/{user_id} - Ver contexto")
    print("   • DELETE /context/{user_id}/clear - Limpiar contexto")
    print("   • POST /cleanup - Limpiar contextos antiguos")
    print("   • GET /stats - Estadísticas del sistema")
    print("")
    
    uvicorn.run(
        "server_contextual:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 