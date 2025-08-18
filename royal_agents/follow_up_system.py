# Sistema de Seguimiento Automático de 14 Etapas para Royal Bot
# Gestiona el ciclo completo de follow-up post-conversación

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import logging
import psycopg2
import pytz
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.DEBUG)  # Cambiado a DEBUG para más detalle
logger = logging.getLogger(__name__)

# Timezone de Argentina/Córdoba
ARG_TZ = pytz.timezone('America/Argentina/Cordoba')

def ensure_argentina_tz(dt):
    """Asegura que un datetime tenga timezone Argentina/Córdoba"""
    if dt is None:
        return None
    
    # Si no tiene timezone, asumimos que es hora local Argentina
    if dt.tzinfo is None:
        return ARG_TZ.localize(dt)
    
    # Si tiene timezone, convertimos a Argentina
    return dt.astimezone(ARG_TZ)

class FollowUpStage(Enum):
    """Etapas del sistema de seguimiento"""
    STAGE_0 = 0    # Inmediato (1 hora después)
    STAGE_1 = 1    # Día 1
    STAGE_2 = 2    # Día 2  
    STAGE_4 = 4    # Día 4
    STAGE_7 = 7    # Día 7
    STAGE_10 = 10  # Día 10
    STAGE_14 = 14  # Día 14
    STAGE_18 = 18  # Día 18
    STAGE_26 = 26  # Día 26
    STAGE_36 = 36  # Día 36
    STAGE_46 = 46  # Día 46
    STAGE_56 = 56  # Día 56
    STAGE_66 = 66  # Día 66
    MAINTENANCE = 999  # Cada 15 días después del día 66

@dataclass
class UserFollowUp:
    """Modelo de datos para seguimiento de usuario"""
    user_id: str
    current_stage: int
    last_interaction: datetime
    stage_start_time: datetime
    is_active: bool
    user_profile: Optional[Dict] = None
    interaction_count: int = 0
    last_stage_completed: Optional[int] = None

class FollowUpDatabaseManager:
    """Gestor de base de datos para el sistema de seguimiento"""
    
    def __init__(self):
        # Usar DATABASE_URL si está disponible (Railway/Producción)
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Parse DATABASE_URL para psycopg2
            import urllib.parse as urlparse
            url = urlparse.urlparse(database_url)
            self.db_config = {
                'database': url.path[1:],
                'user': url.username,
                'password': url.password,
                'host': url.hostname,
                'port': url.port
            }
            logger.info(f"✅ Usando DATABASE_URL para conexión PostgreSQL (host: {url.hostname})")
        else:
            # Fallback para desarrollo local
            self.db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'database': os.getenv('POSTGRES_DB', 'royal_bot'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'password'),
                'port': os.getenv('POSTGRES_PORT', 5432)
            }
            logger.info("📍 Usando configuración local de PostgreSQL")
        
        # Inicializar tabla si no existe
        self._init_database()
        
    def _init_database(self):
        """Inicializa la tabla de seguimiento si no existe"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    # Crear tabla de seguimiento
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_follow_ups (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) UNIQUE NOT NULL,
                            current_stage INTEGER DEFAULT 0,
                            last_interaction TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            stage_start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            is_active BOOLEAN DEFAULT true,
                            user_profile JSONB DEFAULT '{}',
                            interaction_count INTEGER DEFAULT 0,
                            last_stage_completed INTEGER DEFAULT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Crear índices para optimizar consultas
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_follow_ups_user_id 
                        ON user_follow_ups(user_id)
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_follow_ups_active_stage 
                        ON user_follow_ups(is_active, current_stage)
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_follow_ups_stage_start_time 
                        ON user_follow_ups(stage_start_time)
                    """)
                    
                    conn.commit()
                    logger.info("✅ Base de datos de seguimiento inicializada correctamente")
                    
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
    
    def get_user_followup(self, user_id: str) -> Optional[UserFollowUp]:
        """Obtiene el estado de seguimiento de un usuario"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM user_follow_ups 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    row = cur.fetchone()
                    if row:
                        # Normalizar fechas a timezone Argentina
                        normalized_stage_start = ensure_argentina_tz(row['stage_start_time'])
                        normalized_last_interaction = ensure_argentina_tz(row['last_interaction'])
                        
                        return UserFollowUp(
                            user_id=row['user_id'],
                            current_stage=row['current_stage'],
                            last_interaction=normalized_last_interaction,
                            stage_start_time=normalized_stage_start,
                            is_active=row['is_active'],
                            user_profile=row['user_profile'],
                            interaction_count=row['interaction_count'],
                            last_stage_completed=row['last_stage_completed']
                        )
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error obteniendo seguimiento para {user_id}: {e}")
            return None
    
    def create_or_update_followup(self, user_followup: UserFollowUp) -> bool:
        """Crea o actualiza el seguimiento de un usuario"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_follow_ups (
                            user_id, current_stage, last_interaction, stage_start_time,
                            is_active, user_profile, interaction_count, last_stage_completed
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            current_stage = EXCLUDED.current_stage,
                            last_interaction = EXCLUDED.last_interaction,
                            stage_start_time = EXCLUDED.stage_start_time,
                            is_active = EXCLUDED.is_active,
                            user_profile = EXCLUDED.user_profile,
                            interaction_count = EXCLUDED.interaction_count,
                            last_stage_completed = EXCLUDED.last_stage_completed,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        user_followup.user_id,
                        user_followup.current_stage,
                        user_followup.last_interaction,
                        user_followup.stage_start_time,
                        user_followup.is_active,
                        json.dumps(user_followup.user_profile or {}),
                        user_followup.interaction_count,
                        user_followup.last_stage_completed
                    ))
                    
                    conn.commit()
                    logger.info(f"✅ Follow-up actualizado para usuario {user_followup.user_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error actualizando follow-up para {user_followup.user_id}: {e}")
            return False
    
    def get_users_ready_for_followup(self) -> List[UserFollowUp]:
        """Obtiene usuarios listos para recibir el siguiente mensaje de seguimiento"""
        try:
            current_time = datetime.now(ARG_TZ)
            users_ready = []
            
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Buscar usuarios activos
                    cur.execute("""
                        SELECT * FROM user_follow_ups 
                        WHERE is_active = true
                        ORDER BY stage_start_time ASC
                    """)
                    
                    rows = cur.fetchall()
                    
                    for row in rows:
                        # Normalizar fechas a timezone Argentina
                        normalized_stage_start = ensure_argentina_tz(row['stage_start_time'])
                        normalized_last_interaction = ensure_argentina_tz(row['last_interaction'])
                        
                        user_followup = UserFollowUp(
                            user_id=row['user_id'],
                            current_stage=row['current_stage'],
                            last_interaction=normalized_last_interaction,
                            stage_start_time=normalized_stage_start,
                            is_active=row['is_active'],
                            user_profile=row['user_profile'],
                            interaction_count=row['interaction_count'],
                            last_stage_completed=row['last_stage_completed']
                        )
                        
                        # Debug logging
                        logger.debug(f"Usuario {user_followup.user_id}: stage={user_followup.current_stage}, "
                                   f"stage_start={normalized_stage_start}, current_time={current_time}")
                        
                        # Verificar si es momento de enviar mensaje
                        if self._should_send_followup(user_followup, current_time):
                            users_ready.append(user_followup)
                            logger.info(f"✅ Usuario {user_followup.user_id} listo para follow-up etapa {user_followup.current_stage}")
                            
            logger.info(f"📊 Usuarios listos para follow-up: {len(users_ready)}")
            return users_ready
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuarios para follow-up: {e}")
            return []
    
    def _should_send_followup(self, user_followup: UserFollowUp, current_time: datetime) -> bool:
        """Determina si es momento de enviar un mensaje de seguimiento"""
        
        # Definir intervalos entre etapas (cuánto esperar ENTRE cada etapa)
        # La clave es la etapa actual, el valor es cuánto esperar hasta el próximo envío
        stage_intervals = {
            0: timedelta(hours=1),    # Etapa 0: esperar 1 hora
            1: timedelta(days=1),      # Etapa 1 → 2: esperar 1 día
            2: timedelta(days=2),      # Etapa 2 → 4: esperar 2 días
            4: timedelta(days=3),      # Etapa 4 → 7: esperar 3 días
            7: timedelta(days=3),      # Etapa 7 → 10: esperar 3 días
            10: timedelta(days=4),     # Etapa 10 → 14: esperar 4 días
            14: timedelta(days=4),     # Etapa 14 → 18: esperar 4 días
            18: timedelta(days=8),     # Etapa 18 → 26: esperar 8 días
            26: timedelta(days=10),    # Etapa 26 → 36: esperar 10 días
            36: timedelta(days=10),    # Etapa 36 → 46: esperar 10 días
            46: timedelta(days=10),    # Etapa 46 → 56: esperar 10 días
            56: timedelta(days=10),    # Etapa 56 → 66: esperar 10 días
            66: timedelta(days=15),    # Etapa 66 → mantenimiento: esperar 15 días
            999: timedelta(days=15)    # Mantenimiento: cada 15 días
        }
        
        # Calcular tiempo desde el inicio de la etapa
        time_since_stage_start = current_time - user_followup.stage_start_time
        
        # Obtener el intervalo para la etapa actual
        required_interval = stage_intervals.get(user_followup.current_stage)
        
        if required_interval is None:
            logger.warning(f"⚠️ Etapa no definida: {user_followup.current_stage} para usuario {user_followup.user_id}")
            return False
        
        # Calcular si es tiempo de enviar
        should_send = time_since_stage_start >= required_interval
        
        # Logging mejorado
        if should_send:
            logger.info(f"✅ Usuario {user_followup.user_id} listo para follow-up:")
            logger.info(f"   - Etapa actual: {user_followup.current_stage}")
            logger.info(f"   - Tiempo esperado: {required_interval}")
            logger.info(f"   - Tiempo transcurrido: {time_since_stage_start}")
        else:
            # Calcular tiempo restante
            time_remaining = required_interval - time_since_stage_start
            logger.debug(f"⏳ Usuario {user_followup.user_id} en etapa {user_followup.current_stage}:")
            logger.debug(f"   - Tiempo transcurrido: {time_since_stage_start}")
            logger.debug(f"   - Tiempo requerido: {required_interval}")
            logger.debug(f"   - Tiempo restante: {time_remaining}")
        
        return should_send
    
    def deactivate_followup(self, user_id: str) -> bool:
        """Desactiva el seguimiento para un usuario"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_follow_ups 
                        SET is_active = false, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    conn.commit()
                    logger.info(f"✅ Follow-up desactivado para usuario {user_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error desactivando follow-up para {user_id}: {e}")
            return False
    
    def reset_to_stage_zero(self, user_id: str, user_profile: Optional[Dict] = None) -> bool:
        """Resetea un usuario al Día 0 (cuando responde)"""
        current_time = datetime.now(timezone.utc)
        
        # Obtener o crear nuevo seguimiento
        existing = self.get_user_followup(user_id)
        
        if existing:
            # Incrementar contador de interacciones
            interaction_count = existing.interaction_count + 1
            profile = existing.user_profile or {}
            if user_profile:
                profile.update(user_profile)
        else:
            interaction_count = 1
            profile = user_profile or {}
        
        new_followup = UserFollowUp(
            user_id=user_id,
            current_stage=0,  # Resetear a etapa 0
            last_interaction=current_time,
            stage_start_time=current_time,
            is_active=True,
            user_profile=profile,
            interaction_count=interaction_count
        )
        
        success = self.create_or_update_followup(new_followup)
        
        if success:
            logger.info(f"🔄 Usuario {user_id} reseteado a Día 0. Interacciones: {interaction_count}")
        
        return success
    
    def advance_to_next_stage(self, user_id: str) -> bool:
        """Avanza un usuario a la siguiente etapa"""
        try:
            user_followup = self.get_user_followup(user_id)
            if not user_followup:
                logger.warning(f"⚠️ No se encontró follow-up para usuario {user_id}")
                return False
            
            # Determinar siguiente etapa
            current_stage = user_followup.current_stage
            
            # Secuencia de etapas según el plan
            stage_sequence = [0, 1, 2, 4, 7, 10, 14, 18, 26, 36, 46, 56, 66, 999]
            
            try:
                current_index = stage_sequence.index(current_stage)
                if current_index < len(stage_sequence) - 1:
                    next_stage = stage_sequence[current_index + 1]
                else:
                    # Mantenerse en modo mantenimiento
                    next_stage = 999
            except ValueError:
                # Si la etapa actual no está en la secuencia, ir a la siguiente lógica
                next_stage = 1
            
            # Actualizar seguimiento
            user_followup.last_stage_completed = current_stage
            user_followup.current_stage = next_stage
            user_followup.stage_start_time = datetime.now(ARG_TZ)
            
            success = self.create_or_update_followup(user_followup)
            
            if success:
                logger.info(f"📈 Usuario {user_id} avanzado de etapa {current_stage} a {next_stage}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error avanzando etapa para {user_id}: {e}")
            return False

# Instancia global del gestor de base de datos
db_manager = FollowUpDatabaseManager()

# Funciones de conveniencia para usar desde otros módulos
def activate_followup_for_user(user_id: str, user_profile: Optional[Dict] = None) -> bool:
    """Activa el seguimiento para un usuario (después de una conversación)"""
    return db_manager.reset_to_stage_zero(user_id, user_profile)

def user_responded(user_id: str, user_profile: Optional[Dict] = None) -> bool:
    """Marca que un usuario respondió (resetea a Día 0)"""
    return db_manager.reset_to_stage_zero(user_id, user_profile)

def get_users_for_followup() -> List[UserFollowUp]:
    """Obtiene todos los usuarios listos para recibir mensajes de seguimiento"""
    return db_manager.get_users_ready_for_followup()

def complete_followup_stage(user_id: str) -> bool:
    """Marca una etapa como completada y avanza a la siguiente"""
    return db_manager.advance_to_next_stage(user_id)

def deactivate_user_followup(user_id: str) -> bool:
    """Desactiva el seguimiento para un usuario"""
    return db_manager.deactivate_followup(user_id)

def get_user_followup_status(user_id: str) -> Optional[UserFollowUp]:
    """Obtiene el estado actual del seguimiento de un usuario"""
    return db_manager.get_user_followup(user_id)

if __name__ == "__main__":
    # Test básico
    logger.info("🧪 Iniciando test del sistema de seguimiento")
    
    # Crear usuario de prueba
    test_user_id = "test_user_001"
    test_profile = {"type": "emprendedor", "interest": "joyas"}
    
    # Activar seguimiento
    success = activate_followup_for_user(test_user_id, test_profile)
    logger.info(f"Test activación: {success}")
    
    # Obtener status
    status = get_user_followup_status(test_user_id)
    if status:
        logger.info(f"Status: Etapa {status.current_stage}, Activo: {status.is_active}")
    
    logger.info("✅ Test completado")