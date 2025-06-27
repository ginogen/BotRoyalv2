# 🤖 ROYAL BOT - IMPLEMENTACIÓN CHATWOOT COMPLETA

Este documento describe la implementación completa del servidor optimizado para Chatwoot, replicando las funcionalidades esenciales del sistema Node.js pero en Python.

## 📋 RESUMEN DE LA IMPLEMENTACIÓN

### ✅ Funcionalidades Implementadas (Basadas en Node.js)

1. **🔄 Sistema de Workers y Colas**
   - Pool de workers paralelos para procesamiento concurrente
   - Cola de prioridades para gestión inteligente de mensajes
   - Detección y eliminación de mensajes duplicados
   - Rate limiting por usuario

2. **📱 Conexión Bidireccional con Chatwoot**
   - Recepción de mensajes via webhooks
   - Envío de respuestas automáticas
   - Manejo de conversaciones múltiples
   - Gestión de estados por usuario

3. **📞 Integration con Evolution API (WhatsApp)**
   - Recepción de mensajes de WhatsApp
   - Envío de respuestas via WhatsApp
   - Webhook optimizado para Evolution

4. **⚡ Optimización de Concurrencia**
   - Límite configurable de usuarios concurrentes
   - Buffer de mensajes con timeout
   - Cooldown entre mensajes del mismo usuario
   - Gestión de memoria optimizada

### ❌ Funcionalidades NO Incluidas (Como solicitaste)

- ❌ Sistema de conocimiento flexible avanzado
- ❌ Control en tiempo real con etiquetas de Chatwoot
- ❌ Dashboard web complejo
- ❌ Webhooks avanzados de monitoreo
- ❌ Sistema de métricas complejas

## 📁 ARCHIVOS PRINCIPALES

### `royal_chatwoot_server.py`
**Servidor principal optimizado** - Replica funcionalidades core del Node.js:

```python
# Características principales:
- FastAPI con procesamiento asíncrono
- Pool de workers con ThreadPoolExecutor
- Cola de prioridades thread-safe
- Servicios para Chatwoot y Evolution API
- Gestión de concurrencia optimizada
- Rate limiting y detección de duplicados
```

### `start_chatwoot_server.py`
**Script de inicio inteligente** - Facilita la configuración y ejecución:

```python
# Funcionalidades:
- Verificación automática de dependencias
- Validación de configuración
- Modos de inicio (desarrollo/producción/test)
- Creación automática de archivos .env
- Información detallada de endpoints
```

### `config.chatwoot.env.example`
**Configuración completa** - Template con todas las variables necesarias:

```bash
# Variables principales:
CHATWOOT_API_URL=https://tu-chatwoot.com
CHATWOOT_API_TOKEN=tu_token
CHATWOOT_ACCOUNT_ID=123
EVOLUTION_API_URL=https://tu-evolution.com
EVOLUTION_API_TOKEN=tu_token
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
```

## 🚀 INSTALACIÓN Y CONFIGURACIÓN

### 1. Preparar Dependencias

```bash
# Instalar dependencias nuevas
pip install fastapi uvicorn[standard] httpx

# O instalar todas las dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de configuración
cp config.chatwoot.env.example .env

# Editar variables (obligatorias)
CHATWOOT_API_URL=https://tu-chatwoot.com
CHATWOOT_API_TOKEN=tu_token_de_acceso
CHATWOOT_ACCOUNT_ID=123

# Opcional: Evolution API para WhatsApp
EVOLUTION_API_URL=https://tu-evolution.com
EVOLUTION_API_TOKEN=tu_token_evolution
INSTANCE_NAME=tu_instancia
```

### 3. Obtener Datos de Chatwoot

#### Token de API:
1. Ve a tu Chatwoot
2. Click en tu avatar → **Profile Settings**
3. Tab **Access Token**
4. Copy el token generado

#### Account ID:
1. Ve al dashboard de Chatwoot
2. En la URL verás: `/app/accounts/{ACCOUNT_ID}/dashboard`
3. El número es tu `CHATWOOT_ACCOUNT_ID`

#### Configurar Webhook:
1. Chatwoot → **Settings** → **Webhooks**
2. **Add New Webhook**
3. **URL**: `https://tu-dominio.com/webhook/chatwoot`
4. **Events**: Seleccionar `message_created`
5. **Secret**: Opcional pero recomendado

### 4. Iniciar Servidor

```bash
# Método 1: Script automático (recomendado)
python start_chatwoot_server.py

# Método 2: Directo
python royal_chatwoot_server.py

# Método 3: Con uvicorn
uvicorn royal_chatwoot_server:app --host 0.0.0.0 --port 8000
```

## 🔧 CONFIGURACIÓN AVANZADA

### Variables de Rendimiento

```bash
# Número de workers para procesamiento paralelo
WORKER_POOL_SIZE=3

# Máximo usuarios procesando simultáneamente
MAX_CONCURRENT_USERS=5

# Timeout para buffer de mensajes (ms)
MESSAGE_BUFFER_TIMEOUT=8000

# Cooldown entre mensajes del mismo usuario (ms)
MESSAGE_COOLDOWN=2000
```

### Ajustes Recomendados por Escenario

#### 🏠 Desarrollo Local
```bash
WORKER_POOL_SIZE=2
MAX_CONCURRENT_USERS=3
MESSAGE_BUFFER_TIMEOUT=5000
```

#### 🏢 Producción Pequeña (< 100 usuarios/día)
```bash
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
MESSAGE_BUFFER_TIMEOUT=8000
```

#### 🏭 Producción Grande (> 500 usuarios/día)
```bash
WORKER_POOL_SIZE=5
MAX_CONCURRENT_USERS=10
MESSAGE_BUFFER_TIMEOUT=10000
```

## 📡 ENDPOINTS DISPONIBLES

### 🏠 Principal
- **GET** `/` - Información del servidor y características
- **GET** `/health` - Health check con estado de servicios

### 🧪 Testing
- **POST** `/test/message` - Probar bot directamente
  ```json
  {
    "message": "Hola, ¿tenés anillos?",
    "user_id": "test_user"
  }
  ```

### 📊 Monitoreo
- **GET** `/stats` - Estadísticas detalladas del sistema
- **POST** `/admin/clear-queue` - Limpiar cola de mensajes

### 🔗 Webhooks
- **POST** `/webhook/chatwoot` - Recibir mensajes de Chatwoot
- **POST** `/webhook/evolution` - Recibir mensajes de WhatsApp

## 🔄 FLUJO DE PROCESAMIENTO

### 1. Recepción de Mensaje
```
Chatwoot/WhatsApp → Webhook → MessageQueue
```

### 2. Procesamiento Inteligente
```
MessageQueue → Worker Pool → Royal Bot Agent → Response
```

### 3. Envío de Respuesta
```
Response → Chatwoot API / Evolution API → Usuario Final
```

### 4. Características del Sistema

#### 🛡️ Protección Anti-Spam
- **Detección de duplicados**: Hash del mensaje + user_id
- **Rate limiting**: Cooldown configurable entre mensajes
- **Buffer timeout**: Agrupa mensajes rápidos del mismo usuario

#### ⚡ Optimización de Rendimiento
- **Workers paralelos**: Procesamiento concurrente real
- **Cola de prioridades**: Mensajes urgentes primero
- **Límite de concurrencia**: Previene sobrecarga del sistema
- **Limpieza automática**: Elimina datos antiguos de memoria

## 🐛 TROUBLESHOOTING

### Problema: "No recibo mensajes de Chatwoot"

**Verificaciones:**
1. ✅ Variables CHATWOOT_* configuradas
2. ✅ Webhook configurado en Chatwoot
3. ✅ URL del webhook accesible públicamente
4. ✅ Event `message_created` seleccionado

**Debug:**
```bash
# Ver logs del servidor
tail -f logs/server.log

# Probar endpoint de health
curl http://localhost:8000/health

# Test directo del bot
curl -X POST http://localhost:8000/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "user_id": "debug"}'
```

### Problema: "Bot responde lento"

**Optimizaciones:**
```bash
# Aumentar workers
WORKER_POOL_SIZE=5

# Aumentar concurrencia
MAX_CONCURRENT_USERS=8

# Reducir timeout
MESSAGE_BUFFER_TIMEOUT=5000
```

### Problema: "Mensajes duplicados"

**El sistema maneja automáticamente:**
- Hash único por mensaje + usuario
- Buffer de mensajes recientes
- Cooldown entre mensajes

**Si persiste:**
```bash
# Limpiar cola manualmente
curl -X POST http://localhost:8000/admin/clear-queue
```

## 🚀 DESPLIEGUE EN PRODUCCIÓN

### Railway (Recomendado)

```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login y crear proyecto
railway login
railway init

# 3. Configurar variables de entorno
railway variables set CHATWOOT_API_URL=https://tu-chatwoot.com
railway variables set CHATWOOT_API_TOKEN=tu_token
railway variables set CHATWOOT_ACCOUNT_ID=123

# 4. Desplegar
railway up
```

### VPS/Servidor Propio

```bash
# 1. Clonar proyecto
git clone tu-repo
cd BotRoyalv2

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar .env
cp config.chatwoot.env.example .env
nano .env

# 4. Ejecutar con supervisión
screen -S royal-bot
python royal_chatwoot_server.py

# 5. O con systemd
sudo nano /etc/systemd/system/royal-bot.service
sudo systemctl enable royal-bot
sudo systemctl start royal-bot
```

### Configuración de Systemd

```ini
[Unit]
Description=Royal Bot Chatwoot Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/BotRoyalv2
ExecStart=/usr/bin/python3 royal_chatwoot_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📊 MONITOREO Y MÉTRICAS

### Estadísticas Disponibles

**GET `/stats`** proporciona:

```json
{
  "system": {
    "uptime_seconds": 3600,
    "messages_per_minute": 5.2,
    "error_rate": 1.5
  },
  "processing": {
    "messages_processed": 150,
    "queue": {
      "queue_size": 2,
      "active_users": 1,
      "total_processed": 150
    },
    "workers": {
      "pool_size": 3,
      "active_workers": 1,
      "utilization": 33.3
    }
  }
}
```

### Alertas Recomendadas

```bash
# Error rate > 5%
# Queue size > 50
# Worker utilization > 90%
# Response time > 30 segundos
```

## 🔧 PERSONALIZACIÓN

### Modificar Comportamiento del Bot

El servidor usa `run_contextual_conversation_sync()` del bot existente. Para personalizar:

1. **Editar prompts**: Modificar `royal_agents/royal_agent_contextual.py`
2. **Agregar herramientas**: Añadir funciones en `contextual_tools.py`
3. **Cambiar modelo**: Ajustar en la configuración del agente

### Integrar Base de Datos

El servidor es compatible con `database_persistent.py`:

```python
# Ya incluido en royal_chatwoot_server.py
from database_persistent import DatabaseManager

# Se inicializa automáticamente si está disponible
db_manager = DatabaseManager()
```

### Agregar Nuevos Webhooks

```python
@app.post("/webhook/nuevo-servicio")
async def nuevo_webhook(request: Request):
    data = await request.json()
    # Procesar y agregar a message_queue
    message_data = MessageData(...)
    message_queue.add_message(message_data)
    return {"status": "received"}
```

## 📈 COMPARACIÓN CON NODE.JS

### ✅ Funcionalidades Replicadas

| Funcionalidad | Node.js | Python | Estado |
|---------------|---------|---------|--------|
| Worker Pool | ✅ | ✅ | ✅ Replicado |
| Message Queue | ✅ | ✅ | ✅ Replicado |
| Rate Limiting | ✅ | ✅ | ✅ Replicado |
| Duplicate Detection | ✅ | ✅ | ✅ Replicado |
| Chatwoot Integration | ✅ | ✅ | ✅ Replicado |
| Evolution API | ✅ | ✅ | ✅ Replicado |
| Concurrency Control | ✅ | ✅ | ✅ Replicado |

### 🚀 Mejoras en Python

1. **Simplicidad**: Código más claro y mantenible
2. **Integration**: Usa el bot existente sin cambios
3. **Configuración**: Setup más fácil con script de inicio
4. **Debugging**: Mejor manejo de errores y logging
5. **Flexibilidad**: Fácil de modificar y extender

## 🎯 PRÓXIMOS PASOS

### Inmediatos
1. ✅ Configurar variables de entorno
2. ✅ Probar localmente con `start_chatwoot_server.py`
3. ✅ Configurar webhooks en Chatwoot
4. ✅ Desplegar en producción

### Opcionales (Futuras Mejoras)
- 📊 Dashboard web simple para monitoreo
- 🔔 Sistema de alertas por email/Slack
- 📈 Métricas avanzadas con Prometheus
- 🔄 Auto-scaling basado en carga
- 💾 Cache Redis para mejor rendimiento

## 🆘 SOPORTE

### Logs y Debug
```bash
# Ver logs en tiempo real
python royal_chatwoot_server.py | tee logs/server.log

# Verificar salud del sistema
curl http://localhost:8000/health | jq

# Estadísticas detalladas
curl http://localhost:8000/stats | jq
```

### Contacto
- 📧 Crear issue en el repositorio
- 📱 Verificar documentación actualizada
- 🔧 Revisar configuración con `start_chatwoot_server.py`

---

✅ **¡Sistema listo para producción!** 

El servidor replica exitosamente las funcionalidades esenciales del Node.js, optimizado para múltiples conversaciones concurrentes con Chatwoot. 