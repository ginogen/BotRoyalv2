#!/usr/bin/env python3
"""
📬 ADVANCED MESSAGE QUEUE SYSTEM - MAXIMUM EFFICIENCY
Multi-priority persistent queue with dead letter handling
Designed for Railway deployment with PostgreSQL + Redis
"""

import os
import json
import logging
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import time

# Database imports
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# =====================================================
# ENUMS AND CONSTANTS
# =====================================================

class MessagePriority(Enum):
    """Message priority levels with numeric values for ordering"""
    URGENT = 0      # VIP users, system errors, escalations
    HIGH = 1        # Active entrepreneurs, purchase intents
    NORMAL = 2      # General queries, product browsing  
    LOW = 3         # Exploratory, repeated queries

class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

class MessageSource(Enum):
    """Message source identification"""
    CHATWOOT = "chatwoot"
    EVOLUTION = "evolution"
    TEST = "test"
    SYSTEM = "system"
    FOLLOWUP = "followup"

# =====================================================
# DATA MODELS
# =====================================================

@dataclass
class MessageData:
    """Enhanced message data with routing and metadata"""
    user_id: str
    message: str
    source: MessageSource
    priority: MessagePriority = MessagePriority.NORMAL
    
    # Optional routing data
    conversation_id: Optional[str] = None
    phone: Optional[str] = None
    
    # Processing metadata
    queue_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_hash: str = field(default="")
    attempts: int = 0
    max_attempts: int = 3
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error handling
    last_error: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate message hash for deduplication"""
        if not self.message_hash:
            content = f"{self.user_id}:{self.message}:{self.source.value}"
            self.message_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['source'] = self.source.value
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageData':
        """Create from dictionary"""
        # Convert enums
        data['source'] = MessageSource(data['source'])
        data['priority'] = MessagePriority(data['priority'])
        
        # Convert datetime strings
        for field_name in ['created_at', 'scheduled_at', 'started_at', 'completed_at']:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)

@dataclass
class QueueStats:
    """Queue statistics for monitoring"""
    total_pending: int = 0
    total_processing: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    
    pending_by_priority: Dict[str, int] = field(default_factory=dict)
    avg_processing_time: float = 0.0
    oldest_pending: Optional[datetime] = None
    
    queue_depth: int = 0
    throughput_per_minute: float = 0.0
    error_rate: float = 0.0

# =====================================================
# ADVANCED MESSAGE QUEUE MANAGER
# =====================================================

class AdvancedMessageQueue:
    """
    Multi-layer message queue system:
    - PostgreSQL for persistence and durability
    - Redis for high-performance operations
    - In-memory for ultra-fast access patterns
    """
    
    def __init__(self):
        # Database connections
        self.pg_pool: Optional[ThreadedConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # In-memory cache for hot messages
        self.hot_cache: Dict[str, MessageData] = {}
        self.processing_messages: Dict[str, MessageData] = {}
        
        # Deduplication tracking
        self.processed_hashes: set = set()
        self.hash_cleanup_counter = 0
        
        # Performance metrics
        self.metrics = defaultdict(int)
        self.processing_times: List[float] = []
        
        # Configuration
        self.hot_cache_size = int(os.getenv('QUEUE_HOT_CACHE_SIZE', 100))
        self.dedup_window_minutes = int(os.getenv('DEDUP_WINDOW_MINUTES', 10))
        self.dead_letter_threshold = int(os.getenv('DEAD_LETTER_THRESHOLD', 3))
        
        logger.info("📬 AdvancedMessageQueue initialized")
    
    async def initialize(self):
        """Initialize all queue layers"""
        await self._init_postgresql()
        await self._init_redis()
        await self._restore_processing_messages()
        logger.info("✅ AdvancedMessageQueue fully initialized")
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.error("❌ DATABASE_URL not found for queue")
                return
            
            self.pg_pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=8,
                dsn=database_url
            )
            
            # Test connection
            conn = self.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                logger.info("✅ Queue PostgreSQL connection established")
            finally:
                self.pg_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"❌ Queue PostgreSQL initialization failed: {e}")
            self.pg_pool = None
    
    async def _init_redis(self):
        """Initialize Redis for queue operations"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            
            await self.redis_client.ping()
            logger.info("✅ Queue Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Queue Redis not available: {e}")
            self.redis_client = None
    
    async def _restore_processing_messages(self):
        """Restore any messages that were processing during restart"""
        if not self.pg_pool:
            return
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Find messages that were processing but server restarted
            cursor.execute("""
                UPDATE message_queue 
                SET status = 'pending', worker_id = NULL, started_at = NULL
                WHERE status = 'processing' 
                AND started_at < %s
                RETURNING id
            """, (datetime.now() - timedelta(minutes=5),))
            
            restored_count = cursor.rowcount
            conn.commit()
            
            if restored_count > 0:
                logger.info(f"🔄 Restored {restored_count} interrupted messages to pending")
                
        except Exception as e:
            logger.error(f"❌ Failed to restore processing messages: {e}")
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    # =====================================================
    # CORE QUEUE OPERATIONS
    # =====================================================
    
    async def add_message(self, message_data: MessageData) -> bool:
        """Add message to queue with deduplication"""
        
        # Check for recent duplicates
        if self._is_duplicate(message_data):
            logger.info(f"🔄 Duplicate message ignored: {message_data.user_id}")
            self.metrics['duplicates_ignored'] += 1
            return False
        
        # Auto-prioritize based on content and user
        await self._auto_prioritize_message(message_data)
        
        # Store in database for persistence
        if not await self._store_message_db(message_data):
            return False
        
        # Cache hot messages in Redis
        await self._cache_hot_message(message_data)
        
        # Update metrics
        self.metrics['messages_added'] += 1
        self.metrics[f'priority_{message_data.priority.name.lower()}'] += 1
        
        logger.info(f"📥 Message queued: {message_data.user_id} [P:{message_data.priority.name}]")
        return True
    
    async def get_next_message(self, worker_id: str, timeout: float = 5.0) -> Optional[MessageData]:
        """Get next message with priority ordering"""
        
        # Try Redis first for hot messages
        message = await self._get_from_redis_queue()
        if message:
            return await self._mark_processing(message, worker_id)
        
        # Fallback to database with priority ordering
        message = await self._get_from_db_queue()
        if message:
            return await self._mark_processing(message, worker_id)
        
        return None
    
    async def complete_message(self, queue_id: str, success: bool = True, 
                              error: Optional[str] = None, 
                              response_data: Optional[Dict] = None) -> bool:
        """Mark message as completed or failed"""
        
        if queue_id in self.processing_messages:
            message = self.processing_messages.pop(queue_id)
            
            # Calculate processing time
            if message.started_at:
                processing_time = (datetime.now() - message.started_at).total_seconds()
                self.processing_times.append(processing_time)
                
                # Keep only last 100 processing times for metrics
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]
            
            # Update message status
            if success:
                message.completed_at = datetime.now()
                status = MessageStatus.COMPLETED
                self.metrics['messages_completed'] += 1
            else:
                message.last_error = error
                message.attempts += 1
                
                if message.attempts >= message.max_attempts:
                    status = MessageStatus.DEAD_LETTER
                    self.metrics['messages_dead_letter'] += 1
                    logger.warning(f"💀 Message sent to dead letter: {message.user_id}")
                else:
                    status = MessageStatus.FAILED
                    # Reschedule with exponential backoff
                    message.scheduled_at = datetime.now() + timedelta(
                        seconds=min(300, 2 ** message.attempts)
                    )
                    self.metrics['messages_failed'] += 1
            
            return await self._update_message_status(message, status)
        
        return False
    
    # =====================================================
    # INTELLIGENT MESSAGE PROCESSING
    # =====================================================
    
    def _is_duplicate(self, message_data: MessageData) -> bool:
        """Check if message is a recent duplicate"""
        if message_data.message_hash in self.processed_hashes:
            return True
        
        # Add to processed hashes
        self.processed_hashes.add(message_data.message_hash)
        
        # Periodic cleanup of old hashes
        self.hash_cleanup_counter += 1
        if self.hash_cleanup_counter >= 100:
            # Keep only recent hashes (simple approach)
            if len(self.processed_hashes) > 1000:
                # Remove half the hashes (oldest ones first)
                hashes_to_keep = list(self.processed_hashes)[500:]
                self.processed_hashes = set(hashes_to_keep)
            self.hash_cleanup_counter = 0
        
        return False
    
    async def _auto_prioritize_message(self, message_data: MessageData):
        """Automatically prioritize message based on content and context"""
        
        message_lower = message_data.message.lower()
        
        # Urgent priority keywords
        urgent_keywords = ['error', 'problema', 'urgente', 'no funciona', 'ayuda']
        if any(keyword in message_lower for keyword in urgent_keywords):
            message_data.priority = MessagePriority.URGENT
            return
        
        # High priority for business intentions
        high_keywords = ['comprar', 'precio', 'stock', 'disponible', 'envio', 'pago']
        if any(keyword in message_lower for keyword in high_keywords):
            message_data.priority = MessagePriority.HIGH
            return
        
        # Check if user is known entrepreneur (would need context lookup)
        # For now, keep default NORMAL priority
        
        # Low priority for basic greetings
        low_keywords = ['hola', 'buenos dias', 'buenas tardes', 'como estas']
        if any(keyword in message_lower for keyword in low_keywords) and len(message_data.message.split()) <= 3:
            message_data.priority = MessagePriority.LOW
    
    # =====================================================
    # DATABASE OPERATIONS
    # =====================================================
    
    async def _store_message_db(self, message_data: MessageData) -> bool:
        """Store message in PostgreSQL"""
        if not self.pg_pool:
            logger.error("❌ No database connection for message storage")
            return False
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO message_queue (
                    queue_id, user_id, message_content, message_hash,
                    source, priority, status, conversation_id, phone,
                    metadata, created_at, scheduled_at, max_attempts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                message_data.queue_id,
                message_data.user_id,
                message_data.message,
                message_data.message_hash,
                message_data.source.value,
                message_data.priority.name.lower(),
                MessageStatus.PENDING.value,
                message_data.conversation_id,
                message_data.phone,
                json.dumps(message_data.metadata),
                message_data.created_at,
                message_data.scheduled_at,
                message_data.max_attempts
            ))
            
            conn.commit()
            return True
            
        except psycopg2.IntegrityError as e:
            # Handle duplicate message_hash
            if 'message_hash' in str(e):
                logger.info(f"🔄 Duplicate message hash detected: {message_data.message_hash}")
                return False
            raise
            
        except Exception as e:
            logger.error(f"❌ Failed to store message: {e}")
            if conn:
                conn.rollback()
            return False
            
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def _get_from_db_queue(self) -> Optional[MessageData]:
        """Get next message from database with priority ordering"""
        if not self.pg_pool:
            return None
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get highest priority message that's ready to process
            cursor.execute("""
                SELECT * FROM message_queue
                WHERE status = 'pending' 
                AND scheduled_at <= %s
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 0
                        WHEN 'high' THEN 1 
                        WHEN 'normal' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """, (datetime.now(),))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert to MessageData
            message_dict = dict(row)
            
            # Remove database-specific fields that don't belong in MessageData
            database_fields = ['id', 'worker_id', 'status']
            for field in database_fields:
                message_dict.pop(field, None)
            
            # Map database field names to MessageData field names
            field_mapping = {
                'message_content': 'message',
                'created_at': 'created_at',
                'scheduled_at': 'scheduled_at', 
                'started_at': 'started_at',
                'completed_at': 'completed_at'
            }
            
            # Apply field mapping
            for db_field, msg_field in field_mapping.items():
                if db_field in message_dict and db_field != msg_field:
                    message_dict[msg_field] = message_dict.pop(db_field)
            
            message_dict['priority'] = MessagePriority[message_dict['priority'].upper()]
            message_dict['source'] = MessageSource(message_dict['source'])
            
            # Parse metadata - check if it's already a dict or needs JSON parsing
            if message_dict.get('metadata'):
                if isinstance(message_dict['metadata'], str):
                    message_dict['metadata'] = json.loads(message_dict['metadata'])
                elif not isinstance(message_dict['metadata'], dict):
                    message_dict['metadata'] = {}
            else:
                message_dict['metadata'] = {}
            
            # Handle missing fields with defaults
            message_dict.setdefault('error_details', {})
            message_dict.setdefault('attempts', 0)
            message_dict.setdefault('max_attempts', 3)
            
            return MessageData.from_dict(message_dict)
            
        except Exception as e:
            logger.error(f"❌ Failed to get message from database: {e}")
            return None
            
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def _update_message_status(self, message_data: MessageData, status: MessageStatus) -> bool:
        """Update message status in database"""
        if not self.pg_pool:
            return False
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            update_fields = ["status = %s", "attempts = %s"]
            values = [status.value, message_data.attempts]
            
            if message_data.completed_at:
                update_fields.append("completed_at = %s")
                values.append(message_data.completed_at)
            
            if message_data.last_error:
                update_fields.append("last_error = %s")
                values.append(message_data.last_error)
            
            if message_data.scheduled_at:
                update_fields.append("scheduled_at = %s") 
                values.append(message_data.scheduled_at)
            
            values.append(message_data.queue_id)  # For WHERE clause
            
            cursor.execute(f"""
                UPDATE message_queue 
                SET {', '.join(update_fields)}
                WHERE queue_id = %s
            """, values)
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update message status: {e}")
            if conn:
                conn.rollback()
            return False
            
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def _mark_processing(self, message_data: MessageData, worker_id: str) -> MessageData:
        """Mark message as being processed"""
        message_data.started_at = datetime.now()
        
        # Update in database
        if self.pg_pool:
            try:
                conn = self.pg_pool.getconn()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE message_queue 
                    SET status = 'processing', worker_id = %s, started_at = %s
                    WHERE queue_id = %s
                """, (worker_id, message_data.started_at, message_data.queue_id))
                
                conn.commit()
                
            except Exception as e:
                logger.error(f"❌ Failed to mark processing: {e}")
            finally:
                if conn:
                    self.pg_pool.putconn(conn)
        
        # Add to processing messages
        self.processing_messages[message_data.queue_id] = message_data
        self.metrics['messages_processing'] += 1
        
        return message_data
    
    # =====================================================
    # REDIS OPERATIONS (Hot Cache)
    # =====================================================
    
    async def _cache_hot_message(self, message_data: MessageData):
        """Cache high-priority messages in Redis"""
        if not self.redis_client or message_data.priority.value > MessagePriority.HIGH.value:
            return
        
        try:
            key = f"hot_queue:{message_data.priority.name}:{message_data.queue_id}"
            await self.redis_client.setex(
                key, 
                300,  # 5 minute TTL
                json.dumps(message_data.to_dict(), default=str)
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache hot message: {e}")
    
    async def _get_from_redis_queue(self) -> Optional[MessageData]:
        """Get message from Redis hot cache"""
        if not self.redis_client:
            return None
        
        try:
            # Check urgent and high priority first
            for priority in [MessagePriority.URGENT, MessagePriority.HIGH]:
                pattern = f"hot_queue:{priority.name}:*"
                
                async for key in self.redis_client.scan_iter(match=pattern, count=10):
                    message_json = await self.redis_client.get(key)
                    if message_json:
                        await self.redis_client.delete(key)  # Remove from hot cache
                        message_dict = json.loads(message_json)
                        return MessageData.from_dict(message_dict)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get from Redis queue: {e}")
            return None
    
    # =====================================================
    # MONITORING AND STATISTICS
    # =====================================================
    
    async def get_queue_stats(self) -> QueueStats:
        """Get comprehensive queue statistics"""
        stats = QueueStats()
        
        if not self.pg_pool:
            return stats
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Overall counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM message_queue
                GROUP BY status
            """)
            
            for status, count in cursor.fetchall():
                setattr(stats, f'total_{status}', count)
            
            # Pending by priority
            cursor.execute("""
                SELECT priority, COUNT(*) as count
                FROM message_queue
                WHERE status = 'pending'
                GROUP BY priority
            """)
            
            stats.pending_by_priority = dict(cursor.fetchall())
            
            # Queue depth (pending + processing)
            cursor.execute("""
                SELECT COUNT(*) FROM message_queue
                WHERE status IN ('pending', 'processing')
            """)
            stats.queue_depth = cursor.fetchone()[0]
            
            # Average processing time
            cursor.execute("""
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                FROM message_queue
                WHERE status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
                AND created_at > %s
            """, (datetime.now() - timedelta(hours=1),))
            
            result = cursor.fetchone()[0]
            stats.avg_processing_time = float(result) if result else 0.0
            
            # Oldest pending message
            cursor.execute("""
                SELECT MIN(created_at) FROM message_queue
                WHERE status = 'pending'
            """)
            
            oldest = cursor.fetchone()[0]
            stats.oldest_pending = oldest
            
            # Error rate (last hour)
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status IN ('failed', 'dead_letter') THEN 1 END) * 1.0 /
                    NULLIF(COUNT(*), 0) as error_rate
                FROM message_queue
                WHERE created_at > %s
            """, (datetime.now() - timedelta(hours=1),))
            
            error_rate = cursor.fetchone()[0]
            stats.error_rate = float(error_rate) if error_rate else 0.0
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
        finally:
            if conn:
                self.pg_pool.putconn(conn)
        
        # Add processing time metrics
        if self.processing_times:
            stats.avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        
        return stats
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        stats = await self.get_queue_stats()
        
        return {
            'queue_stats': {
                'total_pending': stats.total_pending,
                'total_processing': stats.total_processing,
                'total_completed': stats.total_completed,
                'total_failed': stats.total_failed,
                'total_dead_letter': stats.total_dead_letter,
                'queue_depth': stats.queue_depth,
                'avg_processing_time': stats.avg_processing_time,
                'error_rate': stats.error_rate
            },
            'performance': {
                'messages_added': self.metrics['messages_added'],
                'messages_completed': self.metrics['messages_completed'],
                'messages_failed': self.metrics['messages_failed'],
                'duplicates_ignored': self.metrics['duplicates_ignored'],
                'hot_cache_size': len(self.hot_cache),
                'processing_messages': len(self.processing_messages)
            },
            'priority_breakdown': stats.pending_by_priority,
            'system': {
                'redis_available': self.redis_client is not None,
                'postgresql_available': self.pg_pool is not None,
                'oldest_pending': stats.oldest_pending.isoformat() if stats.oldest_pending else None
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Queue health check"""
        health = {
            'status': 'healthy',
            'components': {
                'postgresql': False,
                'redis': False
            },
            'queue_health': 'good'
        }
        
        # Test PostgreSQL
        if self.pg_pool:
            try:
                conn = self.pg_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM message_queue WHERE status = 'pending'")
                pending_count = cursor.fetchone()[0]
                health['components']['postgresql'] = True
                health['pending_messages'] = pending_count
                
                # Check for queue backup
                if pending_count > 100:
                    health['queue_health'] = 'backed_up'
                    health['status'] = 'degraded'
                
                self.pg_pool.putconn(conn)
            except Exception as e:
                health['components']['postgresql'] = False
                health['postgresql_error'] = str(e)
                health['status'] = 'unhealthy'
        
        # Test Redis
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health['components']['redis'] = True
            except Exception as e:
                health['components']['redis'] = False
                health['redis_error'] = str(e)
        
        return health
    
    # =====================================================
    # MAINTENANCE OPERATIONS
    # =====================================================
    
    async def cleanup_old_messages(self, days: int = 30) -> int:
        """Clean up old completed/failed messages"""
        if not self.pg_pool:
            return 0
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM message_queue
                WHERE status IN ('completed', 'dead_letter')
                AND created_at < %s
            """, (datetime.now() - timedelta(days=days),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"🧹 Cleaned up {deleted_count} old messages")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old messages: {e}")
            return 0
        finally:
            if conn:
                self.pg_pool.putconn(conn)

# =====================================================
# GLOBAL INSTANCE
# =====================================================

# Global queue instance
advanced_queue = AdvancedMessageQueue()

# Convenience functions
async def add_message(message_data: MessageData) -> bool:
    """Add message to queue"""
    return await advanced_queue.add_message(message_data)

async def get_next_message(worker_id: str) -> Optional[MessageData]:
    """Get next message for processing"""
    return await advanced_queue.get_next_message(worker_id)

async def complete_message(queue_id: str, success: bool = True, error: Optional[str] = None) -> bool:
    """Complete message processing"""
    return await advanced_queue.complete_message(queue_id, success, error)

# Initialize function
async def initialize_queue():
    """Initialize the advanced queue system"""
    await advanced_queue.initialize()

if __name__ == "__main__":
    # Test the queue system
    async def test_queue():
        await initialize_queue()
        
        # Test adding messages
        test_message = MessageData(
            user_id="test_user",
            message="Hello, this is a test message",
            source=MessageSource.TEST,
            priority=MessagePriority.NORMAL
        )
        
        success = await add_message(test_message)
        print(f"Add message test: {'✅ Success' if success else '❌ Failed'}")
        
        # Test getting message
        message = await get_next_message("test_worker")
        if message:
            print(f"Got message: {message.message}")
            await complete_message(message.queue_id, True)
        
        # Test metrics
        metrics = await advanced_queue.get_metrics()
        print(f"Queue metrics: {metrics}")
    
    asyncio.run(test_queue())