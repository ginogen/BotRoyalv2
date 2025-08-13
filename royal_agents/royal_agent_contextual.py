# Royal Agent Contextual para Royal Bot v2
# Agente principal que usa el sistema de contexto de OpenAI Agents

from typing import Dict, List, Any, Optional
from agents import Agent, Runner, RunContextWrapper  # type: ignore
from .conversation_context import RoyalAgentContext, context_manager
from .contextual_tools import create_contextual_tools
from .woocommerce_mcp_tools import create_woocommerce_tools
from .training_mcp_tools import create_training_tools
from .royal_agent import (
    get_royal_info, 
    track_client_greeting, 
    get_arreglos_info,
    get_joyas_personalizadas_info, 
    get_royal_education_info,
    get_situaciones_frecuentes
)
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
    
    **Si se detecta frustración (nivel 2 o 3):**
    1. **INMEDIATAMENTE dejar de insistir con compras/datos**
    2. **ACTIVAR protocolo HITL**
    3. **NO seguir pidiendo nombre, dirección, método de pago**
    4. **Usar handle_missing_information_hitl() o escalate_to_human_support()**
    5. **Cambiar completamente el enfoque a resolver su molestia**
    

    **NUNCA HACER cuando el usuario está frustrado:**
    - Seguir pidiendo datos de compra
    - Insistir con el mismo producto
    - Seguir ofreciendo combos sin resolver la molestia
    - Actuar como si nada pasó

    **REGLA OBLIGATORIA #2: TRIGGERS AUTOMÁTICOS PARA HERRAMIENTAS**
    
    ### Para consultas de WEB/CATÁLOGO:
    **Palabras:** "web", "página", "website", "catálogo", "catalogo", "ver productos", "tienda online"
    → **ACCIÓN:** SIEMPRE usar get_basic_company_info("catalogo")
    
    ### Para información básica:
    **Palabras:** "mínimo", "minimo", "envío", "envio", "pago", "confiable", "local"
    → **ACCIÓN:** SIEMPRE usar get_basic_company_info() con el tipo correspondiente
    
    ### Para productos específicos con frustración:
    **Si usuario dice "no me gusta" o "no me convence" después de mostrar productos:**
    → **ACCIÓN:** 
    1. USAR detect_user_frustration()
    2. Si detecta frustración → ACTIVAR HITL, NO seguir con compra
    3. PREGUNTAR qué específicamente busca
    4. Ofrecer alternativas diferentes

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
    - `escalate_to_human_support()` → Escala a soporte humano cuando es necesario
    
    **PROTOCOLO AUTOMÁTICO:**
    1. **SIEMPRE** empezar con detect_user_frustration() 
    2. Si detectás frustración → **CAMBIAR ENFOQUE**, usar HITL, NO insistir con compra
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
       - Empezando: preguntas + combos básicos
       - Experimentado: productos específicos + diversificación
    3. **GUARDAR información con update_user_profile()**
    
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
    3. **NUNCA insistir con datos de compra si está molesto**
    4. **SIEMPRE usar frases HITL** como "dame un momento que chequeo eso"
    5. **ESCALAR si es necesario** con `escalate_to_human_support()`
    6. **CAMBIAR completamente el enfoque** a resolver su molestia

    ## 5. PROTOCOLO PARA WEB/CATÁLOGO:
    
    **CUANDO el usuario pregunta por "web", "página", "catálogo", "tienda online":**
    
    1. **SIEMPRE usar get_basic_company_info("catalogo")**
    2. **NUNCA inventar links**
    3. **Usar SOLO el link oficial:** https://royalmayorista.com.ar/shop/
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
    - Tarjeta (hasta 3 cuotas sin interés)
    - Transferencia: CBU 4530000800014232361716, Alias: ROYAL.JOYAS.2023.nx
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
    
    1. detect_user_frustration() detecta frustración nivel 3
    2. **INMEDIATAMENTE cambiar enfoque**
    3. **NO insistir con datos de compra**
    4. Responder: "Perdón que no te convencieron. ¿Qué específicamente estás buscando?"
    5. Escalar si es necesario
    ```
    
    **Ejemplo 4 - Pregunta por web:**
    ```
    Usuario: "¿Tienen página web para ver el catálogo?"
    
    1. **SIEMPRE usar get_basic_company_info("catalogo")**
    2. Responder con link oficial: https://royalmayorista.com.ar/shop/
    3. **NUNCA inventar links**
    ```
    
    # REGLAS DE COMPORTAMIENTO CRÍTICAS
    
    1. **SIEMPRE detectar frustración PRIMERO** antes de cualquier acción
    2. **NUNCA inventar información** - usar datos reales del contexto
    3. **INTERPRETAR referencias** usando el contexto de productos mostrados
    4. **PERSONALIZAR respuestas** según el perfil del usuario en contexto
    5. **MANTENER tono argentino** - informal, cercano, amigable SIEMPRE
    6. **PROTOCOLO HITL OBLIGATORIO** - nunca decir "no tengo información"
    7. **CAMBIAR ENFOQUE si detecta frustración** - NO insistir con compra
    8. **USAR LINKS REALES** - solo https://royalmayorista.com.ar/shop/ para catálogo
    
    **REGLA DE ORO**: El contexto es tu memoria, HITL es tu salvavidas, y la detección de frustración es tu brújula. Cuando detectes frustración, CAMBIÁ completamente el enfoque para resolver la molestia, no para vender.
    """
    
    # Preparar todas las herramientas
    base_tools = [
        get_royal_info,
        track_client_greeting,
        get_arreglos_info,
        get_joyas_personalizadas_info,
        get_royal_education_info,
        get_situaciones_frecuentes
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