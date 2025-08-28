const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const AgentOrchestrator = require('./orchestrator/agentOrchestrator');
const HumanSimulation = require('./utils/humanSimulation');
const MessageFormatter = require('./utils/messageFormatter');
const DashboardRoutes = require('./dashboard/dashboardRoutes');
const MonitoringRoutes = require('./dashboard/monitoring-routes');
const redisClient = require('./utils/redisClient');
const postgresClient = require('./utils/postgresClient');

// 🚀 Nuevos imports para sistema mejorado
const { WorkerPool } = require('./workers/messageWorker');
const PriorityMessageQueue = require('./utils/priorityQueue');
const logger = require('./utils/logger');
const ChatwootManager = require('./utils/chatwootManager');

// 🚀 APLICAR OPTIMIZADOR DE CONCURRENCIA PARA RAILWAY
const RailwayConcurrencyOptimizer = require('./patches/concurrency-fix');
const concurrencyOptimizer = new RailwayConcurrencyOptimizer();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;

// ✅ Configuración Evolution API con variables de entorno
const INSTANCE_TOKEN = process.env.INSTANCE_TOKEN || 'foyUmx0ddZb2xZIszzBfbBj3bFYzC78f';
const INSTANCE_NAME = process.env.INSTANCE_NAME || 'F1_Retencion';
const EVOLUTION_API_URL = process.env.EVOLUTION_API_URL || 'https://evolution-api-evolutionapi.kcweou.easypanel.host';

// 🤖 Inicializar orquestador de agentes
const orchestrator = new AgentOrchestrator();
const chatwootManager = new ChatwootManager();
global.chatwootManager = chatwootManager;

// 🚀 Sistema mejorado de procesamiento paralelo
const WORKER_POOL_SIZE = parseInt(process.env.WORKER_POOL_SIZE) || 3;
const MAX_CONCURRENT_USERS = parseInt(process.env.MAX_CONCURRENT_USERS) || 5;
let workerPool;
const globalMessageQueue = new PriorityMessageQueue();

// 📬 Sistema de colas mejorado con Redis (mantener para compatibilidad)
const messageQueues = new Map(); // userId -> array de mensajes (fallback)
const processingUsers = new Set(); // usuarios siendo procesados
const messageBuffers = new Map(); // userId -> { messages: [], timeout: timeoutId }
const processedMessages = new Map(); // userId -> Set de IDs de mensajes procesados
const userLastProcessingTime = new Map(); // userId -> timestamp

// Configuración con variables de entorno
const BUFFER_TIMEOUT_MS = parseInt(process.env.BUFFER_TIMEOUT_MS) || 3000;
const MESSAGE_COOLDOWN_MS = parseInt(process.env.MESSAGE_COOLDOWN_MS) || 1000;

// 🎯 Métricas de rendimiento
const performanceMetrics = {
  messagesPerMinute: [],
  responseTimes: [],
  lastMinuteCount: 0,
  lastMinuteTimestamp: Date.now()
};

// 🔄 Procesador global de colas con sistema inteligente
const startGlobalMessageProcessor = () => {
  const processInterval = setInterval(async () => {
    if (!globalMessageQueue.hasMessages()) return;

    const workerStats = workerPool.getStats();
    const availableWorkers = workerStats.idleWorkers;
    
    // Procesar múltiples mensajes si hay workers disponibles
    const messagesToProcess = Math.min(availableWorkers, 3); // Máximo 3 mensajes por ciclo
    
    for (let i = 0; i < messagesToProcess; i++) {
      const nextMessageItem = globalMessageQueue.getNextMessage();
      
      if (!nextMessageItem) break;
      
      try {
        const startTime = Date.now();
        
        const result = await workerPool.processMessage(nextMessageItem.messageData);
        
        const processingTime = Date.now() - startTime;
        globalMessageQueue.markAsProcessed(processingTime);
        
        // Actualizar métricas de rendimiento
        updatePerformanceMetrics(processingTime);
        
        if (result.success) {
          // Enviar respuesta por WhatsApp
          await sendWhatsAppMessage(
            nextMessageItem.messageData.numero, 
            result.response
          );
          
          logger.metrics('debug', `Mensaje procesado exitosamente por Worker ${result.workerId} en ${processingTime}ms`);
        } else {
          logger.error(`Error procesando mensaje: ${result.error}`);
          
          // Enviar mensaje de error al usuario
          await sendWhatsAppMessage(
            nextMessageItem.messageData.numero, 
            result.response
          );
        }
        
      } catch (error) {
        logger.error(`Error crítico procesando mensaje`, error);
        
        // Reintento después de un delay en caso de error
        setTimeout(() => {
          globalMessageQueue.addMessage(
            nextMessageItem.userId, 
            nextMessageItem.messageData
          );
        }, 5000);
      }
    }
  }, 100); // Verificar cada 100ms para máxima responsividad

  return processInterval;
};

// 📊 Función para actualizar métricas de rendimiento
function updatePerformanceMetrics(processingTime) {
  const now = Date.now();
  
  // Actualizar contador por minuto
  if (now - performanceMetrics.lastMinuteTimestamp > 60000) {
    performanceMetrics.messagesPerMinute.push(performanceMetrics.lastMinuteCount);
    performanceMetrics.lastMinuteCount = 0;
    performanceMetrics.lastMinuteTimestamp = now;
    
    // Mantener solo los últimos 10 minutos
    if (performanceMetrics.messagesPerMinute.length > 10) {
      performanceMetrics.messagesPerMinute.shift();
    }
  }
  
  performanceMetrics.lastMinuteCount++;
  performanceMetrics.responseTimes.push(processingTime);
  
  // Mantener solo los últimos 100 tiempos de respuesta
  if (performanceMetrics.responseTimes.length > 100) {
    performanceMetrics.responseTimes.shift();
  }
}

// 📱 Función optimizada para enviar mensajes de WhatsApp
async function sendWhatsAppMessage(numero, text) {
  try {
    const response = await axios.post(
      `${EVOLUTION_API_URL}/message/sendText/${INSTANCE_NAME}`,
      {
        number: numero,
        textMessage: {
          text: text
        }
      },
      {
        headers: {
          'apikey': INSTANCE_TOKEN,
          'Content-Type': 'application/json'
        },
        timeout: 10000 // 10 segundos de timeout
      }
    );
    
    return response.data;
  } catch (error) {
    logger.error(`Error enviando mensaje a ${numero}:`, error.message);
    throw error;
  }
}

// 🧹 Función para limpiar usuarios bloqueados cada 60 segundos (mantenida para compatibilidad)
setInterval(() => {
  const now = Date.now();
  const blockedUsers = [];
  
  for (const [userId, timestamp] of userLastProcessingTime.entries()) {
    if (now - timestamp > 60000) { // 60 segundos
      blockedUsers.push(userId);
    }
  }
  
  blockedUsers.forEach(userId => {
    processingUsers.delete(userId);
    userLastProcessingTime.delete(userId);
    
    // Reintentar procesar si hay mensajes pendientes
    if (messageQueues.has(userId) && messageQueues.get(userId).length > 0) {
      setTimeout(() => processMessageQueue(userId), 1000);
    }
  });
  
  // Limpiar actividad antigua de la cola de prioridades
  globalMessageQueue.cleanupOldActivity();
}, 60000);

// 🔍 Función mejorada para verificar si un mensaje ya fue procesado usando Redis
async function isMessageAlreadyProcessed(userId, messageId, messageText) {
  try {
    // Verificar primero en Redis si está disponible
    if (redisClient.isAvailable()) {
      const messageKey = `${messageId}-${messageText}`;
      const isProcessed = await redisClient.isMessageProcessed(userId, messageKey);
      
      if (isProcessed) {
        return true;
      }
      
      // Marcar como procesado en Redis
      await redisClient.setProcessedMessage(userId, messageKey);
      return false;
    }
    
    // Fallback a memoria local si Redis no está disponible
    if (!processedMessages.has(userId)) {
      processedMessages.set(userId, new Set());
    }

    const userProcessedMessages = processedMessages.get(userId);
    const messageKey = `${messageId}-${messageText}`;

    if (userProcessedMessages.has(messageKey)) {
      return true;
    }

    userProcessedMessages.add(messageKey);

    // Limpiar mensajes antiguos (mantener solo los últimos 20)
    if (userProcessedMessages.size > 20) {
      const messagesArray = Array.from(userProcessedMessages);
      const toDelete = messagesArray.slice(0, messagesArray.length - 20);
      toDelete.forEach(msg => userProcessedMessages.delete(msg));
    }

    return false;
  } catch (error) {
    return false; // En caso de error, procesar el mensaje
  }
}

// 📬 Función optimizada para manejar buffer de mensajes con sistema nuevo
async function handleMessageBuffer(userId, messageData) {
  try {
    // 🚀 USAR OPTIMIZADOR DE CONCURRENCIA RAILWAY
    if (global.concurrencyOptimizer) {
      const result = await global.concurrencyOptimizer.processWithoutBlocking(userId, messageData);
      
      if (result.success) {
        logger.metrics('debug', `📬 Mensaje procesado por optimizador Railway para ${userId}`);
        return result;
      } else if (result.rateLimited) {
        logger.warn(`⚠️ Rate limit excedido para usuario ${userId}`);
        return result;
      }
    }

    // Fallback al sistema original si el optimizador no está disponible
    // Verificar rate limiting con Redis solo si está disponible
    if (redisClient.isAvailable()) {
      const rateLimitOk = await redisClient.checkRateLimit(
        userId, 
        parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 10,
        parseInt(process.env.RATE_LIMIT_WINDOW_MINUTES) || 1
      );
      
      if (!rateLimitOk) {
        logger.warn(`⚠️ Rate limit excedido para usuario ${userId} (fallback)`);
        return;
      }
    }

    // Verificar si el mensaje ya fue procesado
    if (await isMessageAlreadyProcessed(userId, messageData.messageId, messageData.text)) {
      logger.warn(`⚠️ Mensaje duplicado ignorado para ${userId}`);
      return;
    }

    // Agregar directamente a la cola global con prioridades
    globalMessageQueue.addMessage(userId, messageData);
    
    logger.metrics('debug', `📬 Mensaje de ${userId} agregado a cola global - Total pendientes: ${globalMessageQueue.getStats().total}`);

  } catch (error) {
    logger.error(`❌ Error en buffer para ${userId}:`, error);
    
    // Fallback: agregar a cola local como último recurso
    if (!messageQueues.has(userId)) {
      messageQueues.set(userId, []);
    }
    messageQueues.get(userId).push(messageData);
  }
}

// 🔄 Funciones de fallback para compatibilidad con sistema anterior
async function processMessageQueue(userId) {
  if (processingUsers.has(userId)) {
    return; // Ya se está procesando este usuario
  }

  const queue = messageQueues.get(userId);
  if (!queue || queue.length === 0) {
    return; // No hay mensajes en cola
  }

  processingUsers.add(userId);

  try {
    while (queue.length > 0) {
      const messageData = queue.shift();
      
      // Mover mensaje al sistema nuevo de colas
      globalMessageQueue.addMessage(userId, messageData);

      // Pequeña pausa entre mensajes para evitar spam
      if (queue.length > 0) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  } catch (error) {
    logger.error(`❌ Error procesando cola para ${userId}:`, error);
  } finally {
    processingUsers.delete(userId);
    userLastProcessingTime.delete(userId);
  }
}

// 📊 Funciones para calcular métricas de rendimiento
function calculateMessagesPerMinute() {
  if (performanceMetrics.messagesPerMinute.length === 0) return 0;
  const sum = performanceMetrics.messagesPerMinute.reduce((acc, count) => acc + count, 0);
  return Math.round(sum / performanceMetrics.messagesPerMinute.length);
}

function calculateAverageResponseTime() {
  if (performanceMetrics.responseTimes.length === 0) return 0;
  const sum = performanceMetrics.responseTimes.reduce((acc, time) => acc + time, 0);
  return Math.round(sum / performanceMetrics.responseTimes.length);
}

// 🚀 Inicializar sistema al arrancar
(async () => {
  try {
    logger.info('🔄 Inicializando sistema...');
    
    // Inicializar orquestador de agentes
    await orchestrator.initialize();
    logger.info('✅ Orquestador de agentes inicializado');
    
    // Inicializar pool de workers
    workerPool = new WorkerPool(WORKER_POOL_SIZE, orchestrator);
    logger.info(`✅ Pool de ${WORKER_POOL_SIZE} workers inicializado`);
    
    // 🧠 Inicializar sistema de conocimiento flexible automáticamente (OPTIMIZADO)
    try {
      const FlexibleKnowledgeManager = require('./knowledge/flexibleKnowledgeManager');
      const ResponseOptimizer = require('./optimizations/responseOptimizer');
      
      // Inicializar optimizador de respuestas
      global.responseOptimizer = new ResponseOptimizer();
      
      // Configurar optimizaciones
      global.responseOptimizer.configure({
        preprocessing: {
          enabled: true,
          backgroundInit: true,
          lazyLoading: true,
          parallelProcessing: true
        },
        cacheConfig: {
          maxCacheSize: 1000,
          knowledgeCacheTTL: 60 * 60 * 1000, // 1 hora
          queryCacheTTL: 10 * 60 * 1000 // 10 minutos
        }
      });
      
      logger.info('⚡ Optimizador de respuestas inicializado');
      
      // Inicialización en background para no bloquear el inicio
      const knowledgeManager = new FlexibleKnowledgeManager();
      global.flexibleKnowledgeManager = knowledgeManager;
      
      // Inicialización asíncrona en background
      const backgroundInit = async () => {
        try {
          logger.info('🧠 Iniciando carga de conocimiento en background...');
          
          const knowledgeSuccess = await global.responseOptimizer.optimizedKnowledgeInit(knowledgeManager);
          
          if (knowledgeSuccess) {
            const stats = knowledgeManager.getSystemStats();
            logger.info(`✅ Conocimiento cargado: ${stats.documentsProcessed} docs, ${stats.totalChunks} chunks`);
            
            // Pre-cargar queries comunes para acelerar respuestas
            setTimeout(() => {
              const commonQueries = [
                'como responder a un cliente',
                'saludo',
                'despedida',
                'información de productos',
                'precios'
              ];
              
              commonQueries.forEach(async (query) => {
                try {
                  await global.responseOptimizer.optimizedKnowledgeSearch(knowledgeManager, query);
                } catch (error) {
                  // Ignorar errores en pre-carga
                }
              });
              
              logger.info('📦 Pre-cache de queries comunes completado');
            }, 5000);
            
          } else {
            logger.warn('⚠️ Sistema de conocimiento inicializado con limitaciones');
          }
        } catch (error) {
          logger.warn('⚠️ Error en inicialización background de conocimiento:', error.message);
        }
      };
      
      // Ejecutar en background sin bloquear
      backgroundInit();
      
      logger.info('🚀 Sistema de conocimiento iniciando en background - el bot está listo');
      
    } catch (knowledgeError) {
      logger.warn('⚠️ Error configurando sistema de conocimiento:', knowledgeError.message);
      logger.info('📝 El sistema funcionará sin optimizaciones hasta la primera petición');
    }
    
    // Iniciar procesador global de mensajes
    const processInterval = startGlobalMessageProcessor();
    logger.info('✅ Procesador global de mensajes iniciado');
    
    // 🚀 APLICAR OPTIMIZADOR DE CONCURRENCIA RAILWAY
    if (concurrencyOptimizer) {
      concurrencyOptimizer.patchGlobalSystem();
      global.workerPool = workerPool;
      global.globalMessageQueue = globalMessageQueue;
      logger.info('🚀 Optimizador Railway aplicado al sistema global');
    }
    
    // Manejar cierre limpio
    process.on('SIGTERM', () => {
      logger.info('🛑 Cerrando sistema...');
      clearInterval(processInterval);
      process.exit(0);
    });
    
    process.on('SIGINT', () => {
      logger.info('🛑 Cerrando sistema...');
      clearInterval(processInterval);
      process.exit(0);
    });
    
    logger.info('🚀 Sistema completamente inicializado y listo para recibir mensajes');
    
  } catch (error) {
    logger.error('❌ Error inicializando sistema:', error);
    process.exit(1);
  }
})();

// Función para limpiar buffers de un usuario
function clearUserBuffer(userId) {
  const buffer = messageBuffers.get(userId);
  if (buffer) {
    clearTimeout(buffer.timeout);
    messageBuffers.delete(userId);
  }
}

// Función para limpiar todos los buffers (útil para mantenimiento)
function clearAllBuffers() {
  messageBuffers.forEach((buffer, userId) => {
    clearTimeout(buffer.timeout);
  });
  messageBuffers.clear();
}

// Manejar errores no capturados
process.on('uncaughtException', (error) => {
  logger.error('❌ Error no capturado:', error);
  // Limpiar buffers en caso de error crítico
  clearAllBuffers();
  // No terminar el proceso, solo registrar el error
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('❌ Promesa rechazada no manejada:', reason);
  // No terminar el proceso, solo registrar el error
});

// Configurar webhook de Evolution API
app.post('/webhook-evolution', async (req, res) => {
  try {
    const payload = req.body;

    const text = payload?.data?.message?.conversation || null;
    const from = payload?.data?.key?.remoteJid;
    const pushName = payload?.data?.pushName || null;

    if (!from) {
      return res.status(200).send({ message: "Falta remoteJid." });
    }

    const numero = from.split('@')[0];

    if (!text) {
      return res.status(200).send({ message: "Mensaje sin texto." });
    }

    // 🛑 NUEVA VERIFICACIÓN: Comprobar si el bot está pausado para este usuario
    if (chatwootManager.isBotPausedForUser(numero)) {
      const botState = chatwootManager.getBotStateForUser(numero);
      
      logger.info(`🛑 Mensaje ignorado para usuario ${numero} - Bot pausado: ${botState.reason}`);
      
      return res.status(200).send({ 
        message: "Bot pausado para este usuario",
        reason: botState.reason,
        pausedAt: botState.timestamp,
        userId: numero,
        inboxName: botState.inboxName
      });
    }

    // 📬 Usar sistema optimizado de colas con prioridades
    const messageId = payload?.data?.key?.id || Date.now().toString();
    const messageData = {
      text: text,
      numero: numero,
      pushName: pushName,
      messageId: messageId,
      timestamp: Date.now()
    };

    try {
      // Usar sistema de buffer inteligente optimizado
      await handleMessageBuffer(numero, messageData);
      
      const queueStats = globalMessageQueue.getStats();
      const workerStats = workerPool ? workerPool.getStats() : { activeWorkers: 0, totalWorkers: 0 };
      
      return res.status(200).send({ 
        message: "Mensaje agregado a cola de procesamiento con prioridades",
        queueStats: {
          totalPending: queueStats.total,
          highPriority: queueStats.high,
          normalPriority: queueStats.normal,
          lowPriority: queueStats.low
        },
        workerStats: {
          activeWorkers: workerStats.activeWorkers,
          totalWorkers: workerStats.totalWorkers,
          utilizationRate: workerStats.totalWorkers > 0 ? 
            Math.round((workerStats.activeWorkers / workerStats.totalWorkers) * 100) : 0
        },
        timestamp: new Date().toISOString()
      });

    } catch (bufferError) {
      logger.error(`❌ Error en buffer para ${numero}:`, bufferError);
      
      // Fallback a sistema anterior como último recurso
      try {
        if (!messageQueues.has(numero)) {
          messageQueues.set(numero, []);
        }
        messageQueues.get(numero).push(messageData);
        
        // Intentar procesar con sistema anterior
        setTimeout(() => processMessageQueue(numero), 1000);
        
      } catch (directError) {
        logger.error(`❌ Error en procesamiento directo:`, directError);
      }
      
      return res.status(200).send({ 
        message: "Mensaje agregado a cola de fallback",
        warning: "Sistema principal no disponible, usando fallback"
      });
    }

  } catch (error) {
    logger.error("❌ Error al procesar mensaje:", error.message);

    // Respuesta de fallback
    try {
      const numero = payload?.data?.key?.remoteJid ? payload.data.key.remoteJid.split('@')[0] : null;
      if (numero) {
        await sendWhatsAppMessage(numero, 
          "Lo siento, estoy experimentando dificultades técnicas. Un agente humano te contactará pronto."
        );
      }
    } catch (fallbackError) {
      logger.error("❌ Error en respuesta de fallback:", fallbackError.message);
    }

    return res.status(500).send({ error: "Error interno", detail: error.message });
  }
});

// 🏷️ Webhook específico para cambios de etiquetas de Chatwoot (TIEMPO REAL)
app.post('/webhook-chatwoot-labels', async (req, res) => {
  try {
    const payload = req.body;
    
    // Logging básico del webhook
    logger.debug('chatwoot', `Webhook recibido: ${payload.event_type || payload.event}`);
    
    // 🚀 REGISTRAR actividad de webhook inmediatamente
    const eventType = payload.event_type || payload.event;
    chatwootManager.recordWebhookActivity(eventType, payload.conversation || payload);
    
    logger.debug('chatwoot', 'Webhook recibido:', {
      event_type: eventType,
      conversation_id: payload.conversation?.id || payload.id,
      inbox_id: payload.conversation?.inbox_id || payload.inbox_id,
      labels_count: payload.conversation?.labels?.length || payload.labels?.length || 0
    });

    // 🔧 FLEXIBILIDAD: Verificar diferentes estructuras de eventos
    let conversation = payload.conversation || payload;
    
    // Si no hay conversation pero hay datos directos, usar el payload principal
    if (!payload.conversation && payload.id && payload.inbox_id) {
      conversation = payload;
    }
    

    
    // Verificar que es un evento de etiquetas relevante
    const relevantEvents = [
      'conversation_updated',        // 🎯 EVENTO PRINCIPAL - recomendado por Chatwoot
      'conversation_tag_created',    // Backup: cuando se crea una etiqueta
      'conversation_tag_deleted',    // Backup: cuando se elimina una etiqueta
      'label_created',              // Backup: creación de etiqueta global
      'label_updated'               // Backup: actualización de etiqueta global
    ];
    
    // Log especial para el evento principal
    if (eventType === 'conversation_updated') {
      logger.debug('chatwoot', `🎯 Evento PRINCIPAL recibido: ${eventType} - garantiza detección de cambios de etiquetas`);
    }
    
    if (eventType && !relevantEvents.includes(eventType)) {
      logger.debug('chatwoot', `Evento ${eventType} no relevante para control de bot. Usar: conversation_updated (recomendado)`);
      return res.status(200).send({ 
        message: 'Evento no relevante para control de bot',
        recommendedEvent: 'conversation_updated',
        receivedEvent: eventType,
        payloadStructure: Object.keys(payload)
      });
    }

    if (!conversation || !conversation.id) {
      logger.debug('chatwoot', 'Webhook sin datos de conversación válidos:', {
        hasConversation: !!payload.conversation,
        hasId: !!payload.id,
        hasInboxId: !!(payload.inbox_id || payload.conversation?.inbox_id),
        payloadKeys: Object.keys(payload)
      });
      return res.status(200).send({ message: 'Sin datos de conversación válidos' });
    }

    // Verificar que es del inbox correcto (si está configurado)
    const inboxId = conversation.inbox_id;
    

    
    if (chatwootManager.inboxId && inboxId != chatwootManager.inboxId) {
      logger.debug('chatwoot', `Inbox ${inboxId} no monitoreado (configurado: ${chatwootManager.inboxId})`);
      return res.status(200).send({ message: 'Inbox no monitoreado' });
    }

    // Verificar filtro de múltiples inboxes
    if (chatwootManager.inboxIds.length > 0 && !chatwootManager.inboxIds.map(id => parseInt(id)).includes(inboxId)) {
      logger.debug('chatwoot', `Inbox ${inboxId} no está en lista monitoreada: ${chatwootManager.inboxIds}`);
      return res.status(200).send({ message: 'Inbox no en lista monitoreada' });
    }

    // Extraer número de teléfono
    const phoneNumber = chatwootManager.extractPhoneFromConversation(conversation);
    if (!phoneNumber) {
      logger.debug('chatwoot', 'No se pudo extraer número de teléfono:', {
        conversation_id: conversation.id,
        meta: conversation.meta,
        contact: conversation.contact,
        identifier: conversation.meta?.sender?.identifier
      });
      return res.status(200).send({ message: 'No se pudo extraer número de teléfono' });
    }

    // Analizar etiquetas actuales
    const currentTags = conversation.labels || [];

    // 🔧 FUNCIONALIDAD MEJORADA: Buscar etiquetas en changed_attributes con mejor detección
    let finalTags = currentTags;
    let foundInChangedAttributes = false;
    let detectionSource = 'none';
    
    if (currentTags.length === 0 && conversation.changed_attributes) {
      for (const change of conversation.changed_attributes) {
        // Buscar en diferentes posibles estructuras
        if (change.label_list && change.label_list.current_value) {
          finalTags = change.label_list.current_value.map(tag => 
            typeof tag === 'string' ? { title: tag } : tag
          );
          foundInChangedAttributes = true;
          detectionSource = 'label_list.current_value';
          break;
        } else if (change.cached_label_list && change.cached_label_list.current_value) {
          finalTags = change.cached_label_list.current_value.split(',').filter(Boolean).map(tag => ({ title: tag.trim() }));
          foundInChangedAttributes = true;
          detectionSource = 'cached_label_list.current_value';
          break;
        } else if (change.labels && Array.isArray(change.labels)) {
          finalTags = change.labels.map(tag => 
            typeof tag === 'string' ? { title: tag } : tag
          );
          foundInChangedAttributes = true;
          detectionSource = 'changed_attributes.labels';
          break;
        } else if (change.current_value && Array.isArray(change.current_value)) {
          finalTags = change.current_value.map(tag => 
            typeof tag === 'string' ? { title: tag } : tag
          );
          foundInChangedAttributes = true;
          detectionSource = 'current_value_array';
          break;
        }
      }
    } else if (currentTags.length > 0) {
      detectionSource = 'conversation.labels';
    }

    // 🔧 NUEVO: Buscar también en el payload principal si no encontramos nada
    if (finalTags.length === 0 && payload.labels && Array.isArray(payload.labels)) {
      finalTags = payload.labels.map(tag => 
        typeof tag === 'string' ? { title: tag } : tag
      );
      detectionSource = 'payload.labels';
    }

    logger.debug('chatwoot', `Analizando ${finalTags.length} etiquetas para usuario ${phoneNumber}:`, 
      finalTags.map(tag => tag.title || tag.name)
    );

    const botControlTags = chatwootManager.analyzeBotControlTags(finalTags);
    
    if (botControlTags.action) {
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      // Procesar cambio de estado INMEDIATAMENTE
      if (botControlTags.action === 'pause' && !currentState.paused) {
        chatwootManager.pauseBotForUser(phoneNumber, botControlTags.reason, conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot pausado INMEDIATAMENTE para ${phoneNumber}: ${botControlTags.reason} (etiqueta: ${botControlTags.tag})`);
        
        return res.status(200).send({ 
          message: 'Bot pausado inmediatamente',
          userId: phoneNumber,
          reason: botControlTags.reason,
          tag: botControlTags.tag,
          event: eventType,
          source: detectionSource,
          detectedTags: finalTags.map(tag => tag.title || tag.name || tag),
          timestamp: new Date().toISOString()
        });
        
      } else if (botControlTags.action === 'resume' && currentState.paused) {
        chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot reactivado INMEDIATAMENTE para ${phoneNumber} (etiqueta: ${botControlTags.tag})`);
        
        return res.status(200).send({ 
          message: 'Bot reactivado inmediatamente',
          userId: phoneNumber,
          tag: botControlTags.tag,
          event: eventType,
          source: detectionSource,
          detectedTags: finalTags.map(tag => tag.title || tag.name || tag),
          timestamp: new Date().toISOString()
        });
        
      } else {
        logger.debug('chatwoot', `Sin cambio de estado para ${phoneNumber}: action=${botControlTags.action}, currentPaused=${currentState.paused}`);
      }
    } else {
      logger.debug('chatwoot', `Sin etiquetas de control detectadas para ${phoneNumber}`);
    }

    // 🚀 NUEVO: Control por estado de conversación (BACKUP si etiquetas fallan)
    const conversationStatus = conversation.status;
    
    if (conversationStatus === 'resolved' || conversationStatus === 'closed') {
      // Pausar bot cuando se resuelve la conversación
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (!currentState.paused) {
        chatwootManager.pauseBotForUser(phoneNumber, 'Conversación resuelta', conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot pausado por ESTADO para ${phoneNumber}: conversación ${conversationStatus}`);
        
        return res.status(200).send({ 
          message: 'Bot pausado por estado de conversación',
          userId: phoneNumber,
          reason: `Conversación ${conversationStatus}`,
          method: 'conversation_status',
          event: eventType,
          timestamp: new Date().toISOString()
        });
      }
      
    } else if (conversationStatus === 'open' || conversationStatus === 'pending') {
      // Reactivar bot cuando se abre la conversación
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (currentState.paused && currentState.reason === 'Conversación resuelta') {
        chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot reactivado por ESTADO para ${phoneNumber}: conversación ${conversationStatus}`);
        
        return res.status(200).send({ 
          message: 'Bot reactivado por estado de conversación',
          userId: phoneNumber,
          method: 'conversation_status',
          event: eventType,
          timestamp: new Date().toISOString()
        });
      }
    }

    // 🎯 NUEVO: Control por asignación de agente (OPCIÓN ADICIONAL)
    const assigneeId = conversation.assignee_id;
    
    if (assigneeId && assigneeId !== null) {
      // Bot pausado: hay agente asignado
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (!currentState.paused) {
        chatwootManager.pauseBotForUser(phoneNumber, 'Agente asignado', conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot pausado por ASIGNACIÓN para ${phoneNumber}: agente ID ${assigneeId}`);
        
        return res.status(200).send({ 
          message: 'Bot pausado por asignación de agente',
          userId: phoneNumber,
          reason: 'Agente asignado',
          assignee_id: assigneeId,
          method: 'agent_assignment',
          event: eventType,
          timestamp: new Date().toISOString()
        });
      }
      
    } else if (assigneeId === null || assigneeId === undefined) {
      // Bot activo: sin agente asignado
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (currentState.paused && currentState.reason === 'Agente asignado') {
        chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 WEBHOOK: Bot reactivado por DESASIGNACIÓN para ${phoneNumber}`);
        
        return res.status(200).send({ 
          message: 'Bot reactivado por desasignación de agente',
          userId: phoneNumber,
          method: 'agent_unassignment',
          event: eventType,
          timestamp: new Date().toISOString()
        });
      }
    }

    return res.status(200).send({ 
      message: 'Webhook procesado - sin cambios de estado',
      userId: phoneNumber,
      event: eventType,
      conversationStatus: conversationStatus,
      assigneeId: assigneeId,
      controlMethods: {
        labels: finalTags.length > 0 ? 'available' : 'none',
        conversationStatus: conversationStatus,
        agentAssignment: assigneeId ? 'assigned' : 'unassigned'
      },
      labelsAnalyzed: finalTags.length,
      labelsSource: foundInChangedAttributes ? 'changed_attributes' : currentTags.length > 0 ? 'conversation.labels' : finalTags.length > 0 ? 'payload.labels' : 'none',
      labelsFound: finalTags.map(tag => tag.title || tag.name),
      payloadStructure: Object.keys(payload),
      timestamp: new Date().toISOString()
    });

  } catch (error) {

    
    logger.error('Error procesando webhook de Chatwoot:', {
      message: error.message,
      stack: error.stack,
      payload: req.body
    });
    return res.status(500).send({ 
      error: 'Error procesando webhook',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// 🧪 MEJORADO: Endpoint para simular webhook de Chatwoot con datos de prueba
app.post('/bot-control/simulate-webhook', async (req, res) => {
  try {
    const { userId, action, tag, status, assignee_id } = req.body;
    
    // Permitir diferentes tipos de simulación
    if (!userId || !action) {
      return res.status(400).json({
        error: 'Parámetros requeridos: userId, action (pause/resume)',
        optional: 'tag, status, assignee_id',
        examples: [
          {
            type: 'por_etiqueta',
            userId: '5491112345678',
            action: 'pause',
            tag: 'stop_bot'
          },
          {
            type: 'por_estado',
            userId: '5491112345678',
            action: 'pause',
            status: 'resolved'
          },
          {
            type: 'por_asignacion',
            userId: '5491112345678',
            action: 'pause',
            assignee_id: 123
          }
        ]
      });
    }

    // Crear payload simulado de Chatwoot
    const simulatedPayload = {
      event_type: 'conversation_updated',
      conversation: {
        id: Date.now(),
        inbox_id: 1,
        labels: tag ? [{ title: tag }] : [],
        status: status || 'open',
        assignee_id: assignee_id || null,
        meta: {
          sender: {
            identifier: `${userId}@s.whatsapp.net`
          }
        }
      }
    };

    let result;
    
    // Si es simulación por etiquetas, usar el método existente
    if (tag) {
      result = await chatwootManager.processWebhookImmediately(simulatedPayload.conversation);
    } else {
      // Simulación directa por estado o asignación
      const conversation = simulatedPayload.conversation;
      const phoneNumber = userId;
      
      if (status && (status === 'resolved' || status === 'closed')) {
        // Test por estado: pausar
        const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
        
        if (!currentState.paused) {
          chatwootManager.pauseBotForUser(phoneNumber, 'Conversación resuelta', conversation.id, conversation.inbox_id);
          result = { success: true, action: 'paused', method: 'conversation_status', reason: `Conversación ${status}` };
        } else {
          result = { success: false, action: 'already_paused', currentState: currentState };
        }
        
      } else if (status && (status === 'open' || status === 'pending')) {
        // Test por estado: reactivar
        const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
        
        if (currentState.paused && currentState.reason === 'Conversación resuelta') {
          chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
          result = { success: true, action: 'resumed', method: 'conversation_status' };
        } else {
          result = { success: false, action: currentState.paused ? 'paused_by_other_reason' : 'already_active', currentState: currentState };
        }
        
      } else if (assignee_id !== undefined) {
        // Test por asignación
        const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
        
        if (assignee_id && assignee_id !== null) {
          // Pausar por asignación
          if (!currentState.paused) {
            chatwootManager.pauseBotForUser(phoneNumber, 'Agente asignado', conversation.id, conversation.inbox_id);
            result = { success: true, action: 'paused', method: 'agent_assignment', assignee_id: assignee_id };
          } else {
            result = { success: false, action: 'already_paused', currentState: currentState };
          }
        } else {
          // Reactivar por desasignación
          if (currentState.paused && currentState.reason === 'Agente asignado') {
            chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
            result = { success: true, action: 'resumed', method: 'agent_unassignment' };
          } else {
            result = { success: false, action: currentState.paused ? 'paused_by_other_reason' : 'already_active', currentState: currentState };
          }
        }
      } else {
        result = { success: false, action: 'no_valid_method', message: 'Debe especificar tag, status o assignee_id' };
      }
    }

    res.json({
      message: `Webhook simulado para ${action}`,
      userId: userId,
      method: tag ? 'labels' : status ? 'conversation_status' : assignee_id !== undefined ? 'agent_assignment' : 'unknown',
      simulatedPayload: simulatedPayload,
      result: result,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'Error simulando webhook',
      detail: error.message
    });
  }
});

// 🧪 NUEVO: Endpoint específico para probar control por estado
app.post('/bot-control/test-status-control', async (req, res) => {
  try {
    const { userId, status } = req.body;
    
    if (!userId || !status) {
      return res.status(400).json({
        error: 'Parámetros requeridos: userId, status (resolved/open/pending/closed)',
        example: {
          userId: '5493547642250',
          status: 'resolved'
        }
      });
    }

    // Crear payload simulado con estado específico
    const simulatedPayload = {
      event_type: 'conversation_updated',
      conversation: {
        id: Date.now(),
        inbox_id: 1,
        status: status,
        labels: [],
        meta: {
          sender: {
            identifier: `${userId}@s.whatsapp.net`
          }
        }
      }
    };

    // Simular el procesamiento interno del webhook principal
    const conversation = simulatedPayload.conversation;
    const phoneNumber = userId;
    const conversationStatus = conversation.status;
    
    let result = { processed: false, action: 'none', reason: 'No change needed' };
    
    if (conversationStatus === 'resolved' || conversationStatus === 'closed') {
      // Pausar bot cuando se resuelve la conversación
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (!currentState.paused) {
        chatwootManager.pauseBotForUser(phoneNumber, 'Conversación resuelta', conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 TEST: Bot pausado por ESTADO para ${phoneNumber}: conversación ${conversationStatus}`);
        
        result = {
          processed: true,
          action: 'paused',
          reason: `Conversación ${conversationStatus}`,
          method: 'conversation_status'
        };
      } else {
        result = {
          processed: false,
          action: 'already_paused',
          reason: 'Bot ya estaba pausado',
          currentState: currentState
        };
      }
      
    } else if (conversationStatus === 'open' || conversationStatus === 'pending') {
      // Reactivar bot cuando se abre la conversación
      const currentState = chatwootManager.getBotStateForUser(phoneNumber) || { paused: false };
      
      if (currentState.paused && currentState.reason === 'Conversación resuelta') {
        chatwootManager.resumeBotForUser(phoneNumber, conversation.id, conversation.inbox_id);
        
        logger.info(`🚀 TEST: Bot reactivado por ESTADO para ${phoneNumber}: conversación ${conversationStatus}`);
        
        result = {
          processed: true,
          action: 'resumed',
          method: 'conversation_status'
        };
      } else {
        result = {
          processed: false,
          action: currentState.paused ? 'paused_by_other_reason' : 'already_active',
          reason: currentState.paused ? `Pausado por: ${currentState.reason}` : 'Bot ya estaba activo',
          currentState: currentState
        };
      }
    }

    res.json({
      message: `Test de control por estado: ${status}`,
      userId: userId,
      simulatedPayload: simulatedPayload,
      result: result,
      conversationStatus: conversationStatus,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'Error en test de control por estado',
      detail: error.message
    });
  }
});

// 🔍 MEJORADO: Endpoint de debug con más información
app.post('/webhook-chatwoot-debug', async (req, res) => {
  try {
    const payload = req.body;
    
    // 📊 LOG COMPLETO y ESTRUCTURADO para debugging
    const debugInfo = {
      timestamp: new Date().toISOString(),
      event_type: payload.event_type || payload.event,
      conversation_id: payload.conversation?.id || payload.id,
      inbox_id: payload.conversation?.inbox_id || payload.inbox_id,
      labels: {
        conversation_labels: payload.conversation?.labels?.map(l => l.title || l.name) || [],
        payload_labels: payload.labels?.map(l => l.title || l.name) || [],
        changed_attributes: payload.conversation?.changed_attributes || []
      },
      user_info: {
        phone: payload.conversation?.meta?.sender?.identifier || 'No encontrado',
        contact_id: payload.conversation?.contact?.id || 'No encontrado'
      },
      headers: {
        user_agent: req.get('User-Agent'),
        content_type: req.get('Content-Type'),
        authorization: req.get('Authorization') ? 'Presente' : 'Ausente'
      },
      payload_structure: {
        main_keys: Object.keys(payload),
        conversation_keys: payload.conversation ? Object.keys(payload.conversation) : [],
        has_conversation: !!payload.conversation,
        has_labels: !!(payload.conversation?.labels || payload.labels),
        has_changed_attributes: !!payload.conversation?.changed_attributes
      }
    };
    
    logger.debug('chatwoot', 'Webhook debug info captured', debugInfo);
    
    // Guardar para consulta posterior con más detalle
    global.lastWebhookDebug = {
      timestamp: new Date().toISOString(),
      payload: payload,
      headers: req.headers,
      debugInfo: debugInfo,
      analysis: {
        canExtractPhone: !!chatwootManager.extractPhoneFromConversation(payload.conversation || payload),
        hasValidLabels: (payload.conversation?.labels?.length || 0) > 0 || (payload.labels?.length || 0) > 0,
        eventSupported: ['conversation_updated', 'conversation_tag_created', 'conversation_tag_deleted'].includes(payload.event_type)
      }
    };
    
    // 🚀 REGISTRAR actividad de webhook
    const eventType = payload.event_type || payload.event;
    chatwootManager.recordWebhookActivity(eventType, payload.conversation || payload);
    
    return res.status(200).send({ 
      message: 'Webhook debug registrado con información completa',
      timestamp: new Date().toISOString(),
      event_type: eventType,
      conversation_id: payload.conversation?.id || payload.id,
      analysis: global.lastWebhookDebug.analysis,
      debugEndpoints: {
        viewLast: '/webhook-debug/last',
        monitor: '/webhook-debug/monitor',
        simulate: '/bot-control/simulate-webhook'
      }
    });
    
  } catch (error) {
    logger.error('Error en webhook debug:', error.message);
    return res.status(500).send({ error: error.message });
  }
});

// 🔍 Endpoint para ver el último webhook recibido
app.get('/webhook-debug/last', (req, res) => {
  try {
    res.json({
      message: 'Último webhook debug registrado',
      data: global.lastWebhookDebug || { message: 'No hay webhooks registrados aún' },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🔍 Endpoint para monitorear webhooks en tiempo real
app.get('/webhook-debug/monitor', (req, res) => {
  try {
    const stats = chatwootManager.getStats();
    
    res.json({
      message: 'Monitor de webhooks en tiempo real',
      webhookActivity: {
        lastReceived: stats.lastWebhookReceived ? new Date(stats.lastWebhookReceived).toISOString() : 'Nunca',
        totalCount: stats.webhookCount || 0,
        lastData: stats.lastWebhookData || 'No hay datos'
      },
      currentTime: new Date().toISOString(),
      timeSinceLastWebhook: stats.lastWebhookReceived ? 
        Math.round((Date.now() - stats.lastWebhookReceived) / 1000) + ' segundos' : 
        'Nunca recibido',
      instructions: [
        '1. Configura un webhook en Chatwoot que apunte a /webhook-chatwoot-debug',
        '2. Agrega/quita etiquetas en una conversación',
        '3. Ve los resultados actualizarse aquí',
        '4. Verifica que el event_type sea "conversation_updated"'
      ],
      debugEndpoints: {
        debug: '/webhook-chatwoot-debug (para capturar todo)',
        lastWebhook: '/webhook-debug/last (último webhook capturado)',
        production: '/webhook-chatwoot-labels (endpoint de producción)'
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 📚 Endpoint para agregar conocimiento
app.post('/knowledge', async (req, res) => {
  try {
    const { category, content, metadata } = req.body;

    if (!category || !content) {
      return res.status(400).send({ error: "Faltan parámetros: category y content son requeridos" });
    }

    await orchestrator.addKnowledge(category, content, metadata);

    res.send({ 
      message: `Conocimiento agregado a la categoría: ${category}`,
      success: true 
    });
  } catch (error) {
    logger.error("❌ Error agregando conocimiento:", error);
    res.status(500).send({ error: "Error agregando conocimiento", detail: error.message });
  }
});

// 📁 Endpoint para cargar documentos
app.post('/upload-document', async (req, res) => {
  try {
    const { knowledgeBase, content, fileName, fileType } = req.body;

    if (!knowledgeBase || !content || !fileName) {
      return res.status(400).send({ 
        error: "Faltan parámetros: knowledgeBase, content y fileName son requeridos" 
      });
    }

    if (!orchestrator.knowledgeBases[knowledgeBase]) {
      return res.status(400).send({ 
        error: `Base de conocimiento '${knowledgeBase}' no existe` 
      });
    }

    // Crear buffer desde content (base64 o texto)
    let buffer;
    if (fileType === 'pdf' || fileType === 'binary') {
      buffer = Buffer.from(content, 'base64');
    } else {
      buffer = Buffer.from(content, 'utf8');
    }

    const result = await orchestrator.knowledgeBases[knowledgeBase].processDocument(
      fileName, 
      buffer
    );

    if (result.success) {
      await orchestrator.knowledgeBases[knowledgeBase].save('./data');
    }

    res.send({
      message: `Documento ${fileName} procesado`,
      result: result,
      knowledgeBase: knowledgeBase
    });

  } catch (error) {
    logger.error("❌ Error procesando documento:", error);
    res.status(500).send({ 
      error: "Error procesando documento", 
      detail: error.message 
    });
  }
});

// 📂 Endpoint para procesar directorio
app.post('/process-directory', async (req, res) => {
  try {
    const { knowledgeBase, directory, fileTypes } = req.body;

    if (!knowledgeBase || !directory) {
      return res.status(400).send({ 
        error: "Faltan parámetros: knowledgeBase y directory son requeridos" 
      });
    }

    if (!orchestrator.knowledgeBases[knowledgeBase]) {
      return res.status(400).send({ 
        error: `Base de conocimiento '${knowledgeBase}' no existe` 
      });
    }

    const results = await orchestrator.knowledgeBases[knowledgeBase].bulkProcessDirectory(
      directory, 
      fileTypes
    );

    await orchestrator.knowledgeBases[knowledgeBase].save('./data');

    res.send({
      message: `Directorio ${directory} procesado`,
      results: results,
      totalProcessed: results.filter(r => r.success).length,
      totalErrors: results.filter(r => !r.success).length
    });

  } catch (error) {
    logger.error("❌ Error procesando directorio:", error);
    res.status(500).send({ 
      error: "Error procesando directorio", 
      detail: error.message 
    });
  }
});

// 🎛️ Endpoints para gestión de colas de prioridades
app.post('/queue/priority/change', (req, res) => {
  try {
    const { queueId, newPriority } = req.body;
    
    if (!queueId || !['high', 'normal', 'low'].includes(newPriority)) {
      return res.status(400).json({ 
        error: 'Parámetros inválidos. Requeridos: queueId, newPriority (high/normal/low)' 
      });
    }
    
    const success = globalMessageQueue.changePriority(queueId, newPriority);
    
    res.json({
      success,
      message: success ? 
        `Mensaje ${queueId} movido a prioridad ${newPriority}` : 
        `Mensaje ${queueId} no encontrado`,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.delete('/queue/user/:userId', (req, res) => {
  try {
    const { userId } = req.params;
    const removedCount = globalMessageQueue.removeUserMessages(userId);
    
    res.json({
      message: `Removidos ${removedCount} mensajes del usuario ${userId}`,
      removedCount,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/queue/user/:userId/info', (req, res) => {
  try {
    const { userId } = req.params;
    const userInfo = globalMessageQueue.getUserInfo(userId);
    const userMessages = globalMessageQueue.getUserMessages(userId);
    
    res.json({
      userInfo,
      messages: userMessages,
      messageCount: userMessages.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/queue/cleanup', (req, res) => {
  try {
    const { maxAge } = req.body;
    const cleanedCount = globalMessageQueue.cleanupOldActivity(maxAge);
    
    res.json({
      message: `Limpieza completada. ${cleanedCount} usuarios inactivos removidos`,
      cleanedCount,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🛠️ Endpoint mejorado para liberar usuarios bloqueados con soporte para sistema nuevo
app.post('/debug/clear-user/:userId', (req, res) => {
  const { userId } = req.params;
  
  let actions = [];
  
  // Limpiar del sistema antiguo
  if (processingUsers.has(userId)) {
    processingUsers.delete(userId);
    userLastProcessingTime.delete(userId);
    messageBuffers.delete(userId);
    actions.push('sistema_legacy');
  }
  
  // Limpiar del sistema nuevo
  const removedFromQueue = globalMessageQueue.removeUserMessages(userId);
  if (removedFromQueue > 0) {
    actions.push(`${removedFromQueue}_mensajes_cola_nueva`);
  }
  
  // Reintentar procesar si hay mensajes pendientes en sistema antiguo
  if (messageQueues.has(userId) && messageQueues.get(userId).length > 0) {
    setTimeout(() => processMessageQueue(userId), 1000);
    actions.push('reintento_cola_legacy');
  }
  
  res.send({ 
    success: actions.length > 0,
    message: actions.length > 0 ? 
      `Usuario ${userId} liberado de: ${actions.join(', ')}` : 
      `Usuario ${userId} no estaba bloqueado`,
    actions,
    timestamp: new Date().toISOString()
  });
});

// 🛠️ Endpoint de debug para ver estado del sistema
app.get('/debug/status', (req, res) => {
  const queueStats = globalMessageQueue.getStats();
  const workerStats = workerPool ? workerPool.getStats() : null;
  
  res.send({
    timestamp: new Date().toISOString(),
    global: {
      queues: queueStats,
      workers: workerStats,
      nextMessagesPreview: globalMessageQueue.peekNextMessages(3)
    },
    legacy: {
      processingUsers: Array.from(processingUsers),
      messageQueues: Object.fromEntries(
        Array.from(messageQueues.entries()).map(([key, value]) => [key, value.length])
      ),
      messageBuffers: Object.fromEntries(
        Array.from(messageBuffers.entries()).map(([key, value]) => [key, value.messages.length])
      ),
      lastProcessingTimes: Object.fromEntries(userLastProcessingTime)
    },
    performance: {
      messagesPerMinute: calculateMessagesPerMinute(),
      averageResponseTime: calculateAverageResponseTime(),
      currentMinuteMessages: performanceMetrics.lastMinuteCount
    }
  });
});

// 🧪 Endpoint de prueba para el bot
app.post('/test-bot', async (req, res) => {
  try {
    const { message, userId } = req.body;

    if (!message) {
      return res.status(400).send({ error: "Parámetro 'message' es requerido" });
    }

    const testUserId = userId || 'test-user-' + Date.now();

    const result = await orchestrator.processMessage(testUserId, message);

    res.send({
      message: "Bot probado exitosamente",
      input: message,
      output: result.response,
      agent: result.agent,
      confidence: result.confidence,
      userId: testUserId
    });

  } catch (error) {
    logger.error("❌ Error en prueba del bot:", error);
    res.status(500).send({ 
      error: "Error probando el bot", 
      detail: error.message 
    });
  }
});

// 📊 Endpoint para estadísticas
app.get('/stats', async (req, res) => {
  try {
    const queueStats = globalMessageQueue.getStats();
    const workerStats = workerPool ? workerPool.getStats() : null;
    const redisStats = await redisClient.getStats();
    
    const stats = {
      timestamp: new Date().toISOString(),
      system: {
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        version: process.env.npm_package_version || '1.0.0'
      },
      queues: {
        global: queueStats,
        legacy: {
          activeUsers: processingUsers.size,
          queuedMessages: Array.from(messageQueues.values()).reduce((acc, queue) => acc + queue.length, 0),
          bufferedMessages: Array.from(messageBuffers.values()).reduce((acc, buffer) => acc + buffer.messages.length, 0)
        }
      },
      workers: workerStats,
      performance: {
        messagesPerMinute: calculateMessagesPerMinute(),
        averageResponseTime: calculateAverageResponseTime(),
        currentMinuteMessages: performanceMetrics.lastMinuteCount,
        recentResponseTimes: performanceMetrics.responseTimes.slice(-10) // Últimos 10 tiempos
      },
      redis: redisStats
    };
    
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 📊 Endpoint para estadísticas avanzadas con métricas detalladas
app.get('/stats/advanced', async (req, res) => {
  try {
    const workerStats = workerPool ? workerPool.getStats() : null;
    const queueStats = globalMessageQueue.getStats();
    
    const stats = {
      timestamp: new Date().toISOString(),
      workers: workerStats,
      queues: {
        priority: queueStats,
        nextMessages: globalMessageQueue.peekNextMessages(5),
        userDistribution: queueStats.userDistribution,
        queueAges: queueStats.queueAges
      },
      performance: {
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        cpu: process.cpuUsage(),
        messagesPerMinute: calculateMessagesPerMinute(),
        averageResponseTime: calculateAverageResponseTime(),
        recentMetrics: {
          lastMinuteMessages: performanceMetrics.lastMinuteCount,
          responseTimes: performanceMetrics.responseTimes.slice(-10),
          messagesPerMinuteHistory: performanceMetrics.messagesPerMinute
        }
      },
      redis: await redisClient.getStats(),
      environment: {
        nodeEnv: process.env.NODE_ENV || 'development',
        workerPoolSize: WORKER_POOL_SIZE,
        maxConcurrentUsers: MAX_CONCURRENT_USERS,
        bufferTimeout: BUFFER_TIMEOUT_MS,
        messageCooldown: MESSAGE_COOLDOWN_MS
      }
    };
    
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🚀 Endpoint para estadísticas del optimizador Railway
app.get('/stats/railway-optimizer', async (req, res) => {
  try {
    if (!global.concurrencyOptimizer) {
      return res.status(404).json({ 
        error: 'Optimizador Railway no disponible',
        available: false 
      });
    }

    const optimizerStats = await global.concurrencyOptimizer.getDetailedPerformanceStats();
    const dashboardMetrics = global.concurrencyOptimizer.getMetricsForDashboard();
    
    const stats = {
      timestamp: new Date().toISOString(),
      available: true,
      optimizer: optimizerStats,
      dashboard: dashboardMetrics,
      config: global.concurrencyOptimizer.config,
      comparison: {
        withOptimizer: {
          activeUsers: optimizerStats.activeUsers,
          bufferedMessages: optimizerStats.totalBufferedMessages,
          averageResponseTime: optimizerStats.averageResponseTime,
          processedMessages: optimizerStats.processedMessages,
          failedMessages: optimizerStats.failedMessages
        },
        legacy: {
          activeUsers: processingUsers.size,
          queuedMessages: Array.from(messageQueues.values()).reduce((acc, queue) => acc + queue.length, 0),
          bufferedMessages: Array.from(messageBuffers.values()).reduce((acc, buffer) => acc + buffer.messages.length, 0)
        }
      },
      performance: {
        memoryUsage: optimizerStats.memoryUsage,
        uptime: optimizerStats.uptime,
        peakConcurrency: optimizerStats.peakConcurrency,
        systemLoad: process.cpuUsage()
      }
    };
    
    res.json(stats);
  } catch (error) {
    res.status(500).json({ 
      error: 'Error obteniendo estadísticas del optimizador', 
      detail: error.message 
    });
  }
});

// 🎛️ Endpoint para ajustar configuración en tiempo real
app.put('/config/performance', async (req, res) => {
  try {
    const { 
      maxConcurrentUsers, 
      bufferTimeout, 
      workerPoolSize,
      resetWorkers 
    } = req.body;
    
    let changes = {};
    
    if (maxConcurrentUsers && maxConcurrentUsers !== MAX_CONCURRENT_USERS) {
      process.env.MAX_CONCURRENT_USERS = maxConcurrentUsers.toString();
      changes.maxConcurrentUsers = maxConcurrentUsers;
    }
    
    if (bufferTimeout && bufferTimeout !== BUFFER_TIMEOUT_MS) {
      process.env.BUFFER_TIMEOUT_MS = bufferTimeout.toString();
      changes.bufferTimeout = bufferTimeout;
    }
    
    if (workerPoolSize && workerPool && workerPoolSize !== workerPool.getStats().totalWorkers) {
      await workerPool.resizePool(workerPoolSize);
      changes.workerPoolSize = workerPoolSize;
    }
    
    if (resetWorkers && workerPool) {
      workerPool.resetWorkers();
      changes.workersReset = true;
    }
    
    res.json({
      message: 'Configuración actualizada',
      changes: changes,
      currentConfig: {
        maxConcurrentUsers: process.env.MAX_CONCURRENT_USERS,
        bufferTimeout: process.env.BUFFER_TIMEOUT_MS,
        workerPoolSize: workerPool ? workerPool.getStats().totalWorkers : 0
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ 
      error: 'Error actualizando configuración', 
      detail: error.message 
    });
  }
});

// 📊 Endpoint para obtener historial de interacciones de un usuario
app.get('/user/:userId/interactions', async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit, search } = req.query;

    if (search) {
      const interactions = await orchestrator.searchUserInteractions(userId, search, parseInt(limit) || 10);
      res.send({
        userId,
        searchTerm: search,
        interactions,
        totalFound: interactions.length
      });
    } else {
      const interactions = await orchestrator.getUserInteractionHistory(userId, parseInt(limit) || null);
      res.send({
        userId,
        interactions,
        total: interactions.length
      });
    }
  } catch (error) {
    logger.error('❌ Error obteniendo interacciones:', error);
    res.status(500).send({ error: 'Error obteniendo interacciones', detail: error.message });
  }
});

// 🚨 Endpoint para reactivar bot después de intervención humana (uso administrativo)
app.post('/reactivate-bot/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const { adminToken } = req.body;

    // Verificación básica de seguridad (implementar según necesidades)
    if (adminToken !== process.env.ADMIN_TOKEN) {
      return res.status(403).send({ error: 'Token de administrador inválido' });
    }

    await orchestrator.reactivateBotForUser(userId);

    res.send({
      message: `Bot reactivado para usuario ${userId}`,
      success: true,
      timestamp: new Date()
    });
  } catch (error) {
    logger.error('❌ Error reactivando bot:', error);
    res.status(500).send({ error: 'Error reactivando bot', detail: error.message });
  }
});

// 🚨 Endpoint para obtener usuarios que requieren intervención humana
app.get('/human-intervention-required', async (req, res) => {
  try {
    const { adminToken } = req.query;

    if (adminToken !== process.env.ADMIN_TOKEN) {
      return res.status(403).send({ error: 'Token de administrador inválido' });
    }

    const allUsers = await orchestrator.getAllUsers();
    const usersRequiringIntervention = [];

    for (const userId of allUsers) {
      const requiresIntervention = await orchestrator.userRequiresHumanIntervention(userId);
      if (requiresIntervention) {
        const state = await orchestrator.getConversationState(userId);
        const stats = await orchestrator.getUserStats(userId);
        usersRequiringIntervention.push({
          userId,
          escalationReason: state.escalationReason,
          escalationTimestamp: state.escalationTimestamp,
          userName: orchestrator.getUserName(userId),
          totalInteractions: stats.totalInteractions,
          lastInteraction: state.lastInteraction
        });
      }
    }

    res.send({
      totalUsersRequiringIntervention: usersRequiringIntervention.length,
      users: usersRequiringIntervention,
      timestamp: new Date()
    });
  } catch (error) {
    logger.error('❌ Error obteniendo usuarios para intervención:', error);
    res.status(500).send({ error: 'Error obteniendo datos', detail: error.message });
  }
});

// 📊 Endpoint para estadísticas de un usuario específico
app.get('/user/:userId/stats', async (req, res) => {
  try {
    const { userId } = req.params;
    const stats = await orchestrator.getUserStats(userId);
    res.send({
      userId,
      stats
    });
  } catch (error) {
    logger.error('❌ Error obteniendo estadísticas de usuario:', error);
    res.status(500).send({ error: 'Error obteniendo estadísticas', detail: error.message });
  }
});

// 📊 Endpoint para exportar datos completos de un usuario
app.get('/user/:userId/export', async (req, res) => {
  try {
    const { userId } = req.params;
    const userData = await orchestrator.exportUserData(userId);

    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="user_${userId}_data.json"`);
    res.send(userData);
  } catch (error) {
    logger.error('❌ Error exportando datos de usuario:', error);
    res.status(500).send({ error: 'Error exportando datos', detail: error.message });
  }
});

// 📊 Endpoint para listar todos los usuarios
app.get('/users', async (req, res) => {
  try {
    const users = await orchestrator.getAllUsers();
    const usersWithStats = await Promise.all(
      users.map(async userId => ({
        userId,
        stats: await orchestrator.getUserStats(userId)
      }))
    );

    res.send({
      totalUsers: users.length,
      users: usersWithStats
    });
  } catch (error) {
    logger.error('❌ Error obteniendo lista de usuarios:', error);
    res.status(500).send({ error: 'Error obteniendo usuarios', detail: error.message });
  }
});

// ⚙️ Endpoint para obtener configuración global
app.get('/config', (req, res) => {
  res.send({
    config: AgentConfigManager.getGlobalConfig(),
    message: "Configuración global actual de los agentes"
  });
});

// ⚙️ Endpoint para actualizar personalidad
app.put('/config/personality', (req, res) => {
  try {
    const { personality } = req.body;
    AgentConfigManager.updatePersonality(personality);
    res.send({ 
      message: "Personalidad actualizada correctamente",
      newPersonality: AgentConfigManager.getGlobalConfig().personality
    });
  } catch (error) {
    res.status(500).send({ error: "Error actualizando personalidad", detail: error.message });
  }
});

// ⚙️ Endpoint para agregar restricción
app.post('/config/constraints', (req, res) => {
  try {
    const { type, constraint } = req.body;
    AgentConfigManager.addConstraint(type, constraint);
    res.send({ 
      message: `Restricción agregada a ${type}`,
      constraints: AgentConfigManager.getGlobalConfig().constraints[type]
    });
  } catch (error) {
    res.status(500).send({ error: "Error agregando restricción", detail: error.message });
  }
});

// ⚙️ Endpoint para agregar habilidad
app.post('/config/skills', (req, res) => {
  try {
    const { skill } = req.body;
    AgentConfigManager.addSkill(skill);
    res.send({ 
      message: "Habilidad agregada correctamente",
      skills: AgentConfigManager.getGlobalConfig().skills
    });
  } catch (error) {
    res.status(500).send({ error: "Error agregando habilidad", detail: error.message });
  }
});

// 🎛️ Endpoints para gestión de logging
app.get('/config/logging', (req, res) => {
  try {
    const config = logger.getConfig();
    res.json({
      message: 'Configuración actual de logging',
      config,
      availableLevels: ['debug', 'info', 'warn', 'error', 'critical'],
      availableTypes: config.availableTypes
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/config/logging/level', (req, res) => {
  try {
    const { level } = req.body;
    
    if (!['debug', 'info', 'warn', 'error', 'critical'].includes(level)) {
      return res.status(400).json({ 
        error: 'Nivel inválido. Disponibles: debug, info, warn, error, critical' 
      });
    }
    
    logger.setLogLevel(level);
    
    res.json({
      message: `Nivel de logging cambiado a: ${level}`,
      newConfig: logger.getConfig(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/config/logging/types', (req, res) => {
  try {
    const { types } = req.body;
    
    if (!Array.isArray(types)) {
      return res.status(400).json({ 
        error: 'types debe ser un array' 
      });
    }
    
    logger.setEnabledTypes(types);
    
    res.json({
      message: `Tipos de logging actualizados`,
      newConfig: logger.getConfig(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🎛️ Endpoints preconfigurados para facilitar el uso
app.post('/config/logging/production', (req, res) => {
  try {
    logger.setLogLevel('warn');
    logger.setEnabledTypes(['error', 'warn', 'critical']);
    
    res.json({
      message: 'Configuración de producción aplicada',
      config: logger.getConfig(),
      description: 'Solo errores, advertencias y críticos'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/config/logging/development', (req, res) => {
  try {
    logger.setLogLevel('debug');
    logger.setEnabledTypes(['all']);
    
    res.json({
      message: 'Configuración de desarrollo aplicada',
      config: logger.getConfig(),
      description: 'Todos los logs habilitados'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/config/logging/minimal', (req, res) => {
  try {
    logger.setLogLevel('error');
    logger.setEnabledTypes(['error', 'critical']);
    
    res.json({
      message: 'Configuración mínima aplicada',
      config: logger.getConfig(),
      description: 'Solo errores críticos'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Configuración básica
const port = process.env.PORT || 3000;

// Las rutas del dashboard ya están importadas arriba

app.get('/', (req, res) => {
  res.send(`
    <h1>🤖 Bot IA con Agentes LangChain - Sistema Optimizado + Control Chatwoot</h1>
    <p>✅ Sistema activo con procesamiento paralelo, colas de prioridades y control desde Chatwoot</p>

    <h2>🚀 Características del Sistema Mejorado:</h2>
    <ul>
      <li><strong>Workers Pool:</strong> ${WORKER_POOL_SIZE} workers procesando en paralelo</li>
      <li><strong>Colas de Prioridades:</strong> High → Normal → Low</li>
      <li><strong>Procesamiento Inteligente:</strong> Rate limiting y detección de duplicados</li>
      <li><strong>Métricas en Tiempo Real:</strong> Throughput y tiempos de respuesta</li>
      <li><strong>Escalabilidad:</strong> Configuración dinámica de workers</li>
      <li><strong>🎛️ Control desde Chatwoot:</strong> Pausar/reactivar bot con etiquetas</li>
      <li><strong>📥 Filtro por Inbox:</strong> Monitorear inboxes específicos</li>
    </ul>

    <h2>🎛️ Control del Bot desde Chatwoot:</h2>
    <div style="background: #e8f4fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
      <h3>⚡ Nuevo: Control en Tiempo Real con Webhooks</h3>
      <div style="background: #d4edda; padding: 15px; border-radius: 6px; margin: 10px 0;">
        <p><strong>🚀 Respuesta instantánea:</strong> Configura webhooks para control inmediato (< 1 segundo)</p>
        <p><strong>📋 Configuración rápida:</strong> <a href="/bot-control/webhook-info" target="_blank">Ver instrucciones completas</a></p>
        <p><strong>⚠️ IMPORTANTE:</strong> Usa el evento <code>conversation_updated</code> - se dispara cuando agregas/quitas etiquetas</p>
      </div>
      
      <h3>🏷️ Etiquetas de Control:</h3>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div>
          <h4>🛑 Para Pausar Bot:</h4>
          <ul>
            <li><code>stop_bot</code> - Pausar completamente</li>
            <li><code>human_takeover</code> - Agente toma control</li>
            <li><code>complex_issue</code> - Caso complejo</li>
            <li><code>need_human</code> - Requiere humano</li>
          </ul>
        </div>
        <div>
          <h4>▶️ Para Reactivar Bot:</h4>
          <ul>
            <li><code>ok_bot</code> - Reactivar bot</li>
            <li><code>bot_active</code> - Bot activo</li>
            <li><code>resume_bot</code> - Continuar automático</li>
          </ul>
        </div>
      </div>
      <p><strong>⚡ Con webhooks:</strong> Agrega una etiqueta en Chatwoot y el bot responde INMEDIATAMENTE.</p>
      <p><strong>🐌 Sin webhooks:</strong> Demora hasta 30 segundos en detectar cambios.</p>
    </div>

    <h2>🧪 Probar Bot Ahora:</h2>
    <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0;">
      <form id="testForm" style="display: flex; flex-direction: column; gap: 10px;">
        <label for="testMessage">Mensaje de prueba:</label>
        <input type="text" id="testMessage" placeholder="Ej: Tengo un problema urgente" style="padding: 8px;">
        <button type="submit" style="padding: 10px; background: #007cba; color: white; border: none; border-radius: 4px;">
          🚀 Probar Bot
        </button>
      </form>
      <div id="result" style="margin-top: 20px; padding: 10px; background: white; border-radius: 4px; display: none;">
        <h3>Respuesta del Bot:</h3>
        <div id="response"></div>
      </div>
    </div>

    <h2>📊 Monitoreo en Tiempo Real:</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0;">
      <div style="flex: 1; padding: 15px; background: #e8f4f8; border-radius: 8px;">
        <h3>📈 <a href="/stats" target="_blank">Estadísticas Básicas</a></h3>
        <p>Métricas generales del sistema y rendimiento</p>
      </div>
      <div style="flex: 1; padding: 15px; background: #f0f8e8; border-radius: 8px;">
        <h3>🔍 <a href="/stats/advanced" target="_blank">Estadísticas Avanzadas</a></h3>
        <p>Métricas detalladas de workers y colas</p>
      </div>
      <div style="flex: 1; padding: 15px; background: #f8f0e8; border-radius: 8px;">
        <h3>🛠️ <a href="/debug/status" target="_blank">Estado del Sistema</a></h3>
        <p>Debug y estado interno del sistema</p>
      </div>
    </div>

    <h2>🎛️ Control de Chatwoot:</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0;">
      <div style="padding: 15px; background: #ffe8f8; border-radius: 8px;">
        <h3>🏷️ <a href="/bot-control/tags" target="_blank">Etiquetas Disponibles</a></h3>
        <p>Ver todas las etiquetas de control</p>
      </div>
      <div style="padding: 15px; background: #f8e8ff; border-radius: 8px;">
        <h3>📥 <a href="/bot-control/inboxes" target="_blank">Inboxes Monitoreados</a></h3>
        <p>Ver y configurar bandejas de entrada</p>
      </div>
      <div style="padding: 15px; background: #e8fff8; border-radius: 8px;">
        <h3>👥 <a href="/bot-control/paused-users" target="_blank">Usuarios Pausados</a></h3>
        <p>Ver usuarios con bot desactivado</p>
      </div>
    </div>

    <script>
      document.getElementById('testForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = document.getElementById('testMessage').value;
        const resultDiv = document.getElementById('result');
        const responseDiv = document.getElementById('response');

        if (!message.trim()) return;

        try {
          const response = await fetch('/test-bot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
          });

          const data = await response.json();

          responseDiv.innerHTML = \`
            <p><strong>🎯 Agente:</strong> \${data.agent}</p>
            <p><strong>📊 Confianza:</strong> \${data.confidence}</p>
            <p><strong>💬 Respuesta:</strong> \${data.output}</p>
            <p><strong>⚡ Worker:</strong> Worker ID disponible en logs del servidor</p>
          \`;
          resultDiv.style.display = 'block';
        } catch (error) {
          responseDiv.innerHTML = '<p style="color: red;">❌ Error: ' + error.message + '</p>';
          resultDiv.style.display = 'block';
        }
      });
    </script>

    <h2>📋 Endpoints disponibles:</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <div>
        <h3>🎯 Core del Bot:</h3>
        <ul>
          <li><strong>POST /webhook-evolution</strong> - Webhook para Evolution API</li>
          <li><strong>POST /test-bot</strong> - Probar bot localmente</li>
          <li><strong>POST /knowledge</strong> - Agregar conocimiento como texto</li>
          <li><strong>POST /upload-document</strong> - Cargar documentos</li>
        </ul>
        
        <h3>📊 Monitoreo:</h3>
        <ul>
          <li><strong>GET /stats</strong> - Estadísticas básicas</li>
          <li><strong>GET /stats/advanced</strong> - Estadísticas detalladas</li>
          <li><strong>GET /debug/status</strong> - Estado del sistema</li>
          <li><strong>GET /health</strong> - Health check completo</li>
        </ul>
      </div>
      
      <div>
        <h3>🎛️ Control desde Chatwoot:</h3>
        <ul>
          <li><strong>GET /bot-control/tags</strong> - Etiquetas disponibles</li>
          <li><strong>GET /bot-control/inboxes</strong> - Ver inboxes</li>
          <li><strong>GET /bot-control/paused-users</strong> - Usuarios pausados</li>
          <li><strong>GET /bot-control/:userId/status</strong> - Estado por usuario</li>
          <li><strong>POST /bot-control/check-tags</strong> - Verificar etiquetas manualmente</li>
          <li><strong>GET /bot-control/test-connection</strong> - Probar conexión Chatwoot</li>
        </ul>
        
        <h3>⚡ Webhooks (Tiempo Real):</h3>
        <ul>
          <li><strong>POST /webhook-chatwoot-labels</strong> - Webhook para cambios de etiquetas</li>
          <li><strong>GET /bot-control/webhook-info</strong> - Instrucciones de configuración</li>
          <li><strong>POST /bot-control/webhook-mode</strong> - Activar/desactivar modo webhook</li>
          <li><strong>POST /bot-control/test-webhook</strong> - Probar webhook manualmente</li>
        </ul>
      </div>
    </div>

    <h2>🎛️ Variables de Entorno Disponibles:</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <div>
        <h3>🚀 Sistema Principal:</h3>
        <ul>
          <li><strong>WORKER_POOL_SIZE</strong> - Número de workers (default: 3)</li>
          <li><strong>MAX_CONCURRENT_USERS</strong> - Usuarios concurrentes (default: 5)</li>
          <li><strong>MAX_PENDING_TASKS</strong> - Tareas pendientes máximas (default: 100)</li>
          <li><strong>BUFFER_TIMEOUT_MS</strong> - Timeout de buffer (default: 8000)</li>
          <li><strong>MESSAGE_COOLDOWN_MS</strong> - Cooldown entre mensajes (default: 2000)</li>
        </ul>
        
        <h3>📝 Logging:</h3>
        <ul>
          <li><strong>LOG_LEVEL</strong> - Nivel: debug, info, warn, error, critical</li>
          <li><strong>ENABLED_LOG_TYPES</strong> - Tipos habilitados (comma-separated)</li>
          <li><strong>NODE_ENV</strong> - Environment: production reduce logs</li>
        </ul>
      </div>
      
      <div>
        <h3>🎛️ Chatwoot Integration:</h3>
        <ul>
          <li><strong>CHATWOOT_API_URL</strong> - URL de tu Chatwoot</li>
          <li><strong>CHATWOOT_API_TOKEN</strong> - Token de API</li>
          <li><strong>CHATWOOT_ACCOUNT_ID</strong> - ID de cuenta</li>
          <li><strong>CHATWOOT_INBOX_ID</strong> - Inbox específico (opcional)</li>
          <li><strong>CHATWOOT_INBOX_IDS</strong> - Múltiples inboxes (comma-separated)</li>
          <li><strong>CHATWOOT_POLLING_INTERVAL</strong> - Intervalo polling (default: 30000ms)</li>
          <li><strong>CHATWOOT_NOTIFY_STATUS_CHANGES</strong> - Notificar cambios (default: false)</li>
        </ul>
      </div>
    </div>

    <h2>🔧 Control de Logs en Tiempo Real:</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0;">
      <div style="padding: 15px; background: #ffe8e8; border-radius: 8px;">
        <h3>🔇 <a href="/config/logging/minimal" target="_blank">Modo Silencioso</a></h3>
        <p>Solo errores críticos</p>
        <code>POST /config/logging/minimal</code>
      </div>
      <div style="padding: 15px; background: #fff8e8; border-radius: 8px;">
        <h3>🏭 <a href="/config/logging/production" target="_blank">Modo Producción</a></h3>
        <p>Errores, advertencias y críticos</p>
        <code>POST /config/logging/production</code>
      </div>
      <div style="padding: 15px; background: #e8f8e8; border-radius: 8px;">
        <h3>🔧 <a href="/config/logging/development" target="_blank">Modo Desarrollo</a></h3>
        <p>Todos los logs habilitados</p>
        <code>POST /config/logging/development</code>
      </div>
    </div>

    <h3>📋 Endpoints de Control de Logs:</h3>
    <ul>
      <li><strong>GET /config/logging</strong> - Ver configuración actual</li>
      <li><strong>PUT /config/logging/level</strong> - Cambiar nivel (debug/info/warn/error/critical)</li>
      <li><strong>PUT /config/logging/types</strong> - Habilitar tipos específicos</li>
    </ul>

    <h2>🎯 Configuración Rápida de Chatwoot:</h2>
    <div style="background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
      <ol>
        <li><strong>Obtener API Token:</strong> Chatwoot → Profile Settings → Access Token</li>
        <li><strong>Encontrar Account ID:</strong> URL: /app/accounts/<code>123</code>/dashboard</li>
        <li><strong>Encontrar Inbox ID:</strong> Settings → Inboxes → URL: /inboxes/<code>456</code></li>
        <li><strong>Configurar variables:</strong>
          <pre style="background: #fff; padding: 10px; border-radius: 4px;">
CHATWOOT_API_URL=https://tu-chatwoot.com
CHATWOOT_API_TOKEN=tu_token_aqui
CHATWOOT_ACCOUNT_ID=123
CHATWOOT_INBOX_ID=456  # Solo para WhatsApp
          </pre>
        </li>
        <li><strong>Crear etiquetas en Chatwoot:</strong> <code>stop_bot</code>, <code>ok_bot</code>, <code>human_takeover</code>, etc.</li>
        <li><strong>⚠️ Configurar webhook:</strong> Evento <code>conversation_updated</code> (MÁS CONFIABLE)</li>
        <li><strong>¡Listo!</strong> Agrega etiquetas a conversaciones para controlar el bot</li>
      </ol>
    </div>

    <h2>⚡ Webhooks (Tiempo Real):</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0;">
      <div style="padding: 15px; background: #ffe8e8; border-radius: 8px;">
        <h3>🔍 <a href="/webhook-debug/monitor" target="_blank">Monitor Webhooks</a></h3>
        <p>Monitor en tiempo real de webhooks</p>
      </div>
      <div style="padding: 15px; background: #f8e8ff; border-radius: 8px;">
        <h3>🕰️ <a href="/webhook-debug/last" target="_blank">Último Webhook</a></h3>
        <p>Ver el último webhook recibido</p>
      </div>
      <div style="padding: 15px; background: #e8fff8; border-radius: 8px;">
        <h3>📋 <a href="/bot-control/webhook-info" target="_blank">Configurar Webhook</a></h3>
        <p>Instrucciones completas de configuración</p>
      </div>
    </div>

    <h2>🛠️ Debugging de Webhooks:</h2>
    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
      <h3>🚨 Nuevos Endpoints de Debug:</h3>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div>
          <h4>🔍 Para Debugging:</h4>
          <ul>
            <li><code>POST /webhook-chatwoot-debug</code> - Captura TODOS los webhooks con logging completo</li>
            <li><code>GET /webhook-debug/last</code> - Ve el último webhook recibido</li>
            <li><code>GET /webhook-debug/monitor</code> - Monitor en tiempo real</li>
          </ul>
        </div>
        <div>
          <h4>🎯 Para Producción:</h4>
          <ul>
            <li><code>POST /webhook-chatwoot-labels</code> - Endpoint principal (respuesta instantánea)</li>
            <li>Con logging mejorado para troubleshooting</li>
          </ul>
        </div>
      </div>
      
      <h4>📋 Pasos para Debug:</h4>
      <ol>
        <li><strong>Configurar webhook de debug:</strong> En Chatwoot → Webhooks → <code>/webhook-chatwoot-debug</code></li>
        <li><strong>Agregar/quitar etiqueta:</strong> En una conversación de WhatsApp</li>
        <li><strong>Ver resultados:</strong> En <code>/webhook-debug/monitor</code> o en los logs del servidor</li>
        <li><strong>Verificar evento:</strong> Debe ser <code>conversation_updated</code></li>
        <li><strong>Cambiar a producción:</strong> Una vez funcionando, cambiar URL a <code>/webhook-chatwoot-labels</code></li>
      </ol>
    </div>
  `);
});

// Inicializar dashboard antes de que el servidor inicie
(async () => {
  try {
    // Esperar a que el orquestador esté listo
    while (!orchestrator.database) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const dashboardRoutes = new DashboardRoutes(orchestrator.database);
    app.use(dashboardRoutes.router);
    
    // 📊 Configurar rutas de monitoreo
    const monitoringRoutes = new MonitoringRoutes();
    app.use(monitoringRoutes.router);

    // 🧠 Configurar rutas de gestión de conocimiento flexible
    const knowledgeManagementRoutes = require('./routes/knowledgeManagement');
    app.use('/api/knowledge', knowledgeManagementRoutes);
    
    // Configurar captura de logs para el dashboard
    logger.setLogCapture((level, message, data) => {
      monitoringRoutes.addLog(level, message, data);
    });
    
    // Hacer disponible globalmente para métricas
    global.monitoringRoutes = monitoringRoutes;
    global.workerPool = workerPool;
    global.globalMessageQueue = globalMessageQueue;
  } catch (error) {
    logger.error('❌ Error inicializando dashboard routes:', error);
  }
})();

// 🚀 Auto-configuración y diagnósticos del sistema
async function autoConfigureSystem() {
  try {
    logger.info('🔧 Iniciando auto-configuración del sistema...');
    
    // 1. Verificar conexión con Chatwoot
    const chatwootTest = await chatwootManager.testConnection();
    if (chatwootTest.success) {
      logger.info(`✅ Chatwoot conectado - ${chatwootTest.conversationsFound} conversaciones encontradas`);
      
      // 2. Verificar configuración de webhook mode
      const webhookModeDefault = process.env.CHATWOOT_WEBHOOK_MODE_DEFAULT === 'true';
      const now = Date.now();
      const stats = chatwootManager.getStats();
      
      if (webhookModeDefault) {
        logger.info('🚀 Webhook mode activado por defecto via CHATWOOT_WEBHOOK_MODE_DEFAULT=true');
        logger.info('📋 Para respuesta instantánea, configurar webhook en Chatwoot → Settings → Webhooks');
        logger.info(`📋 URL: ${process.env.BASE_URL || 'https://tu-dominio.com'}/webhook-chatwoot-labels`);
        logger.info('📋 Evento: conversation_updated');
      } else {
        // Auto-detectar si el webhook funciona (verificar actividad reciente)
        const isWebhookWorking = stats.lastWebhookReceived && (now - stats.lastWebhookReceived) < 5 * 60 * 1000;
        
        if (isWebhookWorking) {
          logger.info('🚀 Webhook detectado como activo - manteniendo configuración');
        } else {
          logger.info('🔄 Usando modo polling estándar');
          logger.info(`📋 Para mejorar: configurar CHATWOOT_WEBHOOK_MODE_DEFAULT=true o webhook en: ${process.env.BASE_URL || 'https://tu-dominio.com'}/webhook-chatwoot-labels`);
        }
      }
    } else {
      logger.warn('⚠️ Chatwoot no conectado:', chatwootTest.error);
    }
    
    // 3. Verificar configuración de inboxes
    const monitoredInboxes = chatwootManager.getMonitoredInboxesCount();
    if (monitoredInboxes > 0) {
      logger.info(`📥 Monitoreando ${monitoredInboxes} inbox(es) de Chatwoot`);
    } else {
      logger.info('📥 Monitoreando todos los inboxes disponibles');
    }
    
    // 4. Verificar Worker Pool
    if (workerPool) {
      const workerStats = workerPool.getStats();
      logger.info(`👥 Worker Pool: ${workerStats.totalWorkers} workers disponibles`);
    }
    
    // 5. Verificar sistema de colas
    const queueStats = globalMessageQueue.getStats();
    logger.info(`📋 Sistema de colas inicializado (Pendientes: ${queueStats.total})`);
    
    logger.info('✅ Auto-configuración completada');
    
  } catch (error) {
    logger.error('❌ Error en auto-configuración:', error.message);
  }
}

// 🚀 Endpoint mejorado de diagnóstico completo
app.get('/diagnostics', async (req, res) => {
  try {
    const diagnostics = {
      timestamp: new Date().toISOString(),
      
      // Sistema general
      system: {
        uptime: process.uptime(),
        nodeVersion: process.version,
        platform: process.platform,
        memory: process.memoryUsage(),
        pid: process.pid
      },
      
      // Estado de Chatwoot
      chatwoot: await chatwootManager.testConnection(),
      chatwootConfig: {
        isEnabled: chatwootManager.isEnabled,
        apiUrl: chatwootManager.apiUrl ? '✅ Configurado' : '❌ Faltante',
        apiToken: chatwootManager.apiToken ? '✅ Configurado' : '❌ Faltante',
        accountId: chatwootManager.accountId ? '✅ Configurado' : '❌ Faltante',
        inboxFilter: chatwootManager.inboxId || chatwootManager.inboxIds.join(',') || 'Todos',
        pollingInterval: chatwootManager.pollingInterval,
        isWebhookMode: chatwootManager.pollingInterval > 60000,
        stats: chatwootManager.getStats()
      },
      
      // Workers y colas
      workers: workerPool ? workerPool.getStats() : { error: 'Worker Pool no inicializado' },
      queue: globalMessageQueue.getStats(),
      
      // Conexiones externas
      redis: redisClient.getConnectionStatus(),
      postgres: {
        isConnected: postgresClient.isConnected,
        host: process.env.DATABASE_HOST ? '✅ Configurado' : '❌ Faltante'
      },
      
      // Variables de entorno importantes
      environment: {
        NODE_ENV: process.env.NODE_ENV || 'development',
        LOG_LEVEL: process.env.LOG_LEVEL || 'info',
        CHATWOOT_API_URL: process.env.CHATWOOT_API_URL ? '✅ Configurado' : '❌ Faltante',
        CHATWOOT_INBOX_ID: process.env.CHATWOOT_INBOX_ID || 'No configurado',
        CHATWOOT_WEBHOOK_MODE_DEFAULT: process.env.CHATWOOT_WEBHOOK_MODE_DEFAULT === 'true' ? '✅ Activado' : '❌ Desactivado',
        WORKER_POOL_SIZE: process.env.WORKER_POOL_SIZE || '3 (default)',
        BASE_URL: process.env.BASE_URL || 'No configurado'
      },
      
      // Recomendaciones
      recommendations: []
    };
    
    // Generar recomendaciones
    if (!diagnostics.chatwoot.success) {
      diagnostics.recommendations.push('🔧 Configurar variables de Chatwoot: CHATWOOT_API_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID');
    }
    
    if (!diagnostics.chatwootConfig.isWebhookMode) {
      diagnostics.recommendations.push('⚡ Configurar webhook para respuesta instantánea en lugar de polling');
    }
    
    if (!process.env.BASE_URL) {
      diagnostics.recommendations.push('🌐 Configurar BASE_URL para URLs de webhook correctas');
    }
    
    if (diagnostics.workers.error) {
      diagnostics.recommendations.push('👥 Verificar inicialización del Worker Pool');
    }
    
    res.json(diagnostics);
    
  } catch (error) {
    res.status(500).json({
      error: 'Error generando diagnósticos',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// 🎯 Endpoint para forzar auto-configuración
app.post('/system/auto-configure', async (req, res) => {
  try {
    await autoConfigureSystem();
    res.json({
      message: 'Auto-configuración ejecutada exitosamente',
      timestamp: new Date().toISOString(),
      nextSteps: [
        'Verificar /diagnostics para estado completo',
        'Configurar webhook si no está activo',
        'Probar funcionamiento con /bot-control/test-webhook'
      ]
    });
  } catch (error) {
    res.status(500).json({
      error: 'Error en auto-configuración',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

app.listen(PORT, '0.0.0.0', async () => {
  const webhookUrl = 'https://whatsapp-middleware-ok-production.up.railway.app/webhook-evolution';

  logger.info(`🚀 Bot WhatsApp IA iniciado en puerto ${PORT}`);
  logger.info(`📱 Webhook: /webhook-evolution`);
  
  // Ejecutar auto-configuración después de un breve delay
  setTimeout(async () => {
    await autoConfigureSystem();
  }, 2000);
});

// ⚡ Health Check mejorado para Railway
app.get('/health', async (req, res) => {
  try {
    const redisStatus = redisClient.getConnectionStatus();
    
    const health = {
      status: 'OK',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      redis: {
        isConnected: redisStatus.isConnected,
        isDisabled: redisStatus.isDisabled,
        retryCount: redisStatus.retryCount,
        maxRetries: redisStatus.maxRetries,
        status: redisStatus.isConnected ? 'connected' : 
                redisStatus.isDisabled ? 'disabled' : 'disconnected'
      },
      postgres: postgresClient.isConnected ? 'connected' : 'disconnected',
      environment: process.env.NODE_ENV || 'development',
      version: process.env.npm_package_version || '1.0.0'
    };

    // Verificar Redis si está disponible
    if (redisClient.isAvailable()) {
      try {
        await redisClient.set('health-check', { timestamp: Date.now() }, 60);
        health.redis.lastTest = 'success';
      } catch (error) {
        health.redis.lastTest = 'failed';
        health.redis.lastError = error.message;
      }
    }

    // Verificar PostgreSQL si está habilitado
    if (postgresClient.isConnected) {
      try {
        const pgHealth = await postgresClient.healthCheck();
        health.postgresDetails = pgHealth;
      } catch (error) {
        health.postgres = 'error';
        health.postgresError = error.message;
      }
    }

    // Determinar el estado general
    if (!redisStatus.isConnected && !redisStatus.isDisabled) {
      health.status = 'DEGRADED';
      health.message = 'Redis desconectado, funcionando con memoria local';
    }

    res.status(200).json(health);
  } catch (error) {
    res.status(503).json({
      status: 'ERROR',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// 🎛️ Nuevos endpoints para control desde Chatwoot
app.get('/bot-control/tags', (req, res) => {
  res.json({
    message: 'Etiquetas disponibles para control del bot',
    pauseTags: [
      { tag: 'stop_bot', description: 'Pausar bot completamente' },
      { tag: 'pause_bot', description: 'Pausar bot temporalmente' },
      { tag: 'bot_off', description: 'Desactivar bot' },
      { tag: 'human_takeover', description: 'Agente humano toma control' },
      { tag: 'escalate_human', description: 'Escalar a agente humano' },
      { tag: 'need_human', description: 'Requiere atención humana' },
      { tag: 'complex_issue', description: 'Consulta compleja para humano' }
    ],
    resumeTags: [
      { tag: 'ok_bot', description: 'Reactivar bot' },
      { tag: 'resume_bot', description: 'Continuar con bot' },
      { tag: 'bot_on', description: 'Activar bot' },
      { tag: 'bot_active', description: 'Bot activo' },
      { tag: 'auto_bot', description: 'Modo automático' }
    ],
    instructions: [
      '1. En Chatwoot, ve a la conversación que quieres controlar',
      '2. Agrega una de las etiquetas de pausa para detener el bot',
      '3. Maneja la conversación manualmente',
      '4. Agrega una etiqueta de reanudación cuando termines',
      '5. El bot se reactivará automáticamente en ~30 segundos'
    ]
  });
});

app.get('/bot-control/paused-users', (req, res) => {
  try {
    const pausedUsers = chatwootManager.getPausedUsers();
    
    res.json({
      message: `${pausedUsers.length} usuarios con bot pausado`,
      pausedUsers,
      totalUsers: pausedUsers.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/bot-control/:userId/status', (req, res) => {
  try {
    const { userId } = req.params;
    const botState = chatwootManager.getBotStateForUser(userId);
    
    res.json({
      userId,
      botState,
      isPaused: chatwootManager.isBotPausedForUser(userId),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🔧 Endpoint para forzar verificación manual de etiquetas
app.post('/bot-control/check-tags', async (req, res) => {
  try {
    await chatwootManager.checkConversationTags();
    
    res.json({
      message: 'Verificación manual de etiquetas completada',
      stats: chatwootManager.getStats(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🔧 Endpoint para probar conexión con Chatwoot
app.get('/bot-control/test-connection', async (req, res) => {
  try {
    const result = await chatwootManager.testConnection();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 📥 Endpoint para ver inboxes disponibles
app.get('/bot-control/inboxes', (req, res) => {
  try {
    const inboxes = chatwootManager.getAvailableInboxes();
    
    res.json({
      message: 'Inboxes disponibles en Chatwoot',
      totalInboxes: inboxes.length,
      inboxes: inboxes,
      currentConfig: {
        singleInbox: process.env.CHATWOOT_INBOX_ID,
        multipleInboxes: process.env.CHATWOOT_INBOX_IDS,
        monitoringAll: !process.env.CHATWOOT_INBOX_ID && !process.env.CHATWOOT_INBOX_IDS
      },
      instructions: [
        'Para monitorear un inbox específico: CHATWOOT_INBOX_ID=123',
        'Para monitorear múltiples inboxes: CHATWOOT_INBOX_IDS=123,456,789',
        'Para monitorear todos: No configurar ninguna variable'
      ]
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 📥 Endpoint para cambiar inbox monitoreado dinámicamente
app.put('/bot-control/inbox-filter', async (req, res) => {
  try {
    const { inboxId, inboxIds, clearFilter } = req.body;
    
    if (clearFilter) {
      chatwootManager.inboxId = null;
      chatwootManager.inboxIds = [];
      delete process.env.CHATWOOT_INBOX_ID;
      delete process.env.CHATWOOT_INBOX_IDS;
      
      res.json({
        message: 'Filtro de inbox removido - monitoreando todos los inboxes',
        newConfig: chatwootManager.getStats().configuration
      });
      return;
    }
    
    if (inboxId) {
      chatwootManager.inboxId = inboxId.toString();
      chatwootManager.inboxIds = [];
      process.env.CHATWOOT_INBOX_ID = inboxId.toString();
      delete process.env.CHATWOOT_INBOX_IDS;
      
      const inboxInfo = chatwootManager.inboxCache.get(parseInt(inboxId));
      
      res.json({
        message: `Filtro configurado para inbox específico: ${inboxInfo?.name || inboxId}`,
        inboxInfo: inboxInfo,
        newConfig: chatwootManager.getStats().configuration
      });
      
    } else if (inboxIds && Array.isArray(inboxIds)) {
      chatwootManager.inboxId = null;
      chatwootManager.inboxIds = inboxIds.map(id => id.toString());
      process.env.CHATWOOT_INBOX_IDS = inboxIds.join(',');
      delete process.env.CHATWOOT_INBOX_ID;
      
      const inboxNames = inboxIds.map(id => {
        const info = chatwootManager.inboxCache.get(parseInt(id));
        return info ? info.name : `ID: ${id}`;
      });
      
      res.json({
        message: `Filtro configurado para múltiples inboxes: ${inboxNames.join(', ')}`,
        inboxes: inboxNames,
        newConfig: chatwootManager.getStats().configuration
      });
      
    } else {
      res.status(400).json({
        error: 'Parámetros inválidos',
        expectedParameters: {
          inboxId: 'string - ID de inbox único',
          inboxIds: 'array - Array de IDs de inboxes',
          clearFilter: 'boolean - Remover filtros'
        }
      });
    }
    
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🚀 Endpoints para gestión de modo webhook
app.post('/bot-control/webhook-mode', async (req, res) => {
  try {
    const { enabled } = req.body;
    
    if (typeof enabled !== 'boolean') {
      return res.status(400).json({
        error: 'Parámetro "enabled" debe ser boolean',
        example: { enabled: true }
      });
    }
    
    chatwootManager.setWebhookMode(enabled);
    
    res.json({
      message: enabled ? 
        'Modo webhook activado - respuesta instantánea' : 
        'Modo polling normal activado',
      webhookMode: enabled,
      pollingInterval: chatwootManager.pollingInterval,
      pollingIntervalSeconds: chatwootManager.pollingInterval / 1000,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/bot-control/webhook-info', (req, res) => {
  try {
    const baseUrl = process.env.BASE_URL || `https://${req.get('host')}`;
    
    res.json({
      message: 'Información de configuración de webhooks',
      webhook: {
        url: `${baseUrl}/webhook-chatwoot-labels`,
        method: 'POST',
        events: [
          'conversation_updated',     // 🎯 EVENTO PRINCIPAL (REQUERIDO)
          'conversation_tag_created', // Opcional: backup
          'conversation_tag_deleted'  // Opcional: backup
        ]
      },
      importantNote: {
        primaryEvent: 'conversation_updated',
        why: 'Este evento se dispara SIEMPRE cuando agregas/quitas etiquetas o cambias estado',
        reliability: 'Es el más confiable y recomendado por Chatwoot',
        triggers: [
          '✅ Cuando agregas una etiqueta',
          '✅ Cuando quitas una etiqueta', 
          '✅ Cuando cambias el estado de la conversación'
        ]
      },
      currentConfig: {
        pollingInterval: chatwootManager.pollingInterval,
        pollingIntervalSeconds: chatwootManager.pollingInterval / 1000,
        isWebhookMode: chatwootManager.pollingInterval > 60000 // > 1 minuto = modo webhook
      },
      instructions: [
        '1. Ve a Chatwoot → Settings → Webhooks',
        '2. Click "Add Webhook"',
        `3. URL: ${baseUrl}/webhook-chatwoot-labels`,
        '4. ⚠️ IMPORTANTE: Selecciona MÍNIMO el evento "conversation_updated"',
        '5. Opcionalmente: conversation_tag_created, conversation_tag_deleted',
        '6. Save webhook',
        `7. Activar modo webhook: POST ${baseUrl}/bot-control/webhook-mode {"enabled": true}`
      ],
      benefits: [
        '⚡ Respuesta instantánea (<1 segundo)',
        '💰 Menos consumo de recursos',
        '🔄 Polling como backup cada 5 minutos',
        '🎯 Solo se ejecuta cuando hay cambios reales'
      ]
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 🧪 Endpoint para probar webhook manualmente
app.post('/bot-control/test-webhook', async (req, res) => {
  try {
    const { conversation } = req.body;
    
    if (!conversation) {
      return res.status(400).json({
        error: 'Falta objeto "conversation"',
        example: {
          conversation: {
            id: 123,
            inbox_id: 17,
            labels: [{ title: 'stop_bot' }],
            meta: { sender: { identifier: '5491112345678@s.whatsapp.net' } }
          }
        }
      });
    }
    
    const result = await chatwootManager.processWebhookImmediately(conversation);
    
    res.json({
      message: 'Webhook procesado exitosamente',
      result: result,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ 
      error: 'Error procesando webhook de prueba',
      detail: error.message 
    });
  }
});

// 🔍 Endpoint de diagnóstico Redis para Railway
app.get('/diagnose/redis', async (req, res) => {
  try {
    const diagnosis = {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      
      // Variables de entorno (sin valores sensibles)
      config: {
        hasRedisUrl: !!process.env.REDIS_URL,
        redisUrlHost: process.env.REDIS_URL ? 
          process.env.REDIS_URL.replace(/redis:\/\/[^@]*@/, 'redis://***@').replace(/:[0-9]+$/, ':***') : 
          'No configurado',
        redisTls: process.env.REDIS_TLS || 'no configurado',
        nodeEnv: process.env.NODE_ENV || 'development'
      },
      
      // Estado de conexiones
      connections: {
        redisClient: redisClient.getConnectionStatus(),
        comboCache: {
          available: false,
          error: 'Necesita inicialización manual'
        }
      },
      
      // Test básico de Redis
      tests: {}
    };

    // Test de conexión en tiempo real
    if (process.env.REDIS_URL) {
      const Redis = require('ioredis');
      
      try {
        let testRedisUrl = process.env.REDIS_URL;
        
        // Aplicar fix IPv6 si es Railway
        if (testRedisUrl.includes('redis.railway.internal') && !testRedisUrl.includes('family=')) {
          const separator = testRedisUrl.includes('?') ? '&' : '?';
          testRedisUrl = `${testRedisUrl}${separator}family=0`;
          diagnosis.tests.appliedIPv6Fix = true;
        }

        const testRedis = new Redis(testRedisUrl, {
          lazyConnect: true,
          connectTimeout: 5000,
          commandTimeout: 3000,
          family: 0,
          maxRetriesPerRequest: 1,
          retryStrategy: () => null // No reintentos para test rápido
        });

        // Test de conexión con timeout
        const connectionTest = await Promise.race([
          testRedis.connect().then(() => 'connected'),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Timeout de conexión')), 5000)
          )
        ]);

        if (connectionTest === 'connected') {
          // Test de escritura/lectura
          const testKey = `test:${Date.now()}`;
          await testRedis.set(testKey, 'test-value', 'EX', 30);
          const testValue = await testRedis.get(testKey);
          await testRedis.del(testKey);
          
          diagnosis.tests.connection = 'success';
          diagnosis.tests.readWrite = testValue === 'test-value' ? 'success' : 'failed';
          diagnosis.tests.message = '✅ Redis funciona correctamente';
        }

        await testRedis.disconnect();

      } catch (error) {
        diagnosis.tests.connection = 'failed';
        diagnosis.tests.error = error.message;
        diagnosis.tests.errorCode = error.code;
        
        // Sugerencias específicas
        if (error.message.includes('ECONNREFUSED')) {
          diagnosis.tests.suggestion = 'El servicio Redis no está respondiendo. Verifica que esté activo en Railway.';
        } else if (error.message.includes('ENOTFOUND')) {
          diagnosis.tests.suggestion = 'Error de DNS. Verifica la URL de Redis en las variables de entorno.';
        } else if (error.message.includes('ETIMEDOUT')) {
          diagnosis.tests.suggestion = 'Timeout de conexión. El servicio Redis puede estar sobrecargado.';
        } else {
          diagnosis.tests.suggestion = 'Error desconocido. Revisa los logs de Railway para más detalles.';
        }
      }
    } else {
      diagnosis.tests.error = 'REDIS_URL no está configurado';
      diagnosis.tests.suggestion = 'Agrega un servicio Redis en Railway y redespliega la aplicación.';
    }

    res.json(diagnosis);

  } catch (error) {
    res.status(500).json({
      error: 'Error en diagnóstico',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// 📊 Endpoint de estadísticas de rendimiento del optimizador
app.get('/stats/performance', (req, res) => {
  try {
    const stats = {
      timestamp: new Date().toISOString(),
      optimizer: global.responseOptimizer ? global.responseOptimizer.getPerformanceStats() : { error: 'Optimizador no disponible' },
      knowledge: global.flexibleKnowledgeManager ? global.flexibleKnowledgeManager.getSystemStats() : { error: 'Sistema de conocimiento no disponible' },
      system: {
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        nodeVersion: process.version,
        pid: process.pid
      }
    };

    // Agregar análisis detallado si está disponible
    if (global.responseOptimizer) {
      stats.detailedAnalysis = global.responseOptimizer.getDetailedAnalysis();
    }

    res.json(stats);
  } catch (error) {
    res.status(500).json({
      error: 'Error obteniendo estadísticas de rendimiento',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});