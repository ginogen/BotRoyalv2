# 🏆 Royal Bot - Agente de Consultas con OpenAI Agents

Bot inteligente para **Royal Company** usando el esquema de agentes de OpenAI. Pablo, el agente virtual, maneja consultas sobre joyas, relojes, maquillaje e indumentaria con personalidad 100% argentina.

## 🚀 Características Principales

- **Agente Inteligente**: Powered by OpenAI Agents Python SDK
- **Personalidad Argentina**: Tono informal, amigable y local 
- **Anti-Repetición**: Sistema inteligente que evita saludos duplicados
- **Información Completa**: Base de conocimiento integral sobre Royal
- **Multi-Canal**: Webhooks para Chatwoot y Evolution API (WhatsApp)
- **Contexto Persistente**: Redis para mantener historial de conversaciones
- **Deploy Ready**: Configurado para Railway con escalabilidad automática

## 📋 Requisitos

- Python 3.9+
- OpenAI API Key
- Redis (opcional pero recomendado)
- PostgreSQL (para producción)

## ⚡ Instalación Rápida

### 1. Cloná el repositorio
```bash
git clone <url-repo>
cd BotRoyalv2
```

### 2. Creá entorno virtual
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

### 3. Instalá dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurá variables de entorno
```bash
cp config.env.example .env
# Editá .env con tus valores
```

### 5. Probá el agente
```bash
python test_chat.py
```

## 🔧 Configuración

### Variables de Entorno Requeridas

```env
# OpenAI (OBLIGATORIO)
OPENAI_API_KEY=sk-tu-clave-aqui

# Base de Datos (Opcional para desarrollo)
DATABASE_URL=postgresql://user:pass@host:5432/royal_bot

# Redis (Opcional para desarrollo) 
REDIS_URL=redis://localhost:6379

# Webhooks (Solo para producción)
CHATWOOT_WEBHOOK_SECRET=tu-secret
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_TOKEN=tu-token
```

## 🎯 Uso

### Modo Desarrollo - Chat Directo
```bash
# Ejecutar el chat de prueba
python test_chat.py
```

**Comandos disponibles:**
- `salir` - Terminar sesión
- `reset` - Reiniciar conversación  
- `historial` - Ver historial completo

### Modo Producción - Servidor Web
```bash
# Iniciar servidor
python server.py

# O con uvicorn
uvicorn server:app --host 0.0.0.0 --port 8000
```

**Endpoints disponibles:**
- `GET /` - Status del servicio
- `GET /health` - Health check
- `POST /webhook/chatwoot` - Webhook Chatwoot
- `POST /webhook/evolution` - Webhook Evolution API
- `POST /test/message` - Test directo del agente

### Test API con curl
```bash
# Test mensaje directo
curl -X POST "http://localhost:8000/test/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, ¿cómo funciona Royal?", "client_id": "test123"}'
```

## 🧠 Sobre el Agente Pablo

### Personalidad
- **Nombre**: Pablo
- **Tono**: Argentino, informal, amigable
- **Palabras típicas**: "dale", "posta", "bárbaro", "ojo", "mirá"
- **Anti-saludos**: Solo saluda una vez por día por cliente

### Información que maneja
- **Productos**: Joyas (plata 925, oro 18K), relojes, maquillaje, indumentaria
- **Compras**: Mayorista (min $40k) y minorista (sin mínimo) 
- **Envíos**: Andreani, $4999 Córdoba, $7499 nacional, gratis +$80k
- **Pagos**: Tarjeta, transferencia, efectivo, sistema de seña
- **Servicios**: Arreglos de joyas, grabados personalizados
- **Ubicación**: 3 locales en Córdoba Capital

### Palabras Prohibidas
❌ **NUNCA usa**: aquí, puedes, quieres, tienes, debes, tú, tu, etc.
✅ **Siempre usa**: acá, podés, querés, tenés, debés, vos, te, etc.

## 🔌 Integraciones

### Chatwoot
```javascript
// Configurar webhook en Chatwoot
POST https://tu-bot.railway.app/webhook/chatwoot
```

### Evolution API (WhatsApp)
```javascript  
// Configurar webhook en Evolution
POST https://tu-bot.railway.app/webhook/evolution
```

## 🚢 Deploy en Railway

### 1. Conectá tu repo a Railway
```bash
# Railway CLI
railway login
railway link
```

### 2. Configurá variables de entorno en Railway
- `OPENAI_API_KEY`
- `DATABASE_URL` (se crea automáticamente)
- `REDIS_URL` (agregar Redis add-on)
- Variables de webhook según necesites

### 3. Deploy automático
```bash
git push origin main
# Railway hace deploy automático
```

### 4. Verificá funcionamiento
```bash
curl https://tu-app.railway.app/health
```

## 🧪 Testing

### Test Básico
```bash
# Conversación simple
python test_chat.py
```

### Test API
```bash
# Con servidor corriendo
curl -X POST localhost:8000/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Hacen arreglos de joyas?"}'
```

### Test Webhook
```bash
# Simular webhook Chatwoot
curl -X POST localhost:8000/webhook/chatwoot \
  -H "Content-Type: application/json" \
  -d '{"event": "message_created", "message_type": "incoming", "sender_type": "contact", "content": "Hola"}'
```

## 📈 Performance y Escalabilidad

- **Redis**: Caché de contexto con TTL de 24hs
- **Background Tasks**: Procesamiento asíncrono de webhooks
- **Connection Pooling**: Optimizado para múltiples requests
- **Logging**: Sistema completo de logs para debugging
- **Health Checks**: Monitoreo automático de servicios

## 🐛 Troubleshooting

### Error: "OpenAI API Key not found"
```bash
export OPENAI_API_KEY=tu-clave-aqui
# O configurála en .env
```

### Error: "Redis connection failed"
```bash
# Redis es opcional en desarrollo
# El bot funciona sin Redis (sin persistencia de contexto)
```

### Error: "Agent import failed"
```bash
pip install openai-agents
# Verificá que tengas la versión correcta
```

### Bot responde en inglés
- Verificá que el prompt tenga las instrucciones en español
- Chequeá que no esté usando palabras prohibidas

## 📞 Datos de Royal Company

### Información Bancaria
- **CBU**: 4530000800014232361716
- **Alias**: ROYAL.JOYAS.2023.nx  
- **Titular**: Edward Freitas Souzaneto

### Ubicaciones (Córdoba Capital)
- Royal Joyas: 9 de Julio 472
- Royal Joyas: General Paz 159, Galería Planeta, Local 18
- Royal Bijou: San Martín 48, Galería San Martín, Local 23A

### Horarios
- Lunes a viernes: 9:30 a 18:30
- Sábados: 9:30 a 14:00
- Online: 24/7

## 🤝 Contribución

1. Fork el proyecto
2. Creá tu branch (`git checkout -b feature/nueva-feature`)
3. Commit cambios (`git commit -am 'Agrega nueva feature'`)
4. Push al branch (`git push origin feature/nueva-feature`)
5. Abrí un Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver `LICENSE` para más detalles.

## 📧 Soporte

Para soporte técnico o consultas sobre el bot, contactar al equipo de desarrollo.

---
**🏆 Royal Company 2024 - Powered by OpenAI Agents** 