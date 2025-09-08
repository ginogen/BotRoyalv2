"""
📤 Follow-up Manager para Royal Bot v2
Gestión de envío de mensajes de follow-up
"""

import asyncio
import logging
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import AsyncOpenAI

logger = logging.getLogger('followup.manager')

class FollowUpManager:
    """Manager para envío y gestión de follow-ups"""
    
    def __init__(self, database_url: str, evolution_api_url: str, 
                 evolution_token: str, instance_name: str,
                 openai_api_key: str, timezone: str = "America/Argentina/Cordoba"):
        self.database_url = database_url
        self.evolution_api_url = evolution_api_url.rstrip('/')
        self.evolution_token = evolution_token
        self.instance_name = instance_name
        self.timezone = pytz.timezone(timezone)
        
        # Cliente OpenAI para generar mensajes
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Cliente HTTP para Evolution API
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "apikey": evolution_token,  # CORRECTED: Evolution API uses 'apikey', not 'Authorization: Bearer'
                "Content-Type": "application/json"
            }
        )
    
    async def send_followup_message(self, user_id: str, stage: int) -> bool:
        """Enviar mensaje de follow-up para una etapa específica"""
        try:
            # Obtener datos del job
            job_data = await self._get_followup_job(user_id, stage)
            if not job_data:
                logger.error(f"❌ No se encontró job para {user_id} etapa {stage}")
                return False
            
            # Verificar blacklist
            if await self._is_user_blacklisted(user_id):
                logger.info(f"🚫 Usuario {user_id} en blacklist, omitiendo follow-up")
                await self._mark_job_cancelled(user_id, stage)
                return False
            
            # Generar mensaje personalizado
            message = await self._generate_followup_message(user_id, stage, job_data)
            if not message:
                logger.error(f"❌ No se pudo generar mensaje para {user_id} etapa {stage}")
                return False
            
            # Enviar mensaje vía Evolution API
            phone = job_data['phone']
            success = await self._send_whatsapp_message(phone, message)
            
            if success:
                # Registrar en historial
                await self._record_followup_history(user_id, stage, message, job_data)
                logger.info(f"✅ Follow-up enviado: {user_id} etapa {stage}")
                return True
            else:
                logger.error(f"❌ Falló envío WhatsApp para {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando follow-up: {e}")
            return False
    
    async def _get_followup_job(self, user_id: str, stage: int) -> Optional[Dict[str, Any]]:
        """Obtener datos del job de follow-up"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM follow_up_jobs 
                        WHERE user_id = %s AND stage = %s AND status = 'pending'
                    """, (user_id, stage))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo job: {e}")
            return None
    
    async def _is_user_blacklisted(self, user_id: str) -> bool:
        """Verificar si el usuario está en blacklist"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 1 FROM follow_up_blacklist WHERE user_id = %s
                    """, (user_id,))
                    
                    return cursor.fetchone() is not None
                    
        except Exception as e:
            logger.error(f"❌ Error verificando blacklist: {e}")
            return False
    
    async def _generate_followup_message(self, user_id: str, stage: int, 
                                       job_data: Dict[str, Any]) -> Optional[str]:
        """🚨 VERSIÓN SIMPLIFICADA: Generar follow-up basado solo en conversación real"""
        try:
            # Obtener contexto del usuario
            context = await self._get_user_context(user_id)
            if not context:
                logger.error(f"❌ No se encontró contexto para {user_id}")
                return None
            
            # 🔍 VERIFICAR SI HAY CONVERSACIÓN REAL
            if not context.get('has_real_conversation', False):
                logger.warning(f"⚠️ {user_id} no tiene conversación real, usando template básico")
                return self._get_fallback_template(stage)
            
            # 🤖 PROMPT SIMPLIFICADO - Solo basado en conversación
            conversation_text = self._build_conversation_context(context['interaction_history'])
            prompt = self._build_simple_prompt(stage, conversation_text)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_simple_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,  # Mensajes más concisos
                temperature=0.7  # Balance entre creatividad y consistencia
            )
            
            message = response.choices[0].message.content.strip()
            logger.info(f"🤖 Follow-up generado para {user_id} etapa {stage} con conversación real")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error generando mensaje: {e}")
            # Fallback a template básico
            return self._get_fallback_template(stage)
    
    def _build_conversation_context(self, interactions: List[Dict[str, Any]]) -> str:
        """Construir contexto de conversación simple"""
        if not interactions:
            return "Sin conversación previa"
        
        conversation_lines = []
        for i, interaction in enumerate(interactions[-15:], 1):  # Últimos 15 mensajes
            role = "Usuario" if interaction.get('role') == 'user' else "Royalia"
            message = interaction.get('message', '')[:150]  # Limitar longitud
            conversation_lines.append(f"{i}. {role}: {message}")
        
        return "\n".join(conversation_lines)
    
    def _build_simple_prompt(self, stage: int, conversation_text: str) -> str:
        """Prompt simplificado basado solo en conversación"""
        stage_goals = {
            1: "retomar la conversación de manera natural",
            2: "ofrecer ayuda basándote en lo que habló antes",
            3: "hacer una sugerencia específica relacionada con la charla",
            4: "dar una recomendación personalizada",
            5: "compartir algo útil o interesante",
            6: "hacer una oferta con urgencia moderada",
            7: "mensaje de cierre amigable"
        }
        
        goal = stage_goals.get(stage, "hacer seguimiento general")
        
        return f"""Basándote en esta conversación previa con el usuario, genera un mensaje de follow-up para {goal}.

CONVERSACIÓN PREVIA:
{conversation_text}

INSTRUCCIONES:
- Usa tono argentino natural (che, dale, bárbaro)
- Haz referencia específica a algo que se habló antes
- Máximo 150 caracteres
- No te presentes de nuevo
- Incluye una pregunta o call-to-action natural
- El mensaje debe sonar como continuación natural de la charla

Genera SOLO el mensaje, sin explicaciones."""
    
    def _get_simple_system_prompt(self) -> str:
        """System prompt simplificado"""
        return """Eres Royalia de Royal Company. Tu personalidad es amigable, argentina, y conversacional.
        
- Usas lenguaje argentino natural ("che", "dale", "bárbaro", "genial")
- Eres cálida pero profesional
- Te enfocas en ayudar genuinamente al usuario
- Recuerdas conversaciones previas y haces referencias naturales
- NO eres insistente en ventas
- Generas mensajes concisos y naturales"""
    
    def _get_fallback_template(self, stage: int) -> str:
        """Templates básicos cuando no hay conversación real"""
        templates = {
            1: "Hola! ¿Cómo andás? Vi que estuviste por la tienda. ¿En qué te puedo ayudar?",
            2: "¡Dale! ¿Seguís viendo productos o necesitás que te ayude con algo específico?",
            3: "¿Todo bien? ¿Encontraste algo que te guste o querés que te recomiende algo?",
            4: "Che, ¿pudiste ver bien los productos? ¿Te ayudo a elegir algo?",
            5: "¿Cómo va todo? ¿Alguna consulta sobre los productos que viste?",
            6: "¡Última oportunidad! Tenemos ofertas especiales por poco tiempo. ¿Te interesa?",
            7: "No quiero molestarte, pero si necesitás algo, estoy acá. ¿Todo bien?"
        }
        return templates.get(stage, templates[1])
    
    def _build_generation_prompt(self, stage: int, context: Dict[str, Any], 
                               job_data: Dict[str, Any], base_template: str) -> str:
        """Construir prompt avanzado usando conversación completa y contexto rico"""
        user_profile = context.get('user_profile', {})
        recent_products = context.get('recent_products', [])
        is_entrepreneur = context.get('is_entrepreneur', False)
        experience_level = context.get('experience_level', '')
        product_interests = context.get('product_interests', [])
        budget_range = context.get('budget_range', '')
        
        # Obtener historial completo de interacciones
        interaction_history = context.get('interaction_history', [])
        last_message = job_data.get('last_user_message', '')
        
        # Construir contexto conversacional
        conversation_context = ""
        if interaction_history:
            conversation_context = "\nHISTORIAL DE LA CONVERSACIÓN (últimos mensajes):\n"
            # Mostrar últimos 15 mensajes para contexto completo
            for i, interaction in enumerate(interaction_history[-15:], 1):
                role = "Usuario" if interaction["role"] == "user" else "Royalia"
                message = interaction["message"][:200]  # Más espacio para contexto
                conversation_context += f"{i}. {role}: {message}\n"
        
        # Construir contexto de productos vistos
        products_context = ""
        if recent_products:
            products_context = "\nPRODUCTOS QUE EL USUARIO VIO:\n"
            for i, product in enumerate(recent_products[-5:], 1):
                products_context += f"{i}. {product.get('name', 'Sin nombre')} - ${product.get('price', 'N/A')}\n"
        
        # Construir perfil detallado
        profile_context = f"""
PERFIL DEL USUARIO:
- Tipo: {'Emprendedor' if is_entrepreneur else 'Comprador/Cliente'}
- Experiencia: {experience_level or 'No determinada'}
- Intereses detectados: {', '.join(product_interests) if product_interests else 'Ninguno específico'}
- Presupuesto mencionado: {budget_range or 'No mencionado'}
- Estado actual: {context.get('current_state', 'navegando')}
"""

        # Instrucciones específicas por etapa
        stage_instructions = {
            1: "Mensaje de reconexión suave que haga referencia a la conversación previa",
            2: "Ofrecimiento de ayuda basado en lo que discutieron antes", 
            3: "Propuesta específica relacionada con sus productos de interés",
            4: "Recomendaciones personalizadas basadas en su perfil",
            5: "Casos de éxito relevantes a su tipo de emprendimiento",
            6: "Oferta especial con urgencia moderada",
            7: "Mensaje de cierre respetuoso y no insistente"
        }
        
        prompt = f"""
Eres Royalia, el asistente de Royal Company. Vas a generar un mensaje de follow-up personalizado para reconectar con este usuario después de un tiempo de inactividad.

{profile_context}
{conversation_context}
{products_context}

ÚLTIMO MENSAJE DEL USUARIO: "{last_message}"

OBJETIVO DE ESTA ETAPA ({stage}): {stage_instructions.get(stage, 'Follow-up general')}

INSTRUCCIONES CRÍTICAS:
- Este mensaje debe parecer una CONTINUACIÓN NATURAL de la conversación previa
- Haz referencia específica a productos que vio o temas que discutieron
- Usa un tono conversacional argentino, como si fueras un amigo que retoma la charla
- El usuario ya te conoce, NO te presentes de nuevo
- Si vio productos específicos, mencionálos por nombre
- Si es emprendedor con experiencia conocida, adapta el mensaje a su nivel
- Si mencionó intereses específicos, conecta con esos intereses
- Máximo 250 caracteres para WhatsApp
- Incluye una pregunta o call-to-action natural
- NO uses templates genéricos, personaliza 100% basado en SU conversación

EJEMPLOS DEL TONO DESEADO:
- "Che, ¿seguís pensando en el combo de joyas que vimos la otra vez?"
- "¿Cómo va todo? Me quedé pensando en lo que me contaste sobre tu emprendimiento"
- "¡Dale! ¿Al final te decidiste por alguno de los productos que te mostré?"

GENERA SOLO EL MENSAJE, sin explicaciones adicionales.
"""
        return prompt
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Construir system prompt personalizado según el perfil del usuario"""
        is_entrepreneur = context.get('is_entrepreneur', False)
        experience_level = context.get('experience_level', '')
        product_interests = context.get('product_interests', [])
        
        base_system = """Eres Royalia, el asistente de Royal Company. Tu personalidad es amigable, argentina, y conversacional. 

CARACTERÍSTICAS CLAVE:
- Usas lenguaje argentino natural ("che", "dale", "bárbaro", "genial")
- Eres cálida pero profesional
- Te enfocas en ayudar genuinamente al usuario
- NO eres insistente ni agresiva en ventas
- Recuerdas conversaciones previas y haces referencias naturales"""
        
        if is_entrepreneur:
            if experience_level == "empezando":
                base_system += """

ESPECIALIZACIÓN: Este usuario es un EMPRENDEDOR PRINCIPIANTE
- Tono de mentora y acompañante 
- Enfócate en educación y guía
- Menciona que "todos empezamos así"
- Ofrece tips y consejos además de productos
- Usa frases como "para arrancar te conviene...", "ideal para principiantes"
"""
            elif experience_level == "experimentado":
                base_system += """

ESPECIALIZACIÓN: Este usuario es un EMPRENDEDOR EXPERIMENTADO
- Tono de colega y partner comercial
- Habla de números, márgenes, y rentabilidad
- Menciona "para tu negocio", "sabés que...", "como ya tenés experiencia"
- Enfócate en expansión y optimización
- Usa frases como "para ampliar tu catálogo", "sabés cómo funciona esto"
"""
            elif experience_level == "renovando_stock":
                base_system += """

ESPECIALIZACIÓN: Este usuario RENUEVA STOCK
- Tono directo y eficiente
- Enfócate en disponibilidad y reposición
- Menciona "para reponer", "tenemos stock nuevo", "las novedades"
- Habla de productos que "se venden rápido"
- Usa frases como "para renovar tu stock", "llegaron productos nuevos"
"""
        else:
            base_system += """

ESPECIALIZACIÓN: Este usuario es COMPRADOR/CLIENTE
- Tono amigable y servicial
- Enfócate en beneficios personales del producto
- Menciona calidad, diseño, y satisfacción personal
- Usa frases como "para vos", "te va a encantar", "perfecto para tu estilo"
"""
        
        if product_interests:
            interests_text = ', '.join(product_interests)
            base_system += f"""

INTERESES CONOCIDOS: {interests_text}
- Conecta siempre con estos intereses específicos
- Haz referencias naturales a estos productos
- Usa frases como "seguís interesada en {interests_text}?"
"""
        
        return base_system
    
    def _get_stage_description(self, stage: int) -> str:
        """Obtener descripción de la etapa"""
        descriptions = {
            1: "Recordatorio suave - ¿Necesitas más info?",
            2: "Ayuda disponible - Estoy aquí si tienes dudas",
            3: "Oferta especial - Descuento o beneficio",
            4: "Productos recomendados - Basado en su interés",
            5: "Casos de éxito - Testimonios relevantes", 
            6: "Descuento temporal - Urgencia limitada",
            7: "Última oportunidad - Final suave",
            8: "Despedida - Opción de opt-out"
        }
        return descriptions.get(stage, "Follow-up general")
    
    async def _get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """🚨 VERSIÓN SIMPLIFICADA: Obtener contexto SOLO de conversation_contexts"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Obtener contexto completo de conversation_contexts
                    cursor.execute("""
                        SELECT context_data, last_interaction
                        FROM conversation_contexts 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    context_result = cursor.fetchone()
                    if not context_result:
                        logger.warning(f"⚠️ No se encontró contexto para {user_id}")
                        return None
                    
                    context_data = context_result.get('context_data', {})
                    
                    # Extraer historial de interacciones del context_data
                    interaction_history = context_data.get('interaction_history', [])
                    
                    # Filtrar solo mensajes relevantes (user/assistant, no system internos)
                    relevant_interactions = []
                    for interaction in interaction_history:
                        role = interaction.get('role', '')
                        message = interaction.get('message', '')
                        
                        # Solo incluir mensajes reales de conversación
                        if role in ['user', 'assistant'] and message and not any(skip_phrase in message.lower() for skip_phrase in [
                            'escalado a humano', 'información faltante', 'necesita asistencia', 
                            'mostré categorías', 'mostré productos'
                        ]):
                            relevant_interactions.append(interaction)
                    
                    # Tomar últimos 20 mensajes relevantes
                    recent_interactions = relevant_interactions[-20:] if relevant_interactions else []
                    
                    logger.info(f"✅ Contexto para {user_id}: {len(recent_interactions)} mensajes relevantes de {len(interaction_history)} totales")
                    
                    return {
                        'user_id': user_id,
                        'interaction_history': recent_interactions,
                        'last_interaction': context_result.get('last_interaction'),
                        'has_real_conversation': len(recent_interactions) >= 2  # Al menos 2 mensajes reales
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto: {e}")
            return None
    
    async def _send_whatsapp_message(self, phone: str, message: str) -> bool:
        """Enviar mensaje via Evolution API"""
        try:
            logger.info(f"📱 [DEBUG] Intentando enviar mensaje a {phone}")
            logger.info(f"🔗 [DEBUG] Evolution API URL: {self.evolution_api_url}")
            logger.info(f"📱 [DEBUG] Instance: {self.instance_name}")
            # TEMPORAL: Log token parcial para debug
            token_preview = self.evolution_token[:10] + "..." if self.evolution_token else "NO_TOKEN"
            logger.info(f"🔑 [DEBUG] Token preview: {token_preview}")
            
            # Limpiar número de teléfono (sin auto-prefijo de país)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            url = f"{self.evolution_api_url}/message/sendText/{self.instance_name}"
            logger.info(f"🔗 [DEBUG] URL completa: {url}")
            logger.info(f"📱 [DEBUG] Número limpio: {clean_phone}")
            
            payload = {
                "number": clean_phone,
                "text": message
            }
            
            response = await self.http_client.post(url, json=payload)
            logger.info(f"📡 [DEBUG] Response status: {response.status_code}")
            logger.info(f"📡 [DEBUG] Response body: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"✅ [DEBUG] Mensaje enviado exitosamente a {phone}")
                return True
            else:
                logger.error(f"❌ Error Evolution API: {response.status_code} - {response.text}")
                # TEMPORAL: Log detallado del error 400
                logger.error(f"📋 [ERROR DEBUG] Response body: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando WhatsApp: {e}")
            return False
    
    async def _record_followup_history(self, user_id: str, stage: int, 
                                     message: str, job_data: Dict[str, Any]):
        """Registrar follow-up en el historial"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO follow_up_history 
                        (user_id, phone, stage, message_sent, template_used, generation_model)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        job_data['phone'],
                        stage,
                        message,
                        f"stage_{stage}_template",
                        "gpt-4o-mini"
                    ))
                    
        except Exception as e:
            logger.error(f"❌ Error registrando historial: {e}")
    
    async def _mark_job_cancelled(self, user_id: str, stage: int):
        """Marcar job como cancelado"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE follow_up_jobs 
                        SET status = 'cancelled', processed_at = %s
                        WHERE user_id = %s AND stage = %s
                    """, (datetime.now(self.timezone), user_id, stage))
                    
        except Exception as e:
            logger.error(f"❌ Error marcando job cancelado: {e}")
    
    async def handle_user_response(self, user_id: str):
        """Manejar respuesta del usuario (cancelar follow-ups restantes)"""
        try:
            # Cancelar todos los follow-ups pendientes
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE follow_up_jobs 
                        SET status = 'cancelled', processed_at = %s
                        WHERE user_id = %s AND status = 'pending'
                    """, (datetime.now(self.timezone), user_id))
                    
                    cancelled_count = cursor.rowcount
                    
                    # Marcar respuestas en el historial
                    cursor.execute("""
                        UPDATE follow_up_history 
                        SET user_responded = TRUE, responded_at = %s
                        WHERE user_id = %s 
                        AND sent_at > %s 
                        AND user_responded = FALSE
                    """, (
                        datetime.now(self.timezone), 
                        user_id,
                        datetime.now(self.timezone) - timedelta(days=1)
                    ))
                    
                    logger.info(f"🔄 Usuario {user_id} respondió, cancelados {cancelled_count} follow-ups")
                    
        except Exception as e:
            logger.error(f"❌ Error manejando respuesta del usuario: {e}")
    
    async def add_user_to_blacklist(self, user_id: str, phone: str, reason: str = "user_request"):
        """Agregar usuario a blacklist de follow-ups"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Agregar a blacklist
                    cursor.execute("""
                        INSERT INTO follow_up_blacklist (user_id, phone, reason)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            reason = EXCLUDED.reason,
                            added_at = CURRENT_TIMESTAMP
                    """, (user_id, phone, reason))
                    
                    # Cancelar follow-ups pendientes
                    cursor.execute("""
                        UPDATE follow_up_jobs 
                        SET status = 'cancelled', processed_at = %s
                        WHERE user_id = %s AND status = 'pending'
                    """, (datetime.now(self.timezone), user_id))
                    
                    logger.info(f"🚫 Usuario {user_id} agregado a blacklist: {reason}")
                    
        except Exception as e:
            logger.error(f"❌ Error agregando a blacklist: {e}")
    
    async def get_followup_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de follow-ups"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Estadísticas generales
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_pending,
                            COUNT(DISTINCT user_id) as unique_users,
                            MIN(scheduled_for) as next_scheduled
                        FROM follow_up_jobs 
                        WHERE status = 'pending'
                    """)
                    pending_stats = cursor.fetchone()
                    
                    # Estadísticas por etapa (últimos 7 días)
                    cursor.execute("""
                        SELECT 
                            stage,
                            COUNT(*) as sent_count,
                            COUNT(CASE WHEN user_responded THEN 1 END) as response_count,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as response_rate
                        FROM follow_up_history 
                        WHERE sent_at > %s
                        GROUP BY stage
                        ORDER BY stage
                    """, (datetime.now(self.timezone) - timedelta(days=7),))
                    
                    stage_stats = [dict(row) for row in cursor.fetchall()]
                    
                    # Usuarios en blacklist
                    cursor.execute("SELECT COUNT(*) as blacklisted FROM follow_up_blacklist")
                    blacklist_count = cursor.fetchone()['blacklisted']
                    
                    return {
                        "pending_jobs": pending_stats['total_pending'],
                        "unique_users": pending_stats['unique_users'],
                        "next_scheduled": pending_stats['next_scheduled'],
                        "stage_performance": stage_stats,
                        "blacklisted_users": blacklist_count,
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {"error": str(e)}
    
    async def _send_whatsapp_message(self, phone: str, message: str) -> bool:
        """Enviar mensaje via Evolution API con reintentos"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Limpiar número (sin auto-prefijo de país)
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                
                url = f"{self.evolution_api_url}/message/sendText/{self.instance_name}"
                
                payload = {
                    "number": clean_phone,
                    "text": message
                }
                
                # TEMPORAL: Log payload completo para debug
                logger.info(f"📋 [DEBUG] Payload enviado: {payload}")
                
                response = await self.http_client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.debug(f"📱 Mensaje enviado a {phone} (intento {attempt + 1})")
                    return True
                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # Backoff exponencial
                    logger.warning(f"⏳ Rate limit, esperando {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code in [500, 502, 503, 504]:  # Server errors
                    logger.warning(f"🔄 Error del servidor {response.status_code}, reintentando...")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Error Evolution API después de {max_retries} intentos: {response.status_code}")
                        return False
                    await asyncio.sleep(2)  # Pausa más larga para errores del servidor
                    continue
                else:
                    # Errores 4xx (Bad Request, etc.) - No reintentar
                    logger.error(f"❌ Error Evolution API (no reintentable): {response.status_code}")
                    logger.error(f"📋 [ERROR] Response body: {response.text}")
                    return False  # Fallar inmediatamente
                    
            except Exception as e:
                logger.error(f"❌ Error intento {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2)
        
        return False
    
    async def _record_followup_history(self, user_id: str, stage: int, 
                                     message: str, job_data: Dict[str, Any]):
        """Registrar follow-up enviado en el historial"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO follow_up_history 
                        (user_id, phone, stage, message_sent, template_used, generation_model)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        job_data['phone'],
                        stage,
                        message,
                        f"stage_{stage}_ai_generated",
                        "gpt-4o-mini"
                    ))
                    
        except Exception as e:
            logger.error(f"❌ Error registrando historial: {e}")
    
    async def _get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener contexto completo del usuario"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Contexto principal
                    cursor.execute("""
                        SELECT * FROM conversation_contexts WHERE user_id = %s
                    """, (user_id,))
                    context = cursor.fetchone()
                    
                    if not context:
                        return None
                    
                    # Últimas interacciones
                    cursor.execute("""
                        SELECT role, message, created_at 
                        FROM user_interactions 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 10
                    """, (user_id,))
                    
                    interactions = [dict(row) for row in cursor.fetchall()]
                    
                    return {
                        **dict(context),
                        'recent_interactions': interactions
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto: {e}")
            return None
    
    async def close(self):
        """Cerrar conexiones"""
        await self.http_client.aclose()