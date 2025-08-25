"""
Instruction Builder para Royal Bot v2
Construye instrucciones dinámicas combinando personalidad, contexto y reglas
"""

from typing import Dict, List, Any, Optional
from .knowledge_system import get_knowledge_base
import logging

logger = logging.getLogger(__name__)


class InstructionBuilder:
    """
    Construye instrucciones dinámicas para el agente Royal.
    Combina personalidad base, contexto y protocolos desde el Knowledge Base.
    """
    
    def __init__(self):
        """Inicializa el builder con el Knowledge Base."""
        self.kb = get_knowledge_base()
        
    def build_base_instructions(self) -> str:
        """
        Construye las instrucciones base del agente.
        
        Returns:
            String con instrucciones base completas
        """
        personality = self.kb.get_personality()
        
        if not personality:
            logger.warning("⚠️ No se encontró personality data")
            return self._get_fallback_instructions()
        
        instructions = f"""
# IDENTIDAD Y PERSONALIDAD

Sos {personality.get('name', 'Royalia')}, {personality.get('role', 'asesora de Royal Company')}.
{personality.get('description', '')}

## Personalidad Argentina
"""
        
        # Agregar características de tono
        tone = personality.get('tone', {})
        for characteristic in tone.get('characteristics', []):
            instructions += f"- {characteristic}\n"
        
        # Palabras recomendadas
        if tone.get('recommended_words'):
            instructions += f"\nPalabras recomendadas: {', '.join(tone['recommended_words'])}\n"
        
        # Alternativas a "che"
        if tone.get('alternatives_to_che'):
            instructions += "\n## Alternativas al 'CHE' (muy coloquial):\n"
            for alt in tone['alternatives_to_che']:
                instructions += f"• {alt}\n"
        
        # Palabras prohibidas
        forbidden = personality.get('forbidden_words', [])
        if forbidden:
            instructions += f"\n## PALABRAS PROHIBIDAS - NUNCA USAR:\n{', '.join(forbidden)}\n"
        
        # Comportamientos críticos
        instructions += "\n# REGLAS DE COMPORTAMIENTO CRÍTICAS\n\n"
        for behavior in personality.get('critical_behaviors', []):
            instructions += f"• {behavior}\n"
        
        return instructions
    
    def build_company_context(self) -> str:
        """
        Construye el contexto de información de la empresa.
        
        Returns:
            String con información de la empresa
        """
        company = self.kb.get_company_info()
        
        if not company:
            return ""
        
        context = "\n# INFORMACIÓN CLAVE DE ROYAL\n\n"
        
        # Información general
        general = company.get('general', {})
        if general:
            context += f"""## ¿Qué es Royal?
{general.get('name', 'Royal Company')}, fundada en {general.get('founded', '2016')} y operativa desde {general.get('operational_since', '2017')}, 
{general.get('description', '')}. {general.get('products_summary', '')}.
"""
        
        # Ubicaciones
        locations = company.get('locations', {})
        if locations:
            context += "\n## Ubicación (Córdoba Capital):\n"
            for store in locations.get('stores', []):
                context += f"- {store['name']}: {store['address']}\n"
        
        # Horarios
        schedule = company.get('schedule', {})
        if schedule:
            context += f"""
## Horarios:
- Lunes a viernes: {schedule.get('weekdays', '')}
- Sábados: {schedule.get('saturdays', '')}
- Tienda online: {schedule.get('online_store', '')}
"""
        
        # Redes sociales
        social = company.get('social_media', {})
        if social:
            context += "\n## Redes Sociales:\n"
            if 'instagram' in social:
                ig = social['instagram']
                context += f"- Instagram: {ig.get('joyas', '')}, {ig.get('bijou', '')}, {ig.get('indumentaria', '')}\n"
            if 'facebook' in social:
                context += f"- Facebook: {social['facebook']}\n"
            if 'whatsapp' in social:
                context += f"- WhatsApp: {social['whatsapp']}\n"
        
        # Tipos de compra
        purchase_types = company.get('purchase_types', {})
        if purchase_types:
            context += "\n## Tipos de Compra:\n"
            
            # Mayorista
            wholesale = purchase_types.get('wholesale', {})
            if wholesale:
                context += f"""### Mayorista (Revendedores):
- Mínimo: ${wholesale.get('minimum', 0):,}
- {', '.join(wholesale.get('benefits', []))}
""".replace(",", ".")
            
            # Minorista
            retail = purchase_types.get('retail', {})
            if retail:
                context += f"""### Minorista:
- Sin mínimo de compra
- {', '.join(retail.get('benefits', []))}
"""
        
        # Envíos
        shipping = company.get('shipping', {})
        if shipping:
            costs = shipping.get('costs', {})
            times = shipping.get('delivery_times', {})
            context += f"""
## Envíos:
- {shipping.get('provider', '')} ({shipping.get('insurance', '')})
- Córdoba Capital: ${costs.get('cordoba_capital', 0):,}
- Resto del país: ${costs.get('rest_of_country', 0):,}
- GRATIS en pedidos +${costs.get('free_shipping_threshold', 0):,}
- Tiempos: Córdoba {times.get('cordoba', {}).get('description', '') if isinstance(times.get('cordoba'), dict) else times.get('cordoba', '')}, Nacional {times.get('national', {}).get('description', '') if isinstance(times.get('national'), dict) else times.get('national', '')}
""".replace(",", ".")
        
        # Pagos
        payment = company.get('payment_methods', {})
        if payment:
            context += "\n## Pagos:\n"
            
            if payment.get('credit_card', {}).get('enabled'):
                installments = payment['credit_card'].get('installments', 3)
                context += f"- Tarjeta (hasta {installments} cuotas sin interés)\n"
            
            if payment.get('bank_transfer', {}).get('enabled'):
                bt = payment['bank_transfer']
                context += f"- Transferencia: CBU {bt.get('cbu', '')}, Alias: {bt.get('alias', '')}\n"
            
            if payment.get('cash', {}).get('enabled'):
                context += f"- Efectivo en locales\n"
            
            if payment.get('deposit_system', {}).get('enabled'):
                deposit = payment['deposit_system']
                context += f"- Sistema de seña: ${deposit.get('amount', 0):,} ({deposit.get('description', '')})\n".replace(",", ".")
        
        return context
    
    def build_conversation_protocols(self, user_type: Optional[str] = None) -> str:
        """
        Construye protocolos de conversación específicos.
        
        Args:
            user_type: Tipo de usuario (new_entrepreneurs, experienced_sellers, etc.)
            
        Returns:
            String con protocolos de conversación
        """
        personality = self.kb.get_personality()
        
        if not personality:
            return ""
        
        protocols = "\n# PROTOCOLOS DE CONVERSACIÓN\n\n"
        
        # Obtener approach según tipo de usuario
        if user_type:
            approach = self.kb.get_conversation_approach(user_type)
            if approach:
                protocols += f"## Enfoque para {user_type.replace('_', ' ').title()}:\n"
                protocols += f"- Prioridad: {approach.get('priority', 'normal')}\n"
                protocols += f"- Enfoque: {approach.get('approach', 'standard')}\n"
                
                # Preguntas requeridas
                if 'required_questions' in approach:
                    protocols += "\n### Preguntas Obligatorias:\n"
                    for question in approach['required_questions']:
                        protocols += f"• {question}\n"
                
                # Qué mencionar
                if 'must_mention' in approach:
                    protocols += "\n### Debe Mencionar:\n"
                    for item in approach['must_mention']:
                        protocols += f"• {item}\n"
        else:
            # Agregar todos los protocolos generales
            approaches = personality.get('conversation_approach', {})
            
            for user_type, approach in approaches.items():
                protocols += f"\n## {user_type.replace('_', ' ').title()}:\n"
                
                if approach.get('priority') == 'high':
                    protocols += "🚨 **PRIORIDAD ALTA** 🚨\n"
                
                protocols += f"- Enfoque: {approach.get('approach', 'standard')}\n"
                
                if 'required_questions' in approach:
                    protocols += "Preguntas obligatorias:\n"
                    for q in approach['required_questions']:
                        protocols += f"  • {q}\n"
                
                if 'must_mention' in approach:
                    protocols += "Debe mencionar:\n"
                    for m in approach['must_mention']:
                        protocols += f"  • {m}\n"
        
        # Agregar manejo de errores
        error_handling = personality.get('error_handling', {})
        if error_handling:
            protocols += "\n## Manejo de Situaciones:\n"
            for error_type, message in error_handling.items():
                protocols += f"- {error_type.replace('_', ' ').title()}: \"{message}\"\n"
        
        return protocols
    
    def build_contextual_instructions(
        self,
        user_context: Optional[Dict[str, Any]] = None,
        include_faqs: bool = False
    ) -> str:
        """
        Construye instrucciones contextuales basadas en la situación actual.
        
        Args:
            user_context: Contexto del usuario actual
            include_faqs: Si incluir FAQs en las instrucciones
            
        Returns:
            String con instrucciones contextualizadas
        """
        instructions = ""
        
        # Agregar contexto del usuario si existe
        if user_context:
            instructions += "\n# CONTEXTO DEL USUARIO ACTUAL\n\n"
            
            if user_context.get('is_entrepreneur'):
                instructions += "• El usuario es emprendedor\n"
                
            if user_context.get('experience_level'):
                instructions += f"• Nivel de experiencia: {user_context['experience_level']}\n"
                
            if user_context.get('product_interests'):
                interests = ", ".join(user_context['product_interests'])
                instructions += f"• Intereses: {interests}\n"
                
            if user_context.get('budget_range'):
                instructions += f"• Presupuesto: {user_context['budget_range']}\n"
                
            if user_context.get('recent_products'):
                instructions += f"• Productos vistos recientemente: {len(user_context['recent_products'])}\n"
        
        # Agregar FAQs si se solicita
        if include_faqs:
            faqs = self.kb.get_faq()
            if isinstance(faqs, list) and faqs:
                instructions += "\n# PREGUNTAS FRECUENTES DISPONIBLES\n\n"
                
                # Agrupar por categoría
                categories = {}
                for faq in faqs[:10]:  # Limitar a 10 FAQs
                    cat = faq.get('category', 'general')
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(faq)
                
                for cat, cat_faqs in categories.items():
                    instructions += f"\n## {cat.title()}:\n"
                    for faq in cat_faqs:
                        instructions += f"- {faq['question']}\n"
        
        return instructions
    
    def build_complete_instructions(
        self,
        user_type: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        include_company: bool = True,
        include_protocols: bool = True,
        include_faqs: bool = False
    ) -> str:
        """
        Construye instrucciones completas para el agente.
        
        Args:
            user_type: Tipo de usuario
            user_context: Contexto del usuario
            include_company: Si incluir información de la empresa
            include_protocols: Si incluir protocolos de conversación
            include_faqs: Si incluir FAQs
            
        Returns:
            String con todas las instrucciones
        """
        # Construir instrucciones base
        instructions = self.build_base_instructions()
        
        # Agregar información de la empresa
        if include_company:
            instructions += self.build_company_context()
        
        # Agregar protocolos de conversación
        if include_protocols:
            instructions += self.build_conversation_protocols(user_type)
        
        # Agregar contexto específico
        if user_context or include_faqs:
            instructions += self.build_contextual_instructions(user_context, include_faqs)
        
        # Agregar recordatorio final
        instructions += self._build_final_reminders()
        
        logger.info(f"📝 Instrucciones construidas: {len(instructions)} caracteres")
        return instructions
    
    def _build_final_reminders(self) -> str:
        """
        Construye recordatorios finales importantes.
        
        Returns:
            String con recordatorios finales
        """
        return """
# RECORDATORIOS FINALES

1. **SIEMPRE** mantener tono argentino informal
2. **NUNCA** inventar información - usar solo datos del Knowledge Base
3. **PRIORIZAR** emprendedores con enfoque de mentoría
4. **PERSONALIZAR** respuestas según contexto del usuario
5. **USAR** herramientas disponibles para información actualizada

Recordá: Sos una mentora que acompaña, no solo un bot que responde.
"""
    
    def _get_fallback_instructions(self) -> str:
        """
        Obtiene instrucciones de fallback si no hay datos.
        
        Returns:
            String con instrucciones mínimas
        """
        return """
# IDENTIDAD

Sos Royalia, asesora de Royal Company.

## Tono
- Argentino informal
- Vosear siempre
- Amigable pero profesional

## Información Básica
- Royal Company: Empresa mayorista en Argentina
- Productos: Joyas, relojes, maquillaje, indumentaria
- Mínimo mayorista: $40,000
- Envíos a todo el país

## Reglas Críticas
- No inventar información
- Mantener tono argentino
- Priorizar emprendedores
- Usar herramientas disponibles
"""
    
    def get_quick_instructions(self, scenario: str) -> str:
        """
        Obtiene instrucciones rápidas para escenarios específicos.
        
        Args:
            scenario: Escenario específico (greeting, product_query, etc.)
            
        Returns:
            String con instrucciones específicas
        """
        scenarios = {
            "greeting": """Responder con entusiasmo, preguntar si es emprendedor o comprador final.
No saludar si ya se saludó hoy.""",
            
            "product_query": """Preguntar detalles específicos antes de buscar.
Usar herramientas de productos para información actualizada.""",
            
            "entrepreneur": """OBLIGATORIO: Hacer preguntas de conocimiento ANTES de ofrecer productos.
Mencionar acompañamiento y mentoría.
Ofrecer combos emprendedores.""",
            
            "price_question": """Dar información de mínimos.
Explicar diferencia mayorista/minorista.
Mencionar beneficios de cada modalidad.""",
            
            "shipping": """Informar costos y tiempos.
Mencionar envío gratis desde $80,000.
Explicar que es 100% asegurado.""",
            
            "trust": """Mencionar 7 años en el mercado.
30,000+ emprendedoras activas.
Locales físicos en Córdoba."""
        }
        
        return scenarios.get(scenario, "Responder de manera amigable y profesional.")
    
    def update_instructions_with_feedback(
        self,
        base_instructions: str,
        feedback: Dict[str, Any]
    ) -> str:
        """
        Actualiza instrucciones basándose en feedback.
        
        Args:
            base_instructions: Instrucciones base
            feedback: Feedback del usuario o sistema
            
        Returns:
            Instrucciones actualizadas
        """
        if not feedback:
            return base_instructions
        
        additions = "\n# AJUSTES BASADOS EN FEEDBACK\n\n"
        
        if feedback.get('user_frustrated'):
            additions += """El usuario mostró frustración previamente.
- Ser extra empático
- No insistir con ventas
- Resolver problemas primero\n"""
        
        if feedback.get('prefers_brief'):
            additions += """El usuario prefiere respuestas breves.
- Ser conciso
- Ir al punto
- Evitar explicaciones largas\n"""
        
        if feedback.get('is_returning'):
            additions += """El usuario es recurrente.
- No repetir información básica
- Recordar interacciones previas
- Ofrecer novedades\n"""
        
        return base_instructions + additions


# Instancia singleton
_builder_instance: Optional[InstructionBuilder] = None

def get_instruction_builder() -> InstructionBuilder:
    """
    Obtiene la instancia singleton del Instruction Builder.
    
    Returns:
        Instancia de InstructionBuilder
    """
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = InstructionBuilder()
    return _builder_instance