"""
🕒 Follow-up Scheduler para Royal Bot v2
Sistema de programación inteligente de follow-ups
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.interval import IntervalTrigger
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger('followup.scheduler')

class FollowUpScheduler:
    """Scheduler principal para follow-ups automáticos"""
    
    def __init__(self, database_url: str, timezone: str = "America/Argentina/Cordoba",
                 evolution_api_url: str = None, evolution_token: str = None, 
                 instance_name: str = None, openai_api_key: str = None):
        self.database_url = database_url
        self.timezone = pytz.timezone(timezone)
        self.scheduler = None
        self.is_running = False
        
        # Configuración Evolution API para el manager
        self.evolution_api_url = evolution_api_url
        self.evolution_token = evolution_token
        self.instance_name = instance_name
        self.openai_api_key = openai_api_key
        
        # Configuración de etapas (en horas)
        self.stage_delays = {
            1: 0.167,  # TEMPORAL: 10 minutos para pruebas (antes 1 hora)
            2: 6,      # 6 horas  
            3: 24,     # 1 día
            4: 48,     # 2 días
            5: 72,     # 3 días
            6: 96,     # 4 días
            7: 120,    # 5 días
            8: 168     # 7 días
        }
        
        # Horarios permitidos
        self.start_hour = 9   # 9 AM
        self.end_hour = 21    # 9 PM
        self.allowed_weekdays = [1, 2, 3, 4, 5, 6]  # Lunes a sábado
    
    def _ensure_argentina_timezone(self, dt_input) -> datetime:
        """
        Helper para asegurar que cualquier datetime tenga timezone de Argentina
        """
        if isinstance(dt_input, str):
            # Parsear el datetime string con manejo correcto de timezone
            if dt_input.endswith('Z'):
                # UTC format - convertir a Argentina
                dt = datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
                return dt.astimezone(self.timezone)
            elif '+' in dt_input or '-' in dt_input[-6:]:
                # Ya tiene timezone - parsear y convertir a Argentina
                dt = datetime.fromisoformat(dt_input)
                return dt.astimezone(self.timezone)
            else:
                # Sin timezone - asumir Argentina timezone
                dt = datetime.fromisoformat(dt_input)
                if dt.tzinfo is None:
                    return self.timezone.localize(dt)
                return dt
        elif isinstance(dt_input, datetime):
            # Ya es datetime object
            if dt_input.tzinfo is None:
                return self.timezone.localize(dt_input)
            else:
                return dt_input.astimezone(self.timezone)
        else:
            raise ValueError(f"Tipo no soportado para datetime: {type(dt_input)}")
        
    async def initialize(self):
        """Inicializar el scheduler"""
        try:
            # Configurar scheduler sin jobstore persistente (más simple)
            executors = {
                'default': AsyncIOExecutor()
            }
            
            job_defaults = {
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 300  # 5 minutos de gracia
            }
            
            self.scheduler = AsyncIOScheduler(
                executors=executors, 
                job_defaults=job_defaults,
                timezone=self.timezone
            )
            
            # Agregar job recurrente para procesar follow-ups pendientes
            self.scheduler.add_job(
                func=self._process_pending_followups,
                trigger='interval',
                minutes=1,  # Revisar cada minuto
                id='process_pending_followups',
                replace_existing=True
            )
            
            # Agregar job para detectar usuarios inactivos
            self.scheduler.add_job(
                func=self._check_inactive_users,
                trigger='interval',
                minutes=5,  # Revisar cada 5 minutos
                id='check_inactive_users',
                replace_existing=True
            )
            
            # Agregar job de limpieza diaria
            self.scheduler.add_job(
                func=self._daily_cleanup,
                trigger='cron',
                hour=2,  # 2 AM
                id='daily_cleanup',
                replace_existing=True
            )
            
            logger.info("📅 Follow-up scheduler inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando scheduler: {e}")
            raise
    
    def start(self):
        """Iniciar el scheduler"""
        if not self.scheduler:
            raise RuntimeError("Scheduler no inicializado. Llama initialize() primero.")
            
        self.scheduler.start()
        self.is_running = True
        logger.info("🚀 Follow-up scheduler iniciado")
    
    def stop(self):
        """Detener el scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("⏹️ Follow-up scheduler detenido")
    
    async def _process_pending_followups(self):
        """Procesar follow-ups pendientes que ya llegaron a su hora"""
        try:
            current_time = datetime.now(self.timezone)
            
            # TEMPORAL: Para diagnóstico
            logger.info(f"🔍 [DEBUG] Buscando follow-ups pendientes antes de {current_time}")
            logger.info(f"🔍 [DEBUG] Zona horaria: {self.timezone}")
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Buscar follow-ups que ya deben enviarse
                    cursor.execute("""
                        SELECT user_id, stage, scheduled_for, phone, status
                        FROM follow_up_jobs 
                        WHERE status = 'pending' 
                        AND scheduled_for <= %s
                        ORDER BY scheduled_for
                        LIMIT 10
                    """, (current_time,))
                    
                    pending_jobs = cursor.fetchall()
                    
                    # TEMPORAL: Para diagnóstico
                    logger.info(f"🔍 [DEBUG] Follow-ups pendientes encontrados: {len(pending_jobs)}")
                    if pending_jobs:
                        logger.info(f"🔍 [DEBUG] Primer job: user_id={pending_jobs[0]['user_id']}, stage={pending_jobs[0]['stage']}, scheduled_for={pending_jobs[0]['scheduled_for']}")
                    
                    for job in pending_jobs:
                        await self._execute_followup(job['user_id'], job['stage'])
                        
        except Exception as e:
            logger.error(f"❌ Error procesando follow-ups pendientes: {e}")

    async def _check_inactive_users(self):
        """Revisar usuarios inactivos y programar follow-ups"""
        try:
            logger.debug("🔍 Revisando usuarios inactivos...")
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Buscar usuarios inactivos que no tienen follow-ups programados
                    query = """
                    SELECT DISTINCT cc.user_id, cc.last_interaction, cc.context_data
                    FROM conversation_contexts cc
                    LEFT JOIN follow_up_blacklist bl ON cc.user_id = bl.user_id
                    WHERE bl.user_id IS NULL  -- No está en blacklist
                    AND cc.last_interaction < %s  -- Inactivo por más de 1 hora
                    AND NOT EXISTS (  -- No tiene follow-ups pendientes
                        SELECT 1 FROM follow_up_jobs fj 
                        WHERE fj.user_id = cc.user_id 
                        AND fj.status = 'pending'
                    )
                    """
                    
                    # TEMPORAL: Reducido a 10 minutos para pruebas
                    cutoff_time = datetime.now(self.timezone) - timedelta(minutes=10)
                    
                    logger.debug(f"🔍 Checking inactive users since: {cutoff_time}")
                    logger.info(f"🧪 [PRUEBA] Detectando usuarios inactivos por más de 10 minutos")
                    logger.debug(f"🔍 Timezone: {self.timezone}")
                    
                    cursor.execute(query, (cutoff_time,))
                    inactive_users = cursor.fetchall()
                    
                    logger.info(f"👥 Encontrados {len(inactive_users)} usuarios inactivos")
                    
                    # TEMPORAL: Para diagnóstico
                    if inactive_users:
                        logger.info(f"🔍 [DEBUG] Primer usuario inactivo: user_id={inactive_users[0]['user_id']}, last_interaction={inactive_users[0]['last_interaction']}")
                    else:
                        logger.info(f"🔍 [DEBUG] No se encontraron usuarios inactivos")
                    
                    for user in inactive_users:
                        # TEMPORAL: Para diagnóstico
                        logger.info(f"🔍 [DEBUG] Programando follow-ups para usuario inactivo: {user['user_id']}")
                        await self._schedule_user_followups(user)
                        
        except Exception as e:
            logger.error(f"❌ Error revisando usuarios inactivos: {e}")
    
    async def _schedule_user_followups(self, user_data: Dict[str, Any]):
        """Programar todos los follow-ups para un usuario"""
        try:
            user_id = user_data['user_id']
            
            # CRITICAL FIX: Usar timestamp desde context_data que tiene timezone correcto
            context_data = user_data.get('context_data', {})
            last_interaction = context_data.get('last_interaction') or user_data['last_interaction']
            
            # Obtener el último mensaje del usuario
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT message, created_at 
                        FROM user_interactions 
                        WHERE user_id = %s AND role = 'user'
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (user_id,))
                    last_msg = cursor.fetchone()
            
            # Usar helper para asegurar timezone correcto
            last_interaction = self._ensure_argentina_timezone(last_interaction)
            
            # TEMPORAL: Debug logging para timezone
            logger.info(f"🕐 [TIMEZONE DEBUG] Usuario: {user_id}")
            logger.info(f"🕐 [TIMEZONE DEBUG] last_interaction desde campo BD: {user_data.get('last_interaction')}")
            logger.info(f"🕐 [TIMEZONE DEBUG] last_interaction desde context_data: {context_data.get('last_interaction')}")
            logger.info(f"🕐 [TIMEZONE DEBUG] last_interaction procesado final: {last_interaction}")
            logger.info(f"🕐 [TIMEZONE DEBUG] timezone actual: {self.timezone}")
            
            # Programar cada etapa del follow-up
            for stage, delay_hours in self.stage_delays.items():
                scheduled_time = last_interaction + timedelta(hours=delay_hours)
                
                # Stage 1 se envía inmediatamente, otros stages respetan horario comercial
                if stage > 1:
                    scheduled_time = self._adjust_to_business_hours(scheduled_time)
                # Stage 1 no ajusta horario - se envía inmediatamente cuando es hora
                
                await self._create_followup_job(
                    user_id=user_id,
                    stage=stage,
                    scheduled_for=scheduled_time,
                    context_snapshot=user_data.get('context_data', {}),
                    last_user_message=last_msg['message'] if last_msg else None
                )
            
            logger.info(f"📅 Follow-ups programados para usuario {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error programando follow-ups para {user_data.get('user_id')}: {e}")
    
    def _adjust_to_business_hours(self, dt: datetime) -> datetime:
        """Ajustar fecha/hora al horario comercial permitido"""
        # Convertir a timezone local
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)
        
        # Ajustar día de la semana
        while dt.weekday() + 1 not in self.allowed_weekdays:  # weekday() es 0-6
            dt += timedelta(days=1)
            dt = dt.replace(hour=self.start_hour, minute=0, second=0)
        
        # Ajustar hora del día
        if dt.hour < self.start_hour:
            dt = dt.replace(hour=self.start_hour, minute=0, second=0)
        elif dt.hour >= self.end_hour:
            # Mover al siguiente día hábil
            dt += timedelta(days=1)
            dt = dt.replace(hour=self.start_hour, minute=0, second=0)
            # Verificar de nuevo el día de la semana
            while dt.weekday() + 1 not in self.allowed_weekdays:
                dt += timedelta(days=1)
        
        return dt
    
    async def _create_followup_job(self, user_id: str, stage: int, 
                                  scheduled_for: datetime, context_snapshot: Dict,
                                  last_user_message: Optional[str] = None):
        """Crear un trabajo de follow-up en la base de datos"""
        try:
            from psycopg2.extras import Json
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Obtener el teléfono del contexto
                    phone = context_snapshot.get('phone', 'unknown')
                    if phone == 'unknown' and user_id.startswith('whatsapp_'):
                        phone = user_id.replace('whatsapp_', '')
                    
                    # TEMPORAL: Para diagnóstico
                    logger.info(f"🔍 [DEBUG] Creando follow-up job: user_id={user_id}, stage={stage}, scheduled_for={scheduled_for}, phone={phone}")
                    
                    cursor.execute("""
                        INSERT INTO follow_up_jobs 
                        (user_id, phone, stage, scheduled_for, context_snapshot, last_user_message)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, stage) DO UPDATE SET
                            scheduled_for = EXCLUDED.scheduled_for,
                            context_snapshot = EXCLUDED.context_snapshot,
                            status = 'pending'
                    """, (user_id, phone, stage, scheduled_for, 
                          Json(context_snapshot), last_user_message))
                    
                    logger.debug(f"📋 Follow-up programado en BD: usuario {user_id} etapa {stage} para {scheduled_for}")
                    
        except Exception as e:
            logger.error(f"❌ Error creando job de follow-up: {e}")
    
    async def _execute_followup(self, user_id: str, stage: int):
        """Ejecutar un follow-up específico"""
        try:
            logger.info(f"📤 Ejecutando follow-up etapa {stage} para usuario {user_id}")
            
            # Verificar si el usuario sigue inactivo
            is_inactive = await self._is_user_still_inactive(user_id)
            logger.info(f"🔍 [DEBUG] Usuario {user_id} inactivo: {is_inactive}")
            
            if is_inactive:
                # Importar el manager para enviar el mensaje
                from .follow_up_manager import FollowUpManager
                
                manager = FollowUpManager(
                    database_url=self.database_url,
                    evolution_api_url=self.evolution_api_url,
                    evolution_token=self.evolution_token,
                    instance_name=self.instance_name,
                    openai_api_key=self.openai_api_key
                )
                success = await manager.send_followup_message(user_id, stage)
                
                if success:
                    await self._mark_job_completed(user_id, stage)
                    logger.info(f"✅ Follow-up etapa {stage} enviado a {user_id}")
                else:
                    await self._mark_job_failed(user_id, stage)
                    logger.warning(f"⚠️ Falló follow-up etapa {stage} para {user_id}")
            else:
                # Usuario ya está activo, cancelar follow-ups restantes
                await self._cancel_remaining_followups(user_id)
                logger.info(f"🔄 Usuario {user_id} activo, cancelando follow-ups restantes")
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando follow-up: {e}")
            await self._mark_job_failed(user_id, stage)
    
    async def _is_user_still_inactive(self, user_id: str) -> bool:
        """Verificar si el usuario sigue inactivo"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT last_interaction, context_data
                        FROM conversation_contexts 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return False
                    
                    # CRITICAL FIX: Usar timestamp desde context_data que tiene timezone correcto
                    context_data = result.get('context_data', {})
                    last_interaction_from_context = context_data.get('last_interaction')
                    
                    # Usar context_data si está disponible, fallback a campo directo
                    last_interaction_raw = last_interaction_from_context or result['last_interaction']
                    
                    # Usar helper para asegurar timezone correcto
                    last_interaction = self._ensure_argentina_timezone(last_interaction_raw)
                    
                    # TEMPORAL: Debug logging para timezone en inactividad
                    logger.info(f"🕐 [INACTIVE DEBUG] Usuario: {user_id}")
                    logger.info(f"🕐 [INACTIVE DEBUG] last_interaction desde campo BD: {result['last_interaction']}")
                    logger.info(f"🕐 [INACTIVE DEBUG] last_interaction desde context_data: {last_interaction_from_context}")
                    logger.info(f"🕐 [INACTIVE DEBUG] last_interaction usado final: {last_interaction_raw}")
                    logger.info(f"🕐 [INACTIVE DEBUG] last_interaction procesado: {last_interaction}")
                    
                    # TEMPORAL: Reducido a 10 minutos para pruebas
                    cutoff = datetime.now(self.timezone) - timedelta(minutes=10)
                    
                    # DEBUG: Log para entender la comparación
                    logger.debug(f"🕐 [DEBUG] last_interaction: {last_interaction} (tzinfo: {last_interaction.tzinfo})")
                    logger.debug(f"🕐 [DEBUG] cutoff: {cutoff} (tzinfo: {cutoff.tzinfo})")
                    logger.debug(f"🕐 [DEBUG] is inactive: {last_interaction < cutoff}")
                    
                    return last_interaction < cutoff
                    
        except Exception as e:
            logger.error(f"❌ Error verificando inactividad: {e}")
            return False
    
    async def _cancel_remaining_followups(self, user_id: str):
        """Cancelar follow-ups restantes de un usuario"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Cancelar en la base de datos
                    cursor.execute("""
                        UPDATE follow_up_jobs 
                        SET status = 'cancelled', processed_at = %s
                        WHERE user_id = %s AND status = 'pending'
                    """, (datetime.now(self.timezone), user_id))
                    
                    cancelled_count = cursor.rowcount
                    
                    logger.info(f"🚫 Cancelados {cancelled_count} follow-ups para {user_id}")
                    
        except Exception as e:
            logger.error(f"❌ Error cancelando follow-ups: {e}")
    
    async def _mark_job_completed(self, user_id: str, stage: int):
        """Marcar job como completado"""
        await self._update_job_status(user_id, stage, 'sent')
    
    async def _mark_job_failed(self, user_id: str, stage: int):
        """Marcar job como fallido"""
        await self._update_job_status(user_id, stage, 'failed')
    
    async def _update_job_status(self, user_id: str, stage: int, status: str):
        """Actualizar estado de un job"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE follow_up_jobs 
                        SET status = %s, processed_at = %s, attempts = attempts + 1
                        WHERE user_id = %s AND stage = %s
                    """, (status, datetime.now(self.timezone), user_id, stage))
                    
        except Exception as e:
            logger.error(f"❌ Error actualizando status del job: {e}")
    
    async def _daily_cleanup(self):
        """Limpieza diaria de trabajos antiguos"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Limpiar trabajos completados/fallidos de más de 30 días
                    cursor.execute("""
                        DELETE FROM follow_up_jobs 
                        WHERE created_at < %s 
                        AND status IN ('sent', 'cancelled', 'failed')
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    deleted_count = cursor.rowcount
                    logger.info(f"🧹 Limpieza diaria: {deleted_count} jobs antiguos eliminados")
                    
        except Exception as e:
            logger.error(f"❌ Error en limpieza diaria: {e}")
    
    async def schedule_user_followups(self, user_id: str, phone: str, 
                                    context_data: Dict[str, Any],
                                    last_message: Optional[str] = None):
        """API pública para programar follow-ups de un usuario específico"""
        try:
            # Cancelar follow-ups existentes primero
            await self._cancel_remaining_followups(user_id)
            
            base_time = datetime.now(self.timezone)
            
            for stage, delay_hours in self.stage_delays.items():
                scheduled_time = base_time + timedelta(hours=delay_hours)
                
                # Stage 1 se envía inmediatamente, otros stages respetan horario comercial  
                if stage > 1:
                    scheduled_time = self._adjust_to_business_hours(scheduled_time)
                
                await self._create_followup_job(
                    user_id=user_id,
                    stage=stage,
                    scheduled_for=scheduled_time,
                    context_snapshot=context_data,
                    last_user_message=last_message
                )
            
            logger.info(f"📅 Follow-ups programados manualmente para {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error programando follow-ups manuales: {e}")
            return False
    
    async def cancel_user_followups(self, user_id: str):
        """Cancelar todos los follow-ups de un usuario"""
        await self._cancel_remaining_followups(user_id)
    
    async def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """Obtener lista de trabajos pendientes"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT user_id, stage, scheduled_for, created_at, attempts
                        FROM follow_up_jobs 
                        WHERE status = 'pending'
                        ORDER BY scheduled_for
                    """)
                    
                    return [dict(row) for row in cursor.fetchall()]
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo trabajos pendientes: {e}")
            return []
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del scheduler"""
        try:
            jobs = await self.get_pending_jobs()
            
            return {
                "is_running": self.is_running,
                "pending_jobs": len(jobs),
                "next_job": jobs[0]['scheduled_for'] if jobs else None,
                "scheduler_jobs": len(self.scheduler.get_jobs()) if self.scheduler else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {"error": str(e)}