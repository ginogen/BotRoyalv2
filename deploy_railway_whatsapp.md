# 🚀 DESPLEGAR BOT EN RAILWAY + WHATSAPP

## 📋 PASOS RÁPIDOS PARA PRODUCCIÓN

### 1️⃣ SUBIR CÓDIGO A GITHUB

```bash
# Si no tienes el repo en GitHub
git add .
git commit -m "🚀 Bot optimizado para Railway"
git push origin main
```

### 2️⃣ CREAR PROYECTO EN RAILWAY

1. Ve a [railway.app](https://railway.app) 
2. **New Project** → **Deploy from GitHub repo**
3. Selecciona tu repositorio **BotRoyalv2**
4. Railway empezará a desplegar automáticamente

### 3️⃣ CONFIGURAR VARIABLES EN RAILWAY

En Railway Dashboard → Variables, agrega:

```bash
# === OBLIGATORIAS ===
OPENAI_API_KEY=sk-tu-key-aqui
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_TOKEN=tu_token_evolution
INSTANCE_NAME=tu_instancia_whatsapp

# === RENDIMIENTO ===
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
PORT=8000
```

### 4️⃣ OBTENER URL DE RAILWAY

Cuando termine el deploy, tendrás una URL como:
```
https://botroyalv2-production-xxxx.up.railway.app
```

### 5️⃣ CONFIGURAR WEBHOOK EN EVOLUTION API

En tu Evolution API, configura webhook:
- **URL**: `https://tu-url-railway.up.railway.app/webhook/evolution`
- **Events**: `MESSAGES_UPSERT`

### 6️⃣ PROBAR

1. **Health Check**:
```bash
curl https://tu-url-railway.up.railway.app/health
```

2. **Test del Bot**:
```bash
curl -X POST https://tu-url-railway.up.railway.app/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "user_id": "test"}'
```

3. **WhatsApp Real**: Envía mensaje a tu número conectado

## ⚡ COMANDOS ÚTILES

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Ver logs en tiempo real
railway logs --follow

# Configurar variables por CLI
railway variables set EVOLUTION_API_URL=https://tu-evolution.com
railway variables set EVOLUTION_API_TOKEN=tu_token

# Redespliegar
railway up
```

## 🔧 VARIABLES COMPLETAS OPCIONALES

```bash
# WhatsApp (Evolution API)
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_TOKEN=tu_token_aqui
INSTANCE_NAME=tu_instancia

# OpenAI
OPENAI_API_KEY=sk-tu-key-aqui

# Rendimiento
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
MESSAGE_BUFFER_TIMEOUT=8000
MESSAGE_COOLDOWN=2000

# Chatwoot (opcional)
CHATWOOT_API_URL=https://tu-chatwoot.com
CHATWOOT_API_TOKEN=tu_token
CHATWOOT_ACCOUNT_ID=123
```

## 🐛 SI NO FUNCIONA

### 1. Ver logs de Railway
```bash
railway logs
```

### 2. Verificar variables
```bash
railway variables
```

### 3. Test manual del webhook
```bash
curl -X POST https://tu-url-railway.up.railway.app/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {"remoteJid": "5491112345678@s.whatsapp.net"},
      "message": {"conversation": "test manual"}
    }
  }'
```

## ✅ CHECKLIST

- [ ] Código en GitHub
- [ ] Proyecto en Railway
- [ ] Variables configuradas
- [ ] URL de Railway funcionando
- [ ] Webhook en Evolution configurado
- [ ] Health check OK
- [ ] WhatsApp responde

¡Listo! Tu bot está en producción 🚀 