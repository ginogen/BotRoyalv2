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
        """Generar mensaje de follow-up personalizado usando IA"""
        try:
            # Obtener contexto del usuario
            context = await self._get_user_context(user_id)
            if not context:
                logger.error(f"❌ No se encontró contexto para {user_id}")
                return None
            
            # Importar templates
            from .follow_up_templates import FollowUpTemplateEngine
            template_engine = FollowUpTemplateEngine()
            
            # Obtener template base para la etapa
            base_template = template_engine.get_stage_template(stage)
            
            # Generar mensaje personalizado
            prompt = self._build_generation_prompt(stage, context, job_data, base_template)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres Royal Bot, un asistente especializado en productos para emprendedores. Genera mensajes de follow-up naturales y conversacionales."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            message = response.choices[0].message.content.strip()
            logger.debug(f"🤖 Mensaje generado para {user_id} etapa {stage}")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error generando mensaje: {e}")
            return None
    
    def _build_generation_prompt(self, stage: int, context: Dict[str, Any], 
                               job_data: Dict[str, Any], base_template: str) -> str:
        """Construir prompt para generar mensaje personalizado"""
        user_profile = context.get('user_profile', {})
        recent_products = context.get('recent_products', [])
        is_entrepreneur = context.get('is_entrepreneur', False)
        last_message = job_data.get('last_user_message', '')
        
        prompt = f"""
Genera un mensaje de follow-up para la etapa {stage} con estas características:

CONTEXTO DEL USUARIO:
- Tipo: {'Emprendedor' if is_entrepreneur else 'Comprador'}
- Último mensaje: "{last_message}"
- Productos vistos: {recent_products[:3] if recent_products else 'Ninguno'}
- Perfil: {user_profile}

TEMPLATE BASE:
{base_template}

REQUISITOS:
- Máximo 150 caracteres
- Tono conversacional y amigable
- Mencionar productos específicos si los vió
- No usar emojis excesivos
- Incluir call-to-action sutil
- Hacer referencia al contexto previo

ETAPA {stage}: {self._get_stage_description(stage)}
"""
        return prompt
    
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
        """Obtener contexto completo del usuario"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT context_data, user_profile, preferences, 
                               is_entrepreneur, product_interests, current_state
                        FROM conversation_contexts 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
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
            
            # Limpiar número de teléfono
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            if not clean_phone.startswith('54'):
                clean_phone = f"54{clean_phone}"
            
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
                # Limpiar número
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                if not clean_phone.startswith('54'):
                    clean_phone = f"54{clean_phone}"
                
                url = f"{self.evolution_api_url}/message/sendText/{self.instance_name}"
                
                payload = {
                    "number": clean_phone,
                    "text": message
                }
                
                response = await self.http_client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.debug(f"📱 Mensaje enviado a {phone} (intento {attempt + 1})")
                    return True
                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # Backoff exponencial
                    logger.warning(f"⏳ Rate limit, esperando {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Error Evolution API: {response.status_code}")
                    if attempt == max_retries - 1:
                        return False
                    await asyncio.sleep(1)
                    
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