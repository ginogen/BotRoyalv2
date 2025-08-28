#!/usr/bin/env python3
"""
⚡ DYNAMIC WORKER POOL - MAXIMUM EFFICIENCY
Auto-scaling worker pool optimized for Railway deployment
Adapts to load, memory constraints, and performance requirements
"""

import os
import asyncio
import logging
import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from collections import defaultdict, deque
import uuid

# Import our components
from advanced_message_queue import MessageData, advanced_queue
from hybrid_context_manager import hybrid_context_manager

logger = logging.getLogger(__name__)

# =====================================================
# ENUMS AND CONSTANTS
# =====================================================

class WorkerStatus(Enum):
    """Worker status tracking"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"

class PoolScalingReason(Enum):
    """Reasons for pool scaling decisions"""
    QUEUE_DEPTH = "queue_depth"
    RESPONSE_TIME = "response_time"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_USAGE = "cpu_usage"
    MANUAL = "manual"

# =====================================================
# DATA MODELS
# =====================================================

@dataclass
class WorkerMetrics:
    """Individual worker performance metrics"""
    worker_id: str
    status: WorkerStatus = WorkerStatus.IDLE
    
    # Performance tracking
    messages_processed: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    
    # Current task
    current_message_id: Optional[str] = None
    task_started_at: Optional[datetime] = None
    
    # Error tracking
    errors_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    
    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

@dataclass
class PoolMetrics:
    """Overall pool performance metrics"""
    # Current state
    active_workers: int = 0
    idle_workers: int = 0
    busy_workers: int = 0
    error_workers: int = 0
    
    # Performance
    total_messages_processed: int = 0
    average_response_time: float = 0.0
    throughput_per_minute: float = 0.0
    
    # Resource usage
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    
    # Auto-scaling
    last_scale_action: Optional[str] = None
    last_scale_time: Optional[datetime] = None
    scale_reason: Optional[PoolScalingReason] = None

# =====================================================
# CIRCUIT BREAKER PATTERN
# =====================================================

class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        if not self.last_failure_time:
            return True
        
        return (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"🔴 Circuit breaker opened after {self.failure_count} failures")

# =====================================================
# INDIVIDUAL WORKER
# =====================================================

class Worker:
    """Individual worker with performance tracking and error handling"""
    
    def __init__(self, worker_id: str, message_processor: Callable):
        self.worker_id = worker_id
        self.message_processor = message_processor
        self.metrics = WorkerMetrics(worker_id=worker_id)
        self.circuit_breaker = CircuitBreaker()
        
        # Control flags
        self.is_running = False
        self.should_stop = False
        
        # Performance tracking
        self.response_times = deque(maxlen=50)  # Last 50 response times
        
        logger.info(f"👷 Worker {worker_id} initialized")
    
    async def start(self):
        """Start the worker loop"""
        self.is_running = True
        self.should_stop = False
        
        logger.info(f"🚀 Worker {self.worker_id} starting")
        
        while not self.should_stop:
            try:
                await self._work_cycle()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"❌ Worker {self.worker_id} cycle error: {e}")
                self.metrics.errors_count += 1
                self.metrics.last_error = str(e)
                self.metrics.last_error_at = datetime.now()
                self.metrics.status = WorkerStatus.ERROR
                
                # Exponential backoff on errors
                await asyncio.sleep(min(30, 2 ** min(self.metrics.errors_count, 5)))
        
        self.is_running = False
        logger.info(f"🛑 Worker {self.worker_id} stopped")
    
    async def _work_cycle(self):
        """Single work cycle - get and process one message"""
        # Get next message from queue
        message = await advanced_queue.get_next_message(self.worker_id)
        
        if not message:
            self.metrics.status = WorkerStatus.IDLE
            return
        
        # Process the message
        self.metrics.status = WorkerStatus.BUSY
        self.metrics.current_message_id = message.queue_id
        self.metrics.task_started_at = datetime.now()
        
        start_time = time.time()
        success = False
        error = None
        
        try:
            # Use circuit breaker for protection
            result = await self.circuit_breaker.call(
                self.message_processor,
                message.user_id,
                message.message,
                message  # Pass the full message data
            )
            success = True
            
        except Exception as e:
            error = str(e)
            logger.error(f"❌ Worker {self.worker_id} processing error: {e}")
        
        finally:
            # Calculate processing time
            processing_time = time.time() - start_time
            self.response_times.append(processing_time)
            
            # Update metrics
            self.metrics.messages_processed += 1
            self.metrics.total_processing_time += processing_time
            self.metrics.average_processing_time = (
                self.metrics.total_processing_time / self.metrics.messages_processed
            )
            self.metrics.last_activity = datetime.now()
            
            # Complete message in queue
            await advanced_queue.complete_message(
                message.queue_id, 
                success, 
                error
            )
            
            # Reset status
            self.metrics.status = WorkerStatus.IDLE
            self.metrics.current_message_id = None
            self.metrics.task_started_at = None
    
    async def stop(self):
        """Gracefully stop the worker"""
        logger.info(f"🛑 Stopping worker {self.worker_id}")
        self.should_stop = True
        self.metrics.status = WorkerStatus.SHUTTING_DOWN
        
        # Wait for current task to complete (with timeout)
        timeout = 15  # 15 seconds timeout
        while self.is_running and timeout > 0:
            await asyncio.sleep(1)
            timeout -= 1
        
        if self.is_running:
            logger.warning(f"⚠️ Worker {self.worker_id} force stopped after timeout")
    
    def get_current_response_time(self) -> float:
        """Get current average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

# =====================================================
# DYNAMIC WORKER POOL MANAGER
# =====================================================

class DynamicWorkerPool:
    """
    Self-managing worker pool that adapts to:
    - Queue depth and message load
    - System resource availability (Railway constraints)
    - Response time requirements
    - Error rates and circuit breaking
    """
    
    def __init__(self, message_processor: Callable):
        self.message_processor = message_processor
        
        # Worker management
        self.workers: Dict[str, Worker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration (Railway-optimized)
        self.min_workers = int(os.getenv('MIN_WORKERS', 3))
        self.max_workers = int(os.getenv('MAX_WORKERS', 8))
        self.target_response_time = float(os.getenv('TARGET_RESPONSE_TIME', 5.0))  # seconds
        self.scale_cooldown = int(os.getenv('SCALE_COOLDOWN', 20))  # seconds
        
        # Auto-scaling thresholds
        self.scale_up_queue_threshold = int(os.getenv('SCALE_UP_QUEUE_THRESHOLD', 10))
        self.scale_down_idle_threshold = int(os.getenv('SCALE_DOWN_IDLE_THRESHOLD', 5))  # minutes
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', 1024))  # Railway default
        
        # Performance tracking
        self.metrics = PoolMetrics()
        self.scaling_history = deque(maxlen=100)
        self.last_scale_time = datetime.now() - timedelta(minutes=5)
        
        # Control
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info(f"⚡ DynamicWorkerPool initialized (min: {self.min_workers}, max: {self.max_workers})")
    
    async def start(self):
        """Start the worker pool"""
        if self.is_running:
            return
        
        logger.info("🚀 Starting DynamicWorkerPool")
        
        self.is_running = True
        
        # Start with minimum workers
        await self._scale_to(self.min_workers, PoolScalingReason.MANUAL)
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("✅ DynamicWorkerPool started")
    
    async def stop(self):
        """Gracefully stop all workers"""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping DynamicWorkerPool")
        
        self.is_running = False
        
        # Stop monitoring
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop all workers gracefully
        await self._scale_to(0, PoolScalingReason.MANUAL)
        
        logger.info("✅ DynamicWorkerPool stopped")
    
    # =====================================================
    # WORKER LIFECYCLE MANAGEMENT
    # =====================================================
    
    async def _scale_to(self, target_count: int, reason: PoolScalingReason):
        """Scale pool to target worker count"""
        current_count = len(self.workers)
        
        if target_count == current_count:
            return
        
        # Enforce limits
        target_count = max(0, min(target_count, self.max_workers))
        
        if target_count > current_count:
            await self._scale_up(target_count - current_count, reason)
        elif target_count < current_count:
            await self._scale_down(current_count - target_count, reason)
    
    async def _scale_up(self, count: int, reason: PoolScalingReason):
        """Add workers to the pool"""
        logger.info(f"📈 Scaling up by {count} workers (reason: {reason.value})")
        
        for _ in range(count):
            worker_id = f"worker_{uuid.uuid4().hex[:8]}"
            worker = Worker(worker_id, self.message_processor)
            
            # Start worker task
            task = asyncio.create_task(worker.start())
            
            self.workers[worker_id] = worker
            self.worker_tasks[worker_id] = task
        
        # Update metrics
        self.metrics.last_scale_action = "scale_up"
        self.metrics.last_scale_time = datetime.now()
        self.metrics.scale_reason = reason
        self.last_scale_time = datetime.now()
        
        # Record scaling event
        self.scaling_history.append({
            'action': 'scale_up',
            'count': count,
            'reason': reason.value,
            'timestamp': datetime.now(),
            'total_workers': len(self.workers)
        })
    
    async def _scale_down(self, count: int, reason: PoolScalingReason):
        """Remove workers from the pool"""
        logger.info(f"📉 Scaling down by {count} workers (reason: {reason.value})")
        
        # Select workers to remove (prefer idle workers with most errors)
        workers_to_remove = self._select_workers_for_removal(count)
        
        for worker_id in workers_to_remove:
            if worker_id in self.workers:
                worker = self.workers[worker_id]
                task = self.worker_tasks[worker_id]
                
                # Stop worker gracefully
                await worker.stop()
                
                # Cancel task if still running
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Remove from tracking
                del self.workers[worker_id]
                del self.worker_tasks[worker_id]
        
        # Update metrics
        self.metrics.last_scale_action = "scale_down"
        self.metrics.last_scale_time = datetime.now()
        self.metrics.scale_reason = reason
        self.last_scale_time = datetime.now()
        
        # Record scaling event
        self.scaling_history.append({
            'action': 'scale_down',
            'count': count,
            'reason': reason.value,
            'timestamp': datetime.now(),
            'total_workers': len(self.workers)
        })
    
    def _select_workers_for_removal(self, count: int) -> List[str]:
        """Select which workers to remove (prefer idle workers with issues)"""
        worker_candidates = []
        
        for worker_id, worker in self.workers.items():
            priority = 0
            
            # Prefer idle workers
            if worker.metrics.status == WorkerStatus.IDLE:
                priority += 100
            
            # Prefer workers with more errors
            priority += worker.metrics.errors_count * 10
            
            # Prefer workers with longer idle time
            idle_time = (datetime.now() - worker.metrics.last_activity).total_seconds()
            priority += min(idle_time / 60, 50)  # Up to 50 points for idle time
            
            worker_candidates.append((worker_id, priority))
        
        # Sort by priority (highest first)
        worker_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [worker_id for worker_id, _ in worker_candidates[:count]]
    
    # =====================================================
    # AUTO-SCALING LOGIC
    # =====================================================
    
    async def _monitoring_loop(self):
        """Continuous monitoring and auto-scaling"""
        logger.info("📊 Starting pool monitoring loop")
        
        while self.is_running:
            try:
                await self._update_metrics()
                await self._evaluate_scaling()
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Longer delay on error
    
    async def _update_metrics(self):
        """Update pool performance metrics"""
        current_time = datetime.now()
        
        # Worker status counts
        self.metrics.active_workers = len(self.workers)
        self.metrics.idle_workers = sum(1 for w in self.workers.values() 
                                      if w.metrics.status == WorkerStatus.IDLE)
        self.metrics.busy_workers = sum(1 for w in self.workers.values() 
                                      if w.metrics.status == WorkerStatus.BUSY)
        self.metrics.error_workers = sum(1 for w in self.workers.values() 
                                       if w.metrics.status == WorkerStatus.ERROR)
        
        # Performance metrics
        total_processed = sum(w.metrics.messages_processed for w in self.workers.values())
        self.metrics.total_messages_processed = total_processed
        
        if self.workers:
            response_times = []
            for worker in self.workers.values():
                if worker.response_times:
                    response_times.extend(worker.response_times)
            
            if response_times:
                self.metrics.average_response_time = sum(response_times) / len(response_times)
        
        # System resource usage
        try:
            process = psutil.Process()
            self.metrics.cpu_usage_percent = process.cpu_percent()
            
            memory_info = process.memory_info()
            self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            self.metrics.memory_usage_percent = process.memory_percent()
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get system metrics: {e}")
    
    async def _evaluate_scaling(self):
        """Evaluate if scaling is needed"""
        
        # Check cooldown period
        if (datetime.now() - self.last_scale_time).total_seconds() < self.scale_cooldown:
            return
        
        current_workers = len(self.workers)
        
        # Get queue stats
        try:
            queue_stats = await advanced_queue.get_queue_stats()
            queue_depth = queue_stats.queue_depth
        except:
            queue_depth = 0
        
        # Scale up conditions
        scale_up_reasons = []
        
        # 1. Queue depth too high
        if queue_depth > self.scale_up_queue_threshold:
            scale_up_reasons.append(PoolScalingReason.QUEUE_DEPTH)
        
        # 2. Response time too high
        if (self.metrics.average_response_time > self.target_response_time and 
            self.metrics.busy_workers == current_workers):
            scale_up_reasons.append(PoolScalingReason.RESPONSE_TIME)
        
        # Scale down conditions
        scale_down_reasons = []
        
        # 1. Too many idle workers
        if (self.metrics.idle_workers > current_workers * 0.7 and 
            current_workers > self.min_workers and
            queue_depth == 0):
            scale_down_reasons.append(PoolScalingReason.QUEUE_DEPTH)
        
        # 2. Memory pressure
        if self.metrics.memory_usage_mb > self.max_memory_mb * 0.9:
            scale_down_reasons.append(PoolScalingReason.MEMORY_PRESSURE)
        
        # Execute scaling decisions
        if scale_up_reasons and current_workers < self.max_workers:
            # Calculate scale up amount
            scale_amount = min(2, self.max_workers - current_workers)
            
            # More aggressive scaling for queue depth
            if PoolScalingReason.QUEUE_DEPTH in scale_up_reasons:
                scale_amount = min(queue_depth // 5 + 1, self.max_workers - current_workers)
            
            await self._scale_up(scale_amount, scale_up_reasons[0])
            
        elif scale_down_reasons and current_workers > self.min_workers:
            # Conservative scale down
            scale_amount = min(1, current_workers - self.min_workers)
            await self._scale_down(scale_amount, scale_down_reasons[0])
    
    # =====================================================
    # MONITORING AND HEALTH
    # =====================================================
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pool metrics"""
        await self._update_metrics()
        
        return {
            'pool_status': {
                'active_workers': self.metrics.active_workers,
                'idle_workers': self.metrics.idle_workers,
                'busy_workers': self.metrics.busy_workers,
                'error_workers': self.metrics.error_workers,
                'is_running': self.is_running
            },
            'performance': {
                'total_messages_processed': self.metrics.total_messages_processed,
                'average_response_time': self.metrics.average_response_time,
                'throughput_per_minute': self.metrics.throughput_per_minute
            },
            'resources': {
                'cpu_usage_percent': self.metrics.cpu_usage_percent,
                'memory_usage_mb': self.metrics.memory_usage_mb,
                'memory_usage_percent': self.metrics.memory_usage_percent
            },
            'scaling': {
                'last_scale_action': self.metrics.last_scale_action,
                'last_scale_time': self.metrics.last_scale_time.isoformat() if self.metrics.last_scale_time else None,
                'scale_reason': self.metrics.scale_reason.value if self.metrics.scale_reason else None,
                'scaling_history': list(self.scaling_history)[-10:]  # Last 10 scaling events
            },
            'workers': {
                worker_id: {
                    'status': worker.metrics.status.value,
                    'messages_processed': worker.metrics.messages_processed,
                    'average_response_time': worker.metrics.average_processing_time,
                    'errors_count': worker.metrics.errors_count,
                    'current_response_time': worker.get_current_response_time()
                }
                for worker_id, worker in self.workers.items()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Pool health check"""
        health = {
            'status': 'healthy',
            'pool_running': self.is_running,
            'workers_healthy': 0,
            'workers_error': 0,
            'issues': []
        }
        
        # Check worker health
        for worker in self.workers.values():
            if worker.metrics.status == WorkerStatus.ERROR:
                health['workers_error'] += 1
                health['issues'].append(f"Worker {worker.worker_id} in error state")
            else:
                health['workers_healthy'] += 1
        
        # Check for critical issues
        if not self.is_running:
            health['status'] = 'unhealthy'
            health['issues'].append("Pool is not running")
        
        if health['workers_error'] >= len(self.workers) * 0.5:
            health['status'] = 'degraded'
            health['issues'].append("More than 50% of workers in error state")
        
        if self.metrics.memory_usage_percent > 90:
            health['status'] = 'degraded' 
            health['issues'].append("High memory usage")
        
        return health

# =====================================================
# GLOBAL POOL INSTANCE
# =====================================================

# This will be initialized with the actual message processor
dynamic_pool: Optional[DynamicWorkerPool] = None

async def initialize_worker_pool(message_processor: Callable):
    """Initialize the dynamic worker pool"""
    global dynamic_pool
    dynamic_pool = DynamicWorkerPool(message_processor)
    await dynamic_pool.start()
    logger.info("✅ DynamicWorkerPool initialized and started")

async def shutdown_worker_pool():
    """Shutdown the worker pool"""
    global dynamic_pool
    if dynamic_pool:
        await dynamic_pool.stop()
        logger.info("✅ DynamicWorkerPool shutdown completed")

# Convenience functions
async def get_pool_metrics() -> Optional[Dict[str, Any]]:
    """Get pool metrics"""
    if dynamic_pool:
        return await dynamic_pool.get_metrics()
    return None

async def get_pool_health() -> Optional[Dict[str, Any]]:
    """Get pool health"""
    if dynamic_pool:
        return await dynamic_pool.health_check()
    return None

if __name__ == "__main__":
    # Test the worker pool
    async def dummy_processor(user_id: str, message: str) -> str:
        """Dummy message processor for testing"""
        await asyncio.sleep(1)  # Simulate processing time
        return f"Processed: {message}"
    
    async def test_pool():
        await initialize_worker_pool(dummy_processor)
        
        # Let it run for a bit
        await asyncio.sleep(30)
        
        # Get metrics
        metrics = await get_pool_metrics()
        print(f"Pool metrics: {metrics}")
        
        await shutdown_worker_pool()
    
    asyncio.run(test_pool())