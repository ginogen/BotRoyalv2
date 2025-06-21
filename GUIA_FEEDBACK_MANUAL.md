# 🔧 **GUÍA: APLICACIÓN MANUAL DE FEEDBACKS**

## 📋 **Workflow Semanal: Feedback → Mejoras**

### **🗓️ Lunes: Análisis de Feedback**

#### **1. Ejecutar Script de Análisis**
```python
# Crear script: weekly_analysis.py
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def analyze_weekly_feedback():
    conn = sqlite3.connect('bot_feedback.db')
    
    # Feedback de los últimos 7 días
    query = """
    SELECT rating, category, feedback_text, message, timestamp
    FROM conversations 
    WHERE timestamp > datetime('now', '-7 days')
    AND rating IS NOT NULL
    ORDER BY rating ASC, timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Análisis por categoría
    issues = df.groupby('category').agg({
        'rating': ['count', 'mean'],
        'feedback_text': 'first'
    }).round(2)
    
    print("🚨 ISSUES PRIORITARIOS (Rating ≤ 3):")
    critical = issues[issues[('rating', 'mean')] <= 3]
    for category, data in critical.iterrows():
        print(f"\n📌 {category}")
        print(f"   Casos: {data[('rating', 'count')]}")
        print(f"   Rating: {data[('rating', 'mean')]}/5")
        print(f"   Ejemplo: {data[('feedback_text', 'first')][:100]}...")
    
    conn.close()
    return critical

# Ejecutar cada lunes
if __name__ == "__main__":
    analyze_weekly_feedback()
```

#### **2. Priorizar Issues**
```python
# Matriz de priorización
PRIORITY_MATRIX = {
    (5, 1): "🚨 CRÍTICO",      # Frecuencia alta, rating muy bajo
    (3, 1): "🔥 ALTO",         # Frecuencia media, rating muy bajo  
    (5, 2): "⚡ MEDIO",        # Frecuencia alta, rating bajo
    (1, 1): "📋 BAJO"          # Frecuencia baja, rating muy bajo
}

def prioritize_issues(issues_df):
    for category, data in issues_df.iterrows():
        freq = min(5, data[('rating', 'count')])  # Máximo 5
        rating = int(data[('rating', 'mean')])
        priority = PRIORITY_MATRIX.get((freq, rating), "📋 REVISAR")
        print(f"{priority}: {category}")
```

---

### **🛠️ Martes-Miércoles: Identificación y Aplicación de Fixes**

#### **Mapeo: Feedback → Archivo → Fix**

##### **1. "Información Incorrecta"**
```python
# Archivo: Entrenamiento/Entrenamiento-Productos.txt
# Fix: Actualizar datos específicos

# ANTES:
"Los envíos tardan 3-5 días hábiles"

# DESPUÉS (si feedback dice que tardan más):
"Los envíos tardan 5-7 días hábiles via OCA/Andreani"

# Código en royal_agents/training_parser.py - línea ~50
# Verificar que parse correctamente el nuevo texto
```

##### **2. "No Encuentra Productos"**
```python
# Archivo: royal_agents/woocommerce_mcp_tools.py
# Fix: Mejorar parámetros de búsqueda

# ANTES (línea ~120):
def search_products(query, limit=10):
    params = {'search': query, 'per_page': limit}

# DESPUÉS:
def search_products(query, limit=10):
    params = {
        'search': query, 
        'per_page': limit,
        'status': 'publish',
        'stock_status': 'instock'  # Solo productos disponibles
    }
    
    # Búsqueda fuzzy adicional si no hay resultados
    if not results:
        fuzzy_params = {
            'search': query.replace(' ', '%'),  # Búsqueda parcial
            'per_page': limit
        }
        results = make_request('products', fuzzy_params)
```

##### **3. "Tono Inadecuado"**
```python
# Archivo: royal_agents/royal_agent_contextual.py
# Fix: Ajustar system prompt (línea ~80)

# ANTES:
"Sos entusiasta y energético"

# DESPUÉS (si feedback dice "muy agresivo"):
"Sos entusiasta pero relajado, nunca presiones al cliente"

# O si dice "muy informal":
"Usás un tono profesional pero amigable, argentino pero no coloquial"
```

##### **4. "Escala Demasiado Rápido"**
```python
# Archivo: royal_agents/contextual_tools.py
# Fix: Ajustar thresholds (línea ~45)

# ANTES:
if len(frustration_found) >= 1:
    frustration_level = 2

# DESPUÉS:
if len(frustration_found) >= 2:  # Más tolerante
    frustration_level = 2

# O ajustar palabras de frustración:
frustration_indicators = [
    'no funciona', 'terrible',  # Mantener críticas
    # 'confundido', 'perdido'   # Remover palabras suaves
]
```

##### **5. "Respuestas Confusas"**
```python
# Archivo: royal_agents/contextual_tools.py
# Fix: Mejorar lógica de herramientas

# ANTES:
def get_product_info_with_context():
    if not products:
        return "No encontré productos"

# DESPUÉS:
def get_product_info_with_context():
    if not products:
        # Activar HITL en lugar de dar respuesta negativa
        handle_missing_information_hitl("product", product_name)
        return "Dame un momento que chequeo opciones similares 👍"
```

---

### **🧪 Jueves: Testing de Cambios**

#### **Script de Testing Dirigido**
```python
# Crear: test_fixes.py
def test_specific_fix(issue_category, test_messages):
    """Testa un fix específico con mensajes que causaron el problema"""
    
    from royal_agents import run_contextual_conversation_sync
    
    print(f"\n🧪 Testing fix para: {issue_category}")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"Input: {message}")
        
        response = run_contextual_conversation_sync("test_user", message)
        print(f"Output: {response[:200]}...")
        
        # Evaluación manual
        rating = input("Rating 1-5: ")
        if int(rating) >= 4:
            print("✅ Fix exitoso")
        else:
            print("❌ Fix necesita ajustes")

# Ejemplos de uso:
test_specific_fix("No encuentra productos", [
    "¿tenés anillos de plata?",
    "busco cadenas doradas",
    "hay relojes casio?"
])

test_specific_fix("Tono inadecuado", [
    "no me convence este producto",
    "creo que es muy caro",
    "no sé si me sirve"
])
```

---

### **🚀 Viernes: Deploy y Monitoreo**

#### **1. Deploy de Cambios**
```bash
# Testing local final
streamlit run bot_testing_app.py --server.port 8501

# Test con algunos mensajes reales del feedback
# Si todo OK, deploy:

# Opción A: Railway
python deploy.py  # Seleccionar opción 1

# Opción B: Commit y push para auto-deploy
git add .
git commit -m "Fix: [descripción del problema resuelto]"
git push origin main
```

#### **2. Monitoreo Post-Deploy**
```python
# Script: monitor_post_deploy.py
def monitor_improvement():
    """Monitorea si el fix mejoró las métricas"""
    
    # Comparar métricas pre/post deploy
    pre_deploy = get_metrics_before_date(deploy_date)
    post_deploy = get_metrics_after_date(deploy_date)
    
    print("📊 COMPARACIÓN PRE/POST DEPLOY:")
    print(f"Rating promedio: {pre_deploy['avg']} → {post_deploy['avg']}")
    print(f"Issues críticos: {pre_deploy['critical']} → {post_deploy['critical']}")
    
    if post_deploy['avg'] > pre_deploy['avg']:
        print("✅ Mejora detectada")
    else:
        print("⚠️ Revisar: no hay mejora aparente")
```

---

### **📊 Métricas de Éxito**

#### **KPIs por Fix**
```python
SUCCESS_METRICS = {
    "Información incorrecta": {
        "target": "0% feedback 'Incorrecta'",
        "measure": "category == 'Incorrecta'"
    },
    
    "No encuentra productos": {
        "target": "Reducir 50% casos",
        "measure": "'no encuentra' in feedback_text"
    },
    
    "Tono inadecuado": {
        "target": "Rating promedio > 4.0",
        "measure": "avg(rating) where category == 'Tono inadecuado'"
    },
    
    "Escala demasiado": {
        "target": "Solo escalar con rating ≤ 2", 
        "measure": "escalation_logs vs conversation_ratings"
    }
}
```

---

### **🔄 Ciclo Continuo**

#### **Cada 2 Semanas: Review General**
1. **Trend analysis** - ¿Mejoran los ratings?
2. **New patterns** - ¿Aparecen nuevos problemas?
3. **Success validation** - ¿Los fixes funcionaron?
4. **Next priorities** - ¿Qué atacar próximamente?

#### **Monthly: Strategic Review**
1. **Overall bot performance** - Comparar con objetivos
2. **Client satisfaction** - Feedback del cliente final  
3. **Feature gaps** - ¿Qué funcionalidades faltan?
4. **Automation opportunities** - ¿Qué se puede automatizar?

---

## 🎯 **Quick Reference: Problema → Solución**

| Feedback | Archivo | Acción Típica |
|----------|---------|---------------|
| "Info incorrecta" | `Entrenamiento/*.txt` | Actualizar datos base |
| "No encuentra X" | `woocommerce_mcp_tools.py` | Mejorar búsqueda |
| "Muy agresivo" | `royal_agent_contextual.py` | Suavizar prompt |
| "Escala mucho" | `contextual_tools.py` | Subir thresholds |
| "Confuso" | `contextual_tools.py` | Activar más HITL |
| "Lento" | `*.py` (general) | Optimizar timeouts |

---

**💡 TIP:** Documenta cada fix en el commit message para trazabilidad:
```bash
git commit -m "Fix: Reduce false escalations for normal questions

- Increase frustration threshold from 1 to 2 indicators
- Remove 'confundido' from escalation triggers  
- Based on feedback: 'Escala por preguntas normales' (5 cases, avg rating 2.2)"
``` 