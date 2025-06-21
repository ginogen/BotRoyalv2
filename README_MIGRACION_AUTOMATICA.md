# 🔄 MIGRACIÓN AUTOMÁTICA DE BASE DE DATOS

## 📋 **Resumen**

Este sistema asegura que la base de datos PostgreSQL tenga el esquema correcto **automáticamente en cada deploy** sin intervención manual.

## 🚀 **Cómo Funciona**

### **1. Proceso de Deploy**
```
Deploy → migrate_database.py → Verificar esquema → Migrar si es necesario → Iniciar app
```

### **2. Archivos Clave**

#### **`migrate_database.py`**
- ✅ Verifica si el esquema de PostgreSQL es correcto
- 🔧 Migra automáticamente si encuentra problemas
- 💾 Respalda datos existentes antes de la migración
- 🔄 Mapea datos del esquema viejo al nuevo

#### **`start_app.py`**
- 🏁 Script de inicio unificado
- 🔄 Ejecuta migración automáticamente
- 🚀 Inicia Streamlit después de la migración
- ⚠️ Maneja errores con fallback a SQLite

#### **`Procfile`**
- 📝 Configurado para usar `start_app.py` como comando principal
- 🔧 Railway ejecuta esto automáticamente en cada deploy

## 🗂️ **Esquema de Tablas**

### **Tabla: `conversations`** (Unificada)
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),  -- ✅ Esta columna era la que faltaba
    feedback_text TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Tabla: `general_feedback`**
```sql
CREATE TABLE general_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendiente',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📦 **Migración de Datos**

### **Datos Preservados**
- ✅ Conversaciones existentes se migran automáticamente
- ✅ Feedback existente se fusiona en la tabla `conversations`
- ✅ Datos de usuario se preservan

### **Mapeo de Campos**
```
conversations (viejo) → conversations (nuevo)
├── id → session_id (como 'migrated_' + id)  
├── user_id → user_id
├── conversation_data → message
├── timestamp → timestamp
└── satisfaction_rating → rating

feedback (viejo) → conversations.rating + feedback_text
├── rating → conversations.rating
├── comment → conversations.feedback_text
└── category → conversations.category
```

## 🛡️ **Seguridad y Rollback**

### **Backup Automático**
- 💾 Se crean tablas `*_backup` antes de la migración
- 🔄 Los datos se migran desde el backup
- 🗑️ Las tablas backup se eliminan después del éxito

### **Manejo de Errores**
- ⚠️ Si la migración falla, la app usa SQLite como fallback
- 📝 Todos los errores se loggean detalladamente
- 🔄 La migración es idempotente (se puede ejecutar múltiples veces)

## 🔧 **Logs y Monitoreo**

### **Durante el Deploy**
Vas a ver logs como estos en Railway:

```
INFO: 🚀 Iniciando proceso de arranque...
INFO: 🔄 Ejecutando migración de base de datos...
INFO: 🔍 Verificando esquema de PostgreSQL...
INFO: ⚠️ Esquema incorrecto - falta columna 'rating'
INFO: 🔧 Iniciando migración de base de datos...
INFO: 💾 Respaldando datos existentes...
INFO: 📊 5 conversaciones encontradas
INFO: 📊 3 feedbacks encontrados
INFO: 🏗️ Creando tablas con esquema correcto...
INFO: ✅ Tablas creadas exitosamente
INFO: 📦 Migrando datos de backup...
INFO: ✅ Datos migrados exitosamente
INFO: 🎉 ¡Migración completada exitosamente!
INFO: 🚀 Iniciando aplicación Streamlit...
INFO: 📡 Iniciando en puerto 8080
```

### **Si Todo Está Correcto**
```
INFO: 🚀 Iniciando proceso de arranque...
INFO: 🔄 Ejecutando migración de base de datos...
INFO: 🔍 Verificando esquema de PostgreSQL...
INFO: ✅ Esquema correcto - columna 'rating' encontrada
INFO: ✅ Base de datos ya está correcta
INFO: 🚀 Iniciando aplicación Streamlit...
```

## 🎯 **Solución al Problema Original**

### **Problema que Tenías:**
```
ERROR: column "rating" does not exist
```

### **Causa:**
- Las tablas existentes no tenían el esquema que esperaba el código
- El código buscaba `conversations.rating` pero la tabla tenía `feedback.rating`

### **Solución Automática:**
1. ✅ **Detecta** el esquema incorrecto automáticamente
2. 🔄 **Migra** los datos preservando toda la información
3. 🏗️ **Crea** las tablas con el esquema correcto
4. 💾 **Fusiona** los datos de `feedback` en `conversations.rating`
5. 🚀 **Inicia** la aplicación sin errores

## 🚀 **Próximo Deploy**

Cuando hagas el próximo deploy a Railway:

1. **Automáticamente** se ejecutará `migrate_database.py`
2. **Se detectará** que el esquema está incorrecto
3. **Se migrarán** todos tus datos existentes
4. **Se crearán** las tablas correctas
5. **La aplicación iniciará** sin el error de `column "rating" does not exist`

## 🔍 **Verificación Post-Deploy**

Después del deploy, puedes verificar que todo funciona:

1. **Chatea con el bot** - las conversaciones se guardarán
2. **Da feedback con estrellas** - se guardará en la columna `rating`
3. **Revisa los logs** - no deberías ver más errores de "column does not exist"
4. **Verifica en la base de datos** - las tablas tendrán el esquema correcto

## 🆘 **Si Algo Sale Mal**

El sistema es **fail-safe**:
- Si PostgreSQL falla → Usa SQLite como fallback
- Si la migración falla → Logs detallados + fallback a SQLite
- Si hay timeout → Continúa con SQLite

La aplicación **siempre funcionará**, incluso si hay problemas con la base de datos.

---

✅ **¡Tu aplicación ahora se auto-repara en cada deploy!** 