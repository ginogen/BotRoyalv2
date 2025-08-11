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
    """Obtiene información específica sobre Royal Company según la consulta."""
    
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
    """Rastrea si ya se saludó al cliente hoy para evitar saludos repetidos."""
    today = datetime.now().date()
    
    if client_id in client_greetings:
        last_greeting = client_greetings[client_id]
        if last_greeting == today:
            return False  # Ya saludó hoy
    
    client_greetings[client_id] = today
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
def get_situaciones_frecuentes(situacion: str) -> str:
    """Respuestas para situaciones frecuentes específicas."""
    
    situaciones = {
        "como_funciona": """Dale, te explico. En Royal vendemos productos al por mayor para revendedores y emprendedores, con un mínimo de compra de $40,000.
Si sos revendedor, tenés acceso a precios especiales.
Si querés comprar solo para vos, también tenemos venta minorista sin mínimo de compra.
Enviamos a todo el país y tenemos locales físicos en Córdoba. ¿Querés que te asesore sobre los productos ideales para vos?""",
        
        "arreglos": """Sí, en Royal ofrecemos servicio de arreglos y restauración de joyas en plata 925 y oro 18K.
Algunos de nuestros servicios incluyen:
• Soldaduras
• Ajustes de tamaño (agrandar o achicar anillos)
• Cambio de piedras y pulido
• Restauración de piezas antiguas
• Cambio de mallas y pilas de relojes

Podés enviarnos una foto de tu joya por WhatsApp y te pasamos un presupuesto. También podés traerla a nuestro local en General Paz 159, Galería Planeta, Local 18.
¿Querés que te asesoremos sobre tu joya?""",
        
        "personalizadas": """¡Sí! Tenemos una categoría especial de joyas personalizadas en plata 925.
• Grabados personalizados con nombres, iniciales o símbolos
• Anillos, dijes y pulseras con diseño exclusivo
• Pedidos especiales sin mínimo después de tu primera compra mayorista

¿Te gustaría que te asesoremos sobre qué personalización hacer?""",
        
        "redes_sociales": """Sí, nos encontrás en:
Instagram: @royal.joyas (joyas), @royal.bijou (bijouterie), @royal.indumentaria (indumentaria y accesorios)
Facebook: Royal Company
Seguinos para ver novedades, promociones y consejos para emprendedores. ¡Nos encantaría que formes parte de nuestra comunidad! 🎉"""
    }
    
    return situaciones.get(situacion, "Información no disponible para esta situación.")

def create_royal_agent() -> Agent:
    """Crea y configura el agente de consultas de Royal."""
    
    # Instructions detalladas con personalidad argentina
    instructions = """
    # IDENTIDAD Y PERSONALIDAD
    
    Sos Royalia, el primer punto de contacto de Royal Company. Solo saludá en el PRIMER mensaje del día por cliente, nunca más.
    
    ## Personalidad Argentina
    - Hablá en tono argentino informal y amigable, como con un amigo
    - Evitá ser formal o neutro
    - Usá emojis para remarcar algo importante (sin abusar)
    
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
    
    1. **No saludar repetidamente** - Solo en el primer contacto del día por cliente
    2. **No inventar información** - Si no sabés algo específico, decí: "Uy, eso lo tengo que consultar puntualmente. Te confirmo enseguida y te doy una respuesta completa 👍"
    3. **Evitar respuestas duplicadas** - Si el cliente reformula una pregunta, variar la respuesta, no repetir palabra por palabra
    4. **Ser natural y fluido** - No mencionar que sos un bot, sistema de agentes o tecnología interna
    5. **Redirigir cuando sea necesario** - Pero sin que el cliente perciba la estructura interna del sistema
    6. **Mantener tono argentino** - Informal, cercano, amigable SIEMPRE
    7. **Ofrecer sistema de seña** - Cuando el cliente esté por confirmar un pedido, mencionar el sistema de seña de $10,000
    8. **No ser formal o neutro** - Evitar sonar como un bot corporativo, ser como un amigo local
    
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
            get_situaciones_frecuentes
        ]
    )
    
    return royal_agent

# Crear instancia del agente
royal_consultation_agent = create_royal_agent() 