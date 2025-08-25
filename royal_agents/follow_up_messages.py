# Sistema de Mensajes Contextuales con IA para Seguimiento de 14 Etapas
# Genera mensajes únicos basados en el contexto real de cada conversación

import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
import asyncio

# Import para contexto conversacional
from hybrid_context_manager import hybrid_context_manager, ConversationMemory

logger = logging.getLogger(__name__)

class FollowUpStagePrompts:
    """Sistema de prompts para generar mensajes contextuales con IA para cada etapa"""
    
    def __init__(self):
        # Base personality prompt para Royalia
        self.base_personality = """
Eres Royalia, una emprendedora exitosa que ayuda a otras mujeres a emprender con productos de calidad (joyas, maquillaje, indumentaria). 

Tu personalidad:
- Empática y genuinamente preocupada por el éxito de las demás
- Directa pero cálida, nunca agresiva
- Compartes experiencias reales y testimonios
- Usas emojis naturalmente 
- Motivadora pero realista sobre los desafíos
- Orientada a resultados concretos

Tu negocio:
- Combos emprendedores desde $40.000
- Margen de ganancia hasta 150%
- Productos probados que se venden bien
- Acompañamiento completo para emprendedoras
- Enfoque en recuperación rápida de inversión
"""

        # Prompts específicos por etapa
        self.stage_prompts = {
            0: self._get_stage_0_prompt(),   # 1 hora después
            1: self._get_stage_1_prompt(),   # Día 1
            2: self._get_stage_2_prompt(),   # Día 2
            4: self._get_stage_4_prompt(),   # Día 4
            7: self._get_stage_7_prompt(),   # Día 7
            10: self._get_stage_10_prompt(), # Día 10
            14: self._get_stage_14_prompt(), # Día 14
            18: self._get_stage_18_prompt(), # Día 18
            26: self._get_stage_26_prompt(), # Día 26
            36: self._get_stage_36_prompt(), # Día 36
            46: self._get_stage_46_prompt(), # Día 46
            56: self._get_stage_56_prompt(), # Día 56
            66: self._get_stage_66_prompt(), # Día 66
            999: self._get_maintenance_prompt() # Mantenimiento
        }

    def _get_stage_0_prompt(self) -> str:
        return """
ETAPA 0 - SEGUIMIENTO INMEDIATO (1 hora después)

OBJETIVO: Mantener el momentum y la conexión emocional fresca de la conversación inicial.

TONO: Cálido, entusiasta, como continuando una charla entre amigas.

ELEMENTOS CLAVE:
- Referenciar específicamente temas discutidos en la conversación previa
- Mostrar que recordás detalles importantes
- Crear urgencia suave basada en oportunidades actuales
- Ofrecer combos específicos según intereses expresados
- Incluir call-to-action claro pero no presionante

ESTRUCTURA SUGERIDA:
1. Saludo personalizado referenciando la charla previa
2. Conexión emocional con algo específico que mencionó
3. Información de valor relacionada a sus intereses
4. Propuesta concreta con precios
5. Llamada a la acción amigable

Genera un mensaje que suene como si Royalia estuviera continuando naturalmente la conversación que tuvieron hace una hora.
"""

    def _get_stage_1_prompt(self) -> str:
        return """
ETAPA 1 - REFUERZO DE INTERÉS (Día 1)

OBJETIVO: Reforzar el interés y crear momentum hacia la acción, usando elementos de la conversación previa.

TONO: Motivador, con energía positiva, incluir elementos de urgencia y oportunidad.

ELEMENTOS CLAVE:
- Referenciar la conversación del día anterior
- Crear sensación de oportunidad perdida si no actúa
- Mostrar resultados concretos de otras emprendedoras
- Combos específicos con números exactos de inversión/retorno
- Urgencia basada en temporadas/tendencias

El mensaje debe sonar como si Royalia siguiera pensando en ella después de la conversación de ayer.
"""

    def _get_stage_2_prompt(self) -> str:
        return """
ETAPA 2 - PRUEBA SOCIAL Y MOTIVACIÓN (Día 2)

OBJETIVO: Usar testimonios y casos de éxito para superar dudas y motivar la acción.

TONO: Inspirador, con historias reales, manteniendo calidez personal.

ELEMENTOS CLAVE:
- Historia específica de una emprendedora exitosa
- Números concretos de resultados
- Abordar dudas comunes sin mencionar si ella las expresó
- Mostrar que el éxito es replicable

El mensaje debe transmitir que si otras pueden, ella también puede.
"""

    def _get_stage_4_prompt(self) -> str:
        return """
ETAPA 4 - CREACIÓN DE URGENCIA (Día 4)

OBJETIVO: Intensificar la urgencia y abordar directamente la postergación.

TONO: Más directo pero manteniendo empatía, con urgencia palpable.

ELEMENTOS CLAVE:
- Abordar el tema de la postergación directamente
- Crear urgencia basada en temporadas/oportunidades
- Mostrar el costo de oportunidad de esperar

Debe generar una sensación de "ahora o nunca" sin ser agresivo.
"""

    def _get_stage_7_prompt(self) -> str:
        return """
ETAPA 7 - MOMENTO DECISIVO (Día 7 - Una semana)

OBJETIVO: Momento de verdad. Separar a las que realmente quieren emprender de las que solo hablan.

TONO: Directo, honesto, desafiante pero respetuoso.

ELEMENTOS CLAVE:
- Confrontar directamente la diferencia entre hablar y actuar
- Referenciar la semana que pasó desde la conversación inicial
- Crear una dicotomía clara: actuar o seguir postergando

El mensaje debe ser un wake-up call respetuoso pero firme.
"""

    def _get_stage_10_prompt(self) -> str:
        return """
ETAPA 10 - COMPARACIÓN INTERNA (Día 10)

OBJETIVO: Crear reflexión sobre el tiempo perdido versus el progreso que podría haber tenido.

TONO: Reflexivo, ligeramente confrontativo pero no agresivo.

ELEMENTOS CLAVE:
- Mostrar qué hubiera logrado si hubiera empezado hace 10 días
- Comparar con resultados de clientas que sí empezaron
- No juzgar pero sí mostrar las consecuencias de postergar
"""

    def _get_stage_14_prompt(self) -> str:
        return """
ETAPA 14 - ULTIMÁTUM ELEGANTE (Día 14 - 2 semanas)

OBJETIVO: Dar un ultimátum respetuoso pero claro. Decidir si continúa o se despide.

TONO: Firme, directo, pero con cariño. Ultimátum elegante.

ELEMENTOS CLAVE:
- Marcar las 2 semanas transcurridas
- Plantear claramente las dos opciones: emprender o despedirse
- Sin drama pero con firmeza

El mensaje debe ser definitorio pero respetuoso.
"""

    def _get_stage_18_prompt(self) -> str:
        return """
ETAPA 18 - CASO DE ÉXITO ESPECÍFICO (Día 18)

OBJETIVO: Último intento con caso de éxito muy específico y detallado.

TONO: Narrativo, inspirador, con detalles concretos.

ELEMENTOS CLAVE:
- Historia día a día de una emprendedora exitosa en 18 días
- Números muy específicos y creíbles
- Comparación implícita con su situación

El mensaje debe inspirar con hechos concretos, no con promesas vagas.
"""

    def _get_stage_26_prompt(self) -> str:
        return """
ETAPA 26 - REFLEXIÓN DEL MES (Día 26)

OBJETIVO: Hacer un balance del mes transcurrido y dar otra oportunidad.

TONO: Reflexivo, curioso, sin presión, exploratorio.

ELEMENTOS CLAVE:
- Marcar el mes transcurrido
- Curiosidad genuina sobre qué pasó en su mente
- Tres opciones posibles sin juicio

El mensaje debe ser exploratorio y comprensivo.
"""

    def _get_stage_36_prompt(self) -> str:
        return """
ETAPA 36 - MÁS DE UN MES (Día 36)

OBJETIVO: Último mensaje activo, dar opción de salida o compromiso real.

TONO: Realista, directo pero no agresivo, con perspectiva.

ELEMENTOS CLAVE:
- Marcar el tiempo transcurrido (más de un mes)
- Mostrar resultados de quienes sí actuaron
- Aceptar que quizás no es el momento para ella

El mensaje debe ser liberador pero dar una última oportunidad clara.
"""

    def _get_stage_46_prompt(self) -> str:
        return """
ETAPA 46 - CIERRE RESPETUOSO (Día 46)

OBJETIVO: Cerrar elegantemente o definir situación específica.

TONO: Respetuoso, firme, definitorio pero cariñoso.

ELEMENTOS CLAVE:
- Reconocer el tiempo invertido en el seguimiento
- Aceptar que 46 días es tiempo suficiente para decidir
- Pregunta directa sobre continuar o parar

El mensaje debe ser definitorio pero lleno de respeto.
"""

    def _get_stage_56_prompt(self) -> str:
        return """
ETAPA 56 - BALANCE DE 2 MESES (Día 56)

OBJETIVO: Hacer balance de 2 meses y explorar cambios en su situación.

TONO: Analítico, reflexivo, esperanzado pero realista.

ELEMENTOS CLAVE:
- Balance claro: 2 meses atrás vs hoy
- Explorar si cambió algo en su situación
- Opciones específicas de cambios posibles

El mensaje debe ser evaluativo y exploratorio.
"""

    def _get_stage_66_prompt(self) -> str:
        return """
ETAPA 66 - DESPEDIDA DE SERIE ACTIVA (Día 66)

OBJETIVO: Cerrar elegantemente la serie activa de mensajes y pasar a mantenimiento.

TONO: Cariñoso, agradecido, esperanzado, sin presión.

ELEMENTOS CLAVE:
- Marcar que es el último mensaje activo
- Agradecimiento genuino por el tiempo compartido
- Explicar la transición a mensajes de mantenimiento

El mensaje debe ser una hermosa despedida que deje la puerta abierta.
"""

    def _get_maintenance_prompt(self) -> str:
        return """
ETAPA MANTENIMIENTO - CONTACTO SUAVE (Cada 15 días)

OBJETIVO: Mantener contacto amigable sin presión, compartir novedades, mantener relación.

TONO: Amigable, casual, informativo, sin agenda oculta.

ELEMENTOS CLAVE:
- Saludo natural y cálido
- Novedades del negocio o productos
- Pregunta genuina por su situación
- Referencia sutil al tema emprendimiento sin presión

El mensaje debe sentirse como el contacto natural entre conocidas, sin agenda comercial obvia.
"""

    def get_prompt_for_stage(self, stage: int) -> Optional[str]:
        """Obtiene el prompt específico para una etapa"""
        return self.stage_prompts.get(stage)
    
    def get_all_stages(self) -> List[int]:
        """Obtiene todas las etapas disponibles"""
        return list(self.stage_prompts.keys())


class ContextExtractor:
    """Extrae información relevante del contexto conversacional para generar mensajes más naturales"""
    
    @staticmethod
    def extract_conversation_summary(context: ConversationMemory) -> str:
        """Extrae un resumen de la conversación para usar en el prompt de IA"""
        if not context.interaction_history:
            return "No hay historial de conversación disponible."
        
        # Tomar las últimas 5 interacciones más relevantes
        recent_interactions = context.interaction_history[-5:]
        
        conversation_summary = "HISTORIAL DE CONVERSACIÓN:\n"
        for interaction in recent_interactions:
            role = interaction.get('role', 'unknown')
            message = interaction.get('message', '')[:200]  # Limitar longitud
            timestamp = interaction.get('timestamp', '')
            
            conversation_summary += f"- {role.upper()}: {message}\n"
        
        return conversation_summary
    
    @staticmethod
    def extract_user_interests(context: ConversationMemory) -> str:
        """Extrae intereses específicos del usuario"""
        interests = []
        
        # De productos mostrados recientemente
        if context.recent_products:
            product_categories = list(set([p.category for p in context.recent_products if p.category]))
            interests.extend(product_categories)
        
        # De intereses de productos
        if context.product_interests:
            interests.extend(context.product_interests)
        
        # Del perfil de usuario
        if context.user_profile:
            user_interest = context.user_profile.get('interest')
            if user_interest:
                interests.append(user_interest)
        
        return f"INTERESES IDENTIFICADOS: {', '.join(set(interests))}" if interests else "No se identificaron intereses específicos."
    
    @staticmethod
    def extract_budget_info(context: ConversationMemory) -> str:
        """Extrae información sobre presupuesto mencionado"""
        budget = context.budget_range
        if budget:
            return f"PRESUPUESTO MENCIONADO: {budget}"
        return "No se mencionó presupuesto específico."
    
    @staticmethod
    def extract_objections_and_questions(context: ConversationMemory) -> str:
        """Extrae objeciones o preguntas específicas del historial"""
        if not context.interaction_history:
            return "No se identificaron objeciones o preguntas específicas."
        
        # Buscar mensajes del usuario que contengan preguntas o dudas
        user_messages = [i for i in context.interaction_history if i.get('role') == 'user']
        
        objections_found = []
        questions_found = []
        
        for msg in user_messages[-3:]:  # Últimas 3 interacciones del usuario
            message = msg.get('message', '').lower()
            
            # Detectar preguntas
            if '?' in message:
                questions_found.append(message[:100])
            
            # Detectar objeciones comunes
            objection_keywords = ['pero', 'sin embargo', 'no sé si', 'me da miedo', 'no tengo', 'es caro', 'mucha plata']
            for keyword in objection_keywords:
                if keyword in message:
                    objections_found.append(message[:100])
                    break
        
        result = ""
        if questions_found:
            result += f"PREGUNTAS IDENTIFICADAS: {'; '.join(questions_found)}\n"
        if objections_found:
            result += f"OBJECIONES IDENTIFICADAS: {'; '.join(objections_found)}\n"
        
        return result if result else "No se identificaron objeciones o preguntas específicas."


class AIMessageGenerator:
    """Generador de mensajes usando IA basado en contexto conversacional real"""
    
    def __init__(self):
        # Inicializar sistema de prompts
        self.prompt_system = FollowUpStagePrompts()
        self.context_extractor = ContextExtractor()
        
        # Cache para mensajes generados (evitar regenerar el mismo mensaje)
        self.message_cache = {}
        self.cache_max_size = 1000  # Límite de cache para evitar memoria excesiva
        
        # Contador de intentos fallidos para mejorar fallbacks
        self.ai_failure_count = 0
        self.ai_failure_threshold = 5  # Después de 5 fallos, usar más templates
        
        # Configuración de IA
        self.model = "gpt-4o-mini"
        self.max_tokens = 500
        self.temperature = 0.7
        
        # Backup templates para casos donde IA falla
        self.backup_templates = {
            0: "¡Hola! Me quedé pensando en nuestra charla sobre tu emprendimiento. ¿Ya pensaste en qué productos te gustaría arrancar? Con $40.000 podés empezar con productos que tienen hasta 150% de ganancia. ¿Te animo a dar el paso? 🚀",
            1: "¡Buenos días! Ayer charlamos sobre tu emprendimiento y me quedé con ganas de ayudarte. Las emprendedoras que arrancan esta semana tienen ventaja para la temporada fuerte. ¿Querés que te arme un combo perfecto para empezar?",
            7: "Una semana desde que charlamos... ¿Seguís con ganas de emprender o ya te desanimaste? Porque te voy a ser honesta: la diferencia entre las que lo logran y las que se quedan hablando es que las primeras ACTÚAN. ¿Vos sos de las que actúan? 💪",
            14: "2 semanas exactas. Si hubieras empezado hace 2 semanas, hoy estarías facturando. No te escribo para presionarte, pero cada día que pasa es plata que no entra. ¿Emprendemos juntas o nos despedimos? ❤️",
            66: "66 días... Mi último mensaje activo. Fue un placer acompañarte todo este tiempo. A partir de ahora solo te escribiré cada tanto para mantener contacto. La puerta de Royal siempre está abierta para vos 🚪✨",
            999: "¡Hola! ¿Cómo andás? Solo un saludito para contarte las novedades. Tenemos productos nuevos que están funcionando bárbaro. Si algún día te pinta emprender, acá estoy 😊"
        }
        
        logger.info("🤖 AIMessageGenerator inicializado con sistema de IA")
    
    async def generate_contextualized_message(self, stage: int, user_id: str, 
                                           context: ConversationMemory) -> Optional[str]:
        """Genera mensaje contextualizado usando IA"""
        try:
            # Verificar cache primero
            cache_key = f"{user_id}_{stage}_{context.last_interaction.isoformat()}"
            if cache_key in self.message_cache:
                logger.info(f"💾 Usando mensaje cacheado para {user_id}, etapa {stage}")
                return self.message_cache[cache_key]
            
            # Limpiar cache si está muy lleno
            if len(self.message_cache) > self.cache_max_size:
                self._clean_cache()
            
            # Obtener prompt base para la etapa
            stage_prompt = self.prompt_system.get_prompt_for_stage(stage)
            if not stage_prompt:
                logger.warning(f"⚠️ No hay prompt para etapa {stage}")
                return self._get_backup_message(stage, user_id, context)
            
            # Extraer contexto conversacional
            conversation_context = self._build_conversation_context(context)
            
            # Construir prompt completo para IA
            full_prompt = f"""{self.prompt_system.base_personality}

{stage_prompt}

CONTEXTO DE LA CONVERSACIÓN:
{conversation_context}

INSTRUCCIONES FINALES:
- Genera un mensaje natural que suene como Royalia
- Usa la información del contexto para personalizar
- Mantén el objetivo y tono de la etapa
- Máximo 200 palabras
- Incluí emojis naturalmente (sin abusar)
- El mensaje debe fluir como continuación natural de la conversación

GENERA EL MENSAJE DE FOLLOW-UP:"""
            
            # Verificar si debemos usar IA o fallback por fallos anteriores
            if self.ai_failure_count >= self.ai_failure_threshold:
                logger.info(f"🔄 Usando fallback por {self.ai_failure_count} fallos de IA")
                return self._get_backup_message(stage, user_id, context)
            
            # Generar mensaje usando IA
            generated_message = await self._call_ai_to_generate(full_prompt)
            
            if generated_message:
                # Reset failure counter en caso de éxito
                self.ai_failure_count = 0
                
                # Guardar en cache
                self.message_cache[cache_key] = generated_message
                logger.info(f"✅ Mensaje generado con IA para {user_id}, etapa {stage}")
                return generated_message
            else:
                # Incrementar contador de fallos
                self.ai_failure_count += 1
                logger.warning(f"⚠️ IA falló para etapa {stage} (fallo #{self.ai_failure_count}), usando backup")
                return self._get_backup_message(stage, user_id, context)
                
        except Exception as e:
            logger.error(f"❌ Error generando mensaje con IA para etapa {stage}: {e}")
            return self._get_backup_message(stage, user_id, context)
    
    def _build_conversation_context(self, context: ConversationMemory) -> str:
        """Construye contexto conversacional para el prompt de IA"""
        context_parts = []
        
        # Historial de conversación
        conversation_summary = self.context_extractor.extract_conversation_summary(context)
        context_parts.append(conversation_summary)
        
        # Intereses del usuario
        user_interests = self.context_extractor.extract_user_interests(context)
        context_parts.append(user_interests)
        
        # Información de presupuesto
        budget_info = self.context_extractor.extract_budget_info(context)
        context_parts.append(budget_info)
        
        # Objeciones y preguntas
        objections = self.context_extractor.extract_objections_and_questions(context)
        context_parts.append(objections)
        
        # Información adicional del perfil
        if context.user_profile:
            profile_info = f"PERFIL DEL USUARIO: {json.dumps(context.user_profile, indent=2)}"
            context_parts.append(profile_info)
        
        return "\n\n".join(context_parts)
    
    async def _call_ai_to_generate(self, prompt: str) -> Optional[str]:
        """Llama a la IA para generar el mensaje"""
        try:
            import openai
            import os
            
            # Configurar cliente OpenAI
            client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres Royalia, experta en generar mensajes de follow-up contextualizados para emprendedoras. Genera mensajes naturales, cálidos pero efectivos."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.choices and response.choices[0].message:
                generated_text = response.choices[0].message.content
                if generated_text and len(generated_text.strip()) > 10:
                    return generated_text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error llamando a OpenAI: {e}")
            return None
    
    def _get_backup_message(self, stage: int, user_id: str, context: ConversationMemory) -> str:
        """Obtiene mensaje de backup cuando IA falla"""
        # Obtener template base
        base_message = self.backup_templates.get(stage)
        
        if not base_message:
            # Template genérico si no hay específico
            if stage <= 7:
                base_message = "¡Hola! ¿Seguís con ganas de emprender? Me encantaría ayudarte a arrancar con los productos perfectos para vos 😊"
            elif stage <= 30:
                base_message = "¿Cómo andás? Hace un tiempo charlamos sobre emprendimiento. ¿Cambió algo en tu situación? 🤔"
            else:
                base_message = "¡Hola! Solo un saludito para mantenernos en contacto. ¿Todo bien? 💛"
        
        # Personalización básica
        try:
            # Personalizar según intereses si están disponibles
            if context.product_interests:
                interest = context.product_interests[0]
                base_message = base_message.replace("productos perfectos", f"productos de {interest}")
            
            # Personalizar según experiencia
            if hasattr(context, 'is_entrepreneur') and context.is_entrepreneur:
                base_message = base_message.replace("emprendimiento", "expandir tu negocio")
                
        except Exception as e:
            logger.warning(f"⚠️ Error en personalización básica: {e}")
        
        return base_message
    
    def _clean_cache(self):
        """Limpia el cache eliminando la mitad de las entradas más antiguas"""
        try:
            if not self.message_cache:
                return
            
            # Obtener todas las claves y eliminar la mitad más antigua
            cache_keys = list(self.message_cache.keys())
            items_to_remove = len(cache_keys) // 2
            
            for key in cache_keys[:items_to_remove]:
                self.message_cache.pop(key, None)
            
            logger.info(f"🧹 Cache limpiado: eliminadas {items_to_remove} entradas, quedan {len(self.message_cache)}")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache y sistema de fallos"""
        return {
            "cache_size": len(self.message_cache),
            "cache_max_size": self.cache_max_size,
            "ai_failure_count": self.ai_failure_count,
            "ai_failure_threshold": self.ai_failure_threshold,
            "using_fallback_mode": self.ai_failure_count >= self.ai_failure_threshold
        }
    
    def reset_failure_count(self):
        """Resetea el contador de fallos de IA (útil para recovery)"""
        self.ai_failure_count = 0
        logger.info("🔄 Contador de fallos de IA reseteado")


# FUNCIONES PRINCIPALES PARA USO DEL SISTEMA

async def get_followup_message_for_stage(stage: int, user_id: str, 
                                       use_ai_generation: bool = True) -> Optional[str]:
    """
    Obtiene un mensaje personalizado para una etapa específica usando IA o templates
    
    Args:
        stage: Número de etapa (0, 1, 2, 4, 7, etc.)
        user_id: ID del usuario para obtener contexto
        use_ai_generation: Si usar IA para generar mensaje o templates
    
    Returns:
        Mensaje personalizado o None si no se puede generar
    """
    try:
        # Obtener contexto del usuario
        context = await hybrid_context_manager.get_context(user_id)
        
        if use_ai_generation:
            # Generar mensaje usando IA con contexto completo (instancia global)
            ai_generator = get_global_ai_generator()
            message = await ai_generator.generate_contextualized_message(stage, user_id, context)
            
            if message:
                logger.info(f"✅ Mensaje generado con IA para usuario {user_id}, etapa {stage}")
                return message
            else:
                logger.warning(f"⚠️ IA falló, intentando con templates para etapa {stage}")
        
        # Fallback a sistema de templates mejorado
        return await get_followup_message_with_templates(stage, user_id, context)
        
    except Exception as e:
        logger.error(f"❌ Error generando mensaje para etapa {stage}: {e}")
        return None


async def get_followup_message_with_templates(stage: int, user_id: str, 
                                            context: ConversationMemory) -> Optional[str]:
    """
    Sistema de templates mejorado que usa el contexto conversacional
    
    Args:
        stage: Número de etapa
        user_id: ID del usuario
        context: Contexto conversacional del usuario
    
    Returns:
        Mensaje personalizado usando templates
    """
    try:
        # Usar el sistema anterior de templates como fallback
        templates = AIMessageGenerator()
        
        # Obtener template base
        base_message = templates.backup_templates.get(stage)
        
        if not base_message:
            logger.warning(f"⚠️ No hay template para etapa {stage}")
            return None
        
        # Personalizar con contexto disponible
        personalized_message = base_message
        
        # Personalización básica según contexto
        if context.product_interests:
            main_interest = context.product_interests[0]
            if main_interest in ["joyas", "maquillaje", "indumentaria"]:
                personalized_message = personalized_message.replace(
                    "productos perfectos", 
                    f"productos de {main_interest}"
                )
        
        # Personalización según presupuesto si está disponible
        if context.budget_range:
            personalized_message = personalized_message.replace(
                "$40.000", 
                context.budget_range
            )
        
        # Referencia a conversación previa si existe
        if context.interaction_history:
            last_interaction = context.interaction_history[-1]
            if last_interaction.get('role') == 'user':
                last_message = last_interaction.get('message', '')[:50]
                if len(last_message) > 10:
                    personalized_message = f"Me quedé pensando en lo que me dijiste: '{last_message}'...\n\n" + personalized_message
        
        logger.info(f"✅ Mensaje personalizado con templates para usuario {user_id}, etapa {stage}")
        return personalized_message
        
    except Exception as e:
        logger.error(f"❌ Error en templates para etapa {stage}: {e}")
        return None


# INSTANCIA GLOBAL DEL GENERADOR DE IA (Singleton pattern)
_global_ai_generator: Optional[AIMessageGenerator] = None

def get_global_ai_generator() -> AIMessageGenerator:
    """Obtiene la instancia global del generador de IA (patrón singleton)"""
    global _global_ai_generator
    if _global_ai_generator is None:
        _global_ai_generator = AIMessageGenerator()
    return _global_ai_generator

def get_all_available_stages() -> List[int]:
    """Retorna todas las etapas disponibles"""
    prompt_system = FollowUpStagePrompts()
    return prompt_system.get_all_stages()

def get_ai_cache_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del cache global de IA"""
    generator = get_global_ai_generator()
    return generator.get_cache_stats()

def reset_ai_failure_count():
    """Resetea el contador de fallos de IA global"""
    generator = get_global_ai_generator()
    generator.reset_failure_count()


# FUNCIÓN DE COMPATIBILIDAD PARA API ANTIGUA
def get_followup_message_for_stage_sync(stage: int, user_profile: Optional[Dict] = None, 
                                      interaction_count: int = 0) -> Optional[str]:
    """
    Función de compatibilidad sincrónica para mantener API anterior funcionando
    
    DEPRECATED: Usar get_followup_message_for_stage() async en su lugar
    
    Args:
        stage: Número de etapa
        user_profile: Perfil del usuario (formato legacy)
        interaction_count: Número de interacciones
    
    Returns:
        Mensaje usando templates (sin IA por limitaciones sync)
    """
    try:
        logger.warning(f"⚠️ Usando función de compatibilidad legacy para etapa {stage}")
        
        # Usar templates básicos sin IA (función sync no puede usar async AI)
        generator = get_global_ai_generator()
        
        # Crear contexto básico desde user_profile
        from hybrid_context_manager import ConversationMemory
        basic_context = ConversationMemory(user_id="legacy_user")
        
        if user_profile:
            basic_context.user_profile = user_profile
            basic_context.product_interests = [user_profile.get("interest", "general")]
            basic_context.budget_range = user_profile.get("budget_mentioned")
            basic_context.is_entrepreneur = user_profile.get("experience_level") != "empezando"
        
        # Obtener mensaje de backup con personalización básica
        backup_message = generator._get_backup_message(stage, "legacy_user", basic_context)
        
        return backup_message
        
    except Exception as e:
        logger.error(f"❌ Error en función de compatibilidad para etapa {stage}: {e}")
        
        # Fallback a mensajes súper básicos
        basic_messages = {
            0: "¡Hola! ¿Seguís interesada en emprender? 😊",
            1: "¡Buenos días! ¿Ya pensaste en arrancar tu emprendimiento?",
            7: "Una semana después... ¿Seguís con ganas de emprender?",
            14: "2 semanas... ¿Emprendemos juntas o nos despedimos?",
            66: "Mi último mensaje activo. Fue un placer acompañarte 💛",
            999: "¡Hola! ¿Cómo andás? Solo un saludito 👋"
        }
        
        return basic_messages.get(stage, "¡Hola! ¿Todo bien? 😊")


if __name__ == "__main__":
    # Test del sistema de IA para follow-up
    logger.info("🧪 Test de sistema AI para follow-up")
    
    stages = get_all_available_stages()
    logger.info(f"📋 Etapas disponibles: {stages}")
    
    logger.info("✅ Test completado - Sistema AI listo para usar")