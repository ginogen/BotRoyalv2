"""
Agente Unificado para Royal Bot v2
Un único agente que usa el Knowledge Base centralizado
"""

from typing import Dict, List, Any, Optional
from agents import Agent, Runner  # type: ignore
from ..conversation_context import RoyalAgentContext, context_manager
from .knowledge_system import get_knowledge_base
from .instruction_builder import get_instruction_builder
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UnifiedRoyalAgent:
    """
    Agente unificado que centraliza toda la funcionalidad del bot Royal.
    Usa Knowledge Base para datos y Instruction Builder para comportamiento.
    """
    
    def __init__(self):
        """Inicializa el agente unificado."""
        self.kb = get_knowledge_base()
        self.instruction_builder = get_instruction_builder()
        self.agent = None
        self._initialize_agent()
        
    def _initialize_agent(self):
        """Inicializa el agente de OpenAI con configuración base."""
        try:
            # Obtener instrucciones base completas
            base_instructions = self.instruction_builder.build_complete_instructions(
                include_company=True,
                include_protocols=True,
                include_faqs=False  # FAQs se manejan con tools
            )
            
            # Obtener todas las herramientas disponibles
            tools = self._load_all_tools()
            
            # Crear el agente
            self.agent = Agent(
                name="Royalia - Agente Unificado",
                instructions=base_instructions,
                model="gpt-4o-mini",
                tools=tools
            )
            
            logger.info(f"✅ Agente Unificado inicializado con {len(tools)} herramientas")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente: {e}")
            raise
    
    def _load_all_tools(self) -> List:
        """
        Carga todas las herramientas disponibles.
        
        Returns:
            Lista de herramientas para el agente
        """
        tools = []
        
        # Cargar herramientas del Knowledge Base
        kb_tools = self._create_knowledge_base_tools()
        tools.extend(kb_tools)
        
        # Intentar cargar herramientas existentes (si están disponibles)
        try:
            # WooCommerce tools
            from ..woocommerce_mcp_tools import create_woocommerce_tools
            wc_tools = create_woocommerce_tools()
            tools.extend(wc_tools)
            logger.info(f"✅ {len(wc_tools)} WooCommerce tools cargadas")
        except ImportError:
            logger.warning("⚠️ WooCommerce tools no disponibles")
        except Exception as e:
            logger.error(f"❌ Error cargando WooCommerce tools: {e}")
        
        # Intentar cargar Training tools
        try:
            from ..training_mcp_tools import create_training_tools
            training_tools = create_training_tools()
            tools.extend(training_tools)
            logger.info(f"✅ {len(training_tools)} Training tools cargadas")
        except ImportError:
            logger.warning("⚠️ Training tools no disponibles")
        except Exception as e:
            logger.error(f"❌ Error cargando Training tools: {e}")
        
        # Intentar cargar Context tools
        try:
            from ..contextual_tools import create_contextual_tools
            context_tools = create_contextual_tools()
            tools.extend(context_tools)
            logger.info(f"✅ {len(context_tools)} Context tools cargadas")
        except ImportError:
            logger.warning("⚠️ Context tools no disponibles")
        except Exception as e:
            logger.error(f"❌ Error cargando Context tools: {e}")
        
        logger.info(f"📦 Total de herramientas cargadas: {len(tools)}")
        return tools
    
    def _create_knowledge_base_tools(self) -> List:
        """
        Crea herramientas específicas del Knowledge Base.
        
        Returns:
            Lista de herramientas del KB
        """
        from agents import function_tool  # type: ignore
        
        tools = []
        
        @function_tool
        def get_company_info(section: Optional[str] = None) -> str:
            """
            Obtiene información de Royal Company.
            
            Args:
                section: Sección específica (locations, schedule, shipping, payment, etc.)
            """
            kb = get_knowledge_base()
            
            if section:
                info = kb.get_company_info(section)
                if section == "locations":
                    return kb.get_formatted_info("locations")
                elif section == "schedule":
                    return kb.get_formatted_info("schedule")
                elif section == "shipping":
                    return kb.get_formatted_info("shipping")
                elif section == "payment":
                    return kb.get_formatted_info("payment")
                else:
                    return str(info) if info else "Información no disponible"
            
            # Retornar resumen general
            general = kb.get_company_info("general")
            return f"""
Royal Company - {general.get('description', '')}
Fundada en {general.get('founded', '')}
Productos: {general.get('products_summary', '')}
"""
        
        @function_tool
        def get_faq_answer(query: str) -> str:
            """
            Busca y retorna respuesta a pregunta frecuente.
            
            Args:
                query: Pregunta o tema a buscar
            """
            kb = get_knowledge_base()
            
            # Buscar FAQs relevantes
            faqs = kb.search_faq(query)
            
            if not faqs:
                return "No encontré información específica sobre eso. ¿Podés reformular la pregunta?"
            
            # Retornar la primera FAQ más relevante
            faq = faqs[0]
            return faq.get('answer', 'No hay respuesta disponible')
        
        @function_tool
        def get_policies(policy_type: str) -> str:
            """
            Obtiene políticas específicas de Royal.
            
            Args:
                policy_type: Tipo de política (sales, shipping, return, payment, etc.)
            """
            kb = get_knowledge_base()
            
            policies = kb.get_policy(policy_type)
            
            if not policies:
                return f"No hay información sobre políticas de {policy_type}"
            
            # Formatear según tipo
            if policy_type == "sales":
                wholesale = policies.get('wholesale', {})
                return f"""
Políticas de Venta:
• Mínimo mayorista: ${wholesale.get('minimum_amount', 0):,}
• Requisitos: {wholesale.get('requirements', {})}
• Descuentos por volumen disponibles
""".replace(",", ".")
            
            elif policy_type == "shipping":
                return f"""
Políticas de Envío:
• Cobertura: {policies.get('coverage', '')}
• Proveedor: {policies.get('provider', '')}
• Seguro: {policies.get('insurance', '')}
• Envío gratis desde: ${policies.get('free_shipping', {}).get('threshold', 0):,}
""".replace(",", ".")
            
            return str(policies)
        
        @function_tool
        def get_minimum_purchase_info() -> str:
            """Obtiene información sobre mínimos de compra."""
            kb = get_knowledge_base()
            return kb.get_formatted_info("minimum")
        
        @function_tool
        def get_payment_info() -> str:
            """Obtiene información sobre métodos de pago."""
            kb = get_knowledge_base()
            return kb.get_formatted_info("payment")
        
        @function_tool
        def get_shipping_costs() -> str:
            """Obtiene información sobre costos de envío."""
            kb = get_knowledge_base()
            return kb.get_formatted_info("shipping")
        
        @function_tool
        def get_store_locations() -> str:
            """Obtiene ubicaciones de los locales."""
            kb = get_knowledge_base()
            return kb.get_formatted_info("locations")
        
        @function_tool
        def get_business_hours() -> str:
            """Obtiene horarios de atención."""
            kb = get_knowledge_base()
            return kb.get_formatted_info("schedule")
        
        @function_tool
        def search_knowledge(query: str) -> str:
            """
            Busca información en todo el Knowledge Base.
            
            Args:
                query: Término o pregunta a buscar
            """
            kb = get_knowledge_base()
            results = kb.search_knowledge(query)
            
            if not any(results.values()):
                return "No encontré información específica sobre eso."
            
            response = "Encontré la siguiente información:\n\n"
            
            if results['faqs']:
                response += "**Preguntas Frecuentes:**\n"
                for faq in results['faqs'][:2]:  # Máximo 2 FAQs
                    response += f"• {faq['question']}\n  {faq['answer'][:100]}...\n"
            
            if results['company']:
                response += "\n**Información de la empresa:**\n"
                for item in results['company'][:2]:
                    response += f"• {item['section']}: Información disponible\n"
            
            if results['urls']:
                response += "\n**Enlaces relevantes:**\n"
                for url in results['urls'][:3]:
                    response += f"• {url['type']}: {url['url']}\n"
            
            return response
        
        @function_tool
        def get_catalog_url(category: Optional[str] = None) -> str:
            """
            Obtiene URL del catálogo.
            
            Args:
                category: Categoría específica (jewelry, makeup, clothing, etc.)
            """
            kb = get_knowledge_base()
            
            if category:
                url = kb.get_url(category)
                if url:
                    return f"🔗 {category.replace('_', ' ').title()}: {url}"
                return "No tengo URL para esa categoría específica"
            
            # URL principal
            main_url = kb.get_url("main_store")
            return f"📍 Catálogo completo sin logo: {main_url}"
        
        @function_tool
        def track_greeting(user_id: str) -> bool:
            """
            Rastrea si ya se saludó al usuario hoy.
            
            Args:
                user_id: ID del usuario
                
            Returns:
                True si debe saludar, False si ya saludó
            """
            kb = get_knowledge_base()
            
            # Usar cache dinámico para tracking
            greeting_key = f"greeting_{user_id}_{datetime.now().date()}"
            
            if kb.get_dynamic_data(greeting_key):
                return False  # Ya saludó hoy
            
            # Marcar que se saludó
            kb.set_dynamic_data(greeting_key, {"greeted": True}, ttl_minutes=1440)  # 24 horas
            return True
        
        tools.extend([
            get_company_info,
            get_faq_answer,
            get_policies,
            get_minimum_purchase_info,
            get_payment_info,
            get_shipping_costs,
            get_store_locations,
            get_business_hours,
            search_knowledge,
            get_catalog_url,
            track_greeting
        ])
        
        logger.info(f"✅ {len(tools)} Knowledge Base tools creadas")
        return tools
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        context: Optional[RoyalAgentContext] = None
    ) -> str:
        """
        Procesa un mensaje del usuario.
        
        Args:
            user_id: ID del usuario
            message: Mensaje a procesar
            context: Contexto de conversación opcional
            
        Returns:
            Respuesta del agente
        """
        try:
            # Obtener o crear contexto
            if not context:
                context = context_manager.get_or_create_context(user_id)
            
            # Detectar tipo de usuario y actualizar instrucciones
            user_type = self._detect_user_type(message, context)
            
            # Construir instrucciones contextuales
            contextual_instructions = self._build_contextual_instructions(
                user_type=user_type,
                context=context,
                message=message
            )
            
            # Registrar mensaje en contexto
            context.conversation.add_interaction("user", message)
            
            # Ejecutar con el agente
            result = await Runner.run(
                starting_agent=self.agent,
                input=contextual_instructions + "\n\nUsuario dice: " + message,
                context=context
            )
            
            # Registrar respuesta
            context.conversation.add_interaction("assistant", result.final_output)
            
            # Actualizar cache con información relevante si es necesario
            self._update_dynamic_cache(user_id, context)
            
            return result.final_output
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return self.kb.get_error_message("technical_issue")
    
    def _detect_user_type(self, message: str, context: RoyalAgentContext) -> str:
        """
        Detecta el tipo de usuario basándose en el mensaje y contexto.
        
        Args:
            message: Mensaje del usuario
            context: Contexto de conversación
            
        Returns:
            Tipo de usuario detectado
        """
        message_lower = message.lower()
        
        # Palabras clave para emprendedores nuevos
        new_entrepreneur_keywords = [
            'empezar', 'arrancar', 'primera vez', 'no sé qué elegir',
            'nuevo', 'nueva', 'quiero emprender', 'iniciar'
        ]
        
        # Palabras clave para vendedores experimentados
        experienced_keywords = [
            'ya vendo', 'tengo experiencia', 'hace tiempo',
            'mi negocio', 'mis clientas', 'renovar stock'
        ]
        
        # Verificar en mensaje actual
        for keyword in new_entrepreneur_keywords:
            if keyword in message_lower:
                context.conversation.is_entrepreneur = True
                context.conversation.experience_level = "empezando"
                return "new_entrepreneurs"
        
        for keyword in experienced_keywords:
            if keyword in message_lower:
                context.conversation.is_entrepreneur = True
                context.conversation.experience_level = "experimentado"
                return "experienced_sellers"
        
        # Verificar contexto previo
        if context.conversation.is_entrepreneur:
            if context.conversation.experience_level == "empezando":
                return "new_entrepreneurs"
            elif context.conversation.experience_level == "experimentado":
                return "experienced_sellers"
        
        # Por defecto, asumir cliente potencial
        return "retail_customers"
    
    def _build_contextual_instructions(
        self,
        user_type: str,
        context: RoyalAgentContext,
        message: str
    ) -> str:
        """
        Construye instrucciones específicas para el contexto actual.
        
        Args:
            user_type: Tipo de usuario detectado
            context: Contexto de conversación
            message: Mensaje actual del usuario
            
        Returns:
            Instrucciones contextualizadas
        """
        # Preparar contexto del usuario
        user_context = {
            'is_entrepreneur': context.conversation.is_entrepreneur,
            'experience_level': context.conversation.experience_level,
            'product_interests': context.conversation.product_interests,
            'budget_range': context.conversation.budget_range,
            'recent_products': len(context.conversation.recent_products)
        }
        
        # Detectar escenario específico
        scenario = self._detect_scenario(message)
        
        # Construir instrucciones
        instructions = ""
        
        # Agregar instrucciones rápidas del escenario
        if scenario:
            quick_instructions = self.instruction_builder.get_quick_instructions(scenario)
            instructions += f"\n# ESCENARIO DETECTADO: {scenario.upper()}\n{quick_instructions}\n"
        
        # Agregar protocolo específico del tipo de usuario
        user_protocol = self.instruction_builder.build_conversation_protocols(user_type)
        if user_protocol:
            instructions += user_protocol
        
        # Agregar contexto del usuario
        contextual = self.instruction_builder.build_contextual_instructions(
            user_context=user_context,
            include_faqs=False
        )
        if contextual:
            instructions += contextual
        
        return instructions
    
    def _detect_scenario(self, message: str) -> Optional[str]:
        """
        Detecta el escenario específico del mensaje.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Escenario detectado o None
        """
        message_lower = message.lower()
        
        scenarios = {
            'greeting': ['hola', 'buenas', 'buen día', 'buenas tardes', 'cómo estás'],
            'product_query': ['producto', 'anillo', 'cadena', 'pulsera', 'reloj', 'maquillaje'],
            'entrepreneur': ['emprender', 'empezar', 'arrancar', 'negocio', 'revender'],
            'price_question': ['precio', 'costo', 'cuánto', 'valor', 'mínimo'],
            'shipping': ['envío', 'enviar', 'llega', 'demora', 'andreani'],
            'trust': ['confiable', 'seguro', 'garantía', 'real', 'estafa']
        }
        
        for scenario, keywords in scenarios.items():
            if any(keyword in message_lower for keyword in keywords):
                return scenario
        
        return None
    
    def _update_dynamic_cache(self, user_id: str, context: RoyalAgentContext):
        """
        Actualiza el cache dinámico con información relevante.
        
        Args:
            user_id: ID del usuario
            context: Contexto de conversación
        """
        try:
            # Guardar resumen de conversación en cache
            conversation_key = f"conversation_{user_id}"
            conversation_data = {
                'user_type': context.conversation.user_profile.get('type', 'unknown'),
                'interests': context.conversation.product_interests,
                'last_interaction': datetime.now().isoformat(),
                'interaction_count': len(context.conversation.interaction_history)
            }
            
            self.kb.set_dynamic_data(conversation_key, conversation_data, ttl_minutes=60)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando cache: {e}")
    
    def reload_knowledge(self):
        """Recarga el Knowledge Base y reinicializa el agente."""
        logger.info("🔄 Recargando Knowledge Base y reinicializando agente...")
        
        # Recargar KB
        self.kb.reload_data()
        
        # Reinicializar agente con nuevas instrucciones
        self._initialize_agent()
        
        logger.info("✅ Agente reinicializado con conocimiento actualizado")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del agente.
        
        Returns:
            Diccionario con estadísticas
        """
        kb_summary = self.kb.get_summary()
        
        return {
            'agent_name': self.agent.name if self.agent else 'Not initialized',
            'knowledge_base': kb_summary,
            'tools_count': len(self.agent.tools) if self.agent else 0,
            'model': self.agent.model if self.agent else 'N/A'
        }


# Instancia singleton
_unified_agent: Optional[UnifiedRoyalAgent] = None

def get_unified_agent() -> UnifiedRoyalAgent:
    """
    Obtiene la instancia singleton del agente unificado.
    
    Returns:
        Instancia de UnifiedRoyalAgent
    """
    global _unified_agent
    if _unified_agent is None:
        _unified_agent = UnifiedRoyalAgent()
    return _unified_agent


# Función de conveniencia para uso sincrónico
def process_message_sync(user_id: str, message: str) -> str:
    """
    Procesa un mensaje de forma sincrónica.
    
    Args:
        user_id: ID del usuario
        message: Mensaje a procesar
        
    Returns:
        Respuesta del agente
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    agent = get_unified_agent()
    
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                agent.process_message(user_id, message)
            )
        finally:
            loop.close()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_new_loop)
        return future.result(timeout=30)