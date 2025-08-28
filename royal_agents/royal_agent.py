import os
from typing import List, Dict, Any
from agents import Agent, function_tool  # type: ignore
from datetime import datetime, timedelta
import json
import re

# Diccionario para tracking de saludos por cliente
client_greetings = {}

@function_tool
def get_royal_info(query: str) -> str:
    """Obtiene información específica sobre Royal Mayorista según la consulta."""
    
    info_base = {
        "ubicacion": {
            "locales": [
                "Royal Joyas: 9 de Julio 472",
                "Royal Joyas: General Paz 159, Galería Planeta, Local 18", 
                "Royal Bijou: San Martín 48, Galería San Martín, Local 23A"
            ],
            "ciudad": "Córdoba Capital",
            "horarios": "Lunes a viernes: 9:30 a 18:30. Sábados: 9:30 a 14:00"
        },
        "contacto": {
            "instagram_joyas": "@royal.joyas",
            "instagram_bijou": "@royal.bijou", 
            "instagram_indumentaria": "@royal.indumentaria",
            "facebook": "Royal Company",
            "whatsapp": "WhatsApp Oficial disponible",
            "descripcion": "Seguinos para ver novedades, promociones y consejos para emprendedores"
        },
        "productos": {
            "joyas": "Plata 925, oro 18K, joyas personalizadas",
            "relojes": "Casio y otras marcas reconocidas",
            "maquillaje": "Productos de belleza para revendedores",
            "indumentaria": "Ropa y accesorios de moda",
            "servicios": "Arreglos de joyas, grabados personalizados"
        },
        "compras": {
            "mayorista": {
                "minimo": "$40,000",
                "beneficios": "Precios especiales, acceso a productos exclusivos",
                "descuentos": "Hasta 150% de margen de ganancia"
            },
            "minorista": {
                "minimo": "Sin mínimo",
                "publico": "Precios regulares para consumo personal"
            }
        },
        "envios": {
            "cordoba_capital": "$4,999",
            "resto_pais": "$7,499", 
            "gratis": "Pedidos mayores a $80,000",
            "empresa": "Andreani",
            "seguro": "100% asegurado",
            "tiempos": {
                "cordoba": "24 a 48 hs",
                "nacional": "2 a 5 días hábiles"
            }
        },
        "pagos": {
            "metodos": ["Tarjeta (hasta 3 cuotas sin interés)", "Transferencia", "Efectivo en locales"],
            "datos_bancarios": {
                "cbu": "4530000800014232361716",
                "alias": "ROYAL.JOYAS.2023.nx", 
                "titular": "Edward Freitas Souzaneto"
            },
            "seña": "$10,000 (resto al retirar o antes del despacho)"
        }
    }
    
    # Buscar información relevante según la consulta
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["ubicacion", "direccion", "local", "donde"]):
        return json.dumps(info_base["ubicacion"], ensure_ascii=False)
    elif any(word in query_lower for word in ["contacto", "instagram", "facebook", "redes"]):
        return json.dumps(info_base["contacto"], ensure_ascii=False)
    elif any(word in query_lower for word in ["producto", "joya", "reloj", "maquillaje"]):
        return json.dumps(info_base["productos"], ensure_ascii=False)
    elif any(word in query_lower for word in ["compra", "mayorista", "minorista", "precio"]):
        return json.dumps(info_base["compras"], ensure_ascii=False)
    elif any(word in query_lower for word in ["envio", "enviar", "costo", "andreani"]):
        return json.dumps(info_base["envios"], ensure_ascii=False)
    elif any(word in query_lower for word in ["pago", "tarjeta", "transferencia", "cbu"]):
        return json.dumps(info_base["pagos"], ensure_ascii=False)
    else:
        return json.dumps(info_base, ensure_ascii=False)

@function_tool
def track_client_greeting(client_id: str) -> bool:
    """
    Rastrea si ya se saludó al cliente hoy usando contexto persistente.
    También verifica el historial de interacciones para evitar saludos repetidos.
    """
    # Importar aquí para evitar circular imports
    from .conversation_context import context_manager
    
    # Obtener contexto del usuario
    context = context_manager.get_or_create_context(client_id)
    conversation = context.conversation
    
    today = datetime.now().date()
    
    # Verificar si hay interacciones recientes (últimas 2 horas)
    from datetime import timedelta
    recent_cutoff = datetime.now() - timedelta(hours=2)
    
    # Si tiene interacciones recientes, probablemente ya se saludó
    if conversation.interaction_history:
        last_interaction_time = datetime.fromisoformat(conversation.interaction_history[-1]["timestamp"])
        if last_interaction_time > recent_cutoff:
            return False  # Ya hay conversación activa, no saludar
    
    # Verificar saludo del día usando diccionario como backup
    if client_id in client_greetings:
        last_greeting = client_greetings[client_id]
        if last_greeting == today:
            return False  # Ya saludó hoy
    
    # Marcar como saludado
    client_greetings[client_id] = today
    conversation.add_interaction("system", f"Primer saludo del día para {client_id}")
    
    return True  # Primer saludo del día

@function_tool
def get_arreglos_info() -> str:
    """Información detallada sobre servicios de arreglos de joyas."""
    return """
    Servicios de arreglos Royal:
    • Soldaduras de joyas
    • Ajustes de tamaño (agrandar o achicar anillos)
    • Cambio de piedras y pulido
    • Restauración de piezas antiguas
    • Cambio de mallas y pilas de relojes
    
    Proceso:
    1. Envianos una foto por WhatsApp
    2. Te pasamos presupuesto
    3. También podés traerla al local: General Paz 159, Galería Planeta, Local 18
    
    Trabajamos con plata 925 y oro 18K.
    """

@function_tool
def get_joyas_personalizadas_info() -> str:
    """Información sobre joyas personalizadas."""
    return """
    ¡Sí! Tenemos una categoría especial de joyas personalizadas en plata 925:
    • Grabados personalizados con nombres, iniciales o símbolos
    • Anillos, dijes y pulseras con diseño exclusivo
    • Pedidos especiales sin mínimo después de tu primera compra mayorista
    • Diseños únicos según tu preferencia
    
    Proceso: Contanos qué querés y te armamos un diseño exclusivo.
    """

@function_tool
def get_royal_education_info() -> str:
    """Información sobre recursos educativos de Royal."""
    return """
    Royal Company - Recursos para Emprendedores:
    • Más de 100 e-books gratuitos
    • Academia Royal para clientes que compran +$80,000 mensual
    • Combos emprendedores para facilitar inicio de negocios
    • Márgenes de ganancia hasta 150%
    • Modelo de preventa para vender sin stock
    • Apoyo continuo para revendedores
    
    Fundada en 2016, operativa desde 2017, especializada en empoderar emprendedores.
    """

@function_tool
def get_combos_emprendedores_info() -> str:
    """Información introductoria rápida sobre Combos Emprendedores. Complementa el archivo de entrenamiento."""
    return """
    🚀 **COMBOS EMPRENDEDORES - Para quien está empezando**
    
    Para quien está empezando, recomendamos nuestros Combos Emprendedores 💼
    
    **¿Qué son los Combos Emprendedores?**
    Tenemos combos exclusivos de cada rubro —joyas, indumentaria, maquillaje, bijouterie, relojes, accesorios y más— para que, según el rubro que quieras trabajar, puedas arrancar sin perder tiempo eligiendo uno por uno.
    
    **¿Por qué son ideales para empezar?**
    Cuando una emprendedora recién empieza, muchas veces no sabe qué elegir. Por eso, con nuestra experiencia armamos estos combos con productos clásicos, de moda, de bajo precio y con alta rotación, que son los más fáciles de vender y recuperar la inversión rápido 📦💰
    
    **Ventajas:**
    • Arranque más simple y rápido
    • Stock listo para salir a vender
    • Productos seleccionados por experiencia
    • Alta rotación y fácil venta
    • Recuperación rápida de inversión
    • Todo pensado para que funcione
    
    **Rubros disponibles:**
    • Joyas (plata 925, acero)
    • Indumentaria y accesorios
    • Maquillaje y belleza
    • Bijouterie
    • Relojes
    • Y más categorías
    
    **🚀 ¡Es el momento perfecto para empezar!** Ya tenés toda la información que necesitás. Los combos se agotan rápido porque son los favoritos de las emprendedoras.
    
    **Hacé clic en este enlace y empezá tu pedido ahora 👉 https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/**
    
    ¿En qué rubro te gustaría arrancar? Te armo una recomendación personalizada en este momento 💎
    """

@function_tool
def get_investment_guidance() -> str:
    """Provides structured data about investment recommendations for entrepreneurs."""
    return """
INVESTMENT_GUIDANCE_DATA:
{
    "minimum_purchase": 40000,
    "recommended_ranges": "40k-150k+ pesos depending on goals",
    "key_benefits": [
        "Variety testing: learn what customers prefer",
        "Quick ROI: recover investment in weeks not months", 
        "Revenue potential: 40k investment can generate 100k+ sales",
        "Market validation: identify best selling products"
    ],
    "business_logic": "More variety = better customer insights = higher sales",
    "next_action": "Choose product category (joyas, maquillaje, ropa, accesorios) for custom kit",
    "tone_guidance": "Be encouraging about business opportunity - vary your expression each time"
}

INSTRUCTION: Express this data with creative variety. Never use repetitive formulas like 'Me encanta que...' or 'Genial que...'. Be naturally argentinian and enthusiastic but unique each time.
"""

@function_tool
def get_sales_support_process() -> str:
    """Provides structured data about Royal's sales support and personalized assistance."""
    return """
SALES_SUPPORT_DATA:
{
    "personalized_mentorship": "custom product selection based on location and profit margins",
    "quick_process": "complete order in 5 minutes",
    "fast_delivery": "2-3 days to receive stock",
    "quick_roi": "start recovering investment in first week",
    "zone_analysis": "products that sell well in customer's area",
    "margin_optimization": "focus on highest profit items",
    "time_saving": "no need to choose individual products",
    "next_step": "choose product category for custom kit: joyas, maquillaje, indumentaria, accesorios"
}

INSTRUCTION: Present this sales mentorship with enthusiasm and action-oriented language. Vary your expression - never use the same opening phrases. Be naturally argentinian and encouraging.
"""

@function_tool
def get_company_info_by_topic(topic: str) -> str:
    """Provides structured company information by topic."""
    
    info_database = {
        "como_funciona": """
COMPANY_INFO_DATA:
{
    "business_model": "wholesale and retail",
    "target_customers": ["revendedores", "emprendedores", "usuarios_finales"],
    "wholesale_minimum": 40000,
    "retail_minimum": 0,
    "wholesale_benefits": "special wholesale prices and exclusive access",
    "retail_benefits": "no minimum purchase required",
    "shipping": "nationwide delivery",
    "physical_locations": "Córdoba stores",
    "next_step": "product advisory consultation"
}

INSTRUCTION: Explain how Royal works naturally and enthusiastically. Vary your expression each time.
""",
        
        "arreglos": """
JEWELRY_REPAIR_DATA:
{
    "services_available": true,
    "materials": ["plata 925", "oro 18K"],
    "services": ["soldaduras", "ajustes de tamaño", "cambio de piedras", "pulido", "restauración de piezas antiguas", "cambio de mallas y pilas de relojes"],
    "process_whatsapp": "send photo for quote",
    "process_physical": "bring to store for assessment",
    "location": "General Paz 159, Galería Planeta, Local 18",
    "next_step": "jewelry assessment consultation"
}

INSTRUCTION: Present jewelry repair services with creative variety. Be helpful and encouraging.
""",
        
        "personalizadas": """
CUSTOM_JEWELRY_DATA:
{
    "available": true,
    "material": "plata 925",
    "customization_types": ["grabados personalizados", "nombres e iniciales", "símbolos", "diseño exclusivo"],
    "products": ["anillos", "dijes", "pulseras"],
    "ordering": "no minimum after first wholesale purchase",
    "next_step": "personalization consultation"
}

INSTRUCTION: Present custom jewelry options with enthusiasm and creative expression. Each time differently.
""",
        
        "redes_sociales": """
SOCIAL_MEDIA_DATA:
{
    "instagram_accounts": {
        "@royal.joyas": "jewelry",
        "@royal.bijou": "bijouterie", 
        "@royal.indumentaria": "clothing and accessories"
    },
    "facebook": "Royal Company",
    "content_types": ["novedades", "promociones", "consejos para emprendedores"],
    "community_benefit": "join entrepreneurial community and get tips"
}

INSTRUCTION: Share social media info enthusiastically and encourage following. Vary your approach each time.
"""
    }
    
    return info_database.get(topic, "ERROR: Information not available for this topic")

def create_royal_agent() -> Agent:
    """Crea y configura el agente de consultas de Royal."""
    
    # Instructions detalladas con personalidad argentina
    instructions = """
    # IDENTIDAD Y PERSONALIDAD
    
    Sos Royalia, el primer punto de contacto de Royal Company. Solo saludá en el PRIMER mensaje del día por cliente, nunca más.
    
    ## Personalidad Argentina - CREATIVIDAD Y VARIACIÓN
    - Hablá en tono argentino informal y amigable, pero VARIÁ tu forma de expresarte
    - NUNCA uses las mismas frases de inicio: "Me encanta que...", "Genial que...", "Qué bueno que..."
    - Sé natural y espontánea: dale, mirá, bárbaro, genial, perfecto, buenísimo
    - Evitá ser formal o neutro (debes vosear, no hablar en "usted")
    - Usá emojis para remarcar algo importante (sin abusar)
    - CADA respuesta debe sonar diferente, aunque la información sea la misma
    
    ## PALABRAS PROHIBIDAS - NUNCA USAR:
    aquí, puedes, quieres, tienes, debes, sería bueno que, ¿Deseas...?, ¿Puedes...?, 
    Estoy aquí para ayudarte, muy bien, está bien, te ayudaré, te recomiendo que, 
    sígueme, haz clic, tú, tu, enviaré, proporciona, contáctame, 
    estaré encantado de ayudarte, espero que tengas un buen día
    
    # INFORMACIÓN CLAVE DE ROYAL
    
    ## ¿Qué es Royal?
    Royal Company, fundada en 2016 y operativa desde 2017, es una empresa mayorista en Argentina 
    que apoya a emprendedores con productos de moda y belleza. Vende joyas, relojes, maquillaje, 
    indumentaria y accesorios a revendedores y emprendedores de todo el país.
    
    ## Ubicación (Córdoba Capital):
    - Royal Joyas: 9 de Julio 472
    - Royal Joyas: General Paz 159, Galería Planeta, Local 18  
    - Royal Bijou: San Martín 48, Galería San Martín, Local 23A
    
    ## Horarios:
    - Lunes a viernes: 9:30 a 18:30
    - Sábados: 9:30 a 14:00
    - Tienda online 24/7
    
    ## Redes Sociales:
    - Instagram: @royal.joyas (joyas), @royal.bijou (bijouterie), @royal.indumentaria (indumentaria)
    - Facebook: Royal Company
    - WhatsApp Oficial disponible
    
    ## Tipos de Compra:
    ### Mayorista (Revendedores):
    - Mínimo: $40,000
    - Precios especiales
    - Margen hasta 150%
    - Acceso a productos exclusivos
    
    ### Minorista:
    - Sin mínimo de compra
    - Para consumo personal
    - Precios regulares
    
    ## Envíos:
    - Andreani (100% asegurado)
    - Córdoba Capital: $4,999
    - Resto del país: $7,499  
    - GRATIS en pedidos +$80,000
    - Tiempos: Córdoba 24-48hs, Nacional 2-5 días
    
    ## Pagos:
    - Tarjeta (hasta 3 cuotas sin interés)
    - Transferencia: CBU 4530000800014232361716, Alias: ROYAL.JOYAS.2023.nx, Titular: Edward Freitas Souzaneto
    - Efectivo en locales
    - Sistema de seña: $10,000 (resto al retirar)
    
    ## Productos:
    - Joyas: Plata 925, oro 18K, joyas personalizadas con grabados
    - Relojes: Casio y otras marcas reconocidas
    - Maquillaje y productos de belleza para revendedores
    - Indumentaria y accesorios de moda
    - Servicios: Arreglos de joyas, grabados personalizados, restauración
    
    ## Recursos Educativos:
    - Más de 100 e-books gratuitos para emprendedores
    - Academia Royal para clientes que compran +$80,000 mensual
    - Combos emprendedores para facilitar inicio de negocios
    - Márgenes de ganancia hasta 150%
    - Modelo de preventa para vender sin stock (reduce riesgos)
    
    # REGLAS DE COMPORTAMIENTO CRÍTICAS
    
    1. **CREATIVIDAD OBLIGATORIA** - NUNCA repitas las mismas frases de inicio o estructura
    2. **USO INTELIGENTE DE TOOLS** - Cuando uses tools, tomá los datos pero expresalos con TUS palabras, de forma diferente cada vez
    3. **No saludar repetidamente** - Solo en el primer contacto del día por cliente
    4. **No inventar información** - Si no sabés algo específico, decí: "Uy, eso lo tengo que consultar puntualmente. Te confirmo enseguida y te doy una respuesta completa 👍"
    5. **VARIACIÓN TOTAL** - Si el cliente reformula una pregunta, variar COMPLETAMENTE la respuesta, no repetir estructura
    6. **Ser natural y fluido** - No mencionar que sos un bot, sistema de agentes o tecnología interna
    7. **Redirigir cuando sea necesario** - Pero sin que el cliente perciba la estructura interna del sistema
    8. **Mantener tono argentino VARIADO** - Informal, cercano, amigable SIEMPRE, pero expresándote diferente cada vez
    9. **Ofrecer sistema de seña** - Cuando el cliente esté por confirmar un pedido, mencionar el sistema de seña de $10,000
    10. **No ser formal o neutro** - Evitar sonar como un bot corporativo, ser como un amigo local
    
    ## Constraints Adicionales:
    - No proporcionar información no relacionada o suposiciones
    - Evitar jerga técnica, usar lenguaje claro y accesible
    - Mantener actitud de ayuda empática siempre
    - En caso de error, disculparse cortésmente y ofrecer información correcta
    - Actuar como un solo punto de contacto (no mencionar múltiples agentes)
    - Nunca inventar información, si no sabés algo, decí: "Uy, eso lo tengo que consultar puntualmente. Te confirmo enseguida y te doy una respuesta completa 👍"
    - NUNCA PERO NUNCA INVENTAR LINKS O DATOS DE CONTACTO, SI NO ESTAN EN LA INFORMACION DE ROYAL, DECIR QUE NO TENEMOS INFORMACION SOBRE ESO
    
    # SITUACIONES FRECUENTES
    
    ## Cliente pregunta cómo funciona Royal:
    "Dale, te explico. En Royal vendemos al por mayor para revendedores con un mínimo de $40,000. 
    Si sos revendedor, tenés precios re copados. Si querés comprar para vos nomás, 
    también tenemos venta minorista sin mínimo. Enviamos a todo el país y tenemos locales acá en Córdoba. 
    ¿Qué te interesa puntualmente?"
    
    ## Arreglos de joyas:
    "¡Posta que sí! Hacemos arreglos y restauración de joyas en plata 925 y oro 18K.
    Soldaduras, ajustes de anillos, cambio de piedras, pulido, restauración de piezas antiguas, 
    cambio de mallas y pilas de relojes. Mandanos una foto por WhatsApp y te paso presupuesto.
    También podés traerla al local de General Paz 159. ¿Qué necesitás arreglar?"
    
    ## Joyas personalizadas:
    "¡Genial! Tenemos joyas personalizadas en plata 925. Grabados con nombres, iniciales, símbolos.
    Anillos, dijes y pulseras exclusivas. Sin mínimo después de tu primera compra mayorista.
    ¿Tenés algún diseño en mente o querés que te asesoremos?"
    
    Si no sabés algo específico, respondé: "Uy, eso lo tengo que consultar puntualmente. 
    Te confirmo enseguida y te doy una respuesta completa 👍"
    """
    
    # Crear el agente
    royal_agent = Agent(
        name="Royalia - Agente Royal",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[
            get_royal_info,
            track_client_greeting,
            get_arreglos_info,
            get_joyas_personalizadas_info,
            get_royal_education_info,
            get_combos_emprendedores_info,
            get_investment_guidance,
            get_sales_support_process,
            get_company_info_by_topic
        ]
    )
    
    return royal_agent

# Crear instancia del agente
royal_consultation_agent = create_royal_agent() 