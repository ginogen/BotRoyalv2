# 🚀 Deploy en Railway - Guía Paso a Paso

## 📋 Estado Actual
✅ Repositorio Git inicializado  
✅ Commit inicial completado  
✅ Gitignore configurado  
✅ Documentación completa  

## 🔴 PRÓXIMOS PASOS

### 1. Subir a GitHub

#### Opción A: Crear repo desde terminal
```bash
# Crear repositorio público en GitHub usando GitHub CLI
gh repo create BotRoyalv2 --public --description "Bot Royal v2 - Interfaz de Testing"

# Conectar origin
git remote add origin https://github.com/TU_USUARIO/BotRoyalv2.git

# Subir código
git push -u origin main
```

#### Opción B: Crear repo manualmente
1. Ir a [GitHub.com](https://github.com)
2. Click "New repository"
3. Nombre: `BotRoyalv2`
4. Descripción: `Bot Royal v2 - Interfaz de Testing`
5. **NO** agregar README/gitignore (ya los tienes)
6. Click "Create repository"
7. Ejecutar comandos que aparecen:
```bash
git remote add origin https://github.com/TU_USUARIO/BotRoyalv2.git
git branch -M main
git push -u origin main
```

### 2. Deploy en Railway

#### 2.1 Crear Proyecto
1. Ir a [Railway.app](https://railway.app)
2. Login con GitHub
3. Click "New Project"
4. Seleccionar "Deploy from GitHub repo"
5. Elegir tu repositorio `BotRoyalv2`

#### 2.2 Configurar Variables de Entorno
En Railway Dashboard → Variables, agregar:

```env
OPENAI_API_KEY=sk-proj-...tu-key-aquí
WC_URL=https://royalmayorista.com.ar
WC_CONSUMER_KEY=ck_...tu-key-aquí
WC_CONSUMER_SECRET=cs_...tu-secret-aquí
PORT=8501
DATABASE_URL=${DATABASE_URL}
```

**IMPORTANTE:** Railway provee automáticamente `DATABASE_URL` para PostgreSQL.

#### 2.3 Configurar Base de Datos
1. En Railway Dashboard, click "Add a Service"
2. Seleccionar "PostgreSQL"
3. La variable `DATABASE_URL` se auto-configurará
4. El código detectará automáticamente PostgreSQL y migrará desde SQLite

#### 2.4 Deploy Automático
Railway detectará automáticamente:
- ✅ `requirements.txt` → instala dependencias Python
- ✅ `railway.toml` → configuración de build y comando
- ✅ `bot_testing_app.py` → aplicación Streamlit

### 3. Verificar Deploy

#### 3.1 Acceder a la App
- Railway te dará una URL pública: `https://botroyalv2-production.up.railway.app`
- La interfaz Streamlit estará disponible inmediatamente

#### 3.2 Verificar Funcionalidad
1. **Chat funciona**: Probar conversación con Pablo
2. **Base de datos**: Feedback se guarda en PostgreSQL
3. **WooCommerce**: Productos se cargan correctamente
4. **Dashboard**: Métricas se muestran

### 4. Variables de Entorno Requeridas

```env
# ✅ OBLIGATORIAS para funcionamiento básico
OPENAI_API_KEY=sk-proj-...
WC_URL=https://royalmayorista.com.ar
WC_CONSUMER_KEY=ck_...
WC_CONSUMER_SECRET=cs_...

# ✅ AUTOMÁTICAS en Railway
DATABASE_URL=${DATABASE_URL}  # Railway lo provee
PORT=8501                     # Railway lo detecta

# ⚡ OPCIONALES para optimización
DATABASE_TYPE=postgresql      # Se detecta automáticamente
STREAMLIT_SERVER_PORT=8501    # Por defecto
```

### 5. Troubleshooting

#### Error: Variables no configuradas
- Verificar que todas las variables estén en Railway Dashboard
- Reiniciar el servicio después de agregar variables

#### Error: Base de datos
- Railway tarda ~30 segundos en provisionar PostgreSQL
- El código migra automáticamente de SQLite

#### Error: Puerto
- Railway asigna automáticamente el puerto
- No modificar `PORT` a menos que sea necesario

### 6. Monitoreo Post-Deploy

#### Logs en Tiempo Real
```bash
# En Railway Dashboard → Deployments → Ver logs
# O usar Railway CLI:
railway logs
```

#### Métricas de Sistema
- CPU/RAM usage en Railway Dashboard
- Performance de base de datos PostgreSQL
- Número de usuarios concurrentes

### 7. Actualizaciones Futuras

#### Deploy Automático
```bash
# Hacer cambios en código
git add .
git commit -m "Mejora: descripción del cambio"
git push origin main

# Railway detecta automáticamente y re-deploya
```

#### Variables de Entorno
- Cambiar variables en Railway Dashboard
- No requiere re-deploy, aplica inmediatamente

---

## 🎯 RESULTADO ESPERADO

✅ **URL Pública**: `https://botroyalv2-production.up.railway.app`  
✅ **Interfaz Streamlit**: Funcional con chat, dashboard y métricas  
✅ **Base de Datos**: PostgreSQL persistente en Railway  
✅ **Performance**: Sub-segundo response time para chat  
✅ **Escalabilidad**: Railway escala automáticamente según tráfico  

## 📞 SIGUIENTE PASO

**EJECUTAR AHORA:**
```bash
# Si tienes GitHub CLI instalado:
gh repo create BotRoyalv2 --public
git remote add origin https://github.com/TU_USUARIO/BotRoyalv2.git
git push -u origin main

# Luego ir a Railway.app y conectar el repo
```

**¿Necesitás que te ayude con el nombre de usuario de GitHub o algún paso específico?** 