"""
📊 Follow-up Tracker para Royal Bot v2
Sistema de tracking y métricas para follow-ups
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger('followup.tracker')

class FollowUpTracker:
    """Tracker para métricas y análisis de follow-ups"""
    
    def __init__(self, database_url: str, timezone: str = "America/Argentina/Cordoba"):
        self.database_url = database_url
        self.timezone = pytz.timezone(timezone)
    
    async def track_user_response(self, user_id: str, response_message: str):
        """Rastrear respuesta del usuario a follow-up"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Encontrar el follow-up más reciente sin respuesta
                    cursor.execute("""
                        UPDATE follow_up_history 
                        SET user_responded = TRUE, 
                            responded_at = %s,
                            response_message = %s,
                            response_time_hours = EXTRACT(EPOCH FROM (%s - sent_at))/3600
                        WHERE user_id = %s 
                        AND user_responded = FALSE
                        AND sent_at > %s
                        RETURNING stage
                    """, (
                        datetime.now(self.timezone),
                        response_message[:500],  # Truncar mensaje largo
                        datetime.now(self.timezone),
                        user_id,
                        datetime.now(self.timezone) - timedelta(days=7)
                    ))
                    
                    updated_stages = [row[0] for row in cursor.fetchall()]
                    
                    if updated_stages:
                        logger.info(f"📈 Usuario {user_id} respondió a follow-up etapas: {updated_stages}")
                        return True
                    
        except Exception as e:
            logger.error(f"❌ Error tracking respuesta: {e}")
            return False
    
    async def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Obtener métricas de rendimiento"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cutoff_date = datetime.now(self.timezone) - timedelta(days=days)
                    
                    # Métricas por etapa
                    cursor.execute("""
                        SELECT 
                            stage,
                            COUNT(*) as total_sent,
                            COUNT(CASE WHEN user_responded THEN 1 END) as responses,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as response_rate,
                            AVG(response_time_hours) as avg_response_time_hours,
                            MIN(response_time_hours) as min_response_time,
                            MAX(response_time_hours) as max_response_time
                        FROM follow_up_history 
                        WHERE sent_at > %s
                        GROUP BY stage
                        ORDER BY stage
                    """, (cutoff_date,))
                    
                    stage_metrics = [dict(row) for row in cursor.fetchall()]
                    
                    # Métricas generales
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_followups,
                            COUNT(DISTINCT user_id) as unique_users,
                            COUNT(CASE WHEN user_responded THEN 1 END) as total_responses,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as overall_response_rate
                        FROM follow_up_history 
                        WHERE sent_at > %s
                    """, (cutoff_date,))
                    
                    general_metrics = dict(cursor.fetchone())
                    
                    # Mejores y peores etapas
                    best_stage = max(stage_metrics, key=lambda x: x['response_rate']) if stage_metrics else None
                    worst_stage = min(stage_metrics, key=lambda x: x['response_rate']) if stage_metrics else None
                    
                    return {
                        "period_days": days,
                        "general": general_metrics,
                        "by_stage": stage_metrics,
                        "best_performing_stage": best_stage,
                        "worst_performing_stage": worst_stage,
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas: {e}")
            return {"error": str(e)}
    
    async def get_user_followup_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtener historial de follow-ups de un usuario específico"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            stage,
                            message_sent,
                            sent_at,
                            user_responded,
                            responded_at,
                            response_time_hours,
                            response_message
                        FROM follow_up_history 
                        WHERE user_id = %s
                        ORDER BY sent_at DESC
                    """, (user_id,))
                    
                    return [dict(row) for row in cursor.fetchall()]
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial de usuario: {e}")
            return []
    
    async def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Obtener resumen diario de follow-ups"""
        try:
            if not date:
                date = datetime.now(self.timezone).date()
            
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())
            
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Follow-ups enviados en el día
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as sent_today,
                            COUNT(DISTINCT user_id) as unique_users,
                            COUNT(CASE WHEN user_responded THEN 1 END) as responses_today
                        FROM follow_up_history 
                        WHERE sent_at BETWEEN %s AND %s
                    """, (start_of_day, end_of_day))
                    
                    daily_stats = dict(cursor.fetchone())
                    
                    # Follow-ups programados para hoy
                    cursor.execute("""
                        SELECT COUNT(*) as scheduled_today
                        FROM follow_up_jobs 
                        WHERE scheduled_for::date = %s 
                        AND status = 'pending'
                    """, (date,))
                    
                    scheduled_stats = dict(cursor.fetchone())
                    
                    return {
                        "date": date.isoformat(),
                        "sent": daily_stats,
                        "scheduled": scheduled_stats,
                        "response_rate": round(
                            daily_stats['responses_today'] * 100.0 / max(daily_stats['sent_today'], 1), 2
                        )
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen diario: {e}")
            return {"error": str(e)}
    
    async def get_top_performing_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener mensajes con mejor tasa de respuesta"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            stage,
                            message_sent,
                            COUNT(*) as times_sent,
                            COUNT(CASE WHEN user_responded THEN 1 END) as responses,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as response_rate,
                            AVG(response_time_hours) as avg_response_time
                        FROM follow_up_history 
                        WHERE sent_at > %s
                        GROUP BY stage, message_sent
                        HAVING COUNT(*) >= 3  -- Mínimo 3 envíos para ser relevante
                        ORDER BY response_rate DESC, times_sent DESC
                        LIMIT %s
                    """, (datetime.now(self.timezone) - timedelta(days=30), limit))
                    
                    return [dict(row) for row in cursor.fetchall()]
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo mejores mensajes: {e}")
            return []
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Obtener estado actual de la cola de follow-ups"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Jobs pendientes por etapa
                    cursor.execute("""
                        SELECT 
                            stage,
                            COUNT(*) as pending_count,
                            MIN(scheduled_for) as next_scheduled,
                            MAX(scheduled_for) as last_scheduled
                        FROM follow_up_jobs 
                        WHERE status = 'pending'
                        GROUP BY stage
                        ORDER BY stage
                    """)
                    
                    queue_by_stage = [dict(row) for row in cursor.fetchall()]
                    
                    # Jobs por estado
                    cursor.execute("""
                        SELECT 
                            status,
                            COUNT(*) as job_count
                        FROM follow_up_jobs 
                        WHERE created_at > %s
                        GROUP BY status
                    """, (datetime.now(self.timezone) - timedelta(days=7),))
                    
                    status_summary = [dict(row) for row in cursor.fetchall()]
                    
                    # Próximos jobs a ejecutar
                    cursor.execute("""
                        SELECT 
                            user_id,
                            stage,
                            scheduled_for,
                            EXTRACT(EPOCH FROM (scheduled_for - %s))/3600 as hours_until
                        FROM follow_up_jobs 
                        WHERE status = 'pending'
                        AND scheduled_for > %s
                        ORDER BY scheduled_for
                        LIMIT 10
                    """, (datetime.now(self.timezone), datetime.now(self.timezone)))
                    
                    upcoming_jobs = [dict(row) for row in cursor.fetchall()]
                    
                    return {
                        "queue_by_stage": queue_by_stage,
                        "status_summary": status_summary,
                        "upcoming_jobs": upcoming_jobs,
                        "total_pending": sum(row['pending_count'] for row in queue_by_stage),
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de cola: {e}")
            return {"error": str(e)}
    
    async def calculate_effectiveness_scores(self):
        """Calcular scores de efectividad para mensajes"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Actualizar scores basado en respuestas y tiempo
                    cursor.execute("""
                        UPDATE follow_up_history 
                        SET effectiveness_score = CASE
                            WHEN user_responded = TRUE THEN
                                GREATEST(0.1, 1.0 - (response_time_hours / 48.0))  -- Score basado en rapidez
                            ELSE 0.0
                        END
                        WHERE effectiveness_score IS NULL 
                        AND sent_at > %s
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    updated_count = cursor.rowcount
                    logger.info(f"📊 Actualizados {updated_count} scores de efectividad")
                    
        except Exception as e:
            logger.error(f"❌ Error calculando scores: {e}")
    
    async def get_a_b_test_results(self) -> Dict[str, Any]:
        """Obtener resultados de A/B testing de mensajes"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Comparar performance por template usado
                    cursor.execute("""
                        SELECT 
                            template_used,
                            COUNT(*) as sent_count,
                            COUNT(CASE WHEN user_responded THEN 1 END) as response_count,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as response_rate,
                            AVG(effectiveness_score) as avg_effectiveness
                        FROM follow_up_history 
                        WHERE sent_at > %s
                        AND template_used IS NOT NULL
                        GROUP BY template_used
                        HAVING COUNT(*) >= 5  -- Mínimo 5 muestras
                        ORDER BY response_rate DESC
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    return {
                        "template_performance": [dict(row) for row in cursor.fetchall()],
                        "analysis_period": "30 days",
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo A/B test results: {e}")
            return {"error": str(e)}
    
    async def get_user_engagement_analysis(self) -> Dict[str, Any]:
        """Análisis de engagement de usuarios"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Análisis de engagement por tipo de usuario
                    cursor.execute("""
                        SELECT 
                            cc.is_entrepreneur,
                            COUNT(fh.id) as followups_received,
                            COUNT(CASE WHEN fh.user_responded THEN 1 END) as responses,
                            ROUND(
                                COUNT(CASE WHEN fh.user_responded THEN 1 END) * 100.0 / COUNT(fh.id), 2
                            ) as response_rate,
                            AVG(fh.response_time_hours) as avg_response_time
                        FROM conversation_contexts cc
                        JOIN follow_up_history fh ON cc.user_id = fh.user_id
                        WHERE fh.sent_at > %s
                        GROUP BY cc.is_entrepreneur
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    engagement_by_type = [dict(row) for row in cursor.fetchall()]
                    
                    # Análisis temporal - mejores horas para enviar
                    cursor.execute("""
                        SELECT 
                            EXTRACT(HOUR FROM sent_at) as hour,
                            COUNT(*) as sent_count,
                            COUNT(CASE WHEN user_responded THEN 1 END) as response_count,
                            ROUND(
                                COUNT(CASE WHEN user_responded THEN 1 END) * 100.0 / COUNT(*), 2
                            ) as response_rate
                        FROM follow_up_history 
                        WHERE sent_at > %s
                        GROUP BY EXTRACT(HOUR FROM sent_at)
                        HAVING COUNT(*) >= 3
                        ORDER BY response_rate DESC
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    best_hours = [dict(row) for row in cursor.fetchall()]
                    
                    return {
                        "engagement_by_user_type": engagement_by_type,
                        "best_hours_to_send": best_hours,
                        "analysis_period": "30 days",
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error en análisis de engagement: {e}")
            return {"error": str(e)}
    
    async def get_conversion_funnel(self) -> Dict[str, Any]:
        """Análisis de funnel de conversión por etapas"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Funnel por etapa
                    cursor.execute("""
                        WITH stage_funnel AS (
                            SELECT 
                                stage,
                                COUNT(DISTINCT user_id) as users_reached,
                                COUNT(CASE WHEN user_responded THEN DISTINCT user_id END) as users_responded
                            FROM follow_up_history
                            WHERE sent_at > %s
                            GROUP BY stage
                        )
                        SELECT 
                            stage,
                            users_reached,
                            users_responded,
                            ROUND(users_responded * 100.0 / users_reached, 2) as conversion_rate,
                            LAG(users_reached) OVER (ORDER BY stage) as previous_stage_users,
                            ROUND(
                                users_reached * 100.0 / LAG(users_reached) OVER (ORDER BY stage), 2
                            ) as retention_rate
                        FROM stage_funnel
                        ORDER BY stage
                    """, (datetime.now(self.timezone) - timedelta(days=30),))
                    
                    funnel_data = [dict(row) for row in cursor.fetchall()]
                    
                    # Calcular drop-off rates
                    for i, stage_data in enumerate(funnel_data):
                        if i > 0:
                            prev_users = funnel_data[i-1]['users_reached']
                            current_users = stage_data['users_reached']
                            drop_off = round((prev_users - current_users) * 100.0 / prev_users, 2)
                            stage_data['drop_off_rate'] = drop_off
                        else:
                            stage_data['drop_off_rate'] = 0.0
                    
                    return {
                        "funnel_analysis": funnel_data,
                        "total_users_entered": funnel_data[0]['users_reached'] if funnel_data else 0,
                        "total_users_completed": funnel_data[-1]['users_reached'] if funnel_data else 0,
                        "overall_completion_rate": round(
                            (funnel_data[-1]['users_reached'] * 100.0 / funnel_data[0]['users_reached'])
                            if funnel_data and funnel_data[0]['users_reached'] > 0 else 0, 2
                        ),
                        "analysis_period": "30 days",
                        "generated_at": datetime.now(self.timezone).isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error en análisis de funnel: {e}")
            return {"error": str(e)}
    
    async def export_metrics_data(self, format: str = "json") -> Any:
        """Exportar datos de métricas en diferentes formatos"""
        try:
            # Obtener todos los datos
            performance = await self.get_performance_metrics(30)
            engagement = await self.get_user_engagement_analysis()
            funnel = await self.get_conversion_funnel()
            
            export_data = {
                "export_timestamp": datetime.now(self.timezone).isoformat(),
                "performance_metrics": performance,
                "engagement_analysis": engagement,
                "conversion_funnel": funnel
            }
            
            if format == "json":
                return export_data
            elif format == "csv":
                # Aquí podrías agregar lógica para convertir a CSV
                return "CSV export not implemented yet"
            else:
                return export_data
                
        except Exception as e:
            logger.error(f"❌ Error exportando métricas: {e}")
            return {"error": str(e)}