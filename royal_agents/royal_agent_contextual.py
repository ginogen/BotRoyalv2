# Royal Agent Contextual para Royal Bot v2
# Agente principal que usa el sistema de contexto de OpenAI Agents

from typing import Dict, List, Any, Optional
from agents import Agent, Runner, RunContextWrapper  # type: ignore
from .conversation_context import RoyalAgentContext
from .conversation_context import context_manager
from .contextual_tools import create_contextual_tools
from .woocommerce_mcp_tools import create_woocommerce_tools
from .training_mcp_tools import create_training_tools
from .royal_agent import (
    get_royal_info, 
    track_client_greeting, 
    get_arreglos_info,
    get_joyas_personalizadas_info, 
    get_royal_education_info,
    get_combos_emprendedores_info,
    get_investment_guidance,
    get_sales_support_process,
    get_company_info_by_topic
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_contextual_royal_agent() -> Agent[RoyalAgentContext]:
    """
    Crea el agente Royal con capacidades de contexto completas.
    Sigue el patrón oficial de OpenAI Agents SDK.
    """
    
    # Instructions base que se complementan con contexto dinámico
    base_instructions = """
    # IDENTIDAD Y PERSONALIDAD
    
    Sos Royalia, el primer punto de contacto de Royal Mayorista.
    
    ## Personalidad Argentina
    - Hablá en tono argentino informal y amigable, pero sin exagerar ya que estas hablando con posibles clientes.
    - Evitá ser formal o neutro (Debes vosear, no hablar en "usted")
    - Usá emojis para remarcar algo importante y que tenga sentido en la respuesta(sin abusar)
    
    ## PALABRAS PROHIBIDAS - NUNCA USAR:
    aquí, puedes, quieres, tienes, debes, sería bueno que, ¿Deseas...?, ¿Puedes...?, 
    Estoy aquí para ayudarte, muy bien, está bien, te ayudaré, te recomiendo que, 
    sígueme, haz clic, tú, tu, enviaré, proporciona, contáctame, 
    estaré encantado de ayudarte, espero que tengas un buen día
    
    ## ALTERNATIVAS AL "CHE" (muy coloquial):
    En vez de "Che" (que suena poco profesional), usá estas alternativas:
    • "Me encanta que…" → Me encanta que estés pensando en invertir…
    • "Qué bueno que…" → Qué bueno que estés evaluando la inversión…
    • "Genial que…" → Genial que ya estés con ganas de dar este paso…
    • "Me alegra que…" → Me alegra que estés considerando arrancar…
    • "Es buenísimo que…" → Es buenísimo que quieras emprender…
    
    REGLA: Mantener tono argentino amigable pero profesional, evitando excesos coloquiales

    # 🚨 PROTOCOLO CRÍTICO DE FRUSTRACIÓN Y HITL 🚨
    
    **REGLA OBLIGATORIA #1: DETECTAR FRUSTRACIÓN AUTOMÁTICAMENTE**
    
    Antes de CUALQUIER respuesta, SIEMPRE usar detect_user_frustration() para evaluar el estado del usuario.
    
    **Si se detecta necesidad de asistencia (nivel 2 o 3):**
    1. **INMEDIATAMENTE dejar de insistir con compras/datos**
    2. **ACTIVAR protocolo HITL**
    3. **NO seguir pidiendo nombre, dirección, método de pago**
    4. **Usar handle_missing_information_hitl() o escalate_to_human_support()**
    5. **Cambiar completamente el enfoque a resolver su consulta**
    

    **NUNCA HACER cuando el usuario está frustrado:**
    - Seguir pidiendo datos de compra
    - Insistir con el mismo producto
    - Seguir ofreciendo combos sin resolver la consulta
    - Actuar como si nada pasó

    **REGLA OBLIGATORIA #2: TRIGGERS AUTOMÁTICOS PARA HERRAMIENTAS**
    
    ### Para consultas de WEB/CATÁLOGO:
    **Palabras:** "web", "página", "website", "catálogo", "catalogo", "ver productos", "tienda online"
    → **ACCIÓN:** SIEMPRE usar get_basic_company_info("catalogo")
    
    ### Para información básica:
    **Palabras:** "mínimo", "minimo", "envío", "envio", "pago", "confiable", "local"
    → **ACCIÓN:** SIEMPRE usar get_basic_company_info() con el tipo correspondiente
    
    ### Para productos específicos con feedback negativo:
    **Si usuario dice "no me gusta" o "no me convence" después de mostrar productos:**
    → **ACCIÓN:** 
    1. USAR detect_user_frustration()
    2. Si detecta necesidad de asistencia → ACTIVAR HITL, NO seguir con compra
    3. PREGUNTAR qué específicamente busca
    4. Ofrecer alternativas diferentes
    
    ### Para emprendedores que recién empiezan:
    **Palabras:** "empezar", "arrancar", "inicio", "primera vez", "no sé qué elegir", "soy nueva"
    → **ACCIÓN:** SIEMPRE usar get_combos_emprendedores_info()
    → **IMPORTANTE:** Esta información es clave para convertir emprendedores nuevos
    
    ### Para consultas sobre presupuesto e inversión:
    **Palabras:** "cuánto invertir", "presupuesto", "cuánto comprar", "cuánto necesito", "cuánto gastar", "cuánto destinar", "primera inversión"
    → **ACCIÓN:** SIEMPRE usar get_investment_guidance()
    → **CRÍTICO:** Esta información convierte dudas en ventas
    
    ### Para acompañamiento y cierre:
    **Palabras:** "me ayudás", "no sé cuál elegir", "qué me recomendás", "qué me conviene", "estoy motivada", "quiero arrancar ya"
    → **ACCIÓN:** Usar get_sales_support_process() cuando detectes interés alto
    → **OBJETIVO:** Convertir motivación en acción inmediata
    
    ### Para despedidas y cierres de conversación:
    **Palabras:** "abrazo", "beso", "gracias abrazo", "chau", "nos vemos", "hasta luego", "saludos", "que tengas buen día"
    → **ACCIÓN:** SIEMPRE usar detect_conversation_closure() para responder profesionalmente
    → **IMPORTANTE:** Reconocer intención de despedida y cerrar con cortesía profesional
    → **NUNCA:** Continuar conversación después del cierre detectado
    
    ### 🚨 IMPORTANTE - Consultas sobre PEDIDOS/ÓRDENES:
    **Palabras:** "mi pedido", "mi orden", "estado de mi", "dónde está mi", "cuándo llega mi", "seguimiento"
    → **ACCIÓN:** NO usar herramientas del bot - El sistema automáticamente DERIVA estas consultas al equipo de seguimiento
    → **NUNCA:** Intentar consultar estado de pedidos con herramientas
    → **IMPORTANTE:** Estas consultas se detectan automáticamente y se asignan al equipo correspondiente

    # 🧠 CAPACIDADES DE MEMORIA Y CONTEXTO
    
    **IMPORTANTE: Tenés MEMORIA de toda la conversación.**
    
    - Recordás todos los productos que mostraste
    - Sabés si el usuario es emprendedor y su nivel de experiencia
    - Podés interpretar referencias como "el primero", "el segundo", "el de plata"
    - Mantenés el contexto de la conversación para dar respuestas personalizadas

    # 🚨 PROTOCOLO HITL (HUMAN IN THE LOOP) - REGLA CRÍTICA 🚨
    
    **NUNCA JAMÁS uses frases como:**
    - "No tengo esa información"
    - "No sé sobre eso"
    - "No tengo acceso a eso"
    - "Parece que no puedo ayudarte con eso"
    - "Esa información no está disponible"
    - "Lamentablemente no tengo información"
    - "Lamentablemente no..."
    - "Disculpá, no tengo..."
    - "Lo siento, no..."
    - Cualquier frase que empiece con "Lamentablemente", "Disculpá", "Lo siento"
    
    **EN SU LUGAR, SIEMPRE usa frases como:**
    - "Dale, dejame que chequeo eso puntualmente y te confirmo ahora"
    - "Tengo que verificar eso con el equipo. Dame un toque"
    - "Eso lo tengo que consultar específicamente. En un ratito te confirmo"
    - "Los datos me los están actualizando. Ya te traigo la info completa"
    
    ## 🔧 HERRAMIENTAS HITL DISPONIBLES:
    
    ### Para detectar problemas:
    - `detect_user_frustration()` → **USAR EN CADA RESPUESTA** para detectar si el usuario está enojado/frustrado
    - `check_mcp_connectivity_and_fallback()` → Verifica sistemas y activa HITL si hay problemas
    
    ### Para manejar información faltante:
    - `handle_missing_information_hitl()` → Genera respuestas profesionales cuando falta info
    
    ## 🚨 REGLA CRÍTICA PARA PRODUCTOS NO ENCONTRADOS:
    
    **Cuando el usuario pregunte por un producto que no encontrás (ej: esmaltes, perfumes, etc):**
    
    1. **NUNCA digas que no tenés información**
    2. **SIEMPRE intentá buscar con `get_product_info()` primero**
    3. **Si no encontrás resultados, INMEDIATAMENTE usá `handle_missing_information_hitl()`**
    4. **NUNCA inventes información o productos**
    
    **Ejemplo correcto:**
    Usuario: "Tienen esmaltes?"
    1. Usar `get_product_info(product_name="esmalte")`
    2. Si no hay resultados, usar `handle_missing_information_hitl(information_type="product", context_description="usuario pregunta por esmaltes")`
    3. Responder con el mensaje natural que devuelve HITL
    - `escalate_to_human_support()` → Escala a soporte humano cuando es necesario
    
    **PROTOCOLO AUTOMÁTICO:**
    1. **SIEMPRE** empezar con detect_user_frustration() 
    2. Si detectás necesidad de asistencia → **CAMBIAR ENFOQUE**, usar HITL, NO insistir con compra
    3. Si no tenés información → Usar respuestas HITL naturales
    4. Si hay problemas técnicos → Actuar como que verificás en tiempo real
    5. Si es muy complejo → Escalar con escalate_to_human_support()

    ## 🔧 HERRAMIENTAS DE CONTEXTO DISPONIBLES:
    
    ### Para acceder al contexto:
    - `get_context_summary()` → Ver resumen completo del contexto actual
    - `update_user_profile()` → Guardar información del usuario
    - `get_recommendations_with_context()` → Recomendaciones personalizadas
    
    ### Para productos con memoria:
    - `get_product_info_with_context()` → Buscar productos Y guardarlos en memoria
    - `get_combos_with_context()` → Obtener combos Y guardarlos para referencias ("combo 1", "el segundo")
    - `process_purchase_intent()` → Procesar intención de compra con contexto
    
    ### Para limpiar:
    - `clear_conversation_context()` → Reiniciar conversación
    
    # ⚠️ REGLAS CRÍTICAS CON CONTEXTO Y HITL
    
    ## 1. PROTOCOLO PARA EMPRENDEDORES:
    
    **SI detectás que el usuario es emprendedor (por contexto o menciona emprender):**
    
    1. **USAR get_context_summary()** para ver su perfil actual
    2. **APLICAR protocolo según su experiencia:**
       - **Empezando/Primera vez**: USAR get_combos_emprendedores_info() inmediatamente
       - **Experimentado**: productos específicos + diversificación
    3. **GUARDAR información con update_user_profile()**
    4. **REGLA CRÍTICA:** Si mencionan "no sé qué elegir" o "empezar" → combos emprendedores OBLIGATORIO
    5. **REGLA CRÍTICA:** Si preguntan por dinero/presupuesto → get_investment_guidance() OBLIGATORIO
    6. **REGLA DE CONVERSIÓN:** SIEMPRE incluir CTAs claras cuando muestres productos o combos
    7. **REGLA ANTI-OBJECIÓN:** Romper objeciones de precio explicando ROI y rentabilidad
    8. **REGLA DE URGENCIA:** Mencionar que combos se agotan o son limitados (sin mentir)
    
    ## 2. PROTOCOLO PARA PRODUCTOS ESPECÍFICOS:
    
    **CUANDO el usuario pregunta por productos:**
    
    1. **USAR get_context_summary()** para ver productos previos
    2. **Si pregunta por COMBOS** → usar get_combos_with_context() (guarda automáticamente para referencias)
    3. **Si es consulta vaga** → hacer preguntas específicas ANTES de buscar
    4. **Si es consulta específica** → usar get_product_info_with_context()
    5. **SIEMPRE guardar productos en contexto** para referencias futuras
    6. **Si hay errores MCP** → Las herramientas automáticamente activan HITL
    
    ## 3. PROTOCOLO PARA INTENCIONES DE COMPRA:
    
    **CUANDO el usuario dice "quiero el segundo", "me interesa el vintage", etc.:**
    
    1. **USAR detect_user_frustration() PRIMERO** → Si está frustrado, NO proceder con compra
    2. **Si NO está frustrado** → USAR process_purchase_intent() 
    3. **Interpretar la referencia** usando el contexto de productos mostrados
    4. **Proceder con datos de compra** solo si el usuario está contento
    
    ## 4. PROTOCOLO PARA FRUSTRACIÓN/PROBLEMAS:
    
    **SI el usuario está frustrado, enojado o hay problemas técnicos:**
    
    1. **DETECTAR automáticamente** con `detect_user_frustration()`
    2. **NUNCA decir "no tengo acceso" o "no sé"**
    3. **NUNCA insistir con datos de compra si necesita asistencia**
    4. **SIEMPRE usar frases HITL** como "dame un momento que chequeo eso"
    5. **ESCALAR si es necesario** con `escalate_to_human_support()`
    6. **CAMBIAR completamente el enfoque** a resolver su consulta

    ## 5. PROTOCOLO PARA WEB/CATÁLOGO:
    
    **CUANDO el usuario pregunta por "web", "página", "catálogo", "tienda online":**
    
    1. **SIEMPRE usar get_basic_company_info("catalogo")**
    2. **NUNCA inventar links**
    3. **Usar SOLO el link oficial:** https://royalmayorista.com.ar/
    4. **Explicar qué van a encontrar en la web**
    
    # INFORMACIÓN CLAVE DE ROYAL
    
    ## ¿Qué es Royal?
    Royal Company, fundada en 2016 y operativa desde 2017, es una empresa mayorista en Argentina 
    que apoya a emprendedores con productos de moda y belleza.
    
    ## Ubicación (Córdoba Capital):
    - Royal Joyas: 9 de Julio 472
    - Royal Joyas: General Paz 159, Galería Planeta, Local 18  
    - Royal Bijou: San Martín 48, Galería San Martín, Local 23A
    
    ## Tipos de Compra:
    ### Mayorista (Revendedores):
    - Mínimo: $40,000
    - Precios especiales, margen hasta 150%
    
    ### Minorista:
    - Sin mínimo de compra, precios regulares
    
    ## Envíos:
    - Andreani (100% asegurado)
    - Córdoba Capital: $4,999, Resto del país: $7,499  
    - GRATIS en pedidos +$80,000
    
    ## Pagos:
    - Tarjeta (hasta 1 cuota sin interés)
    - Transferencia: CBU 4530000800014232361716, Alias: ROYAL.JOYAS.2023.nx, Titular: Edward Freitas Souzaneto
    - Efectivo en locales, Sistema de seña: $10,000
    
    # 🎯 EJEMPLOS DE USO DEL CONTEXTO Y HITL:
    
    **Ejemplo 1 - Usuario emprendedor:**
    ```
    Usuario: "Quiero empezar a vender"
    
    1. Usar detect_user_frustration() → confirmar que está bien
    2. Usar get_context_summary() → ver si ya sabemos algo
    3. Usar update_user_profile("experience_level", "empezando")
    4. Hacer preguntas según protocolo emprendedor
    5. Usar get_recommendations_with_context() para sugerir combos
    ```
    
    **Ejemplo 2 - Referencia a producto:**
    ```
    Usuario: "Quiero el segundo reloj"
    
    1. Usar detect_user_frustration() → verificar estado de ánimo
    2. Si está bien → usar process_purchase_intent("quiero el segundo reloj")
    3. El sistema automáticamente encuentra el producto del contexto
    4. Proceder con proceso de compra
    ```
    
    **Ejemplo 3 - Usuario frustrado:**
    ```
    Usuario: "Esto no me gusta, son un desastre"
    
    1. detect_user_frustration() detecta necesidad de asistencia nivel 3
    2. **INMEDIATAMENTE cambiar enfoque**
    3. **NO insistir con datos de compra**
    4. Responder: "Perdón que no te convencieron. ¿Qué específicamente estás buscando?"
    5. Escalar si es necesario
    ```
    
    **Ejemplo 4 - Pregunta por web:**
    ```
    Usuario: "¿Tienen página web para ver el catálogo?"
    
    1. **SIEMPRE usar get_basic_company_info("catalogo")**
    2. Responder con link oficial: https://royalmayorista.com.ar/
    3. **NUNCA inventar links**
    ```
    
    **Ejemplo 5 - Pregunta por presupuesto:**
    ```
    Usuario: "¿Cuánto necesito invertir para empezar?"
    
    1. **SIEMPRE usar get_investment_guidance()**
    2. La herramienta da información específica sobre montos ($40,000-$150,000)
    3. **NUNCA inventar montos o rangos** - usar solo la información de la herramienta
    4. Continuar la conversación preguntando por el rubro de interés
    ```
    
    # REGLAS DE COMPORTAMIENTO CRÍTICAS
    
    1. **SIEMPRE detectar necesidad de asistencia PRIMERO** antes de cualquier acción
    2. **NUNCA inventar información** - usar datos reales del contexto
    3. **INTERPRETAR referencias** usando el contexto de productos mostrados
    4. **PERSONALIZAR respuestas** según el perfil del usuario en contexto
    5. **MANTENER tono argentino** - informal, cercano, amigable SIEMPRE
    6. **PROTOCOLO HITL OBLIGATORIO** - nunca decir "no tengo información"
    7. **CAMBIAR ENFOQUE si detecta necesidad de asistencia** - NO insistir con compra
    8. **USAR LINKS REALES** - solo https://royalmayorista.com.ar/ para catálogo
    
    **REGLA DE ORO**: El contexto es tu memoria, HITL es tu salvavidas, y la detección de asistencia es tu brújula. Cuando detectes que el usuario necesita asistencia, CAMBIÁ completamente el enfoque para resolver su consulta, no para vender.
    """
    
    # Preparar todas las herramientas
    base_tools = [
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
    
    # Agregar herramientas contextuales (OBLIGATORIAS)
    contextual_tools = create_contextual_tools()
    all_tools = base_tools + contextual_tools
    
    # Agregar herramientas MCP si están disponibles
    try:
        woocommerce_tools = create_woocommerce_tools()
        all_tools.extend(woocommerce_tools)
        logger.info("✅ WooCommerce tools agregadas")
    except Exception as e:
        logger.warning(f"⚠️ WooCommerce tools no disponibles: {e}")
    
    try:
        training_tools = create_training_tools()
        all_tools.extend(training_tools)
        logger.info("✅ Training tools agregadas")
    except Exception as e:
        logger.warning(f"⚠️ Training tools no disponibles: {e}")
    
    # Crear el agente con tipo de contexto específico
    # Suprimiendo errores de tipo ya que la API funciona correctamente en runtime
    royal_agent = Agent[RoyalAgentContext](  # type: ignore
        name="Royalia - Royal Contextual",
        instructions=base_instructions,
        model="gpt-4o-mini",
        tools=all_tools  # type: ignore
    )
    
    logger.info(f"✅ Agente Royal Contextual creado con {len(all_tools)} herramientas")
    return royal_agent

def get_dynamic_instructions(context: RoyalAgentContext) -> str:
    """
    Genera instrucciones dinámicas basadas en el contexto actual.
    Esto se puede agregar al input de Runner.run()
    """
    
    enhanced_instructions = context.get_enhanced_instructions()
    
    if enhanced_instructions:
        return f"""
CONTEXTO DINÁMICO PARA ESTA CONVERSACIÓN:

{enhanced_instructions}

---
RESPONDE al usuario considerando este contexto específico.
"""
    
    return ""

async def run_contextual_conversation(user_id: str, user_message: str) -> str:
    """
    Ejecuta una conversación usando el agente contextual.
    Esta función maneja todo el flujo de contexto automáticamente.
    """
    
    logger.info(f"🗣️ CONVERSACIÓN CONTEXTUAL iniciada para: {user_id}")
    logger.info(f"   Mensaje: {user_message}")
    
    try:
        # Obtener o crear contexto
        context = context_manager.get_or_create_context(user_id)
        
        # Usuario interaction tracking
        logger.info(f"📝 Usuario {user_id} iniciando conversación contextual")
        
        # Registrar mensaje del usuario
        context.conversation.add_interaction("user", user_message)
        
        # Generar instrucciones dinámicas
        dynamic_instructions = get_dynamic_instructions(context)
        
        # Preparar input completo
        full_input = user_message
        if dynamic_instructions:
            full_input = dynamic_instructions + "\n\nUsuario dice: " + user_message
        
        # Crear agente
        agent = create_contextual_royal_agent()
        
        # Ejecutar conversación con contexto
        result = await Runner.run(
            starting_agent=agent,
            input=full_input,
            context=context
        )
        
        # Registrar respuesta
        context.conversation.add_interaction("assistant", result.final_output)
        
        # Update user context profile
        logger.info(f"📊 Contexto actualizado para usuario: {user_id}")
        
        logger.info(f"✅ Conversación completada para: {user_id}")
        logger.info(f"   Respuesta length: {len(result.final_output)}")
        
        return result.final_output
        
    except Exception as e:
        logger.error(f"❌ Error en conversación contextual: {str(e)}")
        return f"Hubo un problema procesando tu mensaje. Por favor, intenta de nuevo."

# Función de conveniencia para usar sincrónicamente
def run_contextual_conversation_sync(user_id: str, user_message: str) -> str:
    """Versión sincrónica de run_contextual_conversation usando thread pool"""
    
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor
    
    try:
        # Obtener contexto
        context = context_manager.get_or_create_context(user_id)
        
        # Usuario interaction tracking
        logger.info(f"📝 Usuario {user_id} iniciando conversación contextual sync")
        
        # Registrar mensaje
        context.conversation.add_interaction("user", user_message)
        
        # Instrucciones dinámicas
        dynamic_instructions = get_dynamic_instructions(context)
        
        # Input completo
        full_input = user_message
        if dynamic_instructions:
            full_input = dynamic_instructions + "\n\nUsuario dice: " + user_message
        
        # Crear agente
        agent = create_contextual_royal_agent()
        
        # Función para ejecutar en un nuevo event loop
        def run_in_new_loop():
            try:
                # Crear un nuevo event loop para este thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Ejecutar la conversación asíncrona
                async def async_conversation():
                    result = await Runner.run(
                        starting_agent=agent,
                        input=full_input,
                        context=context
                    )
                    return result.final_output
                
                return loop.run_until_complete(async_conversation())
            finally:
                loop.close()
        
        # Ejecutar en thread pool para evitar bloquear
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            result = future.result(timeout=30)  # 30 segundos timeout
        
        # Registrar respuesta
        context.conversation.add_interaction("assistant", result)
        
        # Update user context profile
        logger.info(f"📊 Contexto actualizado para usuario: {user_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en conversación contextual sync: {str(e)}")
        return f"Hubo un problema procesando tu mensaje. Por favor, intenta de nuevo."

# Instancia global del agente
contextual_royal_agent = create_contextual_royal_agent()

# Función helper para limpiar contextos antiguos
def cleanup_old_contexts():
    """Limpia contextos antiguos (llamar periódicamente)"""
    context_manager.cleanup_old_contexts(hours=24)
    logger.info("🧹 Limpieza de contextos antiguos completada")

# Funciones auxiliares para extraer información del contexto para el sistema de seguimiento
def _extract_user_type_from_context(context: RoyalAgentContext) -> str:
    """Extrae el tipo de usuario basado en el contexto de la conversación"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Palabras clave para identificar tipo de usuario
        if any(word in conversation_text for word in ["emprender", "emprendedor", "emprendedora", "arrancar", "empezar"]):
            return "emprendedor"
        elif any(word in conversation_text for word in ["revender", "revendedor", "revendedora", "vender", "negocio"]):
            return "revendedor"
        elif any(word in conversation_text for word in ["comprar para mi", "para uso personal", "para mí"]):
            return "minorista"
        else:
            return "potencial_emprendedor"  # Default
            
    except Exception as e:
        logger.error(f"❌ Error extrayendo tipo de usuario: {e}")
        return "desconocido"

def _extract_interest_from_context(context: RoyalAgentContext) -> str:
    """Extrae el interés principal del usuario basado en la conversación"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Contar menciones por categoría
        interests = {
            "joyas": ["joya", "anillo", "aros", "pulsera", "dije", "plata", "oro"],
            "maquillaje": ["maquillaje", "labial", "base", "sombra", "cosmetic", "belleza"],
            "indumentaria": ["ropa", "remera", "jean", "vestido", "indumentaria", "fashion"],
            "relojes": ["reloj", "casio", "hora"],
            "accesorios": ["accesorio", "bolso", "cartera", "bijouterie"]
        }
        
        # Contar menciones
        interest_scores = {}
        for category, keywords in interests.items():
            score = sum(1 for keyword in keywords if keyword in conversation_text)
            if score > 0:
                interest_scores[category] = score
        
        # Retornar el interés con más menciones
        if interest_scores:
            return max(interest_scores, key=interest_scores.get)
        else:
            return "general"
            
    except Exception as e:
        logger.error(f"❌ Error extrayendo interés: {e}")
        return "general"

def _extract_experience_level_from_context(context: RoyalAgentContext) -> str:
    """Extrae el nivel de experiencia del usuario"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Palabras clave para novatos
        beginner_keywords = ["empezar", "arrancar", "primera vez", "no sé", "nuevo", "nueva", "nunca", "como empiezo"]
        # Palabras clave para experimentados
        experienced_keywords = ["ya vendo", "experiencia", "hace tiempo", "conozco", "ya trabajo", "mi negocio"]
        
        beginner_score = sum(1 for keyword in beginner_keywords if keyword in conversation_text)
        experienced_score = sum(1 for keyword in experienced_keywords if keyword in conversation_text)
        
        if beginner_score > experienced_score:
            return "empezando"
        elif experienced_score > beginner_score:
            return "experimentado"
        else:
            return "intermedio"
            
    except Exception as e:
        logger.error(f"❌ Error extrayendo nivel de experiencia: {e}")
        return "desconocido"

# NUEVAS FUNCIONES DE EXTRACCIÓN AVANZADA
def _extract_specific_products_from_context(context: RoyalAgentContext) -> List[str]:
    """Extrae productos específicos mencionados en la conversación"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Productos específicos con patrones de reconocimiento
        specific_products = {
            # Joyas
            "anillos de plata 925": ["anillo de plata", "anillos plata 925", "anillos de plata"],
            "aros con cristales": ["aros cristal", "aros con cristal", "aros cristales"],
            "pulseras ajustables": ["pulsera ajustable", "pulseras que se ajustan"],
            "dijes personalizados": ["dije personalizado", "dijes con nombre"],
            "conjuntos de aros": ["conjunto de aros", "set de aros"],
            
            # Maquillaje
            "labiales de larga duración": ["labial larga duración", "labiales que duran"],
            "bases líquidas": ["base líquida", "bases fluidas"],
            "paletas de sombras": ["paleta de sombras", "paleta sombra"],
            "kits de maquillaje": ["kit maquillaje", "set de maquillaje"],
            
            # Indumentaria
            "remeras oversized": ["remera oversize", "remeras grandes"],
            "jeans de moda": ["jean de moda", "jeans trendy"],
            "vestidos casuales": ["vestido casual", "vestidos cómodos"],
            
            # Combos
            "combo emprendedor": ["combo emprendedora", "combo para emprender"],
            "combo joyas trendy": ["combo joya", "combo de joyas"],
            "combo todo en uno": ["combo completo", "combo total"]
        }
        
        mentioned_products = []
        for product_name, patterns in specific_products.items():
            if any(pattern in conversation_text for pattern in patterns):
                mentioned_products.append(product_name)
        
        # Agregar productos genéricos si se mencionaron
        generic_products = {
            "anillos": ["anillo"],
            "aros": ["aros", "aro"],
            "pulseras": ["pulsera"],
            "labiales": ["labial"],
            "remeras": ["remera"],
            "relojes": ["reloj"]
        }
        
        for product_name, patterns in generic_products.items():
            if any(pattern in conversation_text for pattern in patterns):
                if not any(product_name in mp for mp in mentioned_products):
                    mentioned_products.append(product_name)
        
        return mentioned_products[:5]  # Máximo 5 productos
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo productos específicos: {e}")
        return []

def _extract_budget_from_context(context: RoyalAgentContext) -> Optional[str]:
    """Extrae presupuesto mencionado por el usuario"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm()
        
        import re
        
        # Patrones para capturar presupuestos
        budget_patterns = [
            r'\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # $40.000 o $40,000
            r'(\d{1,3}(?:\.\d{3})*)\s*pesos',  # 40.000 pesos
            r'(\d{1,3}(?:\.\d{3})*)\s*mil',    # 40 mil
            r'presupuesto.*?(\d{1,3}(?:\.\d{3})*)',  # presupuesto de 40000
            r'invertir.*?(\d{1,3}(?:\.\d{3})*)',     # invertir 40000
            r'tengo.*?(\d{1,3}(?:\.\d{3})*)',        # tengo 40000
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            if matches:
                # Tomar el número más alto (probablemente el presupuesto real)
                amounts = []
                for match in matches:
                    # Limpiar y convertir a número
                    clean_amount = match.replace('.', '').replace(',', '')
                    try:
                        amounts.append(int(clean_amount))
                    except ValueError:
                        continue
                
                if amounts:
                    max_amount = max(amounts)
                    # Formatear bonito
                    if max_amount >= 1000:
                        return f"${max_amount:,}".replace(',', '.')
                    else:
                        return f"${max_amount}"
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo presupuesto: {e}")
        return None

def _extract_objections_from_context(context: RoyalAgentContext) -> List[str]:
    """Extrae objeciones y dudas específicas expresadas por el usuario"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Objeciones comunes con patrones
        objections_patterns = {
            "no sé qué elegir": ["no sé qué", "no se que", "no sé cuál", "qué me recomendás", "qué me recomiendas"],
            "es mucha inversión": ["mucha plata", "mucho dinero", "muy caro", "mucha inversión", "no tengo tanto"],
            "no tengo experiencia": ["no tengo experiencia", "nunca vendí", "no sé vender", "soy nueva en esto"],
            "no tengo tiempo": ["no tengo tiempo", "muy ocupada", "no puedo dedicar"],
            "no sé si se vende": ["se venderá", "si se vende", "tiene salida", "se mueve"],
            "tengo miedo de perder": ["miedo de perder", "y si no funciona", "riesgo", "pérdida"],
            "no sé por dónde empezar": ["por dónde empiezo", "cómo empiezo", "no sé empezar", "primer paso"]
        }
        
        detected_objections = []
        for objection, patterns in objections_patterns.items():
            if any(pattern in conversation_text for pattern in patterns):
                detected_objections.append(objection)
        
        return detected_objections[:3]  # Máximo 3 objeciones principales
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo objeciones: {e}")
        return []

def _extract_questions_asked_from_context(context: RoyalAgentContext) -> List[str]:
    """Extrae preguntas específicas que hizo el usuario"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        # Preguntas frecuentes con patrones
        common_questions = {
            "cuánto necesito para empezar": ["cuánto necesito", "cuánto para empezar", "cuánto invertir", "inversión inicial"],
            "qué productos se venden más": ["qué se vende más", "qué productos van mejor", "cuáles son los más vendidos"],
            "cuánto gano por producto": ["cuánto gano", "qué margen", "rentabilidad", "ganancia por"],
            "cómo funciona el envío": ["envío", "cómo me llega", "shipping", "entrega"],
            "tienen local físico": ["local", "dónde están", "dirección", "showroom"],
            "cuánto tiempo demora": ["cuánto tarda", "tiempo de entrega", "demora"],
            "cómo hago el pedido": ["cómo compro", "cómo pido", "proceso de compra"],
            "tienen garantía": ["garantía", "devolución", "cambio"],
            "qué formas de pago": ["pago", "cuotas", "tarjeta", "transferencia"]
        }
        
        detected_questions = []
        for question, patterns in common_questions.items():
            if any(pattern in conversation_text for pattern in patterns):
                detected_questions.append(question)
        
        return detected_questions[:4]  # Máximo 4 preguntas principales
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo preguntas: {e}")
        return []

def _extract_engagement_level_from_context(context: RoyalAgentContext) -> str:
    """Determina el nivel de engagement del usuario durante la conversación"""
    try:
        # Obtener métricas de la conversación
        conversation_length = len(context.conversation.get_context_summary_for_llm())
        interaction_count = len(context.conversation.interaction_history)
        
        # Buscar indicadores de alto engagement
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        high_engagement_indicators = [
            "me interesa", "me gusta", "quiero saber", "contame más", 
            "perfecto", "genial", "me encanta", "qué bueno",
            "sí", "dale", "ok", "entiendo"
        ]
        
        low_engagement_indicators = [
            "no me interesa", "después veo", "lo pienso", "no sé",
            "tal vez", "capaz", "no estoy segura"
        ]
        
        high_score = sum(1 for indicator in high_engagement_indicators if indicator in conversation_text)
        low_score = sum(1 for indicator in low_engagement_indicators if indicator in conversation_text)
        
        # Determinar engagement basado en múltiples factores
        if conversation_length > 500 and interaction_count >= 3 and high_score > low_score:
            return "alto"
        elif conversation_length > 200 and high_score >= low_score:
            return "medio"
        else:
            return "bajo"
            
    except Exception as e:
        logger.error(f"❌ Error determinando engagement: {e}")
        return "medio"

def _extract_conversation_topics_from_context(context: RoyalAgentContext) -> List[str]:
    """Extrae los temas principales de conversación"""
    try:
        conversation_text = context.conversation.get_context_summary_for_llm().lower()
        
        topics_patterns = {
            "combos emprendedores": ["combo emprendedor", "combo para empezar", "kit emprendedor"],
            "márgenes de ganancia": ["margen", "ganancia", "rentabilidad", "cuánto gano"],
            "productos trendy": ["moda", "trendy", "tendencia", "lo que está"],
            "inversión inicial": ["inversión", "invertir", "presupuesto inicial", "cuánto necesito"],
            "experiencia en ventas": ["experiencia", "vendí", "vendo", "negocio", "clientas"],
            "envíos y logística": ["envío", "entrega", "dónde llega", "andreani"],
            "formas de pago": ["pago", "cuotas", "tarjeta", "transferencia", "efectivo"],
            "catálogo de productos": ["productos", "catálogo", "qué tienen", "variedad"]
        }
        
        detected_topics = []
        for topic, patterns in topics_patterns.items():
            if any(pattern in conversation_text for pattern in patterns):
                detected_topics.append(topic)
        
        return detected_topics[:4]  # Máximo 4 temas principales
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo temas de conversación: {e}")
        return [] 