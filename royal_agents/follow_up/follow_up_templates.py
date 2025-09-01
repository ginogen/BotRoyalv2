"""
📝 Templates de Follow-up para Royal Bot v2
Templates base para generar mensajes personalizados por etapa
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger('followup.templates')

class FollowUpTemplateEngine:
    """Engine para gestión de templates de follow-up"""
    
    def __init__(self):
        self.stage_templates = self._initialize_templates()
        self.entrepreneur_variations = self._initialize_entrepreneur_templates()
        self.buyer_variations = self._initialize_buyer_templates()
    
    def _initialize_templates(self) -> Dict[int, str]:
        """Templates base por etapa"""
        return {
            1: """Hola! Veo que estuviste viendo productos hace un rato. 
¿Necesitas ayuda con algo específico? Estoy aquí para ayudarte.""",
            
            2: """¿Todo bien? Vi que estuviste interesado en algunos productos.
Si tienes alguna duda o necesitas más información, no dudes en escribirme.""",
            
            3: """¡Tengo algo que te puede interesar! 
Basándome en lo que estuviste viendo, creo que estos productos pueden ser perfectos para ti.
¿Te muestro algunas opciones?""",
            
            4: """¡Hola! He estado pensando en tu consulta anterior.
Tengo algunas recomendaciones específicas que creo que te van a encantar.
¿Te las comparto?""",
            
            5: """¿Sabías que muchos emprendedores como tú han tenido excelentes resultados con estos productos?
Me encantaría contarte algunas historias de éxito que te pueden inspirar.""",
            
            6: """¡Última oportunidad! 
Tengo un descuento especial disponible por tiempo limitado para los productos que viste.
¿Te interesa conocer los detalles?""",
            
            7: """No quiero ser insistente, pero quería asegurarme de que tengas toda la info que necesitas.
Si cambias de opinión o tienes alguna pregunta, estaré aquí.""",
            
            8: """Entiendo que quizás no sea el momento indicado.
Si en el futuro necesitas algo, no dudes en escribirme. 
¿Prefieres que no te envíe más mensajes por ahora?"""
        }
    
    def _initialize_entrepreneur_templates(self) -> Dict[int, List[str]]:
        """Templates específicos para emprendedores"""
        return {
            1: [
                "¡Hola emprendedor! Vi que estuviste explorando productos para tu negocio. ¿En qué te puedo ayudar?",
                "¿Cómo va tu emprendimiento? Noté tu interés en algunos productos. ¿Necesitas asesoramiento?"
            ],
            
            3: [
                "¡Perfecto timing! Tengo productos ideales para hacer crecer tu negocio. ¿Los vemos?",
                "Como emprendedor, seguro valoras la calidad. Te muestro opciones premium que te van a encantar."
            ],
            
            5: [
                "🚀 ¿Te cuento cómo otros emprendedores triplicaron sus ventas con estos productos?",
                "Historias reales: emprendedores que transformaron su negocio. ¿Te interesa escucharlas?"
            ]
        }
    
    def _initialize_buyer_templates(self) -> Dict[int, List[str]]:
        """Templates específicos para compradores"""
        return {
            1: [
                "¡Hola! Vi que estuviste viendo algunos productos. ¿Encontraste lo que buscabas?",
                "¿Todo bien? Noté tu interés en algunos productos. ¿Te ayudo a decidir?"
            ],
            
            3: [
                "¡Tengo una sorpresa! Descuentos especiales en los productos que viste. ¿Los revisamos?",
                "¿Sabías que tenemos ofertas especiales? Te muestro las mejores opciones para ti."
            ],
            
            6: [
                "⏰ ¡Última oportunidad! Descuento del 15% en tus productos favoritos hasta mañana.",
                "¡No te pierdas esto! Oferta especial por tiempo limitado en lo que estuviste viendo."
            ]
        }
    
    def get_stage_template(self, stage: int, user_type: str = "general") -> str:
        """Obtener template para una etapa específica"""
        try:
            # Template base
            base_template = self.stage_templates.get(stage, self.stage_templates[1])
            
            # Variaciones por tipo de usuario
            if user_type == "entrepreneur" and stage in self.entrepreneur_variations:
                variations = self.entrepreneur_variations[stage]
                # Alternar entre variaciones basado en la hora
                variation_index = datetime.now().hour % len(variations)
                return variations[variation_index]
            
            elif user_type == "buyer" and stage in self.buyer_variations:
                variations = self.buyer_variations[stage]
                variation_index = datetime.now().hour % len(variations)
                return variations[variation_index]
            
            return base_template
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo template: {e}")
            return self.stage_templates[1]  # Fallback al template de etapa 1
    
    def get_context_enhanced_template(self, stage: int, context: Dict[str, Any]) -> str:
        """Obtener template mejorado con contexto específico"""
        try:
            is_entrepreneur = context.get('is_entrepreneur', False)
            user_type = "entrepreneur" if is_entrepreneur else "buyer"
            
            base_template = self.get_stage_template(stage, user_type)
            
            # Agregar contexto específico
            recent_products = context.get('recent_products', [])
            if recent_products and stage in [3, 4, 6]:
                product_names = [p.get('name', '') for p in recent_products[:2]]
                if product_names:
                    product_context = f" Especialmente sobre {', '.join(product_names)}."
                    base_template += product_context
            
            return base_template
            
        except Exception as e:
            logger.error(f"❌ Error generando template con contexto: {e}")
            return self.get_stage_template(stage)
    
    def get_blacklist_response_template(self) -> str:
        """Template para respuesta de opt-out"""
        return """Perfecto, entiendo. Te he removido de los mensajes automáticos.
Si en el futuro necesitas algo, siempre puedes escribirme cuando quieras.
¡Que tengas un excelente día! 👋"""
    
    def get_stage_description(self, stage: int) -> str:
        """Obtener descripción de cada etapa"""
        descriptions = {
            1: "Recordatorio inicial suave",
            2: "Ofrecimiento de ayuda",
            3: "Oferta especial personalizada",
            4: "Recomendaciones específicas",
            5: "Casos de éxito y testimonios",
            6: "Descuento con urgencia",
            7: "Último contacto respetuoso", 
            8: "Despedida con opción de opt-out"
        }
        return descriptions.get(stage, f"Etapa {stage}")
    
    def get_all_stage_info(self) -> List[Dict[str, Any]]:
        """Obtener información completa de todas las etapas"""
        return [
            {
                "stage": stage,
                "description": self.get_stage_description(stage),
                "template": template,
                "timing": f"{stage}h" if stage < 24 else f"{stage//24}d"
            }
            for stage, template in self.stage_templates.items()
        ]