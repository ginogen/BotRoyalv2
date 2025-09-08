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
            1: 0.25,   # 15 minutos
            2: 1,      # 1 hora
            3: 24,     # 1 día
            4: 48,     # 2 días
            5: 72,     # 3 días
            6: 96,     # 4 días
            7: 120     # 5 días
        }
        
        # 🚨 MODO MIGRACIÓN: Protección anti-duplicación temporal
        self.migration_mode_until = None
        self._check_migration_mode()
        
        # Horarios permitidos
        self.start_hour = 9   # 9 AM
        self.end_hour = 21    # 9 PM
        self.allowed_weekdays = [1, 2, 3, 4, 5, 6]  # Lunes a sábado
    
    def _ensure_argentina_timezone(self, dt_input) -> datetime:
        """
        🚨 VERSIÓN CRÍTICA: Helper ultra-robusto para timezone Argentina con múltiples fallbacks
        VITAL para follow-ups - NUNCA debe fallar
        """
        argentina_tz = self.timezone
        current_time = datetime.now(argentina_tz)
        
        try:
            # FALLBACK 1: String con timezone explícito (preferido)
            if isinstance(dt_input, str):
                logger.info(f"🕐 [TIMEZONE] Procesando string: {dt_input}")
                
                # Sub-fallback 1a: Timezone Argentina explícito
                if '-03:00' in dt_input:
                    result = datetime.fromisoformat(dt_input).astimezone(argentina_tz)
                    logger.info(f"✅ [TIMEZONE] Fallback 1a exitoso: {result}")
                    return result
                
                # Sub-fallback 1b: UTC o timezone genérico
                if dt_input.endswith('Z') or '+' in dt_input or ('-' in dt_input[-6:] and dt_input[-6:] != '-03:00'):
                    if dt_input.endswith('Z'):
                        dt_input = dt_input.replace('Z', '+00:00')
                    result = datetime.fromisoformat(dt_input).astimezone(argentina_tz)
                    logger.info(f"✅ [TIMEZONE] Fallback 1b exitoso: {result}")
                    return result
                
                # Sub-fallback 1c: String sin timezone (asumir Argentina)
                try:
                    dt = datetime.fromisoformat(dt_input)
                    if dt.tzinfo is None:
                        result = argentina_tz.localize(dt)
                        logger.info(f"✅ [TIMEZONE] Fallback 1c exitoso: {result}")
                        return result
                    else:
                        result = dt.astimezone(argentina_tz)
                        logger.info(f"✅ [TIMEZONE] Fallback 1c-alt exitoso: {result}")
                        return result
                except Exception as e:
                    logger.warning(f"⚠️ [TIMEZONE] Fallback 1c falló: {e}")
            
            # FALLBACK 2: Datetime object
            elif isinstance(dt_input, datetime):
                logger.info(f"🕐 [TIMEZONE] Procesando datetime object: {dt_input} (tzinfo: {dt_input.tzinfo})")
                
                if dt_input.tzinfo is None:
                    result = argentina_tz.localize(dt_input)
                    logger.info(f"✅ [TIMEZONE] Fallback 2a exitoso: {result}")
                    return result
                else:
                    result = dt_input.astimezone(argentina_tz)
                    logger.info(f"✅ [TIMEZONE] Fallback 2b exitoso: {result}")
                    return result
            
            # FALLBACK 3: Tipo no soportado - log error pero continuar
            logger.error(f"❌ [TIMEZONE] Tipo no soportado: {type(dt_input)} = {dt_input}")
            
        except Exception as e:
            logger.error(f"❌ [TIMEZONE] Error en procesamiento principal: {e}")
        
        # 🚨 FALLBACK DE EMERGENCIA: Si todo falla, usar timestamp actual menos tiempo razonable
        emergency_timestamp = current_time - timedelta(minutes=30)
        logger.critical(f"🚨 [TIMEZONE] FALLBACK DE EMERGENCIA activado: {emergency_timestamp}")
        logger.critical(f"🚨 [TIMEZONE] Input original que falló: {dt_input} (tipo: {type(dt_input)})")
        
        # Enviar alerta crítica (implementar después)
        # self._send_critical_alert(f"Timezone fallback emergency: {dt_input}")
        
        return emergency_timestamp
    
    def _has_real_conversation(self, context_data: dict) -> bool:
        """🚨 NUEVO: Verificar si el usuario tiene conversación real"""
        try:
            interaction_history = context_data.get('interaction_history', [])
            
            if not interaction_history:
                return False
            
            # Contar mensajes reales (user/assistant, no system internos)
            real_messages = 0
            for interaction in interaction_history:
                role = interaction.get('role', '')
                message = interaction.get('message', '')
                
                # Solo incluir mensajes reales de conversación
                if role in ['user', 'assistant'] and message and not any(skip_phrase in message.lower() for skip_phrase in [
                    'escalado a humano', 'información faltante', 'necesita asistencia', 
                    'mostré categorías', 'mostré productos'
                ]):
                    real_messages += 1
            
            # Necesita al menos 2 mensajes reales para justificar follow-up
            has_conversation = real_messages >= 2
            logger.debug(f"📊 Usuario: {real_messages} mensajes reales, follow-up justificado: {has_conversation}")
            
            return has_conversation
            
        except Exception as e:
            logger.error(f"❌ Error verificando conversación real: {e}")
            return False
    
    def _check_migration_mode(self):
        """Verificar si el modo migración está activo"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Buscar marca de migración en configuración
                    cursor.execute("""
                        SELECT config_value FROM follow_up_config 
                        WHERE config_key = 'migration_mode_until'
                    """)
                    result = cursor.fetchone()
                    
                    if result:
                        migration_until_str = result[0]
                        try:
                            self.migration_mode_until = datetime.fromisoformat(migration_until_str)
                            if self.migration_mode_until > datetime.now(self.timezone):
                                logger.info(f"🚨 [MIGRATION] Modo migración activo hasta: {self.migration_mode_until}")
                            else:
                                # Modo migración expirado, limpiar
                                cursor.execute("""
                                    DELETE FROM follow_up_config 
                                    WHERE config_key = 'migration_mode_until'
                                """)
                                conn.commit()
                                self.migration_mode_until = None
                                logger.info("✅ [MIGRATION] Modo migración expirado y limpiado")
                        except Exception as e:
                            logger.warning(f"⚠️ [MIGRATION] Error parseando fecha de migración: {e}")
                            self.migration_mode_until = None
                    
        except Exception as e:
            logger.warning(f"⚠️ [MIGRATION] Error verificando modo migración: {e}")
            self.migration_mode_until = None
    
    def _is_migration_mode_active(self) -> bool:
        """Verificar si el modo migración está activo"""
        if self.migration_mode_until is None:
            return False
        
        current_time = datetime.now(self.timezone)
        is_active = current_time < self.migration_mode_until
        
        if not is_active and self.migration_mode_until:
            # Modo migración expirado, limpiar
            logger.info("✅ [MIGRATION] Modo migración expirado automáticamente")
            self.migration_mode_until = None
            # Limpiar de BD también
            try:
                with psycopg2.connect(self.database_url) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM follow_up_config 
                            WHERE config_key = 'migration_mode_until'
                        """)
                        conn.commit()
            except Exception as e:
                logger.warning(f"⚠️ [MIGRATION] Error limpiando modo migración: {e}")
        
        return is_active
        
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
                minutes=60,  # Revisar cada 1 hora
                id='check_inactive_users',
                replace_existing=True
            )
            
            # 🚨 SISTEMA DE FALLBACK CRÍTICO: Job de recuperación cada 30 minutos
            self.scheduler.add_job(
                func=self._critical_followup_recovery,
                trigger='interval',
                minutes=30,  # Recuperación cada 30 minutos
                id='critical_followup_recovery',
                replace_existing=True
            )
            
            # 🚨 SISTEMA DE FALLBACK: Verificación hourly de usuarios sin follow-ups
            self.scheduler.add_job(
                func=self._emergency_followup_check,
                trigger='interval',
                minutes=15,  # Verificación cada 15 minutos
                id='emergency_followup_check',
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
                    # Buscar usuarios inactivos que no tienen follow-ups programados o recientes
                    query = """
                    SELECT DISTINCT cc.user_id, cc.last_interaction, cc.context_data
                    FROM conversation_contexts cc
                    LEFT JOIN follow_up_blacklist bl ON cc.user_id = bl.user_id
                    WHERE bl.user_id IS NULL  -- No está en blacklist
                    AND cc.last_interaction < %s  -- Inactivo por más de 15 minutos
                    AND NOT EXISTS (  -- No tiene follow-ups pendientes recientes
                        SELECT 1 FROM follow_up_jobs fj 
                        WHERE fj.user_id = cc.user_id 
                        AND fj.status = 'pending'
                        AND fj.created_at > cc.last_interaction
                    )
                    AND NOT EXISTS (  -- No se envió follow-up en la última hora (COOLDOWN)
                        SELECT 1 FROM follow_up_jobs fj2
                        WHERE fj2.user_id = cc.user_id
                        AND fj2.sent_at > %s  -- No enviado en los últimos 15 minutos
                    )
                    """
                    
                    # Detección de usuarios inactivos después de 15 minutos
                    cutoff_time = datetime.now(self.timezone) - timedelta(minutes=15)
                    cooldown_time = datetime.now(self.timezone) - timedelta(minutes=15)  # Cooldown de 15 minutos
                    
                    logger.debug(f"🔍 Checking inactive users since: {cutoff_time}")
                    logger.info(f"🕐 Detectando usuarios inactivos por más de 15 minutos")
                    logger.debug(f"🔍 Cooldown time: {cooldown_time}")
                    logger.debug(f"🔍 Timezone: {self.timezone}")
                    
                    cursor.execute(query, (cutoff_time, cooldown_time,))
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
        """🚨 PROGRAMAR FOLLOW-UPS: Solo usuarios con conversación real"""
        try:
            user_id = user_data['user_id']
            
            # 🔍 VALIDACIÓN CRÍTICA: Solo follow-ups para usuarios con conversación real
            context_data = user_data.get('context_data', {})
            if not self._has_real_conversation(context_data):
                logger.info(f"⏭️ [SKIP] {user_id} sin conversación real, omitiendo follow-ups")
                return
            
            logger.info(f"✅ [VALID] {user_id} tiene conversación real, programando follow-ups")
            
            # 🚨 SISTEMA DE FALLBACK TRIPLE para timestamp base
            last_interaction = None
            source_used = ""
            
            try:
                # FALLBACK 1: context_data.last_interaction (fuente preferida)
                context_data = user_data.get('context_data', {})
                if context_data and context_data.get('last_interaction'):
                    last_interaction = self._ensure_argentina_timezone(context_data['last_interaction'])
                    source_used = "context_data"
                    logger.info(f"✅ [SCHEDULE] Fallback 1 usado para {user_id}: {last_interaction}")
                
                # FALLBACK 2: Campo directo user_data['last_interaction']
                elif user_data.get('last_interaction'):
                    last_interaction = self._ensure_argentina_timezone(user_data['last_interaction'])
                    source_used = "direct_field"
                    logger.info(f"✅ [SCHEDULE] Fallback 2 usado para {user_id}: {last_interaction}")
                
                # FALLBACK 3: EMERGENCIA - timestamp actual menos 1 hora
                else:
                    last_interaction = datetime.now(self.timezone) - timedelta(hours=1)
                    source_used = "emergency"
                    logger.critical(f"🚨 [SCHEDULE] FALLBACK DE EMERGENCIA para {user_id}: {last_interaction}")
                    
            except Exception as e:
                # FALLBACK ÚLTIMO RECURSO
                logger.critical(f"🚨 [SCHEDULE] ERROR en fallback para {user_id}: {e}")
                last_interaction = datetime.now(self.timezone) - timedelta(hours=2)
                source_used = "last_resort"
            
            # Obtener el último mensaje del usuario con fallback
            last_msg = None
            try:
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
            except Exception as e:
                logger.warning(f"⚠️ [SCHEDULE] No se pudo obtener último mensaje para {user_id}: {e}")
            
            # LOGGING CRÍTICO para debugging
            logger.info(f"📊 [SCHEDULE] Usuario: {user_id}")
            logger.info(f"📊 [SCHEDULE] Fuente timestamp: {source_used}")
            logger.info(f"📊 [SCHEDULE] Last interaction: {last_interaction}")
            logger.info(f"📊 [SCHEDULE] Timezone: {self.timezone}")
            logger.info(f"📊 [SCHEDULE] Último mensaje disponible: {last_msg is not None}")
            
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
        """Crear un trabajo de follow-up en la base de datos con contexto completo"""
        try:
            from psycopg2.extras import Json
            
            # Enriquecer context_snapshot con historial de interacciones completo
            enriched_context = await self._enrich_context_with_interactions(user_id, context_snapshot)
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Obtener el teléfono del contexto
                    phone = enriched_context.get('phone', 'unknown')
                    if phone == 'unknown' and user_id.startswith('whatsapp_'):
                        phone = user_id.replace('whatsapp_', '')
                    
                    # TEMPORAL: Para diagnóstico
                    logger.info(f"🔍 [DEBUG] Creando follow-up job: user_id={user_id}, stage={stage}, scheduled_for={scheduled_for}, phone={phone}")
                    logger.info(f"🔍 [DEBUG] Context snapshot incluye {len(enriched_context.get('interaction_history', []))} interacciones")
                    
                    cursor.execute("""
                        INSERT INTO follow_up_jobs 
                        (user_id, phone, stage, scheduled_for, context_snapshot, last_user_message)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, stage) DO UPDATE SET
                            scheduled_for = EXCLUDED.scheduled_for,
                            context_snapshot = EXCLUDED.context_snapshot,
                            status = 'pending'
                    """, (user_id, phone, stage, scheduled_for, 
                          Json(enriched_context), last_user_message))
                    
                    logger.debug(f"📋 Follow-up programado en BD: usuario {user_id} etapa {stage} para {scheduled_for}")
                    
        except Exception as e:
            logger.error(f"❌ Error creando job de follow-up: {e}")
    
    async def _enrich_context_with_interactions(self, user_id: str, context_snapshot: Dict) -> Dict:
        """Enriquecer context snapshot con historial completo de interacciones"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Obtener últimas 20 interacciones
                    cursor.execute("""
                        SELECT role, message, created_at, metadata
                        FROM user_interactions 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 20
                    """, (user_id,))
                    
                    interactions = [dict(row) for row in cursor.fetchall()]
                    interactions.reverse()  # Orden cronológico
                    
                    # Enriquecer contexto
                    enriched = dict(context_snapshot)
                    enriched['interaction_history'] = interactions
                    
                    logger.debug(f"✅ Context enriched: {len(interactions)} interacciones agregadas")
                    return enriched
                    
        except Exception as e:
            logger.error(f"❌ Error enriching context: {e}")
            return context_snapshot
    
    def _get_stage_description(self, stage: int) -> str:
        """Obtener descripción de la etapa"""
        descriptions = {
            1: "Recordatorio inicial (15 minutos)",
            2: "Seguimiento temprano (1 hora)",
            3: "Seguimiento del día siguiente",
            4: "Recordatorio a 48 horas",
            5: "Seguimiento a 3 días",
            6: "Recordatorio a 4 días",
            7: "Último intento (5 días)"
        }
        return descriptions.get(stage, f"Etapa {stage}")
    
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
        """
        🚨 VERSIÓN CRÍTICA: Verificar inactividad con múltiples fallbacks
        NUNCA debe fallar - vital para follow-ups
        """
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
                        logger.warning(f"⚠️ [INACTIVE] Usuario {user_id} no encontrado en BD")
                        # FALLBACK: Usuario no encontrado = considera inactivo por seguridad
                        return True
                    
                    # SISTEMA DE FALLBACK TRIPLE para timestamp
                    last_interaction = None
                    source_used = ""
                    
                    try:
                        # FALLBACK 1: context_data.last_interaction (fuente preferida)
                        context_data = result.get('context_data', {})
                        if context_data and context_data.get('last_interaction'):
                            last_interaction = self._ensure_argentina_timezone(context_data['last_interaction'])
                            source_used = "context_data"
                            logger.info(f"✅ [INACTIVE] Fallback 1 (context_data) usado para {user_id}: {last_interaction}")
                        
                        # FALLBACK 2: Campo directo last_interaction
                        elif result['last_interaction']:
                            last_interaction = self._ensure_argentina_timezone(result['last_interaction'])
                            source_used = "direct_field"
                            logger.info(f"✅ [INACTIVE] Fallback 2 (direct_field) usado para {user_id}: {last_interaction}")
                        
                        # FALLBACK 3: EMERGENCIA - usar timestamp actual menos 1 hora
                        else:
                            last_interaction = datetime.now(self.timezone) - timedelta(hours=1)
                            source_used = "emergency_fallback"
                            logger.critical(f"🚨 [INACTIVE] FALLBACK DE EMERGENCIA para {user_id}: {last_interaction}")
                            logger.critical(f"🚨 [INACTIVE] Datos originales - context_data: {context_data}, direct: {result['last_interaction']}")
                    
                    except Exception as e:
                        # FALLBACK DE ÚLTIMO RECURSO
                        logger.critical(f"🚨 [INACTIVE] ERROR en fallback, usando ÚLTIMO RECURSO para {user_id}: {e}")
                        last_interaction = datetime.now(self.timezone) - timedelta(hours=2)
                        source_used = "last_resort"
                    
                    # Verificar inactividad con cutoff de 15 minutos
                    cutoff = datetime.now(self.timezone) - timedelta(minutes=15)
                    is_inactive = last_interaction < cutoff
                    
                    # LOGGING DETALLADO para debugging
                    logger.info(f"📊 [INACTIVE] Usuario: {user_id}")
                    logger.info(f"📊 [INACTIVE] Fuente timestamp: {source_used}")
                    logger.info(f"📊 [INACTIVE] Last interaction: {last_interaction}")
                    logger.info(f"📊 [INACTIVE] Cutoff time: {cutoff}")
                    logger.info(f"📊 [INACTIVE] Es inactivo: {is_inactive}")
                    logger.info(f"📊 [INACTIVE] Diferencia minutos: {(cutoff - last_interaction).total_seconds() / 60:.1f}")
                    
                    # VALIDACIÓN CRÍTICA: Si el timestamp es muy futuro, algo está mal
                    current_time = datetime.now(self.timezone)
                    if last_interaction > current_time + timedelta(minutes=5):
                        logger.critical(f"🚨 [INACTIVE] TIMESTAMP FUTURO DETECTADO para {user_id}: {last_interaction}")
                        # En caso de timestamp futuro, considera inactivo por seguridad
                        return True
                    
                    return is_inactive
                    
        except Exception as e:
            logger.critical(f"🚨 [INACTIVE] ERROR CRÍTICO verificando inactividad {user_id}: {e}")
            # FALLBACK FINAL: En caso de error, considera inactivo (mejor enviar que no enviar)
            return True
    
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
    
    async def _critical_followup_recovery(self):
        """🚨 SISTEMA DE RECUPERACIÓN CRÍTICA: Re-programa follow-ups fallidos o perdidos"""
        try:
            # 🛡️ PROTECCIÓN ANTI-DUPLICACIÓN: Verificar modo migración
            if self._is_migration_mode_active():
                logger.info("🚨 [RECOVERY] SALTANDO recovery - modo migración activo para prevenir duplicación")
                return
            
            logger.info("🚨 [RECOVERY] Iniciando recuperación crítica de follow-ups")
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Buscar jobs fallidos de las últimas 24 horas que deberían reintentarse
                    cursor.execute("""
                        SELECT user_id, stage, scheduled_for, attempts
                        FROM follow_up_jobs 
                        WHERE status = 'failed' 
                        AND attempts < 3
                        AND scheduled_for < %s
                        AND created_at > %s
                    """, (
                        datetime.now(self.timezone),
                        datetime.now(self.timezone) - timedelta(hours=24)
                    ))
                    
                    failed_jobs = cursor.fetchall()
                    
                    logger.info(f"🚨 [RECOVERY] Encontrados {len(failed_jobs)} jobs fallidos para recuperar")
                    
                    for job in failed_jobs:
                        try:
                            # Resetear job para reintento
                            cursor.execute("""
                                UPDATE follow_up_jobs 
                                SET status = 'pending', 
                                    scheduled_for = %s,
                                    processed_at = NULL
                                WHERE user_id = %s AND stage = %s
                            """, (
                                datetime.now(self.timezone) + timedelta(minutes=5),  # Reintentar en 5 minutos
                                job['user_id'], 
                                job['stage']
                            ))
                            
                            logger.info(f"✅ [RECOVERY] Job recuperado: {job['user_id']} stage {job['stage']}")
                            
                        except Exception as e:
                            logger.error(f"❌ [RECOVERY] Error recuperando job {job['user_id']}: {e}")
                    
                    conn.commit()
                    
        except Exception as e:
            logger.critical(f"🚨 [RECOVERY] ERROR CRÍTICO en recuperación: {e}")
    
    async def _emergency_followup_check(self):
        """🚨 VERIFICACIÓN DE EMERGENCIA: Encuentra usuarios que deberían tener follow-ups pero no los tienen"""
        try:
            logger.info("🚨 [EMERGENCY] Verificación de emergencia de follow-ups faltantes")
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Buscar usuarios inactivos sin follow-ups programados
                    cursor.execute("""
                        SELECT cc.user_id, cc.last_interaction, cc.context_data
                        FROM conversation_contexts cc
                        LEFT JOIN follow_up_blacklist bl ON cc.user_id = bl.user_id
                        WHERE bl.user_id IS NULL  -- No en blacklist
                        AND cc.last_interaction < %s  -- Inactivo por más de 2 horas
                        AND NOT EXISTS (  -- Sin follow-ups pendientes
                            SELECT 1 FROM follow_up_jobs fj 
                            WHERE fj.user_id = cc.user_id 
                            AND fj.status = 'pending'
                        )
                        AND NOT EXISTS (  -- Sin follow-ups enviados recientemente
                            SELECT 1 FROM follow_up_jobs fj2
                            WHERE fj2.user_id = cc.user_id
                            AND fj2.created_at > %s
                        )
                        LIMIT 10  -- Procesar máximo 10 por vez
                    """, (
                        datetime.now(self.timezone) - timedelta(hours=2),  # 2 horas inactivo
                        datetime.now(self.timezone) - timedelta(hours=6)   # Sin follow-ups en 6 horas
                    ))
                    
                    missing_followups = cursor.fetchall()
                    
                    logger.info(f"🚨 [EMERGENCY] Encontrados {len(missing_followups)} usuarios sin follow-ups")
                    
                    for user in missing_followups:
                        try:
                            # Programar follow-ups de emergencia
                            logger.critical(f"🚨 [EMERGENCY] Programando follow-ups de emergencia para {user['user_id']}")
                            await self._schedule_user_followups(user)
                            
                        except Exception as e:
                            logger.critical(f"🚨 [EMERGENCY] Error programando follow-ups de emergencia para {user['user_id']}: {e}")
                    
        except Exception as e:
            logger.critical(f"🚨 [EMERGENCY] ERROR CRÍTICO en verificación de emergencia: {e}")