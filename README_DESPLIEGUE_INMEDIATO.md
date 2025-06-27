# 🚀 DESPLIEGUE INMEDIATO EN RAILWAY + WHATSAPP

## ⚡ PASOS RÁPIDOS (5 MINUTOS)

### 1️⃣ PREPARAR TU CÓDIGO

```bash
# 1. Hacer commit de todo
git add .
git commit -m "🚀 Bot optimizado para Railway"
git push origin main
```

### 2️⃣ USAR SCRIPT AUTOMÁTICO

```bash
# Script que hace TODO automáticamente
python deploy_railway.py
```

**O si prefieres manual, continúa leyendo:**

### 3️⃣ CREAR PROYECTO EN RAILWAY

1. **Ve a** [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. **Selecciona** tu repositorio `BotRoyalv2`
4. **Espera** a que termine el build

### 4️⃣ CONFIGURAR VARIABLES (OBLIGATORIAS)

En Railway Dashboard → **Variables**:

```bash
# === CRÍTICAS ===
OPENAI_API_KEY=sk-tu-openai-key-aqui
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_TOKEN=tu_token_evolution
INSTANCE_NAME=tu_instancia_whatsapp

# === RENDIMIENTO ===
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
PORT=8000
```

### 5️⃣ OBTENER URL DE RAILWAY

Al terminar el deploy, tendrás algo como:
```
https://botroyalv2-production-abc123.up.railway.app
```

### 6️⃣ CONFIGURAR WEBHOOK

**Opción A - Script automático:**
```bash
python test_evolution_api.py
# Selecciona opción 2 y pega tu URL de Railway
```

**Opción B - Manual en Evolution API:**
- **URL**: `https://tu-url-railway.up.railway.app/webhook/evolution`
- **Events**: `MESSAGES_UPSERT`

### 7️⃣ PROBAR INMEDIATAMENTE

```bash
# 1. Health check
curl https://tu-url-railway.up.railway.app/health

# 2. Test del bot
curl -X POST https://tu-url-railway.up.railway.app/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "user_id": "test"}'

# 3. WhatsApp real
# Envía mensaje a tu número conectado
```

## 🛠️ HERRAMIENTAS INCLUIDAS

### `deploy_railway.py` - Setup Automático
```bash
python deploy_railway.py
# Hace todo: Git, Railway, variables, deploy
```

### `test_evolution_api.py` - Test WhatsApp
```bash
python test_evolution_api.py
# Verifica conexión, configura webhook, hace tests
```

### `start_chatwoot_server.py` - Desarrollo Local
```bash
python start_chatwoot_server.py
# Para probar antes de desplegar
```

## 🐛 SI ALGO FALLA

### ❌ "Error en Railway"
```bash
# Ver logs
railway logs --follow

# Verificar variables
railway variables
```

### ❌ "WhatsApp no responde"
```bash
# Test Evolution API
python test_evolution_api.py

# Verificar webhook manual
curl -X POST https://tu-url-railway.up.railway.app/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{"data": {"key": {"remoteJid": "test@s.whatsapp.net"}, "message": {"conversation": "test"}}}'
```

### ❌ "Bot no funciona"
```bash
# Test directo
curl -X POST https://tu-url-railway.up.railway.app/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Funcionas?", "user_id": "debug"}'
```

## ✅ CHECKLIST FINAL

- [ ] ✅ Código en GitHub
- [ ] ✅ Proyecto en Railway desplegado
- [ ] ✅ Variables configuradas (especialmente OPENAI_API_KEY)
- [ ] ✅ Evolution API webhook configurado
- [ ] ✅ `/health` responde OK
- [ ] ✅ `/test/message` funciona
- [ ] ✅ WhatsApp responde a mensajes reales

## 🎯 MONITOREO EN PRODUCCIÓN

### URLs Importantes:
- `https://tu-url/` - Dashboard
- `https://tu-url/health` - Estado
- `https://tu-url/stats` - Métricas

### Logs en Tiempo Real:
```bash
railway logs --follow
```

## 🚀 ¡LISTO!

Tu bot está funcionando 24/7 en Railway, respondiendo automáticamente por WhatsApp con múltiples conversaciones simultáneas.

---

**¿Problemas?** Usa los scripts de debug incluidos o revisa los logs de Railway. 