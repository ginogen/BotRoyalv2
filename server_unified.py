#!/usr/bin/env python3
"""
Servidor Unificado con Knowledge Base Centralizado
Mantiene TODA la lógica existente: workers, Redis, contexto, memoria, bases de datos
Solo cambia el agente por el sistema unificado
"""

import os
import sys
import json
import asyncio
import logging
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Any, Optional
import redis
import pickle
from concurrent.futures import ThreadPoolExecutor
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === IMPORTAR TODOS LOS COMPONENTES EXISTENTES ===

# Sistema de colas y workers (MANTENIDO)
from advanced_message_queue import AdvancedMessageQueue
from dynamic_worker_pool import DynamicWorkerPool

# Base de datos persistente (MANTENIDO) 
from database_persistent import DatabaseManager

# Contexto híbrido (MANTENIDO)
from hybrid_context_manager import HybridContextManager

# Bot state manager (MANTENIDO)
from bot_state_manager import BotStateManager

# === IMPORTAR EL NUEVO SISTEMA UNIFICADO ===
from royal_agents.core import (
    get_unified_agent,
    get_knowledge_base,
    get_instruction_builder
)

# === CONFIGURACIÓN (MANTENIDA IGUAL) ===

app = Flask(__name__)
CORS(app)

# Redis configuration (MANTENIDO)
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD'),
    'decode_responses': False,  # Para manejar pickled objects
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True
}

# Configuración de workers (MANTENIDO)
WORKER_CONFIG = {
    'min_workers': int(os.getenv('MIN_WORKERS', 2)),
    'max_workers': int(os.getenv('MAX_WORKERS', 10)),
    'scale_up_threshold': float(os.getenv('SCALE_UP_THRESHOLD', 0.8)),
    'scale_down_threshold': float(os.getenv('SCALE_DOWN_THRESHOLD', 0.2)),
    'check_interval': int(os.getenv('CHECK_INTERVAL', 30))
}

# === INICIALIZACIÓN DE COMPONENTES (MANTENIDO) ===

# Redis client
try:
    redis_client = redis.Redis(**REDIS_CONFIG)
    redis_client.ping()
    logger.info("✅ Redis conectado exitosamente")
except Exception as e:
    logger.warning(f"⚠️ Redis no disponible: {e}. Usando fallback en memoria")
    redis_client = None

# Sistema de colas avanzado (MANTENIDO)
message_queue = AdvancedMessageQueue(redis_client=redis_client)

# Worker pool dinámico (MANTENIDO)
worker_pool = DynamicWorkerPool(
    message_queue=message_queue,
    min_workers=WORKER_CONFIG['min_workers'],
    max_workers=WORKER_CONFIG['max_workers'],
    scale_up_threshold=WORKER_CONFIG['scale_up_threshold'],
    scale_down_threshold=WORKER_CONFIG['scale_down_threshold'],
    check_interval=WORKER_CONFIG['check_interval']
)

# Base de datos persistente (MANTENIDO)
db_manager = DatabaseManager()

# Contexto híbrido con memoria (MANTENIDO)
context_manager = HybridContextManager(
    redis_client=redis_client,
    db_manager=db_manager
)

# Bot state manager (MANTENIDO)
bot_state_manager = BotStateManager(redis_client=redis_client)

# === AGENTE UNIFICADO (NUEVO) ===
unified_agent = get_unified_agent()
knowledge_base = get_knowledge_base()
instruction_builder = get_instruction_builder()

logger.info("✅ Sistema Unificado inicializado con:")
logger.info(f"   - Knowledge Base centralizado")
logger.info(f"   - Instruction Builder dinámico")
logger.info(f"   - Agente Unificado")
logger.info(f"   - Workers: {WORKER_CONFIG}")
logger.info(f"   - Redis: {'Conectado' if redis_client else 'Fallback en memoria'}")
logger.info(f"   - Base de datos: {'Conectada' if db_manager else 'No disponible'}")


# === FUNCIONES DE PROCESAMIENTO (ADAPTADAS AL NUEVO SISTEMA) ===

async def process_message_with_unified_agent(
    conversation_id: str,
    message: str,
    metadata: Optional[Dict] = None
) -> str:
    """
    Procesa mensaje usando el agente unificado.
    Mantiene TODA la lógica de contexto, memoria y bases de datos.
    """
    try:
        start_time = time.time()
        
        # 1. Verificar estado del bot (MANTENIDO)
        if not bot_state_manager.is_bot_active(conversation_id):
            logger.info(f"🔕 Bot pausado para {conversation_id}")
            return None  # No responder si el bot está pausado
        
        # 2. Obtener contexto híbrido (MANTENIDO)
        context = context_manager.get_or_create_context(conversation_id)
        logger.info(f"📝 Contexto obtenido para {conversation_id}")
        
        # 3. Guardar mensaje en base de datos (MANTENIDO)
        if db_manager:
            db_manager.save_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
                metadata=metadata
            )
        
        # 4. Detectar tipo de usuario y escenario (NUEVO - usando el agente unificado)
        user_type = unified_agent._detect_user_type(message, context)
        scenario = unified_agent._detect_scenario(message)
        
        logger.info(f"🎯 Usuario tipo: {user_type}, Escenario: {scenario}")
        
        # 5. Actualizar contexto con información detectada (MANTENIDO)
        if user_type == "new_entrepreneurs":
            context.conversation.is_entrepreneur = True
            context.conversation.experience_level = "empezando"
        elif user_type == "experienced_sellers":
            context.conversation.is_entrepreneur = True
            context.conversation.experience_level = "experimentado"
        
        # 6. Procesar con el agente unificado (NUEVO)
        response = await unified_agent.process_message(
            user_id=conversation_id,
            message=message,
            context=context
        )
        
        # 7. Guardar respuesta en base de datos (MANTENIDO)
        if db_manager:
            db_manager.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response,
                metadata={
                    'user_type': user_type,
                    'scenario': scenario,
                    'processing_time': time.time() - start_time
                }
            )
        
        # 8. Actualizar contexto en Redis/DB (MANTENIDO)
        context_manager.save_context(conversation_id, context)
        
        # 9. Actualizar métricas en Redis (MANTENIDO)
        if redis_client:
            redis_client.hincrby('metrics:messages', conversation_id, 1)
            redis_client.hset('metrics:last_message', conversation_id, datetime.now().isoformat())
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Mensaje procesado en {processing_time:.2f}s para {conversation_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {str(e)}")
        
        # Guardar error en base de datos (MANTENIDO)
        if db_manager:
            db_manager.save_message(
                conversation_id=conversation_id,
                role="system",
                content=f"Error: {str(e)}",
                metadata={'error': True}
            )
        
        # Respuesta de fallback usando Knowledge Base (NUEVO)
        return knowledge_base.get_error_message("technical_issue")


def process_message_sync(conversation_id: str, message: str, metadata: Optional[Dict] = None) -> str:
    """Versión síncrona del procesamiento (MANTENIDA)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            process_message_with_unified_agent(conversation_id, message, metadata)
        )
    finally:
        loop.close()


# === WORKER FUNCTION (ADAPTADA) ===

def worker_process_message(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función del worker para procesar mensajes.
    Usa el sistema unificado pero mantiene toda la lógica de workers.
    """
    try:
        conversation_id = task_data['conversation_id']
        message = task_data['message']
        metadata = task_data.get('metadata', {})
        
        # Procesar con el sistema unificado
        response = process_message_sync(conversation_id, message, metadata)
        
        return {
            'success': True,
            'response': response,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Worker error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'conversation_id': task_data.get('conversation_id'),
            'timestamp': datetime.now().isoformat()
        }


# === RUTAS API (MANTENIDAS CON MEJORAS) ===

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint (MANTENIDO)"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'redis': redis_client.ping() if redis_client else False,
            'database': db_manager.is_connected() if db_manager else False,
            'workers': worker_pool.get_stats() if worker_pool else {},
            'knowledge_base': knowledge_base.get_summary(),
            'unified_agent': unified_agent.get_stats()
        }
    }
    return jsonify(health_status)


@app.route('/api/message', methods=['POST'])
def handle_message():
    """Endpoint principal para mensajes (MANTENIDO con mejoras)"""
    try:
        data = request.json
        conversation_id = data.get('conversation_id', 'default')
        message = data.get('message', '')
        metadata = data.get('metadata', {})
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Agregar a la cola de mensajes (MANTENIDO)
        task = {
            'conversation_id': conversation_id,
            'message': message,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }
        
        # Procesar con workers si están disponibles (MANTENIDO)
        if worker_pool and worker_pool.is_running:
            task_id = message_queue.add_task(task, priority='normal')
            
            # Esperar respuesta (con timeout)
            max_wait = 30  # segundos
            start_wait = time.time()
            
            while time.time() - start_wait < max_wait:
                result = message_queue.get_result(task_id)
                if result:
                    if result['success']:
                        return jsonify({
                            'response': result['response'],
                            'conversation_id': conversation_id,
                            'task_id': task_id
                        })
                    else:
                        return jsonify({'error': result['error']}), 500
                time.sleep(0.1)
            
            return jsonify({'error': 'Timeout waiting for response'}), 504
            
        else:
            # Procesamiento directo si no hay workers (MANTENIDO)
            response = process_message_sync(conversation_id, message, metadata)
            return jsonify({
                'response': response,
                'conversation_id': conversation_id
            })
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/context/<conversation_id>', methods=['GET'])
def get_context(conversation_id):
    """Obtener contexto de una conversación (MANTENIDO)"""
    try:
        context = context_manager.get_or_create_context(conversation_id)
        
        # Convertir a diccionario serializable
        context_data = {
            'conversation_id': conversation_id,
            'user_profile': context.conversation.user_profile,
            'is_entrepreneur': context.conversation.is_entrepreneur,
            'experience_level': context.conversation.experience_level,
            'product_interests': context.conversation.product_interests,
            'recent_products': len(context.conversation.recent_products),
            'interaction_count': len(context.conversation.interaction_history),
            'last_interaction': context.conversation.last_interaction.isoformat()
        }
        
        return jsonify(context_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/reload', methods=['POST'])
def reload_knowledge():
    """Recargar Knowledge Base (NUEVO)"""
    try:
        # Recargar knowledge base
        knowledge_base.reload_data()
        
        # Reinicializar agente con nuevo conocimiento
        unified_agent.reload_knowledge()
        
        return jsonify({
            'status': 'success',
            'message': 'Knowledge Base recargado exitosamente',
            'summary': knowledge_base.get_summary()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/search', methods=['POST'])
def search_knowledge():
    """Buscar en el Knowledge Base (NUEVO)"""
    try:
        query = request.json.get('query', '')
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        results = knowledge_base.search_knowledge(query)
        
        return jsonify({
            'query': query,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas del sistema (MANTENIDO con mejoras)"""
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'workers': worker_pool.get_stats() if worker_pool else {},
            'queue': message_queue.get_stats() if message_queue else {},
            'contexts': context_manager.get_stats() if context_manager else {},
            'knowledge_base': knowledge_base.get_summary(),
            'agent': unified_agent.get_stats()
        }
        
        # Agregar métricas de Redis si está disponible
        if redis_client:
            try:
                total_messages = sum(
                    int(v) for v in redis_client.hvals('metrics:messages')
                )
                stats['total_messages'] = total_messages
            except:
                pass
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/toggle/<conversation_id>', methods=['POST'])
def toggle_bot(conversation_id):
    """Activar/desactivar bot para una conversación (MANTENIDO)"""
    try:
        action = request.json.get('action', 'toggle')
        
        if action == 'activate':
            bot_state_manager.activate_bot(conversation_id)
            status = 'activated'
        elif action == 'pause':
            bot_state_manager.pause_bot(conversation_id)
            status = 'paused'
        else:  # toggle
            if bot_state_manager.is_bot_active(conversation_id):
                bot_state_manager.pause_bot(conversation_id)
                status = 'paused'
            else:
                bot_state_manager.activate_bot(conversation_id)
                status = 'activated'
        
        return jsonify({
            'conversation_id': conversation_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def home():
    """Página principal con panel de control (MEJORADA)"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Royal Bot - Sistema Unificado</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 30px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .stat-card h3 {
                margin-top: 0;
                color: #ffd700;
                font-size: 1.3em;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }
            .test-area {
                background: rgba(255, 255, 255, 0.95);
                color: #333;
                border-radius: 15px;
                padding: 30px;
                margin-top: 30px;
            }
            .test-area h2 {
                color: #667eea;
                margin-top: 0;
            }
            input, textarea {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 2px solid #667eea;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover {
                transform: scale(1.05);
            }
            .response-box {
                background: #f0f0f0;
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
                min-height: 100px;
            }
            .actions {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            .success {
                color: #4caf50;
            }
            .error {
                color: #f44336;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Royal Bot - Sistema Unificado</h1>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📚 Knowledge Base</h3>
                    <div id="kb-stats">Cargando...</div>
                </div>
                
                <div class="stat-card">
                    <h3>⚙️ Sistema</h3>
                    <div id="system-stats">Cargando...</div>
                </div>
                
                <div class="stat-card">
                    <h3>👥 Workers</h3>
                    <div id="worker-stats">Cargando...</div>
                </div>
            </div>
            
            <div class="test-area">
                <h2>🧪 Área de Pruebas</h2>
                
                <input type="text" id="conversation_id" placeholder="ID de Conversación" value="test_user">
                
                <textarea id="message" placeholder="Escribe tu mensaje aquí..." rows="3">Hola, quiero empezar a vender</textarea>
                
                <div class="actions">
                    <button onclick="sendMessage()">Enviar Mensaje</button>
                    <button onclick="reloadKnowledge()">Recargar Knowledge Base</button>
                    <button onclick="loadStats()">Actualizar Stats</button>
                </div>
                
                <div class="response-box" id="response">
                    <em>La respuesta aparecerá aquí...</em>
                </div>
            </div>
        </div>
        
        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    // Knowledge Base stats
                    const kb = data.knowledge_base || {};
                    document.getElementById('kb-stats').innerHTML = `
                        <div class="stat-value">${kb.faqs_count || 0}</div>
                        <div>FAQs cargadas</div>
                        <div>${kb.company_sections || 0} secciones</div>
                    `;
                    
                    // System stats
                    document.getElementById('system-stats').innerHTML = `
                        <div class="stat-value">${data.total_messages || 0}</div>
                        <div>Mensajes procesados</div>
                    `;
                    
                    // Worker stats
                    const workers = data.workers || {};
                    document.getElementById('worker-stats').innerHTML = `
                        <div class="stat-value">${workers.active_workers || 0}/${workers.max_workers || 0}</div>
                        <div>Workers activos</div>
                        <div>Cola: ${workers.queue_size || 0} tareas</div>
                    `;
                    
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }
            
            async function sendMessage() {
                const conversationId = document.getElementById('conversation_id').value;
                const message = document.getElementById('message').value;
                const responseBox = document.getElementById('response');
                
                responseBox.innerHTML = '<em>Procesando...</em>';
                
                try {
                    const response = await fetch('/api/message', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            conversation_id: conversationId,
                            message: message
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        responseBox.innerHTML = `<div class="success">${data.response}</div>`;
                    } else {
                        responseBox.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                    }
                    
                } catch (error) {
                    responseBox.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                }
            }
            
            async function reloadKnowledge() {
                const responseBox = document.getElementById('response');
                responseBox.innerHTML = '<em>Recargando Knowledge Base...</em>';
                
                try {
                    const response = await fetch('/api/knowledge/reload', {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        responseBox.innerHTML = `<div class="success">✅ ${data.message}</div>`;
                        loadStats();
                    } else {
                        responseBox.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                    }
                    
                } catch (error) {
                    responseBox.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                }
            }
            
            // Cargar stats al inicio
            loadStats();
            
            // Actualizar stats cada 30 segundos
            setInterval(loadStats, 30000);
        </script>
    </body>
    </html>
    ''')


# === INICIALIZACIÓN DEL SERVIDOR ===

def initialize_server():
    """Inicializa todos los componentes del servidor"""
    try:
        logger.info("🚀 Inicializando servidor unificado...")
        
        # Iniciar workers si están configurados
        if worker_pool:
            worker_pool.start()
            worker_pool.register_worker_function(worker_process_message)
            logger.info(f"✅ Workers iniciados: {worker_pool.get_stats()}")
        
        # Verificar base de datos
        if db_manager:
            db_manager.init_db()
            logger.info("✅ Base de datos inicializada")
        
        # Cargar Knowledge Base
        kb_summary = knowledge_base.get_summary()
        logger.info(f"✅ Knowledge Base cargado: {kb_summary}")
        
        # Verificar agente
        agent_stats = unified_agent.get_stats()
        logger.info(f"✅ Agente unificado listo: {agent_stats}")
        
        logger.info("✅ Servidor unificado inicializado completamente")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando servidor: {e}")
        raise


def cleanup():
    """Limpia recursos al cerrar"""
    try:
        if worker_pool:
            worker_pool.stop()
            logger.info("✅ Workers detenidos")
        
        if redis_client:
            redis_client.close()
            logger.info("✅ Redis cerrado")
        
        if db_manager:
            db_manager.close()
            logger.info("✅ Base de datos cerrada")
            
    except Exception as e:
        logger.error(f"Error en cleanup: {e}")


if __name__ == '__main__':
    try:
        # Inicializar servidor
        initialize_server()
        
        # Configurar puerto
        port = int(os.getenv('PORT', 5000))
        
        # Ejecutar servidor
        logger.info(f"🌐 Servidor ejecutándose en http://localhost:{port}")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False  # No usar debug en producción
        )
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Servidor detenido por el usuario")
        
    finally:
        cleanup()
        logger.info("👋 Servidor cerrado")