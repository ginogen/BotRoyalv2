# 🗄️ **CONFIGURAR PERSISTENCIA DE DATOS**

## ⚠️ **Problema Identificado**

**Con SQLite en deploy, los datos se PIERDEN** en:
- Railway: Cada redeploy/restart
- Streamlit Cloud: Cada 7 días (reinicio automático)
- Heroku: Cada 24h en plan gratuito

## 💡 **Soluciones por Facilidad**

### **🎯 Opción 1: PostgreSQL Gratuita (RECOMENDADA)**

#### **A) Railway + Supabase (Más Fácil)**

1. **Crear DB en Supabase:**
   ```
   1. Ir a https://supabase.com
   2. "New Project" → Nombre: bot-royal-feedback
   3. Copiar Database URL de Settings → Database
   ```

2. **Configurar en Railway:**
   ```bash
   # En Railway dashboard → Variables
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
   ```

3. **Deploy automático:**
   ```bash
   python deploy.py  # Ya configurado para PostgreSQL
   ```

#### **B) Railway + Railway PostgreSQL**

1. **Agregar PostgreSQL:**
   ```bash
   railway add postgresql
   ```

2. **Configurar variables automáticamente:**
   ```bash
   railway variables  # Ver DATABASE_URL generada
   ```

3. **Deploy:**
   ```bash
   railway up
   ```

#### **C) Streamlit Cloud + Supabase**

1. **Configurar en Streamlit Cloud:**
   ```
   Advanced Settings → Secrets:
   DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
   ```

2. **Deploy normal:**
   ```bash
   git push origin main
   ```

---

### **🔄 Opción 2: Backup Automático SQLite**

Si querés mantener SQLite pero con backup automático:

#### **Script de Backup Automático**

```python
# backup_scheduler.py
import schedule
import time
from database_persistent import export_backup
import threading

def backup_job():
    try:
        filename = export_backup()
        print(f"✅ Backup creado: {filename}")
        
        # Opcional: Subir a Google Drive/Dropbox
        # upload_to_cloud(filename)
        
    except Exception as e:
        print(f"❌ Error en backup: {e}")

# Backup cada 6 horas
schedule.every(6).hours.do(backup_job)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

# Ejecutar en background
if __name__ == "__main__":
    backup_thread = threading.Thread(target=run_scheduler, daemon=True)
    backup_thread.start()
```

#### **Integrar en Streamlit**

```python
# En bot_testing_app.py - agregar al inicio
import backup_scheduler  # Inicia backup automático

# En sidebar - agregar botón manual
if st.button("📁 Backup Manual"):
    filename = export_backup()
    st.success(f"✅ Backup creado: {filename}")
    
    # Ofrecer descarga
    with open(filename, 'r') as f:
        st.download_button(
            "⬇️ Descargar Backup", 
            f.read(), 
            filename,
            mime="application/json"
        )
```

---

### **🚀 Opción 3: CSV Export Periódico**

Para máxima simplicidad:

```python
# export_csv.py
import pandas as pd
from database_persistent import get_conversations_data

def export_to_csv():
    data = get_conversations_data()
    df = pd.DataFrame(data)
    
    filename = f"feedback_export_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
    
    return filename

# En la interfaz - botón de export
if st.button("📊 Exportar CSV"):
    filename = export_to_csv()
    df = pd.read_csv(filename)
    
    st.download_button(
        "⬇️ Descargar Feedback CSV",
        df.to_csv(index=False),
        filename,
        mime="text/csv"
    )
```

---

## 🎯 **Configuración Recomendada Paso a Paso**

### **Para Railway (Opción Más Robusta)**

```bash
# 1. Agregar PostgreSQL a Railway
railway add postgresql

# 2. Ver variables generadas
railway variables

# 3. Deploy con DB persistente
railway up

# 4. Verificar conexión
railway logs  # Buscar "✅ PostgreSQL conectado"
```

### **Para Streamlit Cloud (Opción Más Simple)**

```bash
# 1. Crear DB gratuita en Supabase
# https://supabase.com → New Project

# 2. Obtener Database URL
# Settings → Database → Connection String

# 3. Configurar en Streamlit
# App settings → Secrets:
DATABASE_URL = "postgresql://postgres:..."

# 4. Deploy automático
git push origin main
```

### **Para Testing Local**

```bash
# Mantiene SQLite local
streamlit run bot_testing_app.py

# Los datos locales siguen guardándose en bot_feedback.db
```

---

## 📊 **Verificación de Persistencia**

#### **Test de Persistencia**

```python
# test_persistence.py
import time
from database_persistent import save_conversation, get_conversations_data

def test_persistence():
    # Guardar conversación test
    conv_id = save_conversation(
        "test_user", 
        "Test de persistencia",
        "Respuesta test",
        "test_session"
    )
    
    print(f"✅ Guardado: {conv_id}")
    
    # Verificar que se guardó
    data = get_conversations_data()
    found = any(conv['id'] == conv_id for conv in data)
    
    if found:
        print("✅ Test de persistencia: ÉXITO")
    else:
        print("❌ Test de persistencia: FALLO")

if __name__ == "__main__":
    test_persistence()
```

#### **Monitoreo Continuo**

```python
# En bot_testing_app.py - sidebar
with st.sidebar:
    st.header("📊 Estado DB")
    
    data = get_conversations_data()
    st.metric("💬 Total Conversaciones", len(data))
    
    if data:
        latest = max(data, key=lambda x: x['timestamp'])
        st.write(f"🕐 Última: {latest['timestamp']}")
    
    # Indicador de tipo de DB
    from database_persistent import db_manager
    if db_manager.db_type == 'postgresql':
        st.success("🐘 PostgreSQL - Persistente")
    else:
        st.warning("📁 SQLite - Puede perderse")
```

---

## 🚨 **Importante para tu Caso**

**Recomiendo PostgreSQL porque:**

1. **Es gratis** (Supabase/Railway)
2. **Datos 100% seguros** - No se pierden nunca
3. **Escalable** - Soporta múltiples usuarios simultáneos
4. **Profesional** - Industry standard
5. **Fácil setup** - 5 minutos de configuración

**Para empezar rápido:**
```bash
# 1. Crear cuenta en Supabase (2 min)
# 2. Copiar DATABASE_URL (1 min)  
# 3. Configurar en Railway (2 min)
# 4. Deploy (automático)
```

**¿Querés que configure PostgreSQL ahora o preferís empezar con SQLite + backup automático?** 