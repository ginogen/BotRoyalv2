# 🛒 Royal Bot - Integración MCP WooCommerce

Esta implementación agrega capacidades de **Model Context Protocol (MCP)** al agente Royal, permitiendo acceso en tiempo real a productos, stock y pedidos desde WooCommerce.

## 🚀 Características

### ✅ **Información en Tiempo Real**
- 📦 Consulta de productos con precios actualizados
- 📊 Verificación de stock disponible
- 🏷️ Búsqueda por categorías
- 💰 Filtros por rango de precios
- 📋 Estado de pedidos en vivo

### ✅ **Experiencia Mejorada**
- 🎯 Pablo puede dar precios exactos
- 🔍 Búsqueda inteligente de productos
- 📦 Verificación de disponibilidad antes de confirmar
- 💬 Integración transparente (el cliente no percibe la tecnología)

## 📁 Estructura de Archivos

```
royal_agents/
├── woocommerce_mcp_tools.py     # Herramientas MCP para WooCommerce
├── mcp_config.py                # Configuración y validación MCP
├── royal_agent_with_mcp.py      # Agente Royal mejorado con MCP
└── royal_agent.py               # Agente Royal básico (fallback)

test_mcp_royal.py                # Pruebas específicas MCP
config.env.example               # Variables de entorno (actualizado)
```

## ⚙️ Configuración

### 1. **Variables de Entorno**

Agregar al archivo `.env`:

```bash
# WooCommerce MCP Configuration
WOOCOMMERCE_SITE_URL=https://royal-company.com
WOOCOMMERCE_CONSUMER_KEY=ck_your_consumer_key_here
WOOCOMMERCE_CONSUMER_SECRET=cs_your_consumer_secret_here

# MCP Server Configuration
MCP_SERVER_URL=http://localhost:3000
MCP_LOG_LEVEL=info
```

### 2. **Dependencias**

```bash
pip install httpx>=0.25.0
```

### 3. **WooCommerce API**

1. Ir a WooCommerce → Settings → Advanced → REST API
2. Crear nueva API Key con permisos de **lectura**
3. Copiar Consumer Key y Secret al `.env`

## 🔧 Uso

### **Agente Básico con Tools MCP**

```python
from royal_agents.royal_agent_with_mcp import enhanced_royal_agent
from agents import Runner

# El agente detecta automáticamente si MCP está disponible
result = await Runner.run(
    enhanced_royal_agent,
    "¿Qué joyas de plata tenés disponibles?"
)
```

### **Agente con MCP Server Oficial**

```python
from royal_agents.royal_agent_with_mcp import royal_mcp_server_agent
from agents import Runner

# Usa MCP Server oficial (stdio/sse/http)
result = await Runner.run(
    royal_mcp_server_agent,
    "¿Tenés relojes Casio en stock?"
)
```

## 🛠️ Herramientas MCP Disponibles

### 1. **`get_product_info()`**
```python
# Buscar productos por nombre, ID o categoría
await get_product_info(product_name="anillo plata")
await get_product_info(category="joyas")
await get_product_info(product_id="123")
```

### 2. **`check_stock_availability()`**
```python
# Verificar stock de productos específicos
await check_stock_availability(["123", "456", "789"])
```

### 3. **`get_order_status()`**
```python
# Consultar estado de pedidos
await get_order_status(order_id="12345")
await get_order_status(customer_email="cliente@email.com")
```

### 4. **`search_products_by_price_range()`**
```python
# Buscar productos por rango de precios
await search_products_by_price_range(1000, 5000, category="joyas")
```

### 5. **`get_product_categories()`**
```python
# Obtener categorías disponibles
await get_product_categories()
```

## 🧪 Pruebas

### **Pruebas Completas MCP**
```bash
python test_mcp_royal.py
```

### **Chat Interactivo**
```bash
python test_chat.py
```

### **Servidor Webhook**
```bash
python server.py
```

## 📊 Flujo de Trabajo

```mermaid
graph TD
    A[Cliente pregunta por producto] --> B[Pablo recibe consulta]
    B --> C{¿MCP disponible?}
    C -->|Sí| D[Usar get_product_info()]
    C -->|No| E[Usar información estática]
    D --> F[Obtener datos de WooCommerce]
    F --> G[Formatear respuesta argentina]
    E --> G
    G --> H[Responder al cliente]
    H --> I{¿Cliente interesado?}
    I -->|Sí| J[Verificar stock con MCP]
    I -->|No| K[Ofrecer alternativas]
    J --> L[Ofrecer sistema de seña $10,000]
```

## 🔒 Seguridad

- ✅ **API Keys encriptadas** en variables de entorno
- ✅ **Solo permisos de lectura** en WooCommerce
- ✅ **Validación de entrada** en todas las herramientas
- ✅ **Manejo de errores robusto** con fallbacks
- ✅ **No exposición de datos internos** al cliente

## 🚨 Troubleshooting

### **Error: MCP tools no disponibles**
```bash
# Instalar dependencias
pip install httpx

# Verificar variables de entorno
python test_mcp_royal.py
```

### **Error: WooCommerce API**
```bash
# Verificar permisos de API Key
# Verificar URL del sitio
# Verificar conectividad de red
```

### **Error: MCP Server no responde**
```bash
# Verificar que el MCP Server esté corriendo
# Verificar URL en MCP_SERVER_URL
# Verificar logs del servidor
```

## 📈 Beneficios

### **Para el Negocio**
- 🎯 **Información actualizada** siempre
- 📊 **Mejor experiencia del cliente**
- 🔄 **Reducción de consultas manuales**
- 💰 **Aumento en conversiones**

### **Para el Cliente**
- ⚡ **Respuestas instantáneas**
- 📦 **Stock real disponible**
- 💵 **Precios exactos y actualizados**
- 🛒 **Proceso de compra fluido**

### **Para Desarrollo**
- 🔧 **Fácil mantenimiento**
- 📈 **Escalabilidad**
- 🔌 **Integración modular**
- 🧪 **Testing automatizado**

## 🔮 Próximas Mejoras

- [ ] **Integración con inventario** en tiempo real
- [ ] **Notificaciones automáticas** de stock bajo
- [ ] **Recomendaciones inteligentes** basadas en historial
- [ ] **Integración con sistema de pagos**
- [ ] **Analytics de conversaciones**

## 📞 Soporte

Para problemas con la implementación MCP:

1. **Ejecutar pruebas**: `python test_mcp_royal.py`
2. **Verificar logs** del MCP Server
3. **Revisar configuración** de WooCommerce API
4. **Consultar documentación** de OpenAI Agents MCP

---

**¡El agente Royal ahora tiene superpoderes MCP! 🚀** 