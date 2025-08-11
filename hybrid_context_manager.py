#!/usr/bin/env python3
"""
🧠 HYBRID CONTEXT MANAGER - MAXIMUM EFFICIENCY
PostgreSQL + Redis + In-Memory multi-layer context system
Designed for Railway deployment with auto-fallback
"""

import os
import json
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager
import uuid

# Database imports
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import redis.asyncio as redis

# Performance imports
import time
from functools import wraps
from collections import defaultdict, OrderedDict

logger = logging.getLogger(__name__)

# =====================================================
# DATA MODELS (Optimized for performance)
# =====================================================

@dataclass
class ProductReference:
    """Optimized product reference with caching hints"""
    name: str
    price: str
    id: Optional[str] = None
    permalink: Optional[str] = None
    category: Optional[str] = None
    shown_at: datetime = field(default_factory=datetime.now)
    cache_key: str = field(default="")
    
    def __post_init__(self):
        if not self.cache_key:
            self.cache_key = hashlib.md5(f"{self.name}_{self.price}".encode()).hexdigest()[:8]

@dataclass
class ConversationMemory:
    """Enhanced conversation memory with performance optimizations"""
    user_id: str
    conversation_started: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    
    # State tracking
    current_state: str = "browsing"
    user_intent: str = ""
    user_profile: Dict[str, Any] = field(default_factory=dict)
    
    # Product interactions (limited for performance)
    recent_products: List[ProductReference] = field(default_factory=list)
    interaction_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Business context
    preferences: Dict[str, Any] = field(default_factory=dict)
    is_entrepreneur: bool = False
    experience_level: str = ""
    product_interests: List[str] = field(default_factory=list)
    budget_range: Optional[str] = None
    
    # Performance tracking
    _cache_hits: int = field(default=0)
    _last_cache_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage, excluding internal fields"""
        data = asdict(self)
        # Remove internal performance fields
        data.pop('_cache_hits', None)
        data.pop('_last_cache_update', None)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """Create from dictionary, handling datetime conversion"""
        # Convert datetime strings back to datetime objects
        if isinstance(data.get('conversation_started'), str):
            data['conversation_started'] = datetime.fromisoformat(data['conversation_started'])
        if isinstance(data.get('last_interaction'), str):
            data['last_interaction'] = datetime.fromisoformat(data['last_interaction'])
        
        # Convert products back to ProductReference objects
        if 'recent_products' in data:
            products = []
            for prod_data in data['recent_products']:
                if isinstance(prod_data, dict):
                    if isinstance(prod_data.get('shown_at'), str):
                        prod_data['shown_at'] = datetime.fromisoformat(prod_data['shown_at'])
                    products.append(ProductReference(**prod_data))
                else:
                    products.append(prod_data)
            data['recent_products'] = products
        
        return cls(**data)

# =====================================================
# PERFORMANCE DECORATORS
# =====================================================

def performance_monitor(func):
    """Monitor function performance and log slow operations"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            if execution_time > 100:  # Log operations > 100ms
                logger.warning(f"🐌 Slow operation: {func.__name__} took {execution_time:.2f}ms")
            elif execution_time > 50:
                logger.info(f"⚠️ Medium operation: {func.__name__} took {execution_time:.2f}ms")
            
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Failed operation: {func.__name__} failed after {execution_time:.2f}ms - {e}")
            raise
    return wrapper

def cache_result(ttl_seconds: int = 300):
    """Cache function results in memory for specified TTL"""
    def decorator(func):
        cache = OrderedDict()
        cache_times = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Check cache validity
            if (cache_key in cache and 
                current_time - cache_times.get(cache_key, 0) < ttl_seconds):
                return cache[cache_key]
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            
            # Limit cache size to prevent memory bloat
            if len(cache) > 1000:
                # Remove oldest 20% of entries
                for _ in range(200):
                    if cache:
                        oldest_key = next(iter(cache))
                        cache.pop(oldest_key)
                        cache_times.pop(oldest_key, None)
            
            return result
        return wrapper
    return decorator

# =====================================================
# HYBRID CONTEXT MANAGER (Core System)
# =====================================================

class HybridContextManager:
    """
    Multi-layer context management system:
    Layer 1: In-Memory (fastest, <1ms)
    Layer 2: Redis (fast, 1-5ms) 
    Layer 3: PostgreSQL (persistent, 10-50ms)
    """
    
    def __init__(self):
        # Connection pools
        self.pg_pool: Optional[ThreadedConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # In-memory caches
        self.memory_cache: Dict[str, ConversationMemory] = OrderedDict()
        self.cache_times: Dict[str, datetime] = {}
        
        # Performance metrics
        self.metrics = defaultdict(int)
        self.last_cleanup = datetime.now()
        
        # Configuration
        self.max_memory_cache = int(os.getenv('MAX_MEMORY_CACHE', 500))
        self.redis_ttl = int(os.getenv('REDIS_TTL', 3600))  # 1 hour
        self.pg_ttl_days = int(os.getenv('PG_TTL_DAYS', 30))  # 30 days
        
        logger.info("🧠 HybridContextManager initialized")
    
    async def initialize(self):
        """Initialize all connection layers"""
        await self._init_postgresql()
        await self._init_redis()
        logger.info("✅ HybridContextManager fully initialized")
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection pool"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.error("❌ DATABASE_URL not found")
                return
            
            # Create connection pool (thread-safe for FastAPI)
            self.pg_pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=database_url
            )
            
            # Test connection and create tables if needed
            conn = self.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                logger.info("✅ PostgreSQL connection established")
                
                # Apply schema if needed
                await self._ensure_schema(conn)
                
            finally:
                self.pg_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization failed: {e}")
            self.pg_pool = None
    
    async def _init_redis(self):
        """Initialize Redis connection with fallback"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using fallback: {e}")
            self.redis_client = None
    
    async def _ensure_schema(self, conn):
        """Ensure database schema exists"""
        try:
            cursor = conn.cursor()
            
            # Check if schema is applied
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversation_contexts'
                )
            """)
            
            schema_exists = cursor.fetchone()[0]
            
            if not schema_exists:
                logger.info("📋 Applying database schema...")
                # Read and execute schema file
                schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()
                    cursor.execute(schema_sql)
                    conn.commit()
                    logger.info("✅ Database schema applied")
                else:
                    logger.error("❌ Schema file not found")
            
        except Exception as e:
            logger.error(f"❌ Schema application failed: {e}")
    
    # =====================================================
    # CORE CONTEXT OPERATIONS (Multi-layer)
    # =====================================================
    
    @performance_monitor
    async def get_context(self, user_id: str) -> ConversationMemory:
        """Get context with multi-layer fallback"""
        
        # Layer 1: Memory cache (fastest)
        if user_id in self.memory_cache:
            context = self.memory_cache[user_id]
            # Check if cache is still fresh (5 minutes)
            if (datetime.now() - self.cache_times.get(user_id, datetime.min)).seconds < 300:
                self.metrics['memory_hits'] += 1
                logger.debug(f"💾 Memory cache hit: {user_id}")
                return context
        
        # Layer 2: Redis cache (fast)
        if self.redis_client:
            try:
                redis_key = f"context:{user_id}"
                cached_data = await self.redis_client.get(redis_key)
                if cached_data:
                    context_data = json.loads(cached_data)
                    context = ConversationMemory.from_dict(context_data)
                    
                    # Update memory cache
                    self._update_memory_cache(user_id, context)
                    
                    self.metrics['redis_hits'] += 1
                    logger.debug(f"🔄 Redis cache hit: {user_id}")
                    return context
            except Exception as e:
                logger.warning(f"⚠️ Redis get failed: {e}")
        
        # Layer 3: PostgreSQL (persistent)
        context = await self._get_context_from_db(user_id)
        if context:
            # Populate upper layers
            await self._cache_context_redis(user_id, context)
            self._update_memory_cache(user_id, context)
            
            self.metrics['db_hits'] += 1
            logger.debug(f"🗄️ Database hit: {user_id}")
            return context
        
        # Create new context if not found
        context = ConversationMemory(user_id=user_id)
        self._update_memory_cache(user_id, context)
        
        self.metrics['new_contexts'] += 1
        logger.info(f"🆕 New context created: {user_id}")
        
        return context
    
    @performance_monitor
    async def save_context(self, user_id: str, context: ConversationMemory) -> bool:
        """Save context to all layers"""
        context.last_interaction = datetime.now()
        success = True
        
        # Layer 1: Memory (immediate)
        self._update_memory_cache(user_id, context)
        
        # Layer 2: Redis (fast persistence)
        if not await self._cache_context_redis(user_id, context):
            success = False
        
        # Layer 3: PostgreSQL (durable persistence)
        if not await self._save_context_to_db(user_id, context):
            success = False
        
        self.metrics['saves'] += 1
        return success
    
    @performance_monitor 
    async def update_context_field(self, user_id: str, field: str, value: Any) -> bool:
        """Update specific field efficiently"""
        context = await self.get_context(user_id)
        
        if hasattr(context, field):
            setattr(context, field, value)
            context.last_interaction = datetime.now()
            return await self.save_context(user_id, context)
        
        logger.warning(f"⚠️ Unknown context field: {field}")
        return False
    
    @performance_monitor
    async def add_product_reference(self, user_id: str, product: ProductReference) -> bool:
        """Add product reference with intelligent deduplication"""
        context = await self.get_context(user_id)
        
        # Check for duplicates by name and price
        existing = [p for p in context.recent_products 
                   if p.name == product.name and p.price == product.price]
        
        if not existing:
            context.recent_products.append(product)
            
            # Keep only last 10 products for performance
            if len(context.recent_products) > 10:
                context.recent_products = context.recent_products[-10:]
            
            return await self.save_context(user_id, context)
        
        return True  # Already exists, no need to save
    
    @performance_monitor
    async def add_interaction(self, user_id: str, role: str, message: str, 
                            metadata: Optional[Dict] = None) -> bool:
        """Add interaction with automatic cleanup"""
        context = await self.get_context(user_id)
        
        interaction = {
            "role": role,
            "message": message[:500],  # Truncate long messages
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        context.interaction_history.append(interaction)
        
        # Keep only last 20 interactions for performance
        if len(context.interaction_history) > 20:
            context.interaction_history = context.interaction_history[-20:]
        
        return await self.save_context(user_id, context)
    
    # =====================================================
    # REDIS LAYER OPERATIONS
    # =====================================================
    
    async def _cache_context_redis(self, user_id: str, context: ConversationMemory) -> bool:
        """Cache context in Redis with TTL"""
        if not self.redis_client:
            return True  # Skip if Redis not available
        
        try:
            redis_key = f"context:{user_id}"
            context_json = json.dumps(context.to_dict(), default=str)
            
            await self.redis_client.setex(redis_key, self.redis_ttl, context_json)
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis save failed: {e}")
            return False
    
    async def invalidate_redis_cache(self, user_id: str) -> bool:
        """Invalidate Redis cache for user"""
        if not self.redis_client:
            return True
        
        try:
            redis_key = f"context:{user_id}"
            await self.redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis invalidation failed: {e}")
            return False
    
    # =====================================================
    # POSTGRESQL LAYER OPERATIONS  
    # =====================================================
    
    async def _get_context_from_db(self, user_id: str) -> Optional[ConversationMemory]:
        """Get context from PostgreSQL"""
        if not self.pg_pool:
            return None
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT context_data, user_profile, preferences, current_state, 
                       user_intent, is_entrepreneur, experience_level,
                       recent_products, product_interests, budget_range,
                       conversation_started, last_interaction
                FROM conversation_contexts 
                WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Reconstruct context from database fields
            context_data = {
                'user_id': user_id,
                'current_state': row['current_state'],
                'user_intent': row['user_intent'], 
                'user_profile': row['user_profile'] or {},
                'preferences': row['preferences'] or {},
                'is_entrepreneur': row['is_entrepreneur'],
                'experience_level': row['experience_level'],
                'recent_products': row['recent_products'] or [],
                'product_interests': row['product_interests'] or [],
                'budget_range': row['budget_range'],
                'conversation_started': row['conversation_started'],
                'last_interaction': row['last_interaction'],
                'interaction_history': row.get('context_data', {}).get('interaction_history', [])
            }
            
            return ConversationMemory.from_dict(context_data)
            
        except Exception as e:
            logger.error(f"❌ Database get failed: {e}")
            return None
            
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def _save_context_to_db(self, user_id: str, context: ConversationMemory) -> bool:
        """Save context to PostgreSQL"""
        if not self.pg_pool:
            return False
        
        conn = None
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Prepare data for storage
            context_data = {'interaction_history': context.interaction_history}
            recent_products_json = json.dumps([p.to_dict() if hasattr(p, 'to_dict') else asdict(p) 
                                              for p in context.recent_products], default=str)
            
            cursor.execute("""
                INSERT INTO conversation_contexts (
                    user_id, context_data, user_profile, preferences,
                    current_state, user_intent, is_entrepreneur, experience_level,
                    recent_products, product_interests, budget_range,
                    conversation_started, last_interaction
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (user_id) DO UPDATE SET
                    context_data = EXCLUDED.context_data,
                    user_profile = EXCLUDED.user_profile,
                    preferences = EXCLUDED.preferences,
                    current_state = EXCLUDED.current_state,
                    user_intent = EXCLUDED.user_intent,
                    is_entrepreneur = EXCLUDED.is_entrepreneur,
                    experience_level = EXCLUDED.experience_level,
                    recent_products = EXCLUDED.recent_products,
                    product_interests = EXCLUDED.product_interests,
                    budget_range = EXCLUDED.budget_range,
                    last_interaction = EXCLUDED.last_interaction,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                json.dumps(context_data),
                json.dumps(context.user_profile),
                json.dumps(context.preferences),
                context.current_state,
                context.user_intent,
                context.is_entrepreneur,
                context.experience_level,
                recent_products_json,
                context.product_interests,
                context.budget_range,
                context.conversation_started,
                context.last_interaction
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            if conn:
                conn.rollback()
            return False
            
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    # =====================================================
    # MEMORY CACHE OPERATIONS
    # =====================================================
    
    def _update_memory_cache(self, user_id: str, context: ConversationMemory):
        """Update in-memory cache with LRU eviction"""
        self.memory_cache[user_id] = context
        self.cache_times[user_id] = datetime.now()
        
        # LRU eviction if cache is full
        if len(self.memory_cache) > self.max_memory_cache:
            # Remove oldest 20% of entries
            items_to_remove = self.max_memory_cache // 5
            for _ in range(items_to_remove):
                if self.memory_cache:
                    oldest_key = next(iter(self.memory_cache))
                    self.memory_cache.pop(oldest_key)
                    self.cache_times.pop(oldest_key, None)
    
    # =====================================================
    # MAINTENANCE AND CLEANUP
    # =====================================================
    
    async def cleanup_old_contexts(self) -> Dict[str, int]:
        """Clean up old contexts from all layers"""
        results = {'memory': 0, 'redis': 0, 'database': 0}
        
        # Memory cleanup (older than 1 hour)
        cutoff_memory = datetime.now() - timedelta(hours=1)
        old_memory_keys = [
            user_id for user_id, cache_time in self.cache_times.items()
            if cache_time < cutoff_memory
        ]
        for key in old_memory_keys:
            self.memory_cache.pop(key, None)
            self.cache_times.pop(key, None)
        results['memory'] = len(old_memory_keys)
        
        # Redis cleanup (scan and delete old keys)
        if self.redis_client:
            try:
                async for key in self.redis_client.scan_iter(match="context:*"):
                    ttl = await self.redis_client.ttl(key)
                    if ttl <= 0:  # Expired keys
                        await self.redis_client.delete(key)
                        results['redis'] += 1
            except Exception as e:
                logger.warning(f"⚠️ Redis cleanup failed: {e}")
        
        # Database cleanup (older than configured days)
        if self.pg_pool:
            try:
                conn = self.pg_pool.getconn()
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM conversation_contexts 
                    WHERE last_interaction < %s
                """, (datetime.now() - timedelta(days=self.pg_ttl_days),))
                
                results['database'] = cursor.rowcount
                conn.commit()
                
            except Exception as e:
                logger.error(f"❌ Database cleanup failed: {e}")
            finally:
                if conn:
                    self.pg_pool.putconn(conn)
        
        logger.info(f"🧹 Cleanup completed: {results}")
        return results
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_hits = sum([
            self.metrics['memory_hits'],
            self.metrics['redis_hits'], 
            self.metrics['db_hits']
        ])
        
        return {
            'cache_performance': {
                'memory_hits': self.metrics['memory_hits'],
                'redis_hits': self.metrics['redis_hits'],
                'database_hits': self.metrics['db_hits'],
                'total_hits': total_hits,
                'memory_hit_rate': self.metrics['memory_hits'] / max(total_hits, 1),
                'cache_hit_rate': (self.metrics['memory_hits'] + self.metrics['redis_hits']) / max(total_hits, 1)
            },
            'operations': {
                'saves': self.metrics['saves'],
                'new_contexts': self.metrics['new_contexts']
            },
            'system': {
                'memory_cache_size': len(self.memory_cache),
                'max_memory_cache': self.max_memory_cache,
                'redis_available': self.redis_client is not None,
                'postgres_available': self.pg_pool is not None
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            'status': 'healthy',
            'layers': {
                'memory': True,
                'redis': False,
                'postgresql': False
            },
            'performance': await self.get_metrics()
        }
        
        # Test Redis
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health['layers']['redis'] = True
            except Exception as e:
                logger.warning(f"⚠️ Redis health check failed: {e}")
        
        # Test PostgreSQL
        if self.pg_pool:
            try:
                conn = self.pg_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                health['layers']['postgresql'] = True
                self.pg_pool.putconn(conn)
            except Exception as e:
                logger.error(f"❌ PostgreSQL health check failed: {e}")
        
        # Overall status
        if not health['layers']['postgresql']:
            health['status'] = 'degraded'
        elif not health['layers']['redis']:
            health['status'] = 'partial'
            
        return health

# =====================================================
# GLOBAL INSTANCE (Singleton pattern)
# =====================================================

# Global instance for use throughout the application
hybrid_context_manager = HybridContextManager()

# Convenience functions for backward compatibility
async def get_context(user_id: str) -> ConversationMemory:
    """Get conversation context for user"""
    return await hybrid_context_manager.get_context(user_id)

async def save_context(user_id: str, context: ConversationMemory) -> bool:
    """Save conversation context for user"""
    return await hybrid_context_manager.save_context(user_id, context)

async def add_product_reference(user_id: str, product: ProductReference) -> bool:
    """Add product reference to user context"""
    return await hybrid_context_manager.add_product_reference(user_id, product)

async def add_interaction(user_id: str, role: str, message: str, metadata: Optional[Dict] = None) -> bool:
    """Add interaction to user context"""
    return await hybrid_context_manager.add_interaction(user_id, role, message, metadata)

# Initialize on import (for Railway)
async def initialize_hybrid_context():
    """Initialize the hybrid context system"""
    await hybrid_context_manager.initialize()

if __name__ == "__main__":
    # Test the system
    async def test_system():
        await initialize_hybrid_context()
        
        # Test context operations
        context = await get_context("test_user")
        context.user_intent = "testing_system"
        context.is_entrepreneur = True
        
        success = await save_context("test_user", context)
        print(f"Save test: {'✅ Success' if success else '❌ Failed'}")
        
        # Test metrics
        metrics = await hybrid_context_manager.get_metrics()
        print(f"Metrics: {metrics}")
        
        # Test health
        health = await hybrid_context_manager.health_check()
        print(f"Health: {health}")
    
    asyncio.run(test_system())