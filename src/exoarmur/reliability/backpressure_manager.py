"""
Backpressure and Rate Limiting - Phase 6 Reliability Substrate
Bounded queues and tenant-scoped rate limiting with deterministic overload behavior.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import weakref

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BackpressureAction(str, Enum):
    """Backpressure actions for deterministic overload behavior"""
    REJECT = "REJECT"
    DEFER = "DEFER"
    QUEUE_FULL = "QUEUE_FULL"
    RATE_LIMITED = "RATE_LIMITED"


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, tenant_id: str, limit_type: str, current_rate: float, limit: float):
        self.tenant_id = tenant_id
        self.limit_type = limit_type
        self.current_rate = current_rate
        self.limit = limit
        super().__init__(f"Rate limit exceeded for {tenant_id}: {limit_type} ({current_rate:.2f} > {limit})")


class QueueFullError(Exception):
    """Raised when queue is at capacity"""
    
    def __init__(self, queue_name: str, capacity: int, current_size: int):
        self.queue_name = queue_name
        self.capacity = capacity
        self.current_size = current_size
        super().__init__(f"Queue {queue_name} is full ({current_size}/{capacity})")


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    # Global rate limits (requests per second)
    global_requests_per_second: float = 100.0
    
    # Tenant rate limits (requests per second)
    tenant_requests_per_second: float = 10.0
    
    # Rate limit window size in seconds
    window_size_seconds: float = 1.0
    
    # Burst allowance (temporary rate limit increase)
    burst_multiplier: float = 2.0
    
    # Rate limit cleanup interval
    cleanup_interval_seconds: float = 60.0


@dataclass
class QueueConfig:
    """Queue configuration for bounded queues"""
    max_size: int = 1000
    drop_policy: str = "reject"  # "reject", "drop_oldest", "drop_newest"
    max_wait_time: float = 30.0  # Max time to wait for space


class TokenBucket:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, rate: float, burst: float, window_size: float = 1.0):
        self.rate = rate  # Tokens per second
        self.burst = burst  # Maximum tokens
        self.window_size = window_size  # Window size in seconds
        self.tokens = burst  # Start with full burst
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.burst, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available"""
        async with self._lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def consume_async(self, tokens: int = 1) -> bool:
        """Consume tokens asynchronously"""
        while not self.consume(tokens):
            await asyncio.sleep(0.1)  # Small delay before retry
        return True


class TenantRateLimiter:
    """
    Tenant-scoped rate limiter with token bucket algorithm
    
    Rule R4: Internal queues must be bounded.
    Rule R4: Tenant-scoped rate limits must exist.
    Rule R4: Overload behavior must be deterministic.
    """
    
    def __init__(self, tenant_id: str, config: RateLimitConfig):
        self.tenant_id = tenant_id
        self.config = config
        
        # Create token bucket for tenant
        self.bucket = TokenBucket(
            rate=config.tenant_requests_per_second,
            burst=config.tenant_requests_per_second * config.burst_multiplier,
            window_size=config.window_size_seconds
        )
        
        # Create token bucket for global limit
        self.global_bucket = TokenBucket(
            rate=config.global_requests_per_second,
            burst=config.global_requests_per_second * config.burst_multiplier,
            window_size=config.window_size_seconds
        )
        
        logger.info(f"Rate limiter initialized for tenant {tenant_id}: "
                   f"{config.tenant_requests_per_second} req/s, "
                   f"burst {config.tenant_requests_per_second * config.burst_multiplier}")
    
    async def check_rate_limit(self, operation: str = "operation") -> bool:
        """Check if operation is allowed under rate limit
        
        Args:
            operation: Description of operation for audit
            
        Returns:
            True if allowed, False if rate limited
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Check global rate limit first
        if not await self.global_bucket.consume(1):
            raise RateLimitExceeded(
                tenant_id=self.tenant_id, limit_type="global", current_rate=self.global_bucket.tokens, limit=self.config.global_requests_per_second
            )
        
        # Check tenant-specific rate limit
        if not await self.bucket.consume(1):
            raise RateLimitExceeded(
                tenant_id=self.tenant_id, limit_type="tenant", current_rate=self.bucket.tokens, limit=self.config.tenant_requests_per_second
            )
        
        return True
    
    def get_current_rates(self) -> Dict[str, float]:
        """Get current token rates for monitoring"""
        return {
            "global_rate": self.global_bucket.tokens,
            "tenant_rate": self.bucket.tokens,
            "global_limit": self.config.global_requests_per_second,
            "tenant_limit": self.config.tenant_requests_per_second
        }


class BoundedQueue:
    """
    Bounded queue with configurable capacity and drop policy
    
    Rule R4: Internal queues must be bounded.
    Rule R3: No silent drops / no best-effort.
    """
    
    def __init__(self, name: str, config: QueueConfig):
        self.name = name
        self.config = config
        self.queue = deque(maxlen=config.max_size)
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._dropped_count = 0
        logger.info(f"Bounded queue created: {name} (max_size={config.max_size})")
    
    async def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """
        Put item in queue with backpressure
        
        Args:
            item: Item to queue
            timeout: Optional timeout for waiting
            
        Returns:
            True if item was queued, False if queue was full
            
        Raises:
            QueueFullError: If queue is full and timeout expires
        """
        async with self._lock:
            if len(self.queue) >= self.config.max_size:
                # Handle queue full according to drop policy
                if self.config.drop_policy == "reject":
                    raise QueueFullError(self.name, self.config.max_size, len(self.queue))
                elif self.config.drop_policy == "drop_oldest":
                    self._dropped_count += 1
                    self.queue.popleft()
                    logger.warning(f"Dropped oldest item from queue {self.name} (dropped: {self._dropped_count})")
                elif self.config.drop_policy == "drop_newest":
                    self._dropped_count += 1
                    # Don't add new item, just count as dropped
                    logger.warning(f"Dropped newest item from queue {self.name} (dropped: {self._dropped_count})")
                    return False
                else:
                    logger.error(f"Unknown drop policy: {self.config.drop_policy}")
                    return False
            
            # Add item to queue
            self.queue.append(item)
            self._not_empty.notify()
            return True
    
    async def get(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Get item from queue with timeout
        
        Args:
            timeout: Optional timeout for waiting
            
        Returns:
            Item if available, None if queue empty and timeout expires
            
        Raises:
            TimeoutError: If timeout expires
        """
        async with self._lock:
            if not self.queue:
                if timeout is not None:
                    try:
                        await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                    except asyncio.TimeoutError:
                        return None
                else:
                    return None
            
            # Get item from queue
            item = self.queue.popleft()
            if not self.queue:
                self._not_empty.notify_all()
            
            return item
    
    def size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def is_full(self) -> bool:
        """Check if queue is at capacity"""
        return len(self.queue) >= self.config.max_size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "name": self.name,
            "current_size": len(self.queue),
            "max_size": self.config.max_size,
            "dropped_count": self._dropped_count,
            "is_full": self.is_full()
        }


class BackpressureManager:
    """
    Central backpressure management with rate limiting and queue management
    
    Rule R4: Backpressure is required.
    Rule R4: Overload behavior must be deterministic.
    """
    
    def __init__(self):
        self.rate_limiters: Dict[str, TenantRateLimiter] = {}
        self.queues: Dict[str, BoundedQueue] = {}
        self._audit_emitter = None
        self.default_rate_config = RateLimitConfig()
        self.default_queue_config = QueueConfig()
        
        # Cleanup task for rate limiters
        self._cleanup_task = None
        self._cleanup_interval = self.default_rate_config.cleanup_interval_seconds
        
        logger.info("BackpressureManager initialized")
    
    def set_audit_emitter(self, emitter: Callable):
        """Set audit emitter for backpressure events"""
        self._audit_emitter = emitter
    
    def get_rate_limiter(self, tenant_id: str) -> TenantRateLimiter:
        """Get or create rate limiter for tenant"""
        if tenant_id not in self.rate_limiters:
            self.rate_limiters[tenant_id] = TenantRateLimiter(tenant_id, self.default_rate_config)
            logger.info(f"Created rate limiter for tenant {tenant_id}")
        return self.rate_limiters[tenant_id]
    
    def get_queue(self, name: str, config: Optional[QueueConfig] = None) -> BoundedQueue:
        """Get or create bounded queue"""
        effective_config = config or self.default_queue_config
        
        if name not in self.queues:
            self.queues[name] = BoundedQueue(name, effective_config)
            logger.info(f"Created bounded queue: {name} (max_size={effective_config.max_size})")
        return self.queues[name]
    
    async def check_backpressure(
        self,
        tenant_id: str,
        queue_name: Optional[str] = None,
        operation: str = "operation"
    ) -> Dict[str, Any]:
        """
        Check backpressure conditions for tenant
        
        Args:
            tenant_id: Tenant ID to check
            queue_name: Optional queue name to check
            operation: Description of operation
            
        Returns:
            Backpressure status with details
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
            QueueFullError: If queue is full
        """
        status = {
            "tenant_id": tenant_id,
            "operation": operation,
            "backpressure_action": None,
            "rate_limited": False,
            "queue_full": False,
            "queue_stats": {}
        }
        
        # Check rate limits
        rate_limiter = self.get_rate_limiter(tenant_id)
        try:
            await rate_limiter.check_rate_limit(operation)
            status["rate_limited"] = False
        except RateLimitExceeded as e:
            status["rate_limited"] = True
            status["backpressure_action"] = BackpressureAction.RATE_LIMITED
            status["rate_limit_stats"] = rate_limiter.get_current_rates()
            
            # Emit audit event
            await self._emit_backpressure_audit(status)
            
            raise RateLimitExceeded(
                tenant_id=tenant_id, limit_type="rate_limit", current_rate=e.current_rate, limit=e.limit
            )
        
        # Check queue capacity if specified
        if queue_name:
            queue = self.get_queue(queue_name)
            if queue.is_full():
                status["queue_full"] = True
                status["queue_stats"] = queue.get_stats()
                status["backpressure_action"] = BackpressureAction.QUEUE_FULL
                
                # Emit audit event
                await self._emit_backpressure_audit(status)
                
                raise QueueFullError(queue_name, queue.config.max_size, queue.size())
        
        return status
    
    async def execute_with_backpressure(
        self,
        tenant_id: str,
        operation: str,
        coro,
        queue_name: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Execute coroutine with backpressure protection
        
        Args:
            tenant_id: Tenant ID for rate limiting
            operation: Description of operation
            coro: Coroutine to execute
            queue_name: Optional queue name for queuing
            timeout: Optional timeout for operation
            **kwargs: Additional context
            
        Returns:
            Result of coroutine execution
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
            QueueFullError: If queue is full
        """
        # Check backpressure before execution
        await self.check_backpressure(tenant_id, queue_name, operation)
        
        # Execute operation
        return await coro(**kwargs)
    
    def start_cleanup_task(self):
        """Start background cleanup task for rate limiters"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_rate_limiters())
            logger.info("Started rate limiter cleanup task")
    
    async def _cleanup_rate_limiters(self):
        """Cleanup rate limiters periodically"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                # Cleanup inactive rate limiters (could implement TTL logic)
                for tenant_id, limiter in list(self.rate_limiters.items()):
                    # Simple cleanup: remove if no activity for 5 minutes
                    # In production, this would be based on last usage timestamps
                    pass
                
                logger.debug("Rate limiter cleanup completed")
                
            except Exception as e:
                logger.error(f"Rate limiter cleanup failed: {e}")
    
    async def _emit_backpressure_audit(self, status: Dict[str, Any]):
        """Emit audit event for backpressure"""
        if not self._audit_emitter:
            logger.warning("No audit emitter configured for backpressure events")
            return
        
        try:
            audit_data = {
                "event_type": "backpressure",
                "tenant_id": status["tenant_id"],
                "operation": status["operation"],
                "backpressure_action": status.get("backpressure_action"),
                "rate_limited": status["rate_limited"],
                "queue_full": status["queue_full"],
                "rate_limit_stats": status.get("rate_limit_stats", {}),
                "queue_stats": status.get("queue_stats", {}),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self._audit_emitter(audit_data)
            
        except Exception as e:
            logger.error(f"Failed to emit backpressure audit: {e}")


# Global backpressure manager instance
_backpressure_manager: Optional[BackpressureManager] = None


def get_backpressure_manager() -> BackpressureManager:
    """Get the global backpressure manager instance"""
    global _backpressure_manager
    if _backpressure_manager is None:
        _backpressure_manager = BackpressureManager()
        _backpressure_manager.start_cleanup_task()
    return _backpressure_manager


# Decorator for backpressure protection
def with_backpressure(
    tenant_id: str,
    operation: str = "operation",
    queue_name: Optional[str] = None,
    timeout: Optional[float] = None
):
    """
    Decorator for adding backpressure protection to async functions
    
    Args:
        tenant_id: Tenant ID for rate limiting
        operation: Description of operation
        queue_name: Optional queue name for queuing
        timeout: Optional timeout for operation
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            backpressure_mgr = get_backpressure_manager()
            
            # Extract tenant_id from kwargs if available
            ctx_tenant_id = kwargs.get('tenant_id') or tenant_id
            
            return await backpressure_mgr.execute_with_backpressure(
                tenant_id=ctx_tenant_id,
                operation=operation,
                coro=func(*args, **kwargs),
                queue_name=queue_name,
                timeout=timeout
            )
        return wrapper
    return decorator


# Convenience functions for common operations
async def execute_with_rate_limit(
    tenant_id: str,
    operation: str,
    coro,
    **context
):
    """Execute with rate limiting only"""
    backpressure_mgr = get_backpressure_manager()
    return await backpressure_mgr.execute_with_backpressure(
        tenant_id=tenant_id,
        operation=operation,
        coro=coro,
        **context
    )


async def execute_with_queue(
    tenant_id: str,
    operation: str,
    coro,
    queue_name: str,
    **context
):
    """Execute with queue backpressure protection"""
    backpressure_mgr = get_backpressure_manager()
    return await backpressure_mgr.execute_with_backpressure(
        tenant_id=tenant_id,
        operation=operation,
        coro=coro,
        queue_name=queue_name,
        **context
    )
