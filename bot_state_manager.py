#!/usr/bin/env python3
"""
🤖 BOT STATE MANAGER
Sistema de gestión de estados del bot con Redis
Permite pausar/reactivar el bot por usuario/conversación
"""

import redis.asyncio as redis
from typing import Optional, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BotStateManager:
    """
    Gestiona el estado del bot (activo/pausado) para cada usuario
    usando Redis como almacenamiento persistente
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self) -> bool:
        """Inicializar conexión con Redis"""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self.redis_client.ping()
            logger.info("✅ BotStateManager: Redis conectado correctamente")
            return True
        except Exception as e:
            logger.error(f"❌ BotStateManager: Error conectando Redis - {e}")
            logger.warning("⚠️ BotStateManager funcionará sin persistencia")
            return False
    
    async def close(self):
        """Cerrar conexión con Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 BotStateManager: Conexión Redis cerrada")
    
    async def pause_bot(self, identifier: str, reason: str = "manual", ttl: int = 86400) -> bool:
        """
        Pausar el bot para un identificador específico
        
        Args:
            identifier: Número de teléfono o ID de conversación
            reason: Razón de la pausa (agent_control, user_command, manual)
            ttl: Tiempo de vida en segundos (default: 24 horas)
        """
        if not self.redis_client:
            logger.warning(f"⚠️ Sin Redis: No se puede pausar bot para {identifier}")
            return False
        
        try:
            # Limpiar identificador (quitar prefijos comunes)
            clean_id = identifier.replace("@s.whatsapp.net", "").replace("whatsapp_", "")
            
            # Guardar estado con metadata
            key = f"bot_state:{clean_id}"
            value = {
                "status": "paused",
                "reason": reason,
                "paused_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            # Serializar como JSON string
            import json
            await self.redis_client.set(key, json.dumps(value), ex=ttl)
            
            logger.info(f"🔴 Bot pausado para {clean_id} - Razón: {reason} - TTL: {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error pausando bot para {identifier}: {e}")
            return False
    
    async def resume_bot(self, identifier: str) -> bool:
        """
        Reactivar el bot para un identificador específico
        
        Args:
            identifier: Número de teléfono o ID de conversación
        """
        if not self.redis_client:
            logger.warning(f"⚠️ Sin Redis: No se puede reactivar bot para {identifier}")
            return False
        
        try:
            # Limpiar identificador
            clean_id = identifier.replace("@s.whatsapp.net", "").replace("whatsapp_", "")
            
            key = f"bot_state:{clean_id}"
            result = await self.redis_client.delete(key)
            
            if result > 0:
                logger.info(f"🟢 Bot reactivado para {clean_id}")
                return True
            else:
                logger.info(f"ℹ️ Bot ya estaba activo para {clean_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error reactivando bot para {identifier}: {e}")
            return False
    
    async def is_bot_active(self, identifier: str) -> bool:
        """
        Verificar si el bot está activo para un identificador
        
        Args:
            identifier: Número de teléfono o ID de conversación
            
        Returns:
            True si el bot está activo, False si está pausado
        """
        if not self.redis_client:
            # Sin Redis, asumir que el bot está siempre activo
            return True
        
        try:
            # Limpiar identificador
            clean_id = identifier.replace("@s.whatsapp.net", "").replace("whatsapp_", "")
            
            key = f"bot_state:{clean_id}"
            state = await self.redis_client.get(key)
            
            # Si no hay estado guardado, el bot está activo
            if not state:
                return True
            
            # Parsear estado
            import json
            state_data = json.loads(state)
            
            # Bot está pausado si el status es "paused"
            is_active = state_data.get("status") != "paused"
            
            if not is_active:
                logger.debug(f"🔇 Bot pausado para {clean_id} - {state_data.get('reason')}")
            
            return is_active
            
        except Exception as e:
            logger.error(f"❌ Error verificando estado del bot para {identifier}: {e}")
            # En caso de error, asumir que el bot está activo
            return True
    
    async def get_bot_state(self, identifier: str) -> Dict:
        """
        Obtener información detallada del estado del bot
        
        Args:
            identifier: Número de teléfono o ID de conversación
            
        Returns:
            Diccionario con información del estado
        """
        default_state = {
            "active": True,
            "status": "active",
            "reason": None,
            "paused_at": None,
            "ttl_remaining": None
        }
        
        if not self.redis_client:
            return default_state
        
        try:
            # Limpiar identificador
            clean_id = identifier.replace("@s.whatsapp.net", "").replace("whatsapp_", "")
            
            key = f"bot_state:{clean_id}"
            state = await self.redis_client.get(key)
            
            if not state:
                return default_state
            
            # Parsear estado
            import json
            state_data = json.loads(state)
            
            # Obtener TTL restante
            ttl = await self.redis_client.ttl(key)
            
            return {
                "active": state_data.get("status") != "paused",
                "status": state_data.get("status", "active"),
                "reason": state_data.get("reason"),
                "paused_at": state_data.get("paused_at"),
                "ttl_remaining": ttl if ttl > 0 else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del bot para {identifier}: {e}")
            return default_state
    
    async def pause_all_bots(self, reason: str = "maintenance") -> int:
        """
        Pausar todos los bots (útil para mantenimiento)
        
        Returns:
            Número de bots pausados
        """
        if not self.redis_client:
            return 0
        
        try:
            # Obtener todas las claves de estado
            pattern = "bot_state:*"
            cursor = 0
            paused_count = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern)
                
                for key in keys:
                    # Extraer identificador de la clave
                    identifier = key.replace("bot_state:", "")
                    if await self.pause_bot(identifier, reason):
                        paused_count += 1
                
                if cursor == 0:
                    break
            
            logger.info(f"⏸️ {paused_count} bots pausados - Razón: {reason}")
            return paused_count
            
        except Exception as e:
            logger.error(f"❌ Error pausando todos los bots: {e}")
            return 0
    
    async def resume_all_bots(self) -> int:
        """
        Reactivar todos los bots
        
        Returns:
            Número de bots reactivados
        """
        if not self.redis_client:
            return 0
        
        try:
            # Obtener todas las claves de estado
            pattern = "bot_state:*"
            keys = []
            cursor = 0
            
            while True:
                cursor, batch_keys = await self.redis_client.scan(cursor, match=pattern)
                keys.extend(batch_keys)
                if cursor == 0:
                    break
            
            # Eliminar todas las claves
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"▶️ {deleted} bots reactivados")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error reactivando todos los bots: {e}")
            return 0
    
    async def get_stats(self) -> Dict:
        """
        Obtener estadísticas del sistema
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_paused": 0,
            "by_reason": {},
            "redis_connected": self.redis_client is not None
        }
        
        if not self.redis_client:
            return stats
        
        try:
            # Contar bots pausados
            pattern = "bot_state:*"
            cursor = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern)
                
                for key in keys:
                    stats["total_paused"] += 1
                    
                    # Obtener razón
                    state = await self.redis_client.get(key)
                    if state:
                        import json
                        state_data = json.loads(state)
                        reason = state_data.get("reason", "unknown")
                        stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
                
                if cursor == 0:
                    break
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return stats


# Singleton instance
_bot_state_manager: Optional[BotStateManager] = None

async def get_bot_state_manager(redis_url: str = None) -> BotStateManager:
    """
    Obtener instancia singleton del BotStateManager
    
    Args:
        redis_url: URL de Redis (usar variable de entorno si no se proporciona)
    """
    global _bot_state_manager
    
    if _bot_state_manager is None:
        import os
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        _bot_state_manager = BotStateManager(redis_url)
        await _bot_state_manager.initialize()
    
    return _bot_state_manager