# Bot Royal v2 - Interfaz de Testing

Bot conversacional inteligente para Royal Mayorista con interfaz de testing para clientes.

## 🚀 Características

- **Bot Pablo**: Asistente de ventas AI con contexto y memoria
- **Sistema HITL**: Escalación automática a soporte humano
- **Interfaz de Testing**: Streamlit app para pruebas de cliente
- **Dashboard de Feedback**: Métricas y análisis en tiempo real
- **Integración WooCommerce**: Productos y órdenes en tiempo real
- **Sistema de Training**: Gestión de documentos y contexto

## 📦 Instalación

### Requisitos Previos
- Python 3.9+
- Variables de entorno configuradas
- Acceso a base de datos PostgreSQL (Railway) o SQLite (local)

### Variables de Entorno Requeridas

```env
# OpenAI
OPENAI_API_KEY=sk-...

# WooCommerce Royal Mayorista
WC_URL=https://royalmayorista.com.ar
WC_CONSUMER_KEY=ck_...
WC_CONSUMER_SECRET=cs_...

# Base de Datos (PostgreSQL - Railway)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# O para SQLite Local
DATABASE_TYPE=sqlite

# Streamlit
STREAMLIT_SERVER_PORT=8501
```

### Instalación Rápida

```bash
# Clonar repositorio
git clone <tu-repo-url>
cd BotRoyalv2

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp config.env.example config.env
# Editar config.env con tus valores

# Ejecutar
streamlit run bot_testing_app.py --server.port 8501
```

## 🏗️ Deploy en Railway

### 1. Conectar Repositorio
1. Ir a [Railway.app](https://railway.app)
2. Crear nuevo proyecto
3. Conectar tu repositorio GitHub

### 2. Configurar Variables
Agregar estas variables en Railway:
```
OPENAI_API_KEY=tu-key
WC_URL=https://royalmayorista.com.ar
WC_CONSUMER_KEY=tu-key
WC_CONSUMER_SECRET=tu-secret
DATABASE_URL=${DATABASE_URL}
PORT=8501
```

### 3. Configurar Servicio
Railway detectará automáticamente:
- `requirements.txt` para dependencias
- `railway.toml` para configuración de build

## 📁 Estructura del Proyecto

```
BotRoyalv2/
├── bot_testing_app.py          # Interfaz principal Streamlit
├── royal_agents/               # Lógica del bot
│   ├── royal_agent_contextual.py
│   ├── contextual_tools.py
│   ├── conversation_context.py
│   └── mcp_tools/
├── database_persistent.py      # Manager de DB
├── requirements.txt            # Dependencias Python
├── railway.toml               # Configuración Railway
└── documentos/                # Documentación completa
```

## 🤖 Uso del Bot

### Interfaz de Testing
- **Chat de Pruebas**: Conversar con Pablo en tiempo real
- **Sistema de Rating**: Calificar respuestas 1-5 estrellas
- **Transparencia**: Ver system prompts y herramientas
- **Dashboard**: Métricas y análisis de feedback

### Características del Bot
- **Contexto Persistente**: Recuerda productos mostrados
- **Detección de Frustración**: Escalación automática HITL
- **Recomendaciones Personalizadas**: Basadas en perfil de usuario
- **Integración WooCommerce**: Datos en tiempo real

## 📊 Dashboard de Métricas

- Distribución de ratings (1-5 estrellas)
- Análisis por categorías de problemas
- Timeline de actividad
- Feedback general estructurado

## 🛠️ Mantenimiento

### Base de Datos
- **PostgreSQL**: Para producción (Railway)
- **SQLite**: Para desarrollo local
- **Auto-migración**: Detecta y cambia automáticamente

### Logs y Monitoreo
- Logs estructurados con niveles
- Tracking de métricas de performance
- Sistema de escalación HITL automático

## 📝 Documentación

- `INSTRUCCIONES_CLIENTE_TESTING.md` - Guía para clientes
- `CONFIGURAR_PERSISTENCIA_DB.md` - Setup de base de datos
- `IMPLEMENTACION_*_COMPLETA.md` - Documentación técnica

## 🚨 Soporte

Para reportar bugs o mejoras:
1. Usar la interfaz de testing
2. Completar formulario de feedback
3. Especificar tipo y prioridad

## 📄 Licencia

Proyecto privado - Royal Mayorista

---

**Desarrollado para Royal Mayorista** - Bot Pablo v2 con interfaz de testing completa 