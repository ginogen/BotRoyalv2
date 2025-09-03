# Contextual Tools para Royal Bot v2
# Herramientas que usan el contexto de conversación siguiendo el patrón de OpenAI Agents

from typing import Dict, List, Any, Optional, Tuple, Union, cast
from agents import function_tool, RunContextWrapper  # type: ignore
from .conversation_context import RoyalAgentContext, ProductReference
from .woocommerce_mcp_tools import wc_client
from .training_mcp_tools import training_parser, TRAINING_PARSER_AVAILABLE
import logging
import re

# Category matcher para búsqueda de categorías
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from category_matcher import find_categories, format_categories_for_user, extract_product_keywords

logger = logging.getLogger(__name__)

# Tipos para respuestas de API WooCommerce
WooCommerceProduct = Dict[str, Any]
APIResponse = Union[List[WooCommerceProduct], Dict[str, Any]]

@function_tool
async def detect_user_frustration(wrapper: RunContextWrapper[RoyalAgentContext], user_message: str) -> str:
    """
    Detecta si el usuario necesita asistencia adicional o tiene dificultades y activa protocolo HITL.
    
    Args:
        user_message: Mensaje del usuario para analizar necesidad de asistencia
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"😤 DETECT_USER_FRUSTRATION para usuario: {context.user_id}")
    logger.info(f"   Mensaje: {user_message}")
    
    # Palabras/frases que indican necesidad de asistencia - EXPANDIDA
    frustration_indicators = [
        # Enojo directo
        'no funciona', 'no sirve', 'terrible', 'pésimo', 'horrible', 'malísimo',
        'una porquería', 'una mierda', 'no anda', 'roto', 'falla',
        
        # Frustración y descontento - NUEVAS
        'no me gusta', 'no me gustan', 'no me convence', 'no me sirve', 
        'no me ayuda', 'confundido', 'perdido', 'desastre', 'son un desastre',
        'es un desastre', 'qué desastre', 'no entiendo', 'no logro', 'no puedo',
        
        # Expresiones de disconformidad - NUEVAS
        'me molesta', 'me fastidia', 'me cansa', 'estoy harto', 'estoy cansado',
        'esto no va', 'no me gusta esto', 'esto es horrible', 'esto es terrible',
        
        # Quejas
        'siempre lo mismo', 'otra vez', 'de nuevo', 'nunca funciona',
        'hartos', 'cansado', 'aburrido', 'fastidio', 'imposible', 'complicado',
        
        # Problemas urgentes
        'urgente', 'rápido', 'ya', 'inmediatamente', 'problema grave',
        'error', 'falla', 'no me llega', 'perdí', 'se perdió',
        
        # Expresiones argentinas de disconformidad
        'qué quilombo', 'qué bardo', 'no da', 'una garompa', 'un desastre',
        'no va', 'está roto', 'no me anda', 'qué embole', 'es un bodrio'
    ]
    
    message_lower = user_message.lower()
    
    # Detectar indicadores de asistencia necesaria
    frustration_found: List[str] = []
    for indicator in frustration_indicators:
        if indicator in message_lower:
            frustration_found.append(indicator)
    
    # Detectar patrones de asistencia necesaria - MEJORADOS
    patterns = [
        r'no (me )?(\w+)',  # "no me funciona", "no anda", "no me gusta"
        r'por qué no (\w+)',  # "por qué no funciona"
        r'(nunca|siempre) (\w+)',  # "nunca funciona", "siempre falla"
        r'(\w+) (mal|terrible|pésimo|horrible)',  # "funciona mal"
        r'esto (no|es) (\w+)',  # "esto no va", "esto es horrible"
        r'son un (\w+)',  # "son un desastre"
        r'es un (\w+)',  # "es un desastre"
        r'qué (\w+)',  # "qué desastre", "qué horror"
    ]
    
    pattern_matches: List[Tuple[str, ...]] = []
    for pattern in patterns:
        matches = re.findall(pattern, message_lower)
        if matches:
            pattern_matches.extend(matches)
    
    # NUEVO: Detectar negatividad extrema con palabras cortas
    negative_short_phrases = ['no', 'mal', 'feo', 'asco', 'odio']
    if len(message_lower.split()) <= 3:  # Mensajes cortos muy negativos
        for phrase in negative_short_phrases:
            if phrase in message_lower:
                frustration_found.append(f"negative_short: {phrase}")
    
    # Determinar nivel de asistencia necesaria - MEJORADO
    frustration_level = 0
    
    # Nivel alto: múltiples indicadores o frases muy negativas
    if len(frustration_found) >= 2 or any('desastre' in word for word in frustration_found):
        frustration_level = 3  # Alto
    elif len(frustration_found) == 1 or len(pattern_matches) >= 1:
        frustration_level = 2  # Medio
    elif any(word in message_lower for word in ['problema', 'ayuda', 'dudas', 'confuso']):
        frustration_level = 1  # Bajo
    
    # NUEVO: Detectar si es respuesta negativa corta después de mostrar productos
    if (conversation.current_state == "selecting" and 
        len(user_message.split()) <= 4 and 
        any(neg in message_lower for neg in ['no', 'mal', 'feo', 'asco'])):
        frustration_level = max(frustration_level, 2)  # Mínimo nivel medio
        frustration_found.append("negative_response_to_products")
    
    # Registrar en contexto
    if frustration_level > 0:
        conversation.add_interaction("system", f"Usuario necesita asistencia adicional: nivel {frustration_level}")
        conversation.update_user_profile("assistance_level", frustration_level)
        conversation.current_state = "needs_assistance"
        
        logger.warning(f"⚠️ ASISTENCIA REQUERIDA - Nivel: {frustration_level}")
        logger.warning(f"   Indicadores: {frustration_found}")
        logger.warning(f"   Patrones: {pattern_matches}")
        
        # Convertir pattern_matches a strings para poder sumarlos
        pattern_strings = [str(match) for match in pattern_matches]
        total_indicators = len(frustration_found + pattern_strings)
        
        return f"ASSISTANCE_NEEDED|level={frustration_level}|indicators={total_indicators}"
    
    return "NO_FRUSTRATION_DETECTED"

@function_tool
async def handle_missing_information_hitl(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    information_type: str,
    context_description: str = ""
) -> str:
    """
    Maneja situaciones donde el bot no tiene información y activa protocolo HITL.
    
    Args:
        information_type: Tipo de información faltante (product, price, stock, shipping, etc.)
        context_description: Descripción del contexto para logging
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🆘 HANDLE_MISSING_INFORMATION_HITL para usuario: {context.user_id}")
    logger.info(f"   Tipo: {information_type}")
    logger.info(f"   Contexto: {context_description}")
    
    # Registrar en contexto que necesita asistencia humana
    conversation.add_interaction("system", f"Información faltante: {information_type}")
    conversation.update_user_profile("needs_human_assistance", True)
    conversation.update_user_profile("missing_info_type", information_type)
    conversation.current_state = "pending_human_assistance"
    
    # Respuestas argentinas naturales según el tipo
    hitl_responses = {
        'product': [
            "Dale, dejame que chequeo eso puntualmente en el sistema y te confirmo ahora",
            "tengo que verificar eso con el equipo. Dame un momento que te traigo la info completa",
            "Mirá, eso lo tengo que consultar específicamente. En un ratito te confirmo todo",
            "déjame que reviso eso en detalle y te paso los datos exactos"
        ],
        'price': [
            "Los precios me los están actualizando justo ahora. Dame un minuto que te confirmo el valor exacto",
            "tengo que chequear el precio actualizado. Ahora te traigo el dato preciso",
            "Dale, dejame que reviso el valor actual y te confirmo en un moemento",
            "Déjame verificar el precio  y te paso la info"
        ],
        'stock': [
            "El stock lo tengo que verificar en tiempo real. Un segundo que chequeo y te confirmo",
            "Dale, que consulto la disponibilidad exacta y te digo",
            "Tengo que ver qué hay disponible ahora mismo. Ya te confirmo",
            "Dejame que reviso el inventario actualizado y te paso el dato"
        ],
        'shipping': [
            "Los envíos tengo que consultarlos según tu zona específica. Ya te digo",
            "ara el envío necesito chequear tu ubicación exacta. Ahora te confirmo",
            "Dale, que verifico las opciones de envío para tu zona y te cuento",
            "Tengo que consultar las opciones de entrega para donde estás. Un momento"
        ],
        'technical': [
            "Uy, se me está complicando el sistema. Dame un momento que lo soluciono",
            "Tengo un problemita técnico. Ya lo arreglo y te ayudo como corresponde",
            "Se me trabó algo acá. Un segundo que lo destrabó y seguimos",
            "Perdón, se me colgó algo. Ya vuelvo con toda la info que necesitás"
        ],
        'general': [
            "Dale, tengo que chequear eso puntualmente. Dame un ratito y te confirmo todo",
            "Esa info la tengo que verificar bien. En un momento te respondo",
            "Dejame que consulto eso específicamente y te paso toda la información",
            "eso lo tengo que revisar con detalle. Ahora te confirmo"
        ]
    }
    
    # Seleccionar respuesta según el tipo
    import random
    responses = hitl_responses.get(information_type, hitl_responses['general'])
    selected_response = random.choice(responses)
    
    # Agregar contexto específico si es necesario
    if information_type == 'product' and context_description:
        selected_response += f" (sobre {context_description})"
    
    # Agregar emoji de confianza
    selected_response += " 👍"
    
    logger.warning(f"🚨 HITL ACTIVADO - Usuario necesita asistencia humana")
    logger.warning(f"   Respuesta generada: {selected_response}")
    
    return f"HITL_ACTIVATED|{selected_response}"

@function_tool
async def check_mcp_connectivity_and_fallback(wrapper: RunContextWrapper[RoyalAgentContext]) -> str:
    """
    Verifica conectividad MCP y activa fallback/HITL si hay problemas.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🔌 CHECK_MCP_CONNECTIVITY para usuario: {context.user_id}")
    
         # Test básico de conectividad WooCommerce
    try:
        test_result = await wc_client.make_request('products', {'per_page': 1})
        
        if 'error' in test_result:
            logger.error(f"❌ MCP WooCommerce con errores: {test_result['error']}")
            
            # Activar HITL por problemas técnicos directamente
            conversation.add_interaction("system", "Información faltante: technical")
            conversation.update_user_profile("needs_human_assistance", True)
            conversation.current_state = "pending_human_assistance"
            
            import random
            responses = [
                "Uy, se me está complicando el sistema. Dame un momento que lo soluciono 👍",
                "Tengo un problemita técnico. Ya lo arreglo y te ayudo como corresponde 👍",
                "Se me trabó algo acá. Un segundo que lo destrabó y seguimos 👍"
            ]
            return f"HITL_ACTIVATED|{random.choice(responses)}"
        else:
            logger.info("✅ MCP WooCommerce operativo")
            return "MCP_WORKING"
            
    except Exception as e:
        logger.error(f"❌ MCP WooCommerce falla completa: {str(e)}")
        
        # Activar HITL por falla técnica directamente
        conversation.add_interaction("system", "Información faltante: technical")
        conversation.update_user_profile("needs_human_assistance", True)
        conversation.current_state = "pending_human_assistance"
        
        import random
        responses = [
            "Perdón, se me colgó algo. Ya vuelvo con toda la info que necesitás 👍",
            "Uy, se me complicó el sistema. Dame un momento que lo soluciono 👍"
        ]
        return f"HITL_ACTIVATED|{random.choice(responses)}"

@function_tool
async def escalate_to_human_support(
    wrapper: RunContextWrapper[RoyalAgentContext],
    escalation_reason: str,
    user_context: str = ""
) -> str:
    """
    Escala automáticamente a soporte humano con contexto completo.
    
    Args:
        escalation_reason: Razón de la escalación (frustration, missing_info, complex_query, etc.)
        user_context: Contexto adicional del usuario
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🚨 ESCALATE_TO_HUMAN_SUPPORT para usuario: {context.user_id}")
    logger.info(f"   Razón: {escalation_reason}")
    logger.info(f"   Contexto: {user_context}")
    
    # Registrar escalación en contexto
    conversation.add_interaction("system", f"Escalado a humano: {escalation_reason}")
    conversation.update_user_profile("escalated_to_human", True)
    conversation.update_user_profile("escalation_reason", escalation_reason)
    conversation.current_state = "escalated_to_human"
    
    # Generar resumen para el humano
    user_summary = f"""
🚨 ESCALACIÓN AUTOMÁTICA - Usuario: {context.user_id}
📋 Razón: {escalation_reason}
🕐 Tiempo de conversación: {len(conversation.interaction_history)} interacciones
🎯 Estado: {conversation.current_state}

👤 PERFIL DEL USUARIO:
- Emprendedor: {conversation.is_entrepreneur} ({conversation.experience_level})
- Intereses: {', '.join(conversation.product_interests[-3:]) if conversation.product_interests else 'No especificados'}
- Presupuesto: {conversation.budget_range or 'No especificado'}

📦 PRODUCTOS RECIENTES EN MEMORIA:
{conversation.get_recent_products_summary() if conversation.recent_products else 'Ninguno'}

💬 ÚLTIMAS INTERACCIONES:
"""
    
    for interaction in conversation.interaction_history[-3:]:
        role = "👤 Usuario" if interaction["role"] == "user" else "🤖 Royalia"
        message = interaction["message"][:100] + "..." if len(interaction["message"]) > 100 else interaction["message"]
        user_summary += f"{role}: {message}\n"
    
    if user_context:
        user_summary += f"\n🔍 CONTEXTO ADICIONAL: {user_context}"
    
    # Log para el equipo humano
    logger.critical("🚨🚨 ESCALACIÓN A SOPORTE HUMANO 🚨🚨")
    logger.critical(user_summary)
    
    # Respuesta natural argentina para el usuario
    escalation_responses = {
        'frustration': [
            "Dale, mejor que hable con vos directamente alguien del equipo. Ya le paso tu consulta a mi supervisor",
            "Te voy a conectar con alguien más especializado que te va a resolver esto al toque",
            "Para esto necesitás hablar directamente con el equipo. Ya les aviso para que te contacten",
        ],
        'missing_info': [
            "Mirá, mejor que hable con vos directamente alguien que tenga toda la info. Ya los contacto",
            "Dale, que para esto necesitás hablar con el equipo especializado. Te van a contactar",
            "Uy, esto lo tiene que ver específicamente el equipo técnico. Ya les aviso para que te llamen",
        ],
        'complex_query': [
            "Esta consulta está muy específica, mejor que te atienda alguien especializado. Ya los aviso",
            "Para esto necesitás hablar con el equipo técnico directamente. Te van a contactar",
            "Dale, esto lo tiene que manejar alguien con más experiencia. Ya escalé el tema",
        ],
        'technical_issue': [
            "Uy, se me complicó el sistema. Ya avisé al equipo técnico para que te contacten directamente",
            "Tengo un problema técnico que me impide ayudarte bien. El equipo ya está al tanto",
            "Se me trabó algo importante. Ya escalé para que te atiendan como corresponde",
        ]
    }
    
    import random
    responses = escalation_responses.get(escalation_reason, escalation_responses['missing_info'])
    selected_response = random.choice(responses)
    
    # Agregar timeframe realista
    selected_response += " En breve te van a contactar. 📞"
    
    # 🚨 NUEVA FUNCIONALIDAD: Notificación automática a equipo via WhatsApp
    try:
        logger.info(f"🔍 ESCALATION DEBUG - Iniciando notificación automática")
        logger.info(f"🔍 ESCALATION DEBUG - Reason: {escalation_reason}")
        logger.info(f"🔍 ESCALATION DEBUG - Context attributes: {dir(wrapper.context)}")
        logger.info(f"🔍 ESCALATION DEBUG - Context type: {type(wrapper.context)}")
        
        # Determinar team_id según el tipo de escalación
        team_id = 0
        if escalation_reason == 'frustration':
            team_id = getattr(__import__('royal_server_optimized'), 'CHATWOOT_TEAM_ASSISTANCE_ID', 0)
        elif escalation_reason in ['missing_info', 'technical_issue']:
            team_id = getattr(__import__('royal_server_optimized'), 'CHATWOOT_TEAM_SUPPORT_ID', 0)
        elif escalation_reason == 'complex_query':
            team_id = getattr(__import__('royal_server_optimized'), 'CHATWOOT_TEAM_GENERAL_ID', 0)
        else:
            team_id = getattr(__import__('royal_server_optimized'), 'CHATWOOT_TEAM_ASSISTANCE_ID', 0)
        
        logger.info(f"🔍 ESCALATION DEBUG - Team ID determinado: {team_id}")
        
        # Obtener funciones del server
        if team_id > 0:
            server_module = __import__('royal_server_optimized')
            assign_conversation_func = getattr(server_module, 'assign_conversation_to_team', None)
            send_notification_func = getattr(server_module, 'send_team_whatsapp_notification', None)
            
            logger.info(f"🔍 ESCALATION DEBUG - assign_conversation_func available: {assign_conversation_func is not None}")
            logger.info(f"🔍 ESCALATION DEBUG - send_notification_func available: {send_notification_func is not None}")
            
            if assign_conversation_func and send_notification_func:
                # Buscar conversation_id en diferentes lugares del contexto
                conversation_id = None
                user_phone = 'No disponible'
                
                # Método 1: Desde metadata global (nuevo sistema)
                try:
                    import sys
                    server_module = sys.modules.get('royal_server_optimized')
                    if server_module and hasattr(server_module, 'current_escalation_metadata'):
                        metadata = server_module.current_escalation_metadata
                        conversation_id = metadata.get('conversation_id')
                        user_phone = metadata.get('phone', 'No disponible')
                        logger.info(f"🔍 ESCALATION DEBUG - Metadata desde server: conversation_id={conversation_id}, phone={user_phone}")
                except Exception as meta_e:
                    logger.warning(f"⚠️ No se pudo obtener metadata desde server: {meta_e}")
                
                # Método 2: Atributo directo en contexto (fallback)
                if not conversation_id and hasattr(wrapper.context, 'conversation') and hasattr(wrapper.context.conversation, 'conversation_id'):
                    conversation_id = wrapper.context.conversation.conversation_id
                    logger.info(f"🔍 ESCALATION DEBUG - conversation_id desde conversation: {conversation_id}")
                
                # Método 3: Desde conversation.phone
                if user_phone == 'No disponible' and hasattr(wrapper.context, 'conversation') and hasattr(wrapper.context.conversation, 'phone'):
                    user_phone = wrapper.context.conversation.phone
                    logger.info(f"🔍 ESCALATION DEBUG - phone desde conversation: {user_phone}")
                
                # Método 4: En conversation.context_data
                if not conversation_id and hasattr(wrapper.context, 'conversation') and hasattr(wrapper.context.conversation, 'context_data'):
                    conversation_id = wrapper.context.conversation.context_data.get('conversation_id')
                    if not user_phone or user_phone == 'No disponible':
                        user_phone = wrapper.context.conversation.context_data.get('phone', 'No disponible')
                    logger.info(f"🔍 ESCALATION DEBUG - Desde context_data: conversation_id={conversation_id}, phone={user_phone}")
                
                logger.info(f"🔍 ESCALATION DEBUG - FINAL: conversation_id={conversation_id}, phone={user_phone}")
                
                # Asignar conversación al equipo (si tenemos conversation_id)
                if conversation_id:
                    logger.info(f"🔄 Asignando conversación {conversation_id} a team {team_id}")
                    assign_result = await assign_conversation_func(conversation_id, team_id, f"Escalación: {escalation_reason}")
                    logger.info(f"🔍 ESCALATION DEBUG - assign_result: {assign_result}")
                else:
                    logger.warning("⚠️ No se pudo obtener conversation_id para asignación")
                
                # Enviar notificación WhatsApp al equipo
                logger.info(f"📱 Enviando notificación WhatsApp a team {team_id}")
                notification_result = await send_notification_func(
                    team_id=team_id,
                    user_name=context.user_id,
                    user_phone=user_phone,
                    escalation_reason=escalation_reason,
                    context_summary=user_summary
                )
                logger.info(f"🔍 ESCALATION DEBUG - notification_result: {notification_result}")
                
                logger.info(f"✅ Escalación completa: Chatwoot + WhatsApp team {team_id}")
            else:
                logger.warning("⚠️ Funciones de escalación no disponibles")
                logger.warning(f"⚠️ assign_conversation_func: {assign_conversation_func}")
                logger.warning(f"⚠️ send_notification_func: {send_notification_func}")
        else:
            logger.warning(f"⚠️ No hay team_id configurado para {escalation_reason} (team_id: {team_id})")
            
            # Fallback: intentar notificación con team_id por defecto
            default_team_id = getattr(__import__('royal_server_optimized'), 'CHATWOOT_TEAM_ASSISTANCE_ID', 0)
            if default_team_id > 0 and default_team_id != team_id:
                logger.info(f"🔄 FALLBACK - Usando team_id por defecto: {default_team_id}")
                try:
                    server_module = __import__('royal_server_optimized')
                    send_notification_func = getattr(server_module, 'send_team_whatsapp_notification', None)
                    
                    if send_notification_func:
                        # Obtener metadata para phone
                        user_phone = 'No disponible'
                        conversation_id = None
                        
                        try:
                            import sys
                            server_module_meta = sys.modules.get('royal_server_optimized')
                            if server_module_meta and hasattr(server_module_meta, 'current_escalation_metadata'):
                                metadata = server_module_meta.current_escalation_metadata
                                conversation_id = metadata.get('conversation_id')
                                user_phone = metadata.get('phone', 'No disponible')
                                logger.info(f"🔍 FALLBACK DEBUG - metadata: conversation_id={conversation_id}, phone={user_phone}")
                        except Exception as meta_e:
                            logger.warning(f"⚠️ FALLBACK - No se pudo obtener metadata: {meta_e}")
                        
                        # Enviar notificación con team por defecto
                        notification_result = await send_notification_func(
                            team_id=default_team_id,
                            user_name=context.user_id,
                            user_phone=user_phone,
                            escalation_reason=f"FALLBACK: {escalation_reason}",
                            context_summary=user_summary
                        )
                        logger.info(f"✅ FALLBACK - Notificación enviada con team por defecto: {notification_result}")
                    else:
                        logger.warning("⚠️ FALLBACK - Función de notificación no disponible")
                        
                except Exception as fallback_e:
                    logger.error(f"❌ FALLBACK - Error en notificación por defecto: {fallback_e}")
            else:
                logger.warning(f"⚠️ FALLBACK - Team por defecto tampoco configurado: {default_team_id}")
            
    except Exception as e:
        # Si falla la notificación, no afectar la escalación principal
        logger.error(f"❌ Error en notificación automática: {e}")
        logger.warning("⚠️ Escalación continúa sin notificación automática")
        import traceback
        logger.error(f"❌ Stack trace: {traceback.format_exc()}")
    
    return f"ESCALATED_TO_HUMAN|{selected_response}"

@function_tool
async def get_context_summary(wrapper: RunContextWrapper[RoyalAgentContext]) -> str:
    """
    Obtiene resumen del contexto actual de la conversación.
    Esta herramienta permite al LLM acceder a la información de contexto.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"📋 GET_CONTEXT_SUMMARY para usuario: {context.user_id}")
    
    summary_parts = []
    
    # Información del usuario
    summary_parts.append(f"👤 **Usuario:** {context.user_id}")
    summary_parts.append(f"⏰ **Última interacción:** {conversation.last_interaction.strftime('%H:%M:%S')}")
    summary_parts.append(f"🔄 **Estado actual:** {conversation.current_state}")
    
    # Verificar si necesita asistencia humana
    if conversation.user_profile.get("needs_human_assistance"):
        summary_parts.append("🚨 **ALERTA:** Usuario necesita asistencia humana")
        
    if conversation.user_profile.get("assistance_level", 0) > 0:
        level = conversation.user_profile.get("assistance_level")
        summary_parts.append(f"🆘 **NECESITA ASISTENCIA:** Nivel {level}/3")
    
    # Perfil del usuario
    if conversation.is_entrepreneur:
        summary_parts.append(f"🚀 **Perfil:** Emprendedor ({conversation.experience_level})")
        
    if conversation.product_interests:
        interests = ", ".join(conversation.product_interests[-3:])
        summary_parts.append(f"💡 **Intereses:** {interests}")
        
    if conversation.budget_range:
        summary_parts.append(f"💰 **Presupuesto:** {conversation.budget_range}")
    
    # Productos recientes
    if conversation.recent_products:
        summary_parts.append(f"\n📦 **Productos mostrados recientemente ({len(conversation.recent_products)}):**")
        for i, product in enumerate(conversation.recent_products[-5:], 1):
            summary_parts.append(f"  {i}. {product.name} - ${product.price}")
    
    # Historial reciente
    if conversation.interaction_history:
        summary_parts.append(f"\n💬 **Últimas interacciones ({len(conversation.interaction_history)}):**")
        for interaction in conversation.interaction_history[-3:]:
            role = "Usuario" if interaction["role"] == "user" else "Asistente"
            message = interaction["message"][:80] + "..." if len(interaction["message"]) > 80 else interaction["message"]
            summary_parts.append(f"  {role}: {message}")
    
    logger.info(f"✅ Context summary generado: {len(summary_parts)} elementos")
    return "\n".join(summary_parts)

@function_tool
async def get_product_info_with_context(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    product_name: str = "", 
    product_id: str = "", 
    category: str = ""
) -> str:
    """
    Obtiene información de productos y los guarda en el contexto de la conversación.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🔍 GET_PRODUCT_INFO_WITH_CONTEXT para usuario: {context.user_id}")
    logger.info(f"   Búsqueda: {product_name or category or product_id}")
    
    # Llamar a la función original de WooCommerce
    params = {}
    if product_name:
        params['search'] = product_name
    if product_id:
        params['include'] = product_id
    if category:
        params['category'] = category
    
    result = await wc_client.make_request('products', params)
    
    if 'error' in result:
        logger.error(f"❌ Error obteniendo productos: {result['error']}")
        # Activar HITL en lugar de decir "no pude obtener"
        conversation.add_interaction("system", f"Información faltante: product")
        conversation.update_user_profile("needs_human_assistance", True) 
        conversation.current_state = "pending_human_assistance"
        
        import random
        responses = [
            "Dale, dejame que chequeo eso puntualmente en el sistema y te confirmo ahora 👍",
            "Upa, tengo que verificar eso con el equipo. Dame un toque que te traigo la info completa 👍", 
            "Mirá, eso lo tengo que consultar específicamente. En un ratito te confirmo todo 👍"
        ]
        return random.choice(responses)
    
    # Asegurar que products es una lista de productos
    products: List[WooCommerceProduct] = result if isinstance(result, list) else []
    
    if not products:
        logger.info("   No se encontraron productos")
        # Activar HITL en lugar de decir "no encontré"
        conversation.add_interaction("system", f"Información faltante: product") 
        conversation.update_user_profile("needs_human_assistance", True)
        conversation.current_state = "pending_human_assistance"
        
        import random
        responses = [
            "Dale, dejame que chequeo eso puntualmente y te confirmo si tenemos algo similar 👍",
            "Tengo que verificar bien el inventario para esa búsqueda. Ya te confirmo 👍",
            "Déjame que reviso eso en detalle y te paso opciones disponibles 👍"
        ]
        return random.choice(responses)
    
    # Guardar productos en el contexto
    products_saved = []
    for product in products[:5]:  # Máximo 5 productos
        # Obtener datos del producto con valores por defecto
        name = str(product.get('name', 'Sin nombre'))
        price = str(product.get('price', product.get('regular_price', 'Consultar')))
        product_id = str(product.get('id', ''))
        permalink = str(product.get('permalink', ''))
        
        # Obtener categoría de forma segura
        categories = cast(List[Dict[str, Any]], product.get('categories', []))
        category = categories[0].get('name', '') if categories else ''
        
        product_ref = ProductReference(
            name=name,
            price=price,
            id=product_id,
            permalink=permalink,
            category=str(category)
        )
        
        conversation.add_product_reference(product_ref)
        products_saved.append(product_ref)
    
    # Actualizar estado de la conversación
    conversation.current_state = "selecting"
    conversation.add_interaction("assistant", f"Mostré {len(products_saved)} productos de {product_name or category}")
    
    # Formatear respuesta
    products_info = []
    for i, product in enumerate(products[:5], 1):
        name = product.get('name', 'Sin nombre')
        price = product.get('price', product.get('regular_price', 'Consultar'))
        stock_status = product.get('stock_status', 'instock') == 'instock'
        permalink = product.get('permalink', '')
        
        info = f"""
📦 **{i}. {name}**
💰 Precio: ${price}
📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}"""
        
        if product.get('sale_price'):
            info += f"\n🔥 Oferta: ${product.get('sale_price')} (antes ${product.get('regular_price')})"
            
        if permalink:
            info += f"\n🔗 Ver producto: {permalink}"
        
        info += "\n"
        products_info.append(info)
    
    logger.info(f"✅ {len(products_saved)} productos guardados en contexto")
    return "\n".join(products_info)

@function_tool
async def get_combos_with_context(wrapper: RunContextWrapper[RoyalAgentContext]) -> str:
    """
    Obtiene combos emprendedores Y los guarda en el contexto para referencias futuras.
    ¡NUEVA FUNCIÓN que soluciona el problema de memoria!
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🚀 GET_COMBOS_WITH_CONTEXT para usuario: {context.user_id}")
    
    # Buscar combos por categoría (ID 91) y por término de búsqueda
    combo_result = await wc_client.make_request('products', {'category': 91, 'per_page': 8})
    search_result = await wc_client.make_request('products', {'search': 'combo', 'per_page': 5})
    
    all_combos = []
    products_info = []
    
    # Verificar errores
    if 'error' in combo_result and 'error' in search_result:
        logger.error("❌ Error obteniendo combos de ambas fuentes")
        conversation.add_interaction("system", "Información faltante: product")
        conversation.update_user_profile("needs_human_assistance", True)
        conversation.current_state = "pending_human_assistance"
        
        import random
        responses = [
            "Dale, tengo que chequear los combos puntualmente. Dame un ratito y te confirmo todo 👍",
            "Los combos los tengo que verificar bien. En un momento te traigo las opciones disponibles 👍",
            "Déjame que consulto los combos específicamente y te paso toda la información 👍"
        ]
        return random.choice(responses)
    
    # Procesar combos de la categoría específica
    if isinstance(combo_result, list) and len(combo_result) > 0:
        logger.info(f"📦 Combos de categoría encontrados: {len(combo_result)}")
        
        for product in combo_result[:5]:
            all_combos.append(product)
    
    # Procesar resultados de búsqueda adicionales (evitar duplicados)
    if isinstance(search_result, list) and len(search_result) > 0:
        logger.info(f"🔍 Combos de búsqueda encontrados: {len(search_result)}")
        
        for product in search_result[:3]:
            # Evitar duplicados por ID
            if not any(combo.get('id') == product.get('id') for combo in all_combos):
                all_combos.append(product)
    
    # Limitar a máximo 6 combos
    all_combos = all_combos[:6]
    
    if not all_combos:
        logger.warning("❌ No se encontraron combos")
        conversation.add_interaction("system", "Información faltante: product")
        conversation.update_user_profile("needs_human_assistance", True)
        conversation.current_state = "pending_human_assistance"
        
        import random
        responses = [
            "Dale, tengo que chequear qué combos tenemos disponibles. Dame un momento 👍",
            "Los combos emprendedores los tengo que verificar. Ya te confirmo las opciones 👍",
            "Déjame que reviso qué combos hay disponibles y te paso la info completa 👍"
        ]
        return random.choice(responses)
    
    # 🔥 PARTE CRÍTICA: Guardar combos en el contexto
    logger.info(f"💾 Guardando {len(all_combos)} combos en contexto...")
    
    for i, product in enumerate(all_combos, 1):
        name = product.get('name', 'Sin nombre')
        price = product.get('price', product.get('regular_price', 'Consultar'))
        permalink = product.get('permalink', '')
        
        # Crear referencia del producto
        product_ref = ProductReference(
            name=name,
            price=price,
            id=str(product.get('id', '')),
            permalink=permalink,
            category='combo'
        )
        
        # Guardar en contexto
        conversation.add_product_reference(product_ref)
        
        # Formatear para mostrar
        stock_status = product.get('stock_status', 'instock') == 'instock'
        
        info = f"""
{i}. 🎁 **{name}**
   💰 Precio: ${price}
   📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}"""
        
        if permalink:
            info += f"\n   🔗 [Ver combo]({permalink})"
        
        products_info.append(info)
    
    # Actualizar estado de conversación
    conversation.current_state = "selecting"
    conversation.add_interaction("assistant", f"Mostré {len(all_combos)} combos emprendedores")
    
    logger.info(f"✅ {len(all_combos)} combos guardados en contexto para referencias")
    
    header = "🚀 **COMBOS EMPRENDEDORES DISPONIBLES:**\n"
    footer = "\n**🔥 ¡Estos combos se agotan rápido!** La mayoría de emprendedoras eligen estos porque ya están probados.\n\n💡 **Podés elegir ahora:** 'quiero el combo 1', 'me interesa el 3', etc.\n\n**¿Cuál te llama más la atención?** Te ayudo a completar tu pedido en este momento 👉"
    
    return header + "\n".join(products_info) + footer

@function_tool
async def process_purchase_intent(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    user_message: str
) -> str:
    """
    Procesa intención de compra usando el contexto de productos mostrados.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"💳 PROCESS_PURCHASE_INTENT para usuario: {context.user_id}")
    logger.info(f"   Mensaje: {user_message}")
    
    # Verificar si hay productos en el contexto
    if not conversation.recent_products:
        logger.info("   No hay productos en contexto")
        return "🤔 No veo que hayamos visto productos recientemente. ¿Podrías ser más específico sobre qué querés comprar?"
    
    # Buscar producto referenciado
    referenced_product = conversation.find_product_by_reference(user_message)
    
    if referenced_product:
        # Actualizar estado de conversación
        conversation.current_state = "purchasing"
        conversation.add_interaction("user", f"Quiere comprar: {referenced_product.name}")
        
        logger.info(f"✅ Producto identificado: {referenced_product.name}")
        
        response = f"""✅ **¡Perfecto! Elegiste:**

📦 **{referenced_product.name}**
💰 **Precio: ${referenced_product.price}**

💳 **Para confirmar tu pedido necesito:**
1. Tu nombre completo
2. Dirección de envío completa
3. Método de pago preferido

💡 **Opciones de pago:**
• Tarjeta (hasta 3 cuotas sin interés)
• Transferencia bancaria
• Efectivo en locales

🎯 **Sistema de seña:** Podés reservarlo con $10,000 y el resto lo pagás al retirar o antes del despacho.

¿Empezamos con tu nombre completo?"""
        
        return response
    
    # Si no encuentra producto específico, mostrar opciones
    products_list = []
    for i, product in enumerate(conversation.recent_products[-5:], 1):
        products_list.append(f"{i}. {product.name} - ${product.price}")
    
    logger.info("   Producto no identificado claramente")
    
    return f"""🤔 **No estoy seguro cuál de estos productos querés:**

{chr(10).join(products_list)}

¿Podrías decirme el **número** o el **nombre específico** del producto que te interesa?

Por ejemplo: "Quiero el 2" o "Me interesa el {conversation.recent_products[0].name.split()[0]}" """

@function_tool
async def update_user_profile(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    profile_key: str, 
    profile_value: str
) -> str:
    """
    Actualiza el perfil del usuario en el contexto.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"👤 UPDATE_USER_PROFILE para usuario: {context.user_id}")
    logger.info(f"   {profile_key}: {profile_value}")
    
    # Actualizar perfil
    conversation.update_user_profile(profile_key, profile_value)
    
    # Casos especiales
    if profile_key == "experience_level":
        conversation.is_entrepreneur = True
        conversation.experience_level = profile_value
        logger.info(f"   Usuario marcado como emprendedor: {profile_value}")
        
    elif profile_key == "interests":
        if profile_value not in conversation.product_interests:
            conversation.product_interests.append(profile_value)
        logger.info(f"   Interés agregado: {profile_value}")
        
    elif profile_key == "budget_range":
        conversation.budget_range = profile_value
        logger.info(f"   Presupuesto actualizado: {profile_value}")
    
    # Registrar en historial
    conversation.add_interaction("assistant", f"Perfil actualizado: {profile_key} = {profile_value}")
    
    return f"✅ Perfil actualizado: {profile_key} = {profile_value}"

@function_tool
async def get_recommendations_with_context(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    recommendation_type: str = "general"
) -> str:
    """
    Obtiene recomendaciones personalizadas basadas en el contexto del usuario.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"💡 GET_RECOMMENDATIONS_WITH_CONTEXT para usuario: {context.user_id}")
    logger.info(f"   Tipo: {recommendation_type}")
    
    recommendations = []
    
    # Recomendaciones para emprendedores
    if conversation.is_entrepreneur:
        if conversation.experience_level == "empezando":
            recommendations.append("🚀 **Para empezar:** Te recomiendo combos de bijou o maquillaje (menor inversión)")
            recommendations.append("📈 **Estrategia:** Comenzá con productos de alta rotación")
            
        elif conversation.experience_level == "experimentado":
            recommendations.append("💎 **Para expandir:** Combos de joyas de plata tienen mejor margen")
            recommendations.append("🎯 **Tip:** Diversificá con relojes o indumentaria")
    
    # Recomendaciones basadas en intereses
    if conversation.product_interests:
        interests = conversation.product_interests[-3:]  # Últimos 3 intereses
        recommendations.append(f"💡 **Basado en tus intereses ({', '.join(interests)}):**")
        
        if 'joyas' in interests:
            recommendations.append("  • Joyas de plata 925 tienen excelente margen")
        if 'relojes' in interests:
            recommendations.append("  • Relojes Casio son muy pedidos")
        if 'maquillaje' in interests:
            recommendations.append("  • Maquillaje tiene alta rotación")
    
    # Recomendaciones basadas en presupuesto
    if conversation.budget_range:
        recommendations.append(f"💰 **Para tu presupuesto ({conversation.budget_range}):**")
        
        if "40000" in conversation.budget_range or "básico" in conversation.budget_range.lower():
            recommendations.append("  • Combo Emprendedor Básico - ideal para comenzar")
        elif "80000" in conversation.budget_range or "intermedio" in conversation.budget_range.lower():
            recommendations.append("  • Combo Mixto - mejor variedad y margen")
    
    # Recomendaciones basadas en productos vistos
    if conversation.recent_products:
        categories_seen = list(set([p.category for p in conversation.recent_products if p.category]))
        if categories_seen:
            recommendations.append(f"📦 **Productos relacionados a lo que viste:**")
            for category in categories_seen[:2]:
                recommendations.append(f"  • Más productos de {category}")
    
    # Recomendación general si no hay contexto específico
    if not recommendations:
        recommendations.append("💡 **Recomendación general:**")
        recommendations.append("  • Comenzá con combos emprendedores para mejor variedad")
        recommendations.append("  • Joyas y maquillaje tienen alta demanda")
        recommendations.append("  • Preguntame sobre tu experiencia para mejores recomendaciones")
    
    logger.info(f"✅ {len(recommendations)} recomendaciones generadas")
    return "\n".join(recommendations)

@function_tool
async def clear_conversation_context(wrapper: RunContextWrapper[RoyalAgentContext]) -> str:
    """
    Limpia el contexto de la conversación (nueva conversación).
    """
    
    context = wrapper.context
    user_id = context.user_id
    
    logger.info(f"🧹 CLEAR_CONVERSATION_CONTEXT para usuario: {user_id}")
    
    # Reiniciar conversación manteniendo el user_id
    from .conversation_context import ConversationMemory
    context.conversation = ConversationMemory(user_id=user_id)
    
    logger.info("✅ Contexto de conversación limpiado")
    return "✅ Contexto de conversación reiniciado. ¡Empezamos de nuevo!"

@function_tool
async def handle_conversation_continuity(wrapper: RunContextWrapper[RoyalAgentContext], user_message: str) -> str:
    """
    HERRAMIENTA CRÍTICA: Maneja la continuidad conversacional cuando el usuario responde
    a una pregunta específica del bot. Evita que se pierda el hilo de la conversación.
    """
    
    context = wrapper.context
    conversation = context.conversation
    user_id = context.user_id
    
    logger.info(f"🔄 HANDLE_CONVERSATION_CONTINUITY para usuario: {user_id}")
    logger.info(f"   Mensaje: {user_message}")
    logger.info(f"   Esperando respuesta: {conversation.awaiting_response}")
    logger.info(f"   Acción pendiente: {conversation.pending_action}")
    
    # Verificar si es una continuación
    if not conversation.awaiting_response:
        return "No hay contexto de continuación activo."
    
    # Detectar tipo de respuesta
    message_lower = user_message.lower().strip()
    is_confirmation = any(word in message_lower for word in ["si", "sí", "ok", "okay", "dale", "perfecto", "bueno", "genial", "yes", "claro"])
    is_negative = any(word in message_lower for word in ["no", "nah", "nope", "después", "luego", "otro momento"])
    
    # Registrar la respuesta
    conversation.add_interaction("user", user_message, {"is_continuation": True, "pending_action": conversation.pending_action})
    
    response = ""
    
    # Manejar según la acción pendiente
    if conversation.pending_action == "recommendations":
        if is_confirmation:
            response = """Perfecto! Para armarte la recomendación ideal, necesito conocerte un poquito más:

• ¿Ya tenés experiencia vendiendo o sería tu primer emprendimiento?
• ¿Qué tipo de productos te llaman más la atención?
• ¿Tu idea es arrancar de a poco o hacer una inversión más grande?

Con esa info te armo un combo personalizado que sea perfecto para tu situación 💎"""
            
            # Actualizar estado
            conversation.set_awaiting_response("personal_questions", "información sobre experiencia y preferencias", {
                "step": "collecting_profile",
                "questions_asked": ["experience", "preferences", "budget"]
            })
            
        elif is_negative:
            response = """Dale, sin problema! Quedamos acá por si cambiás de opinión.

¿Te interesa que te muestre algún producto específico o tenés alguna consulta sobre Royal? 😊"""
            conversation.clear_awaiting_response()
        else:
            response = f"""Perfecto! Entiendo que querés {user_message}.

Para darte la mejor recomendación personalizada, contame:
• ¿Tenés experiencia vendiendo o sería tu primera vez?
• ¿Qué productos te gustan más?

Así te armo algo ideal para vos 💎"""
            
            conversation.set_awaiting_response("personal_questions", "información sobre experiencia y preferencias")
    
    elif conversation.pending_action == "personal_questions":
        response = f"""Genial, {user_message}! Con esa info ya tengo una mejor idea.

Basándome en lo que me contaste, te recomiendo arrancar con:

🎯 **COMBO PERSONALIZADO SUGERIDO:**
• Joyas de plata 925 (siempre tienen demanda)
• Algunos productos de maquillaje (alta rotación)  
• Mix de accesorios para completar

¿Te parece que vayamos por ahí o preferís enfocarte en una sola categoría primero? 💎"""
        
        conversation.clear_awaiting_response()
        conversation.is_entrepreneur = True
        conversation.update_user_profile("experience_feedback", user_message)
    
    else:
        # Acción no reconocida, respuesta genérica
        response = f"""Gracias por tu respuesta: "{user_message}".

¿En qué más te puedo ayudar? 😊"""
        conversation.clear_awaiting_response()
    
    # Registrar respuesta del bot
    conversation.add_interaction("assistant", response[:100] + "..." if len(response) > 100 else response, {
        "continuity_handled": True,
        "original_action": conversation.pending_action
    })
    
    logger.info(f"✅ Continuidad manejada exitosamente")
    return response

@function_tool
async def set_awaiting_user_response(wrapper: RunContextWrapper[RoyalAgentContext], pending_action: str, question_asked: str) -> str:
    """
    Marca que el bot acaba de hacer una pregunta y está esperando respuesta específica del usuario.
    Usado para mantener continuidad conversacional.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"⏳ SET_AWAITING_USER_RESPONSE: {pending_action}")
    logger.info(f"   Pregunta: {question_asked}")
    
    conversation.set_awaiting_response(pending_action, question_asked)
    
    return f"✅ Marcado como esperando respuesta para: {pending_action}"

@function_tool
async def search_categories_by_query(
    wrapper: RunContextWrapper[RoyalAgentContext], 
    user_query: str
) -> str:
    """
    Busca categorías de productos relevantes en el catálogo completo y devuelve URLs directas.
    Útil cuando el usuario pregunta sobre disponibilidad de tipos de productos.
    
    Args:
        user_query: Consulta del usuario (ej: "tienen lentes de sol", "anillos de plata")
    """
    
    context = wrapper.context
    conversation = context.conversation
    user_id = context.user_id
    
    logger.info(f"🔍 SEARCH_CATEGORIES_BY_QUERY para usuario: {user_id}")
    logger.info(f"   Query: {user_query}")
    
    try:
        # Buscar categorías relevantes
        matches = find_categories(user_query, max_results=6)
        
        if not matches:
            # Si no encuentra categorías específicas, activar HITL para consulta personalizada
            conversation.add_interaction("system", "Información faltante: category_search")
            conversation.update_user_profile("needs_human_assistance", True)
            conversation.current_state = "pending_human_assistance"
            
            import random
            fallback_responses = [
                f"Dale, dejame que chequeo puntualmente si tenemos {user_query} y te confirmo con toda la info 👍",
                f"Tengo que verificar específicamente sobre {user_query}. Dame un momento que te traigo las opciones disponibles 👍",
                f"Déjame que reviso {user_query} en detalle y te paso la información completa 👍"
            ]
            return random.choice(fallback_responses)
        
        # Registrar categorías encontradas en el contexto
        conversation.add_interaction("assistant", f"Mostré {len(matches)} categorías relacionadas con: {user_query}")
        
        # Guardar categorías en el contexto como productos de referencia
        for match in matches[:3]:  # Máximo 3 para no sobrecargar contexto
            category_ref = ProductReference(
                name=match.category.name,
                price="Ver productos", 
                id="",
                permalink=match.category.url,
                category="category_link"
            )
            conversation.add_product_reference(category_ref)
        
        # Actualizar estado de conversación
        conversation.current_state = "browsing_categories"
        conversation.add_interaction("assistant", f"Mostré categorías para: {user_query}")
        
        # Formatear respuesta usando la función del category_matcher
        formatted_response = format_categories_for_user(matches, max_display=5)
        
        # Agregar contexto personalizado argentino
        if len(matches) > 1:
            formatted_response += f"\n\n💡 **Tip:** Podés explorar cualquiera de estos links y si te gusta algo específico, decime cuál te interesa y te ayudo con más detalles."
        else:
            formatted_response += f"\n\n💡 **¡Dale!** Explorá el link y si ves algo que te gusta, decime y te doy más info específica."
        
        logger.info(f"✅ {len(matches)} categorías encontradas para '{user_query}'")
        return formatted_response
        
    except Exception as e:
        logger.error(f"❌ Error buscando categorías: {e}")
        
        # Fallback a HITL en caso de error
        conversation.add_interaction("system", "Error técnico: category_search")
        conversation.update_user_profile("needs_human_assistance", True)
        conversation.current_state = "pending_human_assistance"
        
        import random
        error_responses = [
            "Uy, se me complicó el sistema de búsqueda. Dame un momento que lo soluciono y te ayudo 👍",
            "Tengo un problemita técnico buscando categorías. Ya lo arreglo y te traigo toda la info 👍"
        ]
        return random.choice(error_responses)

@function_tool
async def analyze_user_message_and_update_profile(wrapper: RunContextWrapper[RoyalAgentContext], user_message: str) -> str:
    """
    HERRAMIENTA CRÍTICA: Analiza automáticamente el mensaje del usuario para extraer 
    información del perfil y evitar preguntas redundantes.
    """
    
    context = wrapper.context
    conversation = context.conversation
    user_id = context.user_id
    
    logger.info(f"🧠 ANALYZE_USER_MESSAGE para usuario: {user_id}")
    logger.info(f"   Mensaje: {user_message}")
    
    message_lower = user_message.lower()
    profile_updates = []
    
    # 1. DETECCIÓN DE NIVEL DE EXPERIENCIA
    beginner_patterns = [
        "todavía no vendí", "todavia no vendi", "nunca vendí", "nunca vendi", 
        "no vendí nada", "no vendi nada", "primera vez", "primer emprendimiento",
        "empezar", "comenzar", "arrancar", "no tengo experiencia", 
        "soy nuevo", "soy nueva", "recién empiezo", "recien empiezo"
    ]
    
    experienced_patterns = [
        "ya vendí", "ya vendi", "tengo experiencia", "vengo vendiendo", 
        "hace tiempo que vendo", "soy revendedor", "soy revendedora",
        "mi negocio", "mis clientes", "mis ventas", "renovar stock"
    ]
    
    restocking_patterns = [
        "renovar stock", "reponer stock", "necesito más", "se me acabó",
        "se me acabo", "quiero más productos", "restock"
    ]
    
    if any(pattern in message_lower for pattern in beginner_patterns):
        if not conversation.experience_level:  # Solo actualizar si no está definido
            conversation.update_user_profile("experience_level", "empezando")
            conversation.is_entrepreneur = True
            profile_updates.append("Experiencia: principiante/empezando")
            logger.info(f"📊 Detectado: usuario principiante")
    
    elif any(pattern in message_lower for pattern in experienced_patterns):
        if not conversation.experience_level:
            conversation.update_user_profile("experience_level", "experimentado") 
            conversation.is_entrepreneur = True
            profile_updates.append("Experiencia: experimentado")
            logger.info(f"📊 Detectado: usuario experimentado")
    
    elif any(pattern in message_lower for pattern in restocking_patterns):
        if not conversation.experience_level:
            conversation.update_user_profile("experience_level", "renovando_stock")
            conversation.is_entrepreneur = True
            profile_updates.append("Experiencia: renovando stock")
            logger.info(f"📊 Detectado: usuario renovando stock")
    
    # 2. DETECCIÓN DE INTERESES DE PRODUCTO
    product_interests = []
    
    if any(word in message_lower for word in ["joya", "joyas", "anillo", "collar", "pulsera", "aros"]):
        product_interests.append("joyas")
    if any(word in message_lower for word in ["maquillaje", "makeup", "labial", "sombra", "base"]):
        product_interests.append("maquillaje") 
    if any(word in message_lower for word in ["ropa", "indumentaria", "remera", "vestido", "pantalón"]):
        product_interests.append("indumentaria")
    if any(word in message_lower for word in ["bijou", "bijouterie", "accesorios"]):
        product_interests.append("bijouterie")
    if any(word in message_lower for word in ["reloj", "relojes"]):
        product_interests.append("relojes")
    
    for interest in product_interests:
        if interest not in conversation.product_interests:
            conversation.product_interests.append(interest)
            profile_updates.append(f"Interés detectado: {interest}")
            logger.info(f"📊 Detectado interés: {interest}")
    
    # 3. DETECCIÓN DE PRESUPUESTO
    budget_patterns = [
        (r"(\d+)k", "aproximadamente {} mil pesos"),
        (r"\$(\d+\.?\d*)", "${} pesos"),
        (r"(\d+)\s*mil", "{} mil pesos"),
        (r"poco.*dinero", "presupuesto ajustado"),
        (r"mucha.*plata", "presupuesto amplio"),
    ]
    
    import re
    for pattern, description in budget_patterns:
        match = re.search(pattern, message_lower)
        if match and not conversation.budget_range:
            if match.groups():
                budget_info = description.format(match.group(1))
            else:
                budget_info = description
            conversation.budget_range = budget_info
            profile_updates.append(f"Presupuesto: {budget_info}")
            logger.info(f"📊 Detectado presupuesto: {budget_info}")
            break
    
    # 4. DETECCIÓN DE INTENCIÓN
    if any(word in message_lower for word in ["emprender", "emprendimiento", "negocio", "revender"]):
        if not conversation.user_intent:
            conversation.user_intent = "emprendedor"
            conversation.is_entrepreneur = True
            profile_updates.append("Intención: emprendedor")
            logger.info(f"📊 Detectado: intención emprendedora")
    
    # Registrar actualizaciones en el historial
    if profile_updates:
        conversation.add_interaction("system", f"Perfil actualizado automáticamente: {', '.join(profile_updates)}", {
            "auto_analysis": True,
            "updates": profile_updates
        })
        
        result = f"✅ Perfil actualizado automáticamente:\n" + "\n".join(f"• {update}" for update in profile_updates)
        logger.info(f"✅ {len(profile_updates)} actualizaciones de perfil realizadas")
        return result
    else:
        return "✅ Mensaje analizado, no se detectaron actualizaciones de perfil necesarias"

@function_tool
async def should_ask_about_experience(wrapper: RunContextWrapper[RoyalAgentContext]) -> str:
    """
    Valida si es necesario preguntar sobre experiencia del usuario o si ya se conoce.
    CRÍTICO: Evita preguntas redundantes.
    """
    
    context = wrapper.context
    conversation = context.conversation
    
    logger.info(f"🤔 SHOULD_ASK_ABOUT_EXPERIENCE para usuario: {context.user_id}")
    logger.info(f"   Experience level actual: {conversation.experience_level}")
    logger.info(f"   Is entrepreneur: {conversation.is_entrepreneur}")
    
    # Si ya tenemos el nivel de experiencia, NO preguntar
    if conversation.experience_level:
        response = f"❌ NO PREGUNTAR - Ya conocemos la experiencia del usuario: {conversation.experience_level}"
        logger.info(response)
        return response
    
    # Revisar historial de interacciones por pistas
    beginner_hints = [
        "todavía no vendí", "todavia no vendi", "nunca vendí", "primera vez",
        "empezar", "comenzar", "arrancar", "soy nuevo", "soy nueva"
    ]
    
    experienced_hints = [
        "ya vendí", "tengo experiencia", "vengo vendiendo", "mi negocio", 
        "mis clientes", "renovar stock"
    ]
    
    recent_messages = conversation.interaction_history[-3:]  # Últimos 3 mensajes
    all_text = " ".join([msg["message"].lower() for msg in recent_messages if msg["role"] == "user"])
    
    if any(hint in all_text for hint in beginner_hints):
        # Actualizar automáticamente y no preguntar
        conversation.update_user_profile("experience_level", "empezando")
        conversation.is_entrepreneur = True
        response = "❌ NO PREGUNTAR - Detectado automáticamente: principiante (basado en mensajes recientes)"
        logger.info(response)
        return response
    
    if any(hint in all_text for hint in experienced_hints):
        conversation.update_user_profile("experience_level", "experimentado")
        conversation.is_entrepreneur = True
        response = "❌ NO PREGUNTAR - Detectado automáticamente: experimentado (basado en mensajes recientes)"
        logger.info(response)
        return response
    
    # Si no tenemos información, SÍ es válido preguntar
    response = "✅ SÍ PREGUNTAR - No tenemos información sobre experiencia del usuario"
    logger.info(response)
    return response

def create_contextual_tools():
    """Crea todas las herramientas contextuales"""
    
    tools = [
        # HITL HABILITADO
        detect_user_frustration,
        handle_missing_information_hitl,
        check_mcp_connectivity_and_fallback,
        escalate_to_human_support,
        
        # Herramientas contextuales principales
        get_context_summary,
        get_product_info_with_context,
        get_combos_with_context,
        process_purchase_intent,
        update_user_profile,
        get_recommendations_with_context,
        clear_conversation_context,
        handle_conversation_continuity,
        set_awaiting_user_response,
        analyze_user_message_and_update_profile,
        should_ask_about_experience,
        
        # Búsqueda de categorías
        search_categories_by_query
    ]
    
    logger.info(f"✅ Contextual Tools creadas: {len(tools)} herramientas disponibles (HITL + Categorías habilitado)")
    return tools 