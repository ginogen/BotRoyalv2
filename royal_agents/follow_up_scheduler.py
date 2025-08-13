# Scheduler de Tareas Automáticas para Sistema de Seguimiento
# Ejecuta mensajes automáticos según cronograma de 14 etapas

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.job import Job

from .follow_up_system import (
    get_users_for_followup, 
    complete_followup_stage, 
    UserFollowUp,
    db_manager
)
from .follow_up_messages import get_followup_message_for_stage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FollowUpScheduler:
    """Scheduler principal para el sistema de seguimiento automático"""
    
    def __init__(self, message_sender_callback: Optional[Callable] = None):
        """
        Inicializa el scheduler
        
        Args:
            message_sender_callback: Función para enviar mensajes (debe aceptar user_id, message)
        """
        # Configurar scheduler
        executors = {
            'default': ThreadPoolExecutor(max_workers=20)
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 30
        }
        
        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/Argentina/Cordoba'
        )
        
        # Callback para enviar mensajes
        self.message_sender = message_sender_callback
        
        # Control de estado
        self.is_running = False
        self.processed_jobs_cache = set()  # Cache para evitar duplicados
        
        # Estadísticas
        self.stats = {
            'messages_sent': 0,
            'errors': 0,
            'jobs_processed': 0,
            'last_check': None
        }
        
    def start(self):
        """Inicia el scheduler"""
        try:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                
                # Job principal que revisa cada 10 minutos si hay usuarios para follow-up
                self.scheduler.add_job(
                    func=self._check_and_process_followups,
                    trigger=IntervalTrigger(minutes=10),
                    id='main_followup_checker',
                    name='Main Follow-up Checker',
                    replace_existing=True
                )
                
                # Job de limpieza cada 6 horas
                self.scheduler.add_job(
                    func=self._cleanup_old_jobs,
                    trigger=IntervalTrigger(hours=6),
                    id='cleanup_jobs',
                    name='Cleanup Old Jobs',
                    replace_existing=True
                )
                
                # Job de estadísticas cada hora
                self.scheduler.add_job(
                    func=self._log_stats,
                    trigger=IntervalTrigger(hours=1),
                    id='stats_logger',
                    name='Statistics Logger',
                    replace_existing=True
                )
                
                logger.info("✅ Follow-up Scheduler iniciado correctamente")
                logger.info(f"📊 Jobs activos: {len(self.scheduler.get_jobs())}")
                
        except Exception as e:
            logger.error(f"❌ Error iniciando scheduler: {e}")
            raise
    
    def stop(self):
        """Detiene el scheduler"""
        try:
            if self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("🛑 Follow-up Scheduler detenido")
                
        except Exception as e:
            logger.error(f"❌ Error deteniendo scheduler: {e}")
    
    def schedule_followup_for_user(self, user_id: str, stage: int, delay_hours: int = 1):
        """
        Programa un follow-up específico para un usuario
        
        Args:
            user_id: ID del usuario
            stage: Etapa del seguimiento
            delay_hours: Horas de delay antes de enviar (default 1 para stage 0)
        """
        try:
            # Calcular fecha de ejecución
            run_date = datetime.now() + timedelta(hours=delay_hours)
            
            # ID único para el job
            job_id = f"followup_{user_id}_{stage}_{int(time.time())}"
            
            # Programar job
            self.scheduler.add_job(
                func=self._send_followup_message,
                trigger=DateTrigger(run_date=run_date),
                args=[user_id, stage],
                id=job_id,
                name=f"Follow-up Stage {stage} para {user_id}",
                replace_existing=False
            )
            
            logger.info(f"📅 Follow-up programado: Usuario {user_id}, Etapa {stage}, Fecha: {run_date}")
            
        except Exception as e:
            logger.error(f"❌ Error programando follow-up para {user_id}: {e}")
    
    def _check_and_process_followups(self):
        """Job principal que revisa y procesa usuarios listos para follow-up"""
        try:
            logger.info("🔍 Revisando usuarios para follow-up automático...")
            
            # Obtener usuarios listos
            users_ready = get_users_for_followup()
            
            if not users_ready:
                logger.info("📭 No hay usuarios listos para follow-up en este momento")
                return
            
            logger.info(f"📬 {len(users_ready)} usuarios listos para follow-up")
            
            # Procesar cada usuario
            for user_followup in users_ready:
                try:
                    # Evitar duplicados con cache
                    cache_key = f"{user_followup.user_id}_{user_followup.current_stage}"
                    
                    if cache_key not in self.processed_jobs_cache:
                        self._send_followup_message(user_followup.user_id, user_followup.current_stage)
                        
                        # Agregar a cache (será limpiado periódicamente)
                        self.processed_jobs_cache.add(cache_key)
                        
                        # Pequeña pausa entre mensajes
                        time.sleep(2)
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando follow-up para {user_followup.user_id}: {e}")
                    self.stats['errors'] += 1
            
            self.stats['last_check'] = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Error en check_and_process_followups: {e}")
            self.stats['errors'] += 1
    
    def _send_followup_message(self, user_id: str, stage: int):
        """Envía un mensaje de seguimiento a un usuario específico"""
        try:
            logger.info(f"📤 Enviando mensaje de seguimiento - Usuario: {user_id}, Etapa: {stage}")
            
            # Obtener estado actual del usuario
            user_followup = db_manager.get_user_followup(user_id)
            
            if not user_followup or not user_followup.is_active:
                logger.info(f"⏭️ Saltando follow-up - Usuario {user_id} no está activo o no existe")
                return
            
            # Verificar que la etapa coincida (por si hubo cambios)
            if user_followup.current_stage != stage:
                logger.info(f"⏭️ Saltando follow-up - Usuario {user_id} cambió de etapa {stage} a {user_followup.current_stage}")
                return
            
            # Obtener mensaje para la etapa
            message_content = get_followup_message_for_stage(
                stage=stage, 
                user_profile=user_followup.user_profile,
                interaction_count=user_followup.interaction_count
            )
            
            if not message_content:
                logger.error(f"❌ No se pudo obtener mensaje para etapa {stage}")
                return
            
            # Enviar mensaje usando callback
            if self.message_sender:
                success = self.message_sender(user_id, message_content)
                
                if success:
                    # Avanzar a la siguiente etapa
                    complete_followup_stage(user_id)
                    
                    self.stats['messages_sent'] += 1
                    self.stats['jobs_processed'] += 1
                    
                    logger.info(f"✅ Follow-up enviado exitosamente - Usuario: {user_id}, Etapa: {stage}")
                else:
                    logger.error(f"❌ Error enviando mensaje a {user_id}")
                    self.stats['errors'] += 1
            else:
                logger.warning(f"⚠️ No hay callback configurado para enviar mensajes")
                # Simular envío para testing
                logger.info(f"🧪 SIMULACIÓN - Mensaje para {user_id}:")
                logger.info(f"📝 {message_content[:100]}...")
                
                # Avanzar etapa en modo simulación
                complete_followup_stage(user_id)
                self.stats['jobs_processed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error enviando follow-up a {user_id}: {e}")
            self.stats['errors'] += 1
    
    def _cleanup_old_jobs(self):
        """Limpia jobs antiguos y cache"""
        try:
            # Limpiar cache de jobs procesados
            if len(self.processed_jobs_cache) > 1000:
                self.processed_jobs_cache.clear()
                logger.info("🧹 Cache de jobs limpiado")
            
            # Obtener jobs activos
            active_jobs = self.scheduler.get_jobs()
            completed_jobs = []
            
            for job in active_jobs:
                # Identificar jobs de follow-up completados o antiguos
                if job.id.startswith('followup_') and job.next_run_time:
                    # Si el job debería haber corrido hace más de 1 hora
                    if job.next_run_time < datetime.now() - timedelta(hours=1):
                        completed_jobs.append(job.id)
            
            # Remover jobs antiguos
            for job_id in completed_jobs:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass  # Job ya no existe
            
            if completed_jobs:
                logger.info(f"🧹 {len(completed_jobs)} jobs antiguos limpiados")
                
        except Exception as e:
            logger.error(f"❌ Error en cleanup: {e}")
    
    def _log_stats(self):
        """Log de estadísticas del sistema"""
        try:
            active_jobs = len(self.scheduler.get_jobs())
            
            logger.info("📊 ESTADÍSTICAS FOLLOW-UP SCHEDULER:")
            logger.info(f"   Mensajes enviados: {self.stats['messages_sent']}")
            logger.info(f"   Jobs procesados: {self.stats['jobs_processed']}")
            logger.info(f"   Errores: {self.stats['errors']}")
            logger.info(f"   Jobs activos: {active_jobs}")
            logger.info(f"   Último check: {self.stats['last_check']}")
            logger.info(f"   Cache size: {len(self.processed_jobs_cache)}")
            
        except Exception as e:
            logger.error(f"❌ Error loggeando stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del scheduler"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'active_jobs': len(self.scheduler.get_jobs()) if self.scheduler else 0,
            'cache_size': len(self.processed_jobs_cache)
        }
    
    def get_user_scheduled_jobs(self, user_id: str) -> List[Dict]:
        """Obtiene jobs programados para un usuario específico"""
        try:
            user_jobs = []
            for job in self.scheduler.get_jobs():
                if job.id.startswith(f'followup_{user_id}_'):
                    user_jobs.append({
                        'job_id': job.id,
                        'name': job.name,
                        'next_run': job.next_run_time,
                        'args': job.args
                    })
            return user_jobs
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo jobs para {user_id}: {e}")
            return []
    
    def cancel_user_followups(self, user_id: str) -> int:
        """Cancela todos los follow-ups programados para un usuario"""
        try:
            cancelled_count = 0
            jobs_to_remove = []
            
            for job in self.scheduler.get_jobs():
                if job.id.startswith(f'followup_{user_id}_'):
                    jobs_to_remove.append(job.id)
            
            for job_id in jobs_to_remove:
                try:
                    self.scheduler.remove_job(job_id)
                    cancelled_count += 1
                except:
                    pass
            
            logger.info(f"🚫 {cancelled_count} follow-ups cancelados para usuario {user_id}")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"❌ Error cancelando follow-ups para {user_id}: {e}")
            return 0

# Funciones de callback por defecto para integración
def default_message_sender(user_id: str, message: str) -> bool:
    """
    Callback por defecto para envío de mensajes.
    Esta función debe ser sobrescrita por la implementación real.
    """
    logger.info(f"📧 DEFAULT SENDER - Usuario: {user_id}")
    logger.info(f"📝 Mensaje: {message[:100]}...")
    return True

# Instancia global del scheduler
follow_up_scheduler = FollowUpScheduler(message_sender_callback=default_message_sender)

# Funciones de conveniencia para otros módulos
def start_follow_up_scheduler(message_callback: Optional[Callable] = None):
    """Inicia el scheduler con callback personalizado"""
    if message_callback:
        follow_up_scheduler.message_sender = message_callback
    
    follow_up_scheduler.start()
    return follow_up_scheduler

def stop_follow_up_scheduler():
    """Detiene el scheduler"""
    follow_up_scheduler.stop()

def get_scheduler_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del scheduler"""
    return follow_up_scheduler.get_stats()

def schedule_immediate_followup(user_id: str, delay_hours: int = 1):
    """Programa un follow-up inmediato (stage 0) para un usuario"""
    follow_up_scheduler.schedule_followup_for_user(user_id, stage=0, delay_hours=delay_hours)

def cancel_user_scheduled_followups(user_id: str) -> int:
    """Cancela follow-ups programados para un usuario"""
    return follow_up_scheduler.cancel_user_followups(user_id)

if __name__ == "__main__":
    # Test del scheduler
    logger.info("🧪 Test del Follow-up Scheduler")
    
    # Iniciar scheduler en modo test
    scheduler = FollowUpScheduler()
    scheduler.start()
    
    # Simular programación de follow-up
    test_user = "test_scheduler_001"
    schedule_immediate_followup(test_user, delay_hours=0.01)  # 36 segundos para test
    
    logger.info("⏰ Esperando ejecución de test...")
    time.sleep(60)
    
    # Ver estadísticas
    stats = scheduler.get_stats()
    logger.info(f"📊 Stats finales: {stats}")
    
    scheduler.stop()
    logger.info("✅ Test completado")