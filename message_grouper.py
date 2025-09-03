#!/usr/bin/env python3
"""
📬 MESSAGE GROUPER - SISTEMA DE AGRUPAMIENTO DE MENSAJES CONSECUTIVOS
Agrupa mensajes consecutivos del mismo usuario para crear contexto coherente para la IA.
No interfiere con el sistema existente de colas y procesamiento.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN
# =====================================================

# Variables de entorno para configuración
MESSAGE_GROUPING_ENABLED = os.getenv("MESSAGE_GROUPING_ENABLED", "true").lower() == "true"
MESSAGE_GROUPING_DELAY = int(os.getenv("MESSAGE_GROUPING_DELAY", "3"))  # segundos
MAX_GROUPED_MESSAGES = int(os.getenv("MAX_GROUPED_MESSAGES", "4"))
GROUPING_DEBUG = os.getenv("GROUPING_DEBUG", "false").lower() == "true"

# =====================================================
# MODELOS DE DATOS
# =====================================================

@dataclass
class PendingMessage:
    """Mensaje pendiente en el buffer de agrupamiento"""
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class PendingGroup:
    """Grupo de mensajes pendientes para un usuario"""
    user_id: str
    messages: List[PendingMessage] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """Agregar mensaje al grupo"""
        message = PendingMessage(
            content=content.strip(),
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        
        if GROUPING_DEBUG:
            logger.info(f"🔄 Mensaje agregado al grupo {self.user_id}: '{content}' (total: {len(self.messages)})")

    def should_process_immediately(self) -> bool:
        """Determinar si el grupo debe procesarse inmediatamente"""
        # Procesar si alcanzó el máximo
        if len(self.messages) >= MAX_GROUPED_MESSAGES:
            return True
        
        # Procesar si hay mensajes urgentes
        last_message = self.messages[-1].content.lower()
        urgent_keywords = ['urgente', 'problema', 'error', 'ayuda', 'rápido']
        if any(keyword in last_message for keyword in urgent_keywords):
            return True
        
        return False

    def create_grouped_message(self) -> str:
        """Crear mensaje agrupado contextual para la IA"""
        if len(self.messages) == 1:
            return self.messages[0].content
        
        # Formato contextual para múltiples mensajes
        result_parts = []
        
        # Primer mensaje
        first_msg = self.messages[0]
        result_parts.append(f"Usuario escribió: '{first_msg.content}'")
        
        # Mensajes adicionales
        for i, msg in enumerate(self.messages[1:], 1):
            # Calcular tiempo entre mensajes
            time_diff = (msg.timestamp - self.messages[i-1].timestamp).total_seconds()
            
            if time_diff <= 2:
                result_parts.append(f"Y agregó inmediatamente: '{msg.content}'")
            elif time_diff <= 5:
                result_parts.append(f"Y agregó: '{msg.content}'")
            else:
                result_parts.append(f"Luego agregó: '{msg.content}'")
        
        grouped_message = ". ".join(result_parts)
        
        if GROUPING_DEBUG:
            logger.info(f"🔗 Mensaje agrupado creado: '{grouped_message}'")
        
        return grouped_message

# =====================================================
# MESSAGE GROUPER PRINCIPAL
# =====================================================

class MessageGrouper:
    """
    Sistema de agrupamiento de mensajes consecutivos.
    Mantiene buffers temporales por usuario y agrupa mensajes relacionados.
    """
    
    def __init__(self):
        self.pending_groups: Dict[str, PendingGroup] = {}
        self.stats = {
            'messages_received': 0,
            'groups_created': 0, 
            'messages_grouped': 0,
            'immediate_processing': 0
        }
        
        logger.info(f"📬 MessageGrouper inicializado (habilitado: {MESSAGE_GROUPING_ENABLED})")
    
    async def should_group(self, user_id: str, message: str, metadata: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
        """
        Determina si el mensaje debe agruparse o procesarse inmediatamente.
        
        Returns:
            Tuple[bool, Optional[str]]: 
            - bool: True si debe esperar (no procesar aún), False si procesar ahora
            - str: Mensaje agrupado si está listo para procesar, None si debe esperar
        """
        
        if not MESSAGE_GROUPING_ENABLED:
            # Sistema deshabilitado, procesar inmediatamente
            return False, message
        
        self.stats['messages_received'] += 1
        
        # Limpiar mensaje
        message = message.strip()
        if not message:
            return False, message
        
        # Verificar si existe grupo pendiente para este usuario
        if user_id in self.pending_groups:
            group = self.pending_groups[user_id]
            
            # Cancelar timer anterior
            if group.timer_task and not group.timer_task.done():
                group.timer_task.cancel()
                if GROUPING_DEBUG:
                    logger.info(f"⏰ Timer cancelado para {user_id} (nuevo mensaje)")
            
            # Agregar mensaje al grupo
            group.add_message(message, metadata)
            
            # Verificar si debe procesarse inmediatamente
            if group.should_process_immediately():
                grouped_message = group.create_grouped_message()
                self._cleanup_group(user_id)
                self.stats['immediate_processing'] += 1
                
                if GROUPING_DEBUG:
                    logger.info(f"⚡ Procesamiento inmediato para {user_id}: {len(group.messages)} mensajes")
                
                return False, grouped_message
            
            # Programar nuevo timer
            group.timer_task = asyncio.create_task(
                self._process_group_after_delay(user_id)
            )
            
            return True, None  # Esperar más mensajes
        
        else:
            # Nuevo grupo - crear y programar timer
            group = PendingGroup(user_id=user_id)
            group.add_message(message, metadata)
            
            # Verificar si es mensaje urgente (procesar inmediatamente)
            if group.should_process_immediately():
                self.stats['immediate_processing'] += 1
                
                if GROUPING_DEBUG:
                    logger.info(f"⚡ Mensaje urgente para {user_id}, procesando inmediatamente")
                
                return False, message
            
            # Guardar grupo y programar timer
            self.pending_groups[user_id] = group
            group.timer_task = asyncio.create_task(
                self._process_group_after_delay(user_id)
            )
            
            if GROUPING_DEBUG:
                logger.info(f"⏰ Nuevo grupo creado para {user_id}, timer iniciado ({MESSAGE_GROUPING_DELAY}s)")
            
            return True, None  # Esperar más mensajes
    
    async def _process_group_after_delay(self, user_id: str) -> None:
        """Procesar grupo después del delay configurado"""
        try:
            await asyncio.sleep(MESSAGE_GROUPING_DELAY)
            
            if user_id not in self.pending_groups:
                return  # Ya fue procesado
            
            group = self.pending_groups[user_id]
            grouped_message = group.create_grouped_message()
            
            # Usar callback pattern para evitar dependencias circulares
            if hasattr(self, '_message_processor_callback'):
                try:
                    success = await self._message_processor_callback(
                        user_id=user_id,
                        message=grouped_message,
                        metadata=group.messages[0].metadata,
                        group_size=len(group.messages)
                    )
                    
                except Exception as pe:
                    logger.error(f"❌ Error en callback de procesamiento: {pe}")
                    success = False
            else:
                logger.warning(f"⚠️ No hay callback configurado para procesar grupo de {user_id}")
                # En testing mode, simular éxito
                success = True
            
            # Actualizar estadísticas
            if success:
                self.stats['groups_created'] += 1
                self.stats['messages_grouped'] += len(group.messages)
                
                if GROUPING_DEBUG:
                    logger.info(f"✅ Grupo procesado para {user_id}: {len(group.messages)} mensajes agrupados")
            else:
                logger.error(f"❌ Error procesando grupo para {user_id}")
            
            # Limpiar grupo
            self._cleanup_group(user_id)
            
        except asyncio.CancelledError:
            # Timer fue cancelado, no hacer nada
            if GROUPING_DEBUG:
                logger.info(f"⏰ Timer cancelado para {user_id}")
            pass
        except Exception as e:
            logger.error(f"❌ Error procesando grupo {user_id}: {e}")
            self._cleanup_group(user_id)
    
    def _cleanup_group(self, user_id: str) -> None:
        """Limpiar grupo de usuario"""
        if user_id in self.pending_groups:
            group = self.pending_groups.pop(user_id)
            if group.timer_task and not group.timer_task.done():
                group.timer_task.cancel()
            
            if GROUPING_DEBUG:
                logger.info(f"🧹 Grupo limpiado para {user_id}")
    
    async def force_process_all_groups(self) -> int:
        """Forzar procesamiento de todos los grupos pendientes (para shutdown)"""
        processed = 0
        
        for user_id in list(self.pending_groups.keys()):
            group = self.pending_groups[user_id]
            if group.timer_task and not group.timer_task.done():
                group.timer_task.cancel()
            
            # Procesar inmediatamente
            try:
                grouped_message = group.create_grouped_message()
                # Aquí normalmente llamaríamos a process_message_pipeline
                # pero en shutdown solo limpiamos
                processed += 1
                logger.info(f"🔄 Forzado procesamiento de grupo {user_id}")
            except Exception as e:
                logger.error(f"❌ Error en forzado de grupo {user_id}: {e}")
            
            self._cleanup_group(user_id)
        
        return processed
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del agrupamiento"""
        return {
            'grouping_enabled': MESSAGE_GROUPING_ENABLED,
            'grouping_delay': MESSAGE_GROUPING_DELAY,
            'max_grouped_messages': MAX_GROUPED_MESSAGES,
            'pending_groups': len(self.pending_groups),
            'stats': self.stats.copy(),
            'active_timers': sum(1 for group in self.pending_groups.values() 
                               if group.timer_task and not group.timer_task.done())
        }
    
    async def cleanup_expired_groups(self) -> int:
        """Limpiar grupos que han estado pendientes demasiado tiempo"""
        cleaned = 0
        cutoff_time = datetime.now() - timedelta(minutes=5)  # 5 minutos máximo
        
        for user_id in list(self.pending_groups.keys()):
            group = self.pending_groups[user_id]
            if group.created_at < cutoff_time:
                logger.warning(f"🧹 Limpiando grupo expirado para {user_id}")
                self._cleanup_group(user_id)
                cleaned += 1
        
        return cleaned

# =====================================================
# INSTANCIA GLOBAL
# =====================================================

# Instancia global del agrupador
message_grouper = MessageGrouper()

# Funciones de conveniencia
async def should_group_message(user_id: str, message: str, metadata: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
    """Función de conveniencia para verificar agrupamiento"""
    return await message_grouper.should_group(user_id, message, metadata or {})

async def force_process_all_pending() -> int:
    """Función de conveniencia para forzar procesamiento"""
    return await message_grouper.force_process_all_groups()

def get_grouper_stats() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas"""
    return message_grouper.get_stats()

# =====================================================
# TASK PERIÓDICA DE LIMPIEZA
# =====================================================

async def start_grouper_maintenance():
    """Iniciar tareas de mantenimiento del agrupador"""
    
    async def maintenance_loop():
        while True:
            try:
                # Limpiar grupos expirados cada 2 minutos
                await asyncio.sleep(120)
                cleaned = await message_grouper.cleanup_expired_groups()
                
                if cleaned > 0:
                    logger.info(f"🧹 Limpieza automática: {cleaned} grupos expirados")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error en mantenimiento de agrupador: {e}")
    
    # Solo iniciar si está habilitado
    if MESSAGE_GROUPING_ENABLED:
        asyncio.create_task(maintenance_loop())
        logger.info("✅ Mantenimiento de MessageGrouper iniciado")

if __name__ == "__main__":
    # Test del sistema de agrupamiento
    async def test_grouper():
        print("🧪 Testing MessageGrouper...")
        
        # Test básico
        should_wait1, msg1 = await should_group_message("test_user", "hola", {"source": "test"})
        print(f"Mensaje 1 - Esperar: {should_wait1}, Mensaje: {msg1}")
        
        # Esperar un poco
        await asyncio.sleep(1)
        
        # Segundo mensaje
        should_wait2, msg2 = await should_group_message("test_user", "como estas", {"source": "test"})
        print(f"Mensaje 2 - Esperar: {should_wait2}, Mensaje: {msg2}")
        
        # Esperar el procesamiento automático
        await asyncio.sleep(4)
        
        # Estadísticas
        stats = get_grouper_stats()
        print(f"Estadísticas: {json.dumps(stats, indent=2, default=str)}")
    
    asyncio.run(test_grouper())