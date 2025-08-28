# Training MCP Tools para Royal Bot v2
# Herramientas especializadas en contenido de entrenamiento

import os
import asyncio
from typing import Dict, List, Any, Optional
from agents import function_tool  # type: ignore
import logging

# Import the training parser
try:
    from .training_parser import training_parser, ConversationExample, TrainingRule, FAQ
    TRAINING_PARSER_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Training Parser importado correctamente")
except ImportError as e:
    TRAINING_PARSER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Error importando Training Parser: {str(e)}")

@function_tool
async def get_combo_recommendations(client_experience: str, client_context: str = "") -> str:
    """
    Obtiene recomendaciones de combos según experiencia y contexto del cliente
    
    Args:
        client_experience: "empezando" | "experimentado" | "renovando_stock" | "indeciso"
        client_context: contexto adicional de la conversación
    """
    
    logger.info(f"🎯 GET_COMBO_RECOMMENDATIONS llamada:")
    logger.info(f"   client_experience: '{client_experience}'")
    logger.info(f"   client_context: '{client_context}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de entrenamiento no disponible. Consultá nuestros combos en https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/"
    
    try:
        # Mapear experiencia a escenarios
        scenario_map = {
            'empezando': 'cliente_indeciso',
            'indeciso': 'cliente_indeciso',
            'experimentado': 'cliente_experimentado',
            'renovando_stock': 'cliente_experimentado'
        }
        
        scenario = scenario_map.get(client_experience.lower(), 'cliente_indeciso')
        
        # Obtener ejemplo de conversación relevante
        example = training_parser.get_conversation_example_by_scenario(scenario)
        
        # Obtener reglas específicas para combos
        combo_rules = training_parser.get_rules_by_category('combos')
        critical_rules = [rule for rule in combo_rules if rule.rule_type == "CRITICO"]
        
        # Obtener beneficios de combos
        benefits = training_parser.get_combo_benefits()
        combo_types = training_parser.get_combo_types()
        
        # Construir respuesta personalizada
        response = f"🎯 **Recomendación de Combos para Cliente {client_experience.title()}**\n\n"
        
        if example:
            response += f"📝 **Enfoque recomendado:**\n"
            response += f"Basándome en el entrenamiento, para un cliente que {client_experience}, "
            response += f"el enfoque debe ser:\n\n"
            response += f"*Ejemplo de respuesta ideal:*\n"
            response += f'"{example.royalia_response[:200]}..."\n\n'
        
        if critical_rules:
            response += f"⚠️ **Reglas Críticas a Seguir:**\n"
            for rule in critical_rules[:3]:  # Top 3 reglas críticas
                response += f"• {rule.description}\n"
            response += "\n"
        
        if benefits:
            response += f"💎 **Beneficios Clave a Mencionar:**\n"
            for benefit in benefits[:4]:  # Top 4 beneficios
                response += f"• {benefit}\n"
            response += "\n"
        
        if combo_types:
            response += f"🛍️ **Tipos de Combos Disponibles:**\n"
            for combo_type in combo_types:
                response += f"• Combos de {combo_type.title()}\n"
            response += "\n"
        
        # Enlaces específicos según experiencia
        response += f"🔗 **Enlaces Recomendados:**\n"
        if client_experience.lower() in ['empezando', 'indeciso']:
            response += "• Combos Emprendedores: https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/\n"
            response += "• Combos de Bijou (económicos): https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/combo-emprendedor-bijou/\n"
        else:
            response += "• Combos de Joyas de Plata: https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/combo-emprendedor-joyas/combo-emprendedor-plata/\n"
            response += "• Combos Completos: https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/combo-emprendedor-joyas/combo-emprendedor-plata/combos-completos/\n"
        
        logger.info(f"✅ Combo recommendations generadas exitosamente")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en get_combo_recommendations: {str(e)}")
        return f"Hubo un problema obteniendo las recomendaciones de combos. Te paso el enlace general: https://royalmayorista.com.ar/categoria-producto/combo-emprendedor/"

@function_tool
async def get_conversation_example(scenario: str, user_message_context: str = "") -> str:
    """
    Obtiene ejemplos de conversación para escenarios específicos
    
    Args:
        scenario: "cliente_indeciso" | "cliente_experimentado" | "dudas_confiabilidad" | "pregunta_catalogo" | "pregunta_minimo" | "pregunta_envio"
        user_message_context: contexto del mensaje del usuario para mejor matching
    """
    
    logger.info(f"💬 GET_CONVERSATION_EXAMPLE llamada:")
    logger.info(f"   scenario: '{scenario}'")
    logger.info(f"   user_message_context: '{user_message_context}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de entrenamiento no disponible"
    
    try:
        # Buscar ejemplo específico
        example = training_parser.get_conversation_example_by_scenario(scenario)
        
        if not example and user_message_context:
            # Buscar por contexto si no encuentra por escenario
            search_results = training_parser.search_training_content(user_message_context)
            if search_results['examples']:
                example = search_results['examples'][0]
        
        if example:
            response = f"💬 **Ejemplo de Conversación - {scenario.replace('_', ' ').title()}**\n\n"
            response += f"**Usuario dice:** {example.user_message}\n\n"
            response += f"**Royalía responde:** {example.royalia_response}\n\n"
            response += f"**Contexto:** {example.context}\n\n"
            
            # Agregar reglas relacionadas
            related_rules = training_parser.get_rules_by_category(example.context)
            if related_rules:
                response += f"📋 **Reglas Relacionadas:**\n"
                for rule in related_rules[:2]:
                    response += f"• {rule.description}\n"
            
            logger.info(f"✅ Conversation example encontrado")
            return response
        else:
            logger.warning(f"⚠️ No se encontró ejemplo para scenario: {scenario}")
            return f"No encontré un ejemplo específico para '{scenario}'. Te recomiendo usar un enfoque natural y seguir las reglas generales de entrenamiento."
    
    except Exception as e:
        logger.error(f"❌ Error en get_conversation_example: {str(e)}")
        return "Hubo un problema obteniendo el ejemplo de conversación"

@function_tool
async def get_training_rules(topic: str, rule_type: str = "all") -> str:
    """
    Obtiene reglas específicas del entrenamiento
    
    Args:
        topic: "combos" | "productos" | "general"
        rule_type: "CRITICO" | "IMPORTANTE" | "ESPECIFICO" | "all"
    """
    
    logger.info(f"📋 GET_TRAINING_RULES llamada:")
    logger.info(f"   topic: '{topic}'")
    logger.info(f"   rule_type: '{rule_type}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de entrenamiento no disponible"
    
    try:
        # Obtener reglas según topic
        if topic.lower() == "combos":
            rules = training_parser.get_rules_by_category('combos')
        elif topic.lower() == "productos":
            rules = training_parser.get_rules_by_category('productos')
        else:
            # Obtener todas las reglas
            rules = training_parser.training_rules
        
        # Filtrar por tipo de regla
        if rule_type.upper() != "ALL":
            rules = [rule for rule in rules if rule.rule_type == rule_type.upper()]
        
        if not rules:
            return f"No encontré reglas específicas para '{topic}' del tipo '{rule_type}'"
        
        response = f"📋 **Reglas de Entrenamiento - {topic.title()}**\n\n"
        
        # Agrupar por tipo de regla
        rules_by_type = {}
        for rule in rules:
            if rule.rule_type not in rules_by_type:
                rules_by_type[rule.rule_type] = []
            rules_by_type[rule.rule_type].append(rule)
        
        # Mostrar por orden de importancia
        order = ["CRITICO", "IMPORTANTE", "ESPECIFICO", "GENERAL"]
        
        for rule_type_key in order:
            if rule_type_key in rules_by_type:
                icon = "🚨" if rule_type_key == "CRITICO" else "⚠️" if rule_type_key == "IMPORTANTE" else "📌"
                response += f"{icon} **{rule_type_key}:**\n"
                
                for rule in rules_by_type[rule_type_key][:5]:  # Máximo 5 por tipo
                    response += f"• {rule.description}\n"
                response += "\n"
        
        logger.info(f"✅ Training rules obtenidas: {len(rules)} reglas")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en get_training_rules: {str(e)}")
        return "Hubo un problema obteniendo las reglas de entrenamiento"

@function_tool
async def get_faq_response(question_topic: str) -> str:
    """
    Obtiene respuesta de FAQ según el tema de la pregunta
    
    Args:
        question_topic: tema de la pregunta (ej: "minimo", "envio", "catalogo", "pago", etc.)
    """
    
    logger.info(f"❓ GET_FAQ_RESPONSE llamada:")
    logger.info(f"   question_topic: '{question_topic}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de entrenamiento no disponible"
    
    try:
        # Buscar FAQ por topic
        faq = training_parser.get_faq_by_topic(question_topic)
        
        if faq:
            response = f"❓ **FAQ - {question_topic.title()}**\n\n"
            response += f"**P:** {faq.question}\n\n"
            response += f"**R:** {faq.answer}\n\n"
            response += f"*Fuente: {faq.category}*"
            
            logger.info(f"✅ FAQ encontrada")
            return response
        else:
            # Si no encuentra FAQ exacta, buscar en todo el contenido
            search_results = training_parser.search_training_content(question_topic)
            
            if search_results['faqs']:
                faq = search_results['faqs'][0]
                response = f"❓ **FAQ Relacionada - {question_topic.title()}**\n\n"
                response += f"**P:** {faq.question}\n\n"
                response += f"**R:** {faq.answer}\n\n"
                response += f"*Fuente: {faq.category}*"
                
                logger.info(f"✅ FAQ relacionada encontrada")
                return response
            else:
                logger.warning(f"⚠️ No se encontró FAQ para: {question_topic}")
                return f"No encontré una respuesta específica para '{question_topic}' en las FAQs. Te recomiendo consultar la información general o contactar directamente."
    
    except Exception as e:
        logger.error(f"❌ Error en get_faq_response: {str(e)}")
        return "Hubo un problema obteniendo la respuesta FAQ"

@function_tool
async def validate_response_against_training(message: str, context: str = "") -> str:
    """
    Valida si una respuesta cumple con las reglas de entrenamiento
    
    Args:
        message: mensaje/respuesta a validar
        context: contexto de la conversación
    """
    
    logger.info(f"✅ VALIDATE_RESPONSE_AGAINST_TRAINING llamada:")
    logger.info(f"   message length: {len(message)}")
    logger.info(f"   context: '{context}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de validación no disponible"
    
    try:
        validation_result = {
            'is_valid': True,
            'violations': [],
            'suggestions': [],
            'score': 100
        }
        
        message_lower = message.lower()
        
        # Validar palabras prohibidas
        mentorship_data = training_parser.get_mentorship_personality()
        if 'forbidden_words' in mentorship_data:
            forbidden_words = mentorship_data['forbidden_words']
            for word in forbidden_words:
                if word.lower() in message_lower:
                    validation_result['is_valid'] = False
                    validation_result['violations'].append(f'Palabra prohibida encontrada: "{word}"')
                    validation_result['score'] -= 10
        
        # Validar reglas críticas
        critical_rules = training_parser.get_critical_rules()
        for rule in critical_rules:
            # Validaciones específicas según la regla
            if 'siempre ofrecer combos' in rule.description.lower():
                if 'empezando' in context.lower() and 'combo' not in message_lower:
                    validation_result['suggestions'].append('Se recomienda ofrecer combos a clientes que están empezando')
                    validation_result['score'] -= 5
            
            elif 'nunca ofrecer combos sin explicar' in rule.description.lower():
                if 'combo' in message_lower and 'beneficio' not in message_lower:
                    validation_result['suggestions'].append('Al ofrecer combos, siempre explicar los beneficios')
                    validation_result['score'] -= 5
        
        # Validar personalidad argentina con variedad
        argentine_indicators = [
            'mirá', 'bárbaro', 'genial', 'joya', 'posta', 'claro', 'perfecto', 
            'buenísimo', 'excelente', 'obvio', 'tranquila', 'laburo', 'ojo', 
            'che', 'vos', 'tenés', 'querés', 'podés', 'dale'  # dale al final
        ]
        has_argentine_tone = any(indicator in message_lower for indicator in argentine_indicators)
        
        # Detectar abuso de "dale"
        dale_count = message_lower.count('dale')
        if dale_count > 1:
            validation_result['suggestions'].append('Evitar usar "dale" múltiples veces. Variar con: "Perfecto", "Claro", "Excelente"')
            validation_result['score'] -= 5
        
        if not has_argentine_tone and len(message) > 50:
            validation_result['suggestions'].append('Considerar usar más expresiones argentinas variadas para mantener el tono local')
            validation_result['score'] -= 3
        
        # Preparar respuesta
        if validation_result['is_valid'] and validation_result['score'] >= 90:
            response = f"✅ **Respuesta VÁLIDA** (Puntaje: {validation_result['score']}/100)\n\n"
            response += "La respuesta cumple con las reglas de entrenamiento."
        else:
            response = f"⚠️ **Respuesta con Observaciones** (Puntaje: {validation_result['score']}/100)\n\n"
        
        if validation_result['violations']:
            response += f"🚨 **Violaciones Encontradas:**\n"
            for violation in validation_result['violations']:
                response += f"• {violation}\n"
            response += "\n"
        
        if validation_result['suggestions']:
            response += f"💡 **Sugerencias de Mejora:**\n"
            for suggestion in validation_result['suggestions']:
                response += f"• {suggestion}\n"
        
        logger.info(f"✅ Validation completada. Score: {validation_result['score']}/100")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en validate_response_against_training: {str(e)}")
        return "Hubo un problema validando la respuesta"

@function_tool
async def get_personality_guidance() -> str:
    """
    Obtiene orientación sobre la personalidad y tono de Royalía
    """
    
    logger.info("🎭 GET_PERSONALITY_GUIDANCE llamada")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de entrenamiento no disponible"
    
    try:
        personality = training_parser.get_mentorship_personality()
        
        response = "🎭 **Guía de Personalidad Royalía**\n\n"
        
        if 'personality_traits' in personality and personality['personality_traits']:
            response += "✨ **Rasgos de Personalidad:**\n"
            for trait in personality['personality_traits'][:5]:
                response += f"• {trait}\n"
            response += "\n"
        
        if 'approach' in personality and personality['approach']:
            response += "🤝 **Enfoque de Mentoría:**\n"
            for approach in personality['approach'][:3]:
                response += f"• {approach}\n"
            response += "\n"
        
        if 'forbidden_words' in personality and personality['forbidden_words']:
            response += "🚫 **Palabras a Evitar:**\n"
            for word in personality['forbidden_words'][:10]:
                response += f"• {word}\n"
            response += "\n"
        
        response += "🎯 **Palabras Recomendadas (con VARIACIÓN):**\n"
        response += "• **Inicios variados**: Perfecto, Claro, Te explico, Bárbaro, Genial, Excelente, Buenísimo\n"
        response += "• **Argentinismos**: mirá, ojo, posta, joya, tranquila, laburo, obvio\n"
        response += "• **ROTAR 'dale'**: usar máximo 1 vez cada 5 respuestas\n"
        response += "• Evitar formalidad excesiva\n"
        response += "• Mantener tono argentino natural y amigable\n"
        
        logger.info("✅ Personality guidance generada")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en get_personality_guidance: {str(e)}")
        return "Hubo un problema obteniendo la guía de personalidad"

@function_tool
async def get_basic_company_info(info_type: str) -> str:
    """
    Obtiene información básica de la empresa con enlaces según el tipo solicitado
    
    Args:
        info_type: "catalogo" | "minimo" | "envio" | "pago" | "confiabilidad" | "local" | "general"
    """
    
    logger.info(f"🏢 GET_BASIC_COMPANY_INFO llamada:")
    logger.info(f"   info_type: '{info_type}'")
    
    # Información básica con enlaces específicos según el entrenamiento
    basic_info = {
        "catalogo": {
            "response": "Te paso nuestro catálogo mayorista https://royalmayorista.com.ar/shop/ En Royal vas a encontrar joyas, relojes, lentes, bijouterie, maquillaje e indumentaria, todo al por mayor para que tengas más variedad y más ventas. Además, te acompaño como mentora para ayudarte a organizarte, armar promociones o lo que necesites en tu emprendimiento. Contame un poco de vos, ¿ya tenés experiencia revendiendo o estás por empezar tu emprendimiento?",
            "links": ["https://royalmayorista.com.ar/shop/"]
        },
        "minimo": {
            "response": "El mínimo es de $40.000, y con compras desde $100.000 te hacemos el envío gratis. Además, cuando comprás en Royal no solo accedés a productos de calidad a precios mayoristas, sino que te acompaño como mentora para ayudarte a hacer crecer tu emprendimiento: desde ideas de publicaciones hasta planificación de ventas. ¿Ya estás vendiendo o estás por arrancar tu negocio?",
            "links": []
        },
        "envio": {
            "response": "Sí, hacemos envíos a todo el país. Gratis a partir de $100.000 de compra. Lo mejor es que en Royal no solo conseguís productos, sino que tenés una mentora a disposición. Si querés, te puedo ayudar a organizar tu semana de ventas o armar tu primera oferta para tus redes. ¿Desde qué ciudad estás escribiendo? ¿Ya tenés redes para tu emprendimiento?",
            "links": []
        },
        "pago": {
            "response": "Sí. Podés pagar con tarjeta de crédito o débito. También transferencia bancaria sin recargo. Además, te acompaño en el proceso de venta: si querés te puedo ayudar a armar promos según los métodos de pago que elijan tus clientas, para que aproveches al máximo cada venta. ¿Ya tenés armado tu catálogo personalizado para vender?",
            "links": []
        },
        "confiabilidad": {
            "response": "Royal tiene 7 años en el mercado, más de 30.000 emprendedoras ya trabajan con nosotros, tenemos locales físicos en Córdoba capital y redes verificadas. Además, te acompaño en todo el proceso. Mi trabajo es ayudarte a que puedas emprender con seguridad y confianza. Incluso te puedo ayudar a organizar publicaciones, precios, ideas para vender mejor. ¿Ya estuviste emprendiendo antes o sería tu primer negocio?",
            "links": []
        },
        "local": {
            "response": "Sí. Podés retirar en nuestros locales en Córdoba Capital. Además de los productos, tenés mi acompañamiento como mentora para ayudarte a crecer con tu emprendimiento. Ideas, planificación, contenido, promociones, lo que necesites. ¿Desde qué zona sos? ¿Ya estás vendiendo por redes o por WhatsApp?",
            "links": []
        },
        "catalogo_sin_logo": {
            "response": "Sí. Te paso el enlace con el catálogo sin logo para que puedas ofrecer los productos a tus clientas: https://royalmayorista.com.ar/shop/ Si querés te puedo dar ideas de textos o historias para que vendas más con esas fotos. ¿Ya estás vendiendo por WhatsApp, Instagram o recién arrancás?",
            "links": ["https://royalmayorista.com.ar/shop/"]
        },
        "joyas_plata": {
            "response": "Te paso la categoría de joyas de plata 925: https://royalmayorista.com.ar/categoria-producto/royal-joyas/ Allí encontrarás aros, anillos, dijes, cadenas y pulseras, todos con certificado de autenticidad de Royal. Como mentora, también puedo ayudarte a planificar cómo presentar estas piezas, armar promociones o definir precios. ¿Ya vendés joyas por tu cuenta o estás armando tu emprendimiento?",
            "links": ["https://royalmayorista.com.ar/categoria-producto/royal-joyas/"]
        },
        "bijou": {
            "response": "Acá tenés nuestra categoría de insumos para bijou: https://royalmayorista.com.ar/categoria-producto/bijou/ Vas a encontrar bases, piedras, hilos, dijes y todo lo necesario para armar accesorios. Además, te puedo acompañar en la estructura de costos, armado de kits y estrategias de venta para bijouterie. ¿Qué te parece?",
            "links": ["https://royalmayorista.com.ar/categoria-producto/bijou/"]
        }
    }
    
    try:
        info = basic_info.get(info_type.lower())
        
        if info:
            response = f"📋 **Información de Royal - {info_type.title()}**\n\n"
            response += info['response']
            
            if info['links']:
                response += f"\n\n🔗 **Enlaces:**\n"
                for link in info['links']:
                    response += f"• {link}\n"
            
            logger.info(f"✅ Basic company info enviada para: {info_type}")
            return response
        else:
            # Información general si no encuentra tipo específico
            general_response = "En Royal tenemos productos al por mayor: joyas, relojes, maquillaje, indumentaria y más. "
            general_response += "Mínimo $40.000, envío gratis desde $100.000. "
            general_response += "Catálogo completo: https://royalmayorista.com.ar/shop/ "
            general_response += "¿En qué te puedo ayudar específicamente?"
            
            logger.info(f"✅ Basic company info general enviada")
            return general_response
            
    except Exception as e:
        logger.error(f"❌ Error en get_basic_company_info: {str(e)}")
        return "Hubo un problema obteniendo la información. Te recomiendo visitar https://royalmayorista.com.ar/shop/ para ver nuestro catálogo completo."

@function_tool
async def search_training_content(query: str) -> str:
    """
    Busca contenido específico en todo el material de entrenamiento
    
    Args:
        query: término de búsqueda
    """
    
    logger.info(f"🔍 SEARCH_TRAINING_CONTENT llamada:")
    logger.info(f"   query: '{query}'")
    
    if not TRAINING_PARSER_AVAILABLE:
        return "Sistema de búsqueda no disponible"
    
    try:
        results = training_parser.search_training_content(query)
        
        response = f"🔍 **Resultados de Búsqueda: '{query}'**\n\n"
        
        total_results = sum(len(results[key]) for key in results.keys())
        
        if total_results == 0:
            return f"No encontré contenido relacionado con '{query}' en el material de entrenamiento."
        
        response += f"📊 **Total de resultados encontrados:** {total_results}\n\n"
        
        if results['examples']:
            response += f"💬 **Ejemplos de Conversación ({len(results['examples'])}):**\n"
            for example in results['examples'][:2]:  # Mostrar máximo 2
                response += f"• *{example.user_message[:60]}...* → *{example.royalia_response[:80]}...*\n"
            response += "\n"
        
        if results['rules']:
            response += f"📋 **Reglas Relacionadas ({len(results['rules'])}):**\n"
            for rule in results['rules'][:3]:  # Mostrar máximo 3
                response += f"• {rule.description[:100]}...\n"
            response += "\n"
        
        if results['faqs']:
            response += f"❓ **FAQs Relacionadas ({len(results['faqs'])}):**\n"
            for faq in results['faqs'][:2]:  # Mostrar máximo 2
                response += f"• **P:** {faq.question[:60]}...\n"
                response += f"  **R:** {faq.answer[:80]}...\n"
            response += "\n"
        
        if results['links']:
            response += f"🔗 **Enlaces Relevantes ({len(results['links'])}):**\n"
            for link in results['links'][:3]:  # Mostrar máximo 3
                response += f"• {link}\n"
        
        logger.info(f"✅ Search completada. {total_results} resultados encontrados")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en search_training_content: {str(e)}")
        return f"Hubo un problema buscando '{query}' en el contenido de entrenamiento"

def create_training_tools():
    """Crea todas las herramientas de entrenamiento MCP"""
    
    tools = [
        get_combo_recommendations,
        get_conversation_example,
        get_training_rules,
        get_faq_response,
        get_basic_company_info,
        validate_response_against_training,
        get_personality_guidance,
        search_training_content
    ]
    
    logger.info(f"✅ Training Tools creadas: {len(tools)} herramientas disponibles")
    return tools

# Log de disponibilidad
if TRAINING_PARSER_AVAILABLE:
    logger.info("✅ Training MCP Tools completamente disponibles")
else:
    logger.error("❌ Training MCP Tools con funcionalidad limitada") 