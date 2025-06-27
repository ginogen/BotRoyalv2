# 🚀 GUÍA COMPLETA: DESPLIEGUE EN RAILWAY + WHATSAPP

## 📋 PRERREQUISITOS

Antes de comenzar, asegúrate de tener:
- ✅ Cuenta en Railway (gratis)
- ✅ Evolution API configurada (para WhatsApp)
- ✅ Chatwoot configurado (opcional)
- ✅ Git instalado

## 🔗 PASO 1: PREPARAR RAILWAY

### 1.1 Crear Cuenta en Railway
1. Ve a [railway.app](https://railway.app)
2. **Sign Up** con GitHub (recomendado)
3. Confirma tu email

### 1.2 Instalar Railway CLI (Opcional)
```bash
# Método 1: NPM
npm install -g @railway/cli

# Método 2: Direct download
# Ve a: https://docs.railway.app/develop/cli#install
```

## 🚀 PASO 2: CREAR PROYECTO EN RAILWAY

### 2.1 Desde GitHub (Recomendado)

1. **Push tu código a GitHub** (si no lo has hecho):
```bash
git add .
git commit -m "🚀 Servidor Chatwoot optimizado para Railway"
git push origin main
```

2. **Conectar con Railway**:
   - Ve a [railway.app/dashboard](https://railway.app/dashboard)
   - Click **"New Project"**
   - Selecciona **"Deploy from GitHub repo"**
   - Autoriza Railway en GitHub
   - Selecciona tu repositorio **BotRoyalv2**

### 2.2 Desde Railway CLI
```bash
# Login en Railway
railway login

# En tu directorio del proyecto
railway init
railway link  # Si ya tienes un proyecto
```

## ⚙️ PASO 3: CONFIGURAR VARIABLES DE ENTORNO EN RAILWAY

### 3.1 Variables Obligatorias para WhatsApp

En Railway Dashboard → Tu Proyecto → **Variables**:

```bash
# === SERVIDOR ===
PORT=8000

# === CONFIGURACIÓN DE RENDIMIENTO ===
WORKER_POOL_SIZE=3
MAX_CONCURRENT_USERS=5
MESSAGE_BUFFER_TIMEOUT=8000
MESSAGE_COOLDOWN=2000

# === EVOLUTION API (WHATSAPP) ===
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_TOKEN=tu_token_evolution_aqui
INSTANCE_NAME=tu_instancia_whatsapp

# === OPENAI (para el bot) ===
OPENAI_API_KEY=sk-tu-key-de-openai-aqui

# === CHATWOOT (opcional) ===
CHATWOOT_API_URL=https://tu-chatwoot.com
CHATWOOT_API_TOKEN=tu_token_chatwoot
CHATWOOT_ACCOUNT_ID=123
```

### 3.2 Configurar Variables por CLI
```bash
# Variables esenciales para WhatsApp
railway variables set EVOLUTION_API_URL=https://tu-evolution-api.com
railway variables set EVOLUTION_API_TOKEN=tu_token_aqui
railway variables set INSTANCE_NAME=tu_instancia
railway variables set OPENAI_API_KEY=sk-tu-key-aqui
railway variables set WORKER_POOL_SIZE=3
railway variables set MAX_CONCURRENT_USERS=5
```

## 📱 PASO 4: OBTENER DATOS DE EVOLUTION API

### 4.1 Si Ya Tienes Evolution API:
```bash
# Necesitas estos datos:
EVOLUTION_API_URL=https://tu-dominio-evolution.com
EVOLUTION_API_TOKEN=tu_token_de_la_api
INSTANCE_NAME=nombre_de_tu_instancia_whatsapp
```

### 4.2 Si No Tienes Evolution API:

**Opciones populares:**
- [Evolution API Official](https://github.com/EvolutionAPI/evolution-api)
- Servicios como Typebot, N8N que incluyen Evolution
- Proveedores de WhatsApp API

**Configuración Básica Evolution:**
1. Desplegar Evolution API en otro servicio
2. Crear instancia de WhatsApp
3. Conectar tu número
4. Obtener token de API

## 🚀 PASO 5: DESPLEGAR EN RAILWAY

### 5.1 Deploy Automático
```bash
# Si usas CLI
railway up

# O desde GitHub (automático)
# Railway detecta cambios en tu repo y despliega automáticamente
```

### 5.2 Verificar Despliegue
1. En Railway Dashboard verás el **deployment**
2. Espera a que aparezca **"Success"** 
3. Click en **"View Logs"** para ver el progreso
4. Cuando esté listo, tendrás tu **URL pública**

### 5.3 Tu URL será algo como:
```
https://botroyalv2-production-xxxx.up.railway.app
```

## 🔗 PASO 6: CONFIGURAR WEBHOOK EN EVOLUTION API

### 6.1 URL del Webhook
Tu webhook para WhatsApp será:
```
https://tu-url-de-railway.up.railway.app/webhook/evolution
```

### 6.2 Configurar en Evolution API

**Método 1: API Request**
```bash
curl -X POST 'https://tu-evolution-api.com/webhook/set/tu_instancia' \
  -H 'apikey: tu_token_evolution' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://tu-url-railway.up.railway.app/webhook/evolution",
    "enabled": true,
    "events": ["MESSAGES_UPSERT"]
  }'
```

**Método 2: Panel de Evolution**
1. Ve al panel de tu Evolution API
2. Selecciona tu instancia
3. **Webhooks** → **Add Webhook**
4. URL: `https://tu-url-railway.up.railway.app/webhook/evolution`
5. Events: `MESSAGES_UPSERT`
6. **Save**

## 🧪 PASO 7: PROBAR EL SISTEMA

### 7.1 Verificar Health Check
```bash
curl https://tu-url-railway.up.railway.app/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "services": {
    "evolution": "configured",
    "database": "connected"
  },
  "workers": {
    "pool_size": 3,
    "active_workers": 0
  }
}
```

### 7.2 Test Directo del Bot
```bash
curl -X POST https://tu-url-railway.up.railway.app/test/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, ¿tenés anillos de plata?",
    "user_id": "test_whatsapp"
  }'
```

### 7.3 Probar con WhatsApp Real

1. **Envía un mensaje a tu número de WhatsApp conectado**
2. **Verifica en Railway Logs**:
   - Ve a Railway Dashboard → Tu proyecto → **Deployments** → **View Logs**
   - Deberías ver: `📥 Mensaje WhatsApp agregado: numero_telefono`

3. **El bot debería responder automáticamente**

## 📊 PASO 8: MONITOREO EN PRODUCCIÓN

### 8.1 URLs de Monitoreo
```bash
# Dashboard principal
https://tu-url-railway.up.railway.app/

# Estadísticas en tiempo real
https://tu-url-railway.up.railway.app/stats

# Health check
https://tu-url-railway.up.railway.app/health
```

### 8.2 Ver Logs en Tiempo Real
```bash
# Con Railway CLI
railway logs --follow

# O en Railway Dashboard → View Logs
```

## 🐛 TROUBLESHOOTING

### ❌ "No recibo mensajes de WhatsApp"

**Verificaciones:**
```bash
# 1. Verificar webhook configurado
curl https://tu-evolution-api.com/webhook/find/tu_instancia \
  -H 'apikey: tu_token'

# 2. Verificar instancia activa
curl https://tu-evolution-api.com/instance/connectionState/tu_instancia \
  -H 'apikey: tu_token'

# 3. Test manual del webhook
curl -X POST https://tu-url-railway.up.railway.app/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {"remoteJid": "5491112345678@s.whatsapp.net"},
      "message": {"conversation": "test desde curl"}
    }
  }'
```

### ❌ "Error 500 en Railway"

**Revisar logs:**
```bash
railway logs

# Buscar errores como:
# - Missing environment variables
# - ImportError 
# - Connection errors
```

**Soluciones comunes:**
```bash
# Verificar variables configuradas
railway variables

# Reinstalar dependencias
railway restart

# Verificar que requirements.txt esté actualizado
```

### ❌ "Bot no responde o responde mal"

**Debug del bot:**
```bash
# Test directo
curl -X POST https://tu-url-railway.up.railway.app/test/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "test debug",
    "user_id": "debug_user"
  }'

# Verificar que OPENAI_API_KEY esté configurada
railway variables | grep OPENAI
```

## 🔧 CONFIGURACIÓN AVANZADA

### Aumentar Rendimiento para Más Usuarios
```bash
# Variables para mayor volumen
railway variables set WORKER_POOL_SIZE=5
railway variables set MAX_CONCURRENT_USERS=10
railway variables set MESSAGE_BUFFER_TIMEOUT=10000
```

### Agregar Chatwoot (Opcional)
```bash
# Si también quieres Chatwoot
railway variables set CHATWOOT_API_URL=https://tu-chatwoot.com
railway variables set CHATWOOT_API_TOKEN=tu_token
railway variables set CHATWOOT_ACCOUNT_ID=123

# Configurar webhook en Chatwoot:
# URL: https://tu-url-railway.up.railway.app/webhook/chatwoot
# Event: message_created
```

## ✅ CHECKLIST FINAL

Antes de considerar listo:

- [ ] ✅ Proyecto desplegado en Railway
- [ ] ✅ Variables de entorno configuradas
- [ ] ✅ Evolution API conectada y webhook configurado
- [ ] ✅ Health check responde OK
- [ ] ✅ Test directo del bot funciona
- [ ] ✅ WhatsApp responde a mensajes reales
- [ ] ✅ Logs muestran actividad normal
- [ ] ✅ Stats endpoint muestra métricas

## 🎯 COMANDOS ÚTILES DE RAILWAY

```bash
# Ver estado del proyecto
railway status

# Ver variables
railway variables

# Ver logs en tiempo real
railway logs --follow

# Redespliegar
railway up --detach

# Abrir en browser
railway open

# Conectar terminal al contenedor
railway shell
```

## 📞 EJEMPLO DE FLUJO COMPLETO

1. **Usuario envía**: "Hola" por WhatsApp
2. **Evolution API recibe** el mensaje
3. **Evolution API envía** webhook a Railway
4. **Railway recibe** en `/webhook/evolution`
5. **Sistema procesa** con worker pool
6. **Bot genera** respuesta contextual
7. **Railway envía** respuesta via Evolution API
8. **Usuario recibe** respuesta en WhatsApp

## 🚀 ¡LISTO PARA PRODUCCIÓN!

Una vez completados todos los pasos, tu bot estará:
- ✅ **Funcionando 24/7** en Railway
- ✅ **Respondiendo automáticamente** por WhatsApp
- ✅ **Manejando múltiples conversaciones** simultáneas
- ✅ **Optimizado para concurrencia** 
- ✅ **Con monitoreo en tiempo real**

---

**¿Problemas?** Revisa los logs de Railway y verifica que todas las variables estén configuradas correctamente. 