# 🏷️ Sistema Completo de Control de Bot con Etiquetas `bot-paused` y `bot-active`

## 📋 Resumen

Sistema avanzado para que los agentes de Chatwoot puedan pausar/reactivar el bot usando dos etiquetas con lógica de prioridades:

- **`bot-paused`**: Pausa el bot manualmente
- **`bot-active`**: Reactiva el bot INMEDIATAMENTE (funciona como override para cualquier pausa)

## ✅ Nueva Implementación: Etiqueta `bot-active` 

### 🆕 Funcionalidades Agregadas

1. **Detección dual de etiquetas** con función `detect_bot_control_tags()` ✅
2. **Lógica de prioridades**: `bot-active` siempre gana sobre `bot-paused` ✅  
3. **Reactivación forzada**: Funciona para pausas por reclamos, agentes, etc. ✅
4. **Logging detallado** para todas las acciones ✅
5. **Endpoints de prueba** actualizados ✅
6. **Tests automatizados** para todos los casos ✅

## 🎯 Casos de Uso

### 🔧 Caso Principal: Reclamos con Reactivación Inmediata

```
┌─────────────────────────────────────────────────────────────┐
│              FLUJO COMPLETO DE RECLAMO                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 👤 Usuario: "Tengo un reclamo con mi pedido"           │
│           ↓                                                 │
│  2. 🤖 Sistema detecta keywords → Asigna a equipo soporte  │
│           ↓                                                 │
│  3. ⏸️ Bot pausado automáticamente por 24 horas             │
│           ↓                                                 │
│  4. 👨‍💼 Agente resuelve el problema                          │
│           ↓                                                 │
│  5. 🏷️ Agente agrega etiqueta "bot-active"                 │
│           ↓                                                 │
│  6. ✅ Bot reactivado INMEDIATAMENTE (sin esperar 24h)      │
│           ↓                                                 │
│  7. 🤖 Bot funciona normalmente                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 📋 Tabla de Prioridades y Acciones

| Etiquetas Presentes | Acción del Sistema | Estado Final | Caso de Uso |
|-------------------|-------------------|-------------|-------------|
| Ninguna | Mantener estado actual | Sin cambio | Normal |
| `bot-paused` solamente | Pausar bot | 🔴 Pausado | Agente toma control |
| `bot-active` solamente | Reactivar bot | 🟢 Activo | Reactivar tras reclamo/pausa |
| Ambas presentes | **Reactivar** (bot-active gana) | 🟢 Activo | Override de cualquier pausa |

## 🔧 Implementación Técnica

### 📁 Archivos Modificados

1. **`royal_server_optimized.py`**:
   - Nueva función `detect_bot_control_tags()` (reemplaza `detect_bot_paused_tag()`)
   - Lógica actualizada en `handle_conversation_updated()` 
   - Nuevos endpoints de prueba
   - Instrucciones actualizadas

2. **`test_bot_paused_tag.py`**:
   - Tests para ambas etiquetas
   - Test de prioridades `bot-active` > `bot-paused`
   - Test de escenario completo de reclamo
   - Clase renombrada a `BotControlTagsTester`

### 🔍 Función Principal: `detect_bot_control_tags()`

```python
def detect_bot_control_tags(labels: list) -> dict:
    """
    Detecta etiquetas de control del bot ('bot-paused' y 'bot-active')
    
    Returns:
        {
            'bot_paused': bool,
            'bot_active': bool, 
            'action': 'pause'|'activate'|None,
            'priority_tag': str|None
        }
    """
```

**Lógica de Prioridades**:
- Si `bot-active` presente → `action = 'activate'`
- Si solo `bot-paused` presente → `action = 'pause'`
- Si ninguna presente → `action = None`

## 🧪 Testing del Sistema

### Nuevos Endpoints de Prueba

| Endpoint | Función |
|----------|---------|
| `POST /test/bot-control-tags` | Probar ambas etiquetas |
| `POST /test/complaint-scenario` | Simular reclamo completo |
| `GET /test/bot-paused-instructions` | Ver instrucciones actualizadas |

### Ejemplos de Prueba

#### 1. Reactivación Forzada tras Reclamo

```bash
# Simular reclamo (pausa 24h)
curl -X POST http://localhost:8000/test/complaint-scenario \
  -H "Content-Type: application/json" \
  -d '{"step": "complaint", "phone": "5491112345678"}'

# Reactivar inmediatamente con bot-active
curl -X POST http://localhost:8000/test/complaint-scenario \
  -H "Content-Type: application/json" \
  -d '{"step": "agent_reactivates", "phone": "5491112345678"}'
```

#### 2. Override de Prioridades

```bash
# Simular ambas etiquetas (bot-active debe ganar)
curl -X POST http://localhost:8000/test/bot-control-tags \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5491112345678",
    "bot_paused": true,
    "bot_active": true
  }'
```

### Script de Testing Automatizado

```bash
cd /Users/gino/BotRoyalv2
python test_bot_paused_tag.py
```

**Tests Incluidos**:
- ✅ Detección de etiquetas 
- ✅ Ciclo pausar/reactivar básico
- ✅ Formatos de webhook
- ✅ **Override bot-active** (nuevo)
- ✅ **Escenario reclamo completo** (nuevo)

## 🔍 Logging Detallado

### Logs de bot-active

```bash
🟢 Bot FORZADAMENTE reactivado por etiqueta 'bot-active' para 5491112345678
   ↳ Razón de pausa anterior sobreescrita: 'Asignado a equipo support'
```

### Logs de detección

```bash
🎯 Etiquetas de control detectadas: {
  'bot_paused': False, 
  'bot_active': True, 
  'action': 'activate', 
  'priority_tag': 'bot-active'
}
```

## ⚙️ Configuración en Chatwoot

### 1. Crear Ambas Etiquetas

1. Ir a **Settings** → **Labels** en Chatwoot
2. Crear etiquetas:
   - **`bot-paused`** (color rojo) - Para pausar manualmente
   - **`bot-active`** (color verde) - Para reactivar forzadamente

### 2. Configurar Webhook (Igual que antes)

- **URL**: `https://tu-servidor.com/webhook/chatwoot`
- **Evento**: ✅ **`conversation_updated`**
- **Método**: POST

## 🎯 Instrucciones para Agentes

### Para Casos de Reclamos

1. **Problema detectado automáticamente**: El sistema ya pausó el bot por 24h
2. **Resolver el problema**: Atender al cliente manualmente 
3. **Problema resuelto**: Agregar etiqueta **`bot-active`** a la conversación
4. **Resultado**: Bot reactivado INMEDIATAMENTE (no esperar 24h)

### Para Pausas Manuales

1. **Pausar**: Agregar etiqueta **`bot-paused`**
2. **Reactivar normal**: Remover etiqueta **`bot-paused`**
3. **Reactivar forzado**: Agregar etiqueta **`bot-active`**

## 🔒 Robustez del Sistema

### Ventajas de bot-active

- ✅ **Funciona para cualquier pausa**: Reclamos, comandos, manual
- ✅ **Override inmediato**: No importa TTL o razón de pausa
- ✅ **Prioridad clara**: Siempre gana sobre bot-paused
- ✅ **Logging detallado**: Trazabilidad completa
- ✅ **Compatible**: No rompe sistema existente

### Casos Cubiertos

- ❌ **Pausa por reclamo** (24h) → ✅ **Reactivación con bot-active**
- ❌ **Pausa por comando** → ✅ **Reactivación con bot-active**
- ❌ **Pausa manual** → ✅ **Reactivación con bot-active**  
- ❌ **Pausa por etiqueta** → ✅ **Reactivación con bot-active**

## 📊 Estado de Implementación

- ✅ **Core Logic**: Detección y procesamiento de ambas etiquetas
- ✅ **Priority System**: bot-active > bot-paused
- ✅ **Force Reactivation**: Override cualquier pausa
- ✅ **Enhanced Logging**: Logs detallados de todas las acciones
- ✅ **Updated Tests**: Tests para todos los nuevos casos
- ✅ **New Endpoints**: APIs de prueba actualizadas
- ✅ **Documentation**: Instrucciones completas actualizadas

## 🚀 ¡Solución Completa!

El sistema ahora resuelve **completamente** el problema original:

**ANTES**: 
- Usuario hace reclamo → Bot pausado 24h → Agente debe esperar o usar comandos complejos

**AHORA**:
- Usuario hace reclamo → Bot pausado 24h → Agente agrega `bot-active` → **Bot reactivado INMEDIATAMENTE**

¡**Simple, efectivo y robusto**! 🎉

### Próximos Pasos

1. **Configurar webhook** (si no está ya configurado)
2. **Crear etiquetas** `bot-paused` y `bot-active` en Chatwoot
3. **Probar sistema** con script de testing
4. **Capacitar agentes** en uso de etiqueta `bot-active`
5. **Monitorear logs** para verificar funcionamiento

El sistema está **100% listo** para resolver pausas por reclamos de forma inmediata! 🚀