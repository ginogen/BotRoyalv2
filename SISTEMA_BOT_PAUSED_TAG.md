# 🏷️ Sistema de Control de Bot con Etiqueta `bot-paused`

## 📋 Resumen

Sistema simplificado para que los agentes de Chatwoot puedan pausar/reactivar el bot de forma instantánea usando una sola etiqueta: **`bot-paused`**

## ✅ Implementación Completada

### 🔧 Funciones Implementadas

1. **Detección de webhooks `conversation_updated`** ✅
2. **Función de análisis de etiqueta `bot-paused`** ✅  
3. **Integración con BotStateManager existente** ✅
4. **Endpoints de prueba** ✅
5. **Script de testing completo** ✅

### 📁 Archivos Modificados

- **`royal_server_optimized.py`**: Webhook handler principal con detección de etiquetas
- **`test_bot_paused_tag.py`**: Script de pruebas automatizadas
- **`SISTEMA_BOT_PAUSED_TAG.md`**: Este documento de instrucciones

## 🚀 Cómo Funciona

### Flujo Simplificado

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO BOT-PAUSED TAG                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 👤 Agente agrega etiqueta "bot-paused" en Chatwoot         │
│           ↓                                                     │
│  2. 📡 Webhook conversation_updated se dispara                  │
│           ↓                                                     │
│  3. 🔍 Sistema detecta etiqueta bot-paused                     │
│           ↓                                                     │
│  4. 🔴 Bot se pausa para ese usuario                           │
│           ↓                                                     │
│  5. 👨‍💼 Agente maneja conversación manualmente                  │
│           ↓                                                     │
│  6. 👤 Agente remueve etiqueta "bot-paused"                    │
│           ↓                                                     │
│  7. 📡 Webhook conversation_updated se dispara nuevamente       │
│           ↓                                                     │
│  8. 🔍 Sistema detecta que no hay etiqueta                     │
│           ↓                                                     │
│  9. 🟢 Bot se reactiva automáticamente                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Comportamiento del Sistema

| Estado de la Etiqueta | Acción del Sistema | Resultado |
|-----------------------|-------------------|-----------|
| ✅ `bot-paused` presente | Pausar bot si está activo | Bot deja de responder |
| ❌ `bot-paused` removida | Reactivar bot si estaba pausado por etiqueta | Bot vuelve a responder |

## ⚙️ Configuración en Chatwoot

### 1. Crear la Etiqueta

1. Ir a **Settings** → **Labels** en Chatwoot
2. Crear nueva etiqueta con el nombre exacto: **`bot-paused`**
3. Asignar color (recomendado: rojo para indicar pausa)

### 2. Configurar Webhook

1. Ir a **Settings** → **Integrations** → **Webhooks** 
2. Crear nuevo webhook:
   - **URL**: `https://tu-servidor.com/webhook/chatwoot`
   - **Evento**: ✅ **`conversation_updated`** (CRÍTICO)
   - **Método**: POST
   - **Headers**: `Content-Type: application/json`

### 3. Asignar Permisos

Asegurar que los agentes tengan permisos para:
- Agregar/remover etiquetas en conversaciones
- Ver el estado de las etiquetas

## 🧪 Testing del Sistema

### Antes de Usar en Producción

Ejecutar el script de pruebas:

```bash
cd /Users/gino/BotRoyalv2
python test_bot_paused_tag.py
```

### Endpoints de Prueba Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/test/bot-paused-tag` | POST | Simula agregar/remover etiqueta |
| `/test/conversation-webhook` | POST | Simula webhook completo |
| `/test/bot-paused-instructions` | GET | Ver instrucciones del sistema |
| `/bot/status/{phone}` | GET | Ver estado actual del bot |

### Ejemplo de Prueba Manual

```bash
# Pausar bot para usuario 5491112345678
curl -X POST http://localhost:8000/test/bot-paused-tag \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "123",
    "phone": "5491112345678", 
    "has_bot_paused_tag": true
  }'

# Verificar estado
curl http://localhost:8000/bot/status/5491112345678

# Reactivar bot
curl -X POST http://localhost:8000/test/bot-paused-tag \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "123",
    "phone": "5491112345678", 
    "has_bot_paused_tag": false
  }'
```

## 🔍 Verificación y Logging

### Logs a Monitorear

```bash
# Buscar logs relacionados con bot-paused
tail -f logs/server.log | grep -i "bot-paused\|conversation_updated\|🏷️"
```

### Tipos de Log Importantes

```
🏷️ Evento conversation_updated detectado - procesando etiquetas...
🔍 Etiquetas encontradas para conversación 123: [{'title': 'bot-paused'}]
🎯 Etiqueta bot-paused detectada: True
🔴 Bot pausado por etiqueta para 5491112345678
🟢 Bot reactivado por remoción de etiqueta para 5491112345678
```

## ⚠️ Puntos Importantes

### Nombre de la Etiqueta

- **EXACTAMENTE**: `bot-paused` (con guión, sin espacios)
- **Case-sensitive**: Debe ser exactamente así
- **Sin variaciones**: `bot_paused`, `Bot-Paused`, `botpaused` NO funcionarán

### Compatibilidad

- ✅ **Compatible** con sistema existente de comandos por notas privadas
- ✅ **Compatible** con control por estado de conversación  
- ✅ **Compatible** con control por asignación de agente
- ✅ **Funciona** con ambos canales (WhatsApp + Chatwoot)

### Limitaciones

- Solo reactivación automática si fue pausado por etiqueta
- Si bot fue pausado por otra razón (agente, comando), no se reactivará automáticamente
- Requiere webhook `conversation_updated` configurado

## 🎯 Uso en Producción

### Para los Agentes

1. **Para pausar bot**: Agregar etiqueta `bot-paused` a la conversación
2. **Para reactivar bot**: Remover etiqueta `bot-paused` de la conversación
3. **Verificar estado**: El bot debe dejar de responder inmediatamente

### Para Administradores

1. **Monitorear logs** para asegurar funcionamiento correcto
2. **Verificar webhook** esté llegando correctamente
3. **Probar sistema** regularmente con endpoints de test

## 🛠️ Solución de Problemas

### Bot No Se Pausa

1. ✅ Verificar webhook configurado con evento `conversation_updated`
2. ✅ Verificar etiqueta exacta: `bot-paused`
3. ✅ Verificar logs del servidor para errores
4. ✅ Probar con endpoint `/test/bot-paused-tag`

### Bot No Se Reactiva

1. ✅ Verificar que etiqueta fue completamente removida
2. ✅ Verificar que bot fue pausado por etiqueta (no por otro método)
3. ✅ Verificar logs para mensajes de reactivación
4. ✅ Usar endpoint `/bot/status/{phone}` para ver estado

### Webhook No Llega

1. ✅ Verificar URL del webhook
2. ✅ Verificar evento `conversation_updated` seleccionado
3. ✅ Verificar logs de Chatwoot
4. ✅ Probar con herramienta como ngrok para development

## 📊 Estado de la Implementación

- ✅ **Core System**: Detección y procesamiento de etiquetas
- ✅ **Integration**: BotStateManager existente
- ✅ **Testing**: Script de pruebas completo
- ✅ **Endpoints**: API para testing y debugging
- ✅ **Documentation**: Instrucciones completas
- ✅ **Compatibility**: Con sistema existente

## 🚀 ¡Listo para Usar!

El sistema está **completamente implementado** y listo para usar. Solo falta:

1. **Configurar webhook** en Chatwoot con evento `conversation_updated`
2. **Crear etiqueta** `bot-paused` en Chatwoot
3. **Probar** con el script de testing
4. **Instruir a agentes** sobre cómo usar la etiqueta

¡El sistema es simple, efectivo y funciona inmediatamente! 🎉