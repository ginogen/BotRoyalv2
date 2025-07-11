# Conversation Context para Royal Bot v2
# Sistema de memoria y contexto basado en OpenAI Agents SDK

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProductReference:
    """Referencia a un producto mostrado al usuario"""
    name: str
    price: str
    id: Optional[str] = None
    permalink: Optional[str] = None
    category: Optional[str] = None
    shown_at: datetime = field(default_factory=datetime.now)

@dataclass 
class ConversationMemory:
    """Memoria de la conversación actual"""
    user_id: str
    conversation_started: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    
    # Estado de la conversación
    current_state: str = "browsing"  # browsing, selecting, purchasing, completed
    user_intent: str = ""  # emprendedor, comprador, consulta
    user_profile: Dict[str, Any] = field(default_factory=dict)
    
    # Productos mostrados recientemente (máximo 10)
    recent_products: List[ProductReference] = field(default_factory=list)
    
    # Historial de interacciones (últimas 20)
    interaction_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Preferencias detectadas
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Contexto específico del negocio
    is_entrepreneur: bool = False
    experience_level: str = ""  # empezando, experimentado, renovando_stock
    product_interests: List[str] = field(default_factory=list)
    budget_range: Optional[str] = None
    
    def add_product_reference(self, product: ProductReference):
        """Agrega referencia a producto mostrado"""
        # Evitar duplicados
        existing = [p for p in self.recent_products if p.name == product.name]
        if not existing:
            self.recent_products.append(product)
            
        # Mantener solo los últimos 10
        if len(self.recent_products) > 10:
            self.recent_products = self.recent_products[-10:]
            
        self.last_interaction = datetime.now()
        logger.info(f"📦 Producto agregado al contexto: {product.name}")
    
    def add_interaction(self, role: str, message: str, metadata: Optional[Dict] = None):
        """Agrega interacción al historial"""
        interaction = {
            "role": role,
            "message": message[:500],  # Truncar mensajes muy largos
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.interaction_history.append(interaction)
        
        # Mantener solo las últimas 20 interacciones
        if len(self.interaction_history) > 20:
            self.interaction_history = self.interaction_history[-20:]
            
        self.last_interaction = datetime.now()
    
    def get_recent_products_summary(self) -> str:
        """Genera resumen de productos mostrados recientemente"""
        if not self.recent_products:
            return ""
            
        summary = "🧠 PRODUCTOS MOSTRADOS RECIENTEMENTE:\n"
        for i, product in enumerate(self.recent_products[-5:], 1):  # Últimos 5
            summary += f"{i}. {product.name} - ${product.price}"
            if product.category:
                summary += f" ({product.category})"
            summary += "\n"
            
        return summary
    
    def find_product_by_reference(self, reference: str) -> Optional[ProductReference]:
        """Encuentra producto por referencia del usuario"""
        reference_lower = reference.lower()
        
        # Buscar por posición (primero, segundo, etc.) - EXPANDIDO para incluir más números
        position_map = {
            'primer': 0, 'primero': 0, '1': 0, 'uno': 0,
            'segundo': 1, '2': 1, 'dos': 1,
            'tercer': 2, 'tercero': 2, '3': 2, 'tres': 2,
            'cuarto': 3, '4': 3, 'cuatro': 3,
            'quinto': 4, '5': 4, 'cinco': 4,
            'sexto': 5, '6': 5, 'seis': 5,
            'séptimo': 6, 'septimo': 6, '7': 6, 'siete': 6,
            'octavo': 7, '8': 7, 'ocho': 7,
            'noveno': 8, '9': 8, 'nueve': 8,
            'décimo': 9, 'decimo': 9, '10': 9, 'diez': 9
        }
        
        # NUEVO: Detección específica para "combo X" o "el X"
        import re
        
        # Buscar patrones como "combo 6", "el 6", "combo sexto"
        combo_patterns = [
            r'combo\s*(\d+)',
            r'el\s*(\d+)',
            r'combo\s*(sexto|séptimo|octavo|noveno|décimo)',
            r'el\s*(sexto|séptimo|octavo|noveno|décimo)'
        ]
        
        for pattern in combo_patterns:
            match = re.search(pattern, reference_lower)
            if match:
                number_text = match.group(1)
                # Si es un número, convertir a posición (1-indexed a 0-indexed)
                if number_text.isdigit():
                    position = int(number_text) - 1
                    if 0 <= position < len(self.recent_products):
                        logger.info(f"🎯 Producto encontrado por número: posición {position + 1}")
                        return self.recent_products[position]
                # Si es texto, usar el mapeo
                elif number_text in position_map:
                    position = position_map[number_text]
                    if position < len(self.recent_products):
                        logger.info(f"🎯 Producto encontrado por texto: {number_text} -> posición {position + 1}")
                        return self.recent_products[position]
        
        # Buscar en el mapeo de posiciones original
        for word, position in position_map.items():
            if word in reference_lower and position < len(self.recent_products):
                logger.info(f"🎯 Producto encontrado por mapeo: {word} -> posición {position + 1}")
                return self.recent_products[position]
        
        # Buscar por nombre parcial
        for product in self.recent_products:
            product_words = product.name.lower().split()
            reference_words = reference_lower.split()
            
            # Si alguna palabra coincide
            if any(word in product.name.lower() for word in reference_words):
                logger.info(f"🎯 Producto encontrado por nombre parcial: {product.name}")
                return product
        
        # Buscar por precio
        if '$' in reference or 'peso' in reference_lower:
            price_matches = re.findall(r'(\d+\.?\d*)', reference)
            if price_matches:
                target_price = price_matches[0]
                for product in self.recent_products:
                    if target_price in product.price:
                        logger.info(f"🎯 Producto encontrado por precio: ${target_price}")
                        return product
        
        logger.warning(f"❌ No se pudo identificar producto por referencia: '{reference}'")
        return None
    
    def update_user_profile(self, key: str, value: Any):
        """Actualiza perfil del usuario"""
        self.user_profile[key] = value
        self.last_interaction = datetime.now()
        
        # Actualizar flags específicos
        if key == "experience_level":
            self.experience_level = value
            self.is_entrepreneur = True
        elif key == "interests":
            if isinstance(value, list):
                self.product_interests.extend(value)
            else:
                self.product_interests.append(value)
    
    def get_context_summary_for_llm(self) -> str:
        """Genera resumen del contexto para incluir en el prompt del LLM"""
        summary_parts = []
        
        # Estado actual
        if self.current_state != "browsing":
            summary_parts.append(f"🔄 Estado: {self.current_state}")
        
        # Perfil del usuario
        if self.is_entrepreneur:
            summary_parts.append(f"👤 Usuario: Emprendedor ({self.experience_level})")
            
        if self.product_interests:
            interests = ", ".join(self.product_interests[-3:])  # Últimos 3 intereses
            summary_parts.append(f"💡 Intereses: {interests}")
            
        if self.budget_range:
            summary_parts.append(f"💰 Presupuesto: {self.budget_range}")
        
        # Productos recientes
        if self.recent_products:
            products_summary = self.get_recent_products_summary()
            summary_parts.append(products_summary)
        
        # Contexto de interacciones recientes
        if len(self.interaction_history) >= 2:
            recent_interactions = self.interaction_history[-2:]
            summary_parts.append("💬 CONTEXTO RECIENTE:")
            for interaction in recent_interactions:
                role = "👤" if interaction["role"] == "user" else "🤖"
                message = interaction["message"][:100] + "..." if len(interaction["message"]) > 100 else interaction["message"]
                summary_parts.append(f"{role} {message}")
        
        return "\n".join(summary_parts) if summary_parts else ""

@dataclass
class RoyalAgentContext:
    """Contexto principal para el agente Royal"""
    user_id: str
    conversation: ConversationMemory = field(default_factory=lambda: ConversationMemory(""))
    
    # Configuración del agente
    agent_config: Dict[str, Any] = field(default_factory=dict)
    
    # Estado de herramientas MCP
    mcp_available: bool = False
    training_available: bool = False
    
    def __post_init__(self):
        """Inicializar conversation con user_id correcto"""
        if not self.conversation.user_id:
            self.conversation.user_id = self.user_id
    
    def get_enhanced_instructions(self) -> str:
        """Genera instrucciones dinámicas basadas en el contexto"""
        base_instruction = ""
        
        # Contexto específico según el estado
        if self.conversation.is_entrepreneur:
            base_instruction += f"""
🚨 CONTEXTO CRÍTICO: Este usuario es un EMPRENDEDOR ({self.conversation.experience_level})
- Aplicar PROTOCOLO OBLIGATORIO para emprendedores
- NUNCA mostrar productos sin hacer preguntas primero
- Enfocar en mentoría y acompañamiento
"""
        
        # Contexto de productos recientes
        context_summary = self.conversation.get_context_summary_for_llm()
        if context_summary:
            base_instruction += f"\n🧠 CONTEXTO DE LA CONVERSACIÓN:\n{context_summary}\n"
        
        # Instrucciones específicas según el estado
        if self.conversation.current_state == "selecting":
            base_instruction += """
⚠️ El usuario está SELECCIONANDO un producto de los mostrados recientemente.
- Interpretar referencias como "el primero", "el segundo", nombres parciales
- Usar process_purchase_intent() si menciona compra
"""
        elif self.conversation.current_state == "purchasing":
            base_instruction += """
💳 El usuario está en proceso de COMPRA.
- Solicitar datos necesarios: nombre, dirección, método de pago
- Ofrecer sistema de seña ($10,000)
"""
            
        return base_instruction

class ContextManager:
    """Manejador global de contextos de conversación"""
    
    def __init__(self):
        self.active_contexts: Dict[str, RoyalAgentContext] = {}
        logger.info("🧠 ContextManager inicializado")
    
    def get_or_create_context(self, user_id: str) -> RoyalAgentContext:
        """Obtiene o crea contexto para usuario"""
        if user_id not in self.active_contexts:
            self.active_contexts[user_id] = RoyalAgentContext(
                user_id=user_id,
                conversation=ConversationMemory(user_id=user_id)
            )
            logger.info(f"🆕 Nuevo contexto creado para usuario: {user_id}")
        
        return self.active_contexts[user_id]
    
    def cleanup_old_contexts(self, hours: int = 24):
        """Limpia contextos antiguos"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        
        old_contexts = [
            user_id for user_id, context in self.active_contexts.items()
            if context.conversation.last_interaction < cutoff
        ]
        
        for user_id in old_contexts:
            del self.active_contexts[user_id]
            logger.info(f"🧹 Contexto limpiado para usuario: {user_id}")

# Instancia global
context_manager = ContextManager() 