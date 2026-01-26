"""
Retry Policy Framework - Phase 6 Reliability Substrate
Bounded retry policy with exponential backoff, jitter, and durable idempotency protection.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, TypeVar, Union, List
from enum import Enum
from dataclasses import dataclass, field
import functools
import hashlib

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryCategory(str, Enum):
    """Retry operation categories for deterministic audit codes"""
    NATS_CONNECT = "RETRY_NATS_CONNECT"
    NATS_PUBLISH = "RETRY_NATS_PUBLISH"
    NATS_SUBSCRIBE = "RETRY_NATS_SUBSCRIBE"
    NATS_STREAM_CREATE = "RETRY_NATS_STREAM_CREATE"
    
    KV_CREATE = "RETRY_KV_CREATE"
    KV_GET = "RETRY_KV_GET"
    KV_PUT = "RETRY_KV_PUT"
    KV_DELETE = "RETRY_KV_DELETE"
    
    EXECUTION_INTENT = "RETRY_EXECUTION_INTENT"
    EXECUTION_CONTAINMENT = "RETRY_EXECUTION_CONTAINMENT"
    EXECUTION_EXPIRATION = "RETRY_EXECUTION_EXPIRATION"
    
    APPROVAL_CHECK = "RETRY_APPROVAL_CHECK"
    APPROVAL_GRANT = "RETRY_APPROVAL_GRANT"
    
    REPLAY_PROCESSING = "RETRY_REPLAY_PROCESSING"
    REPLAY_VALIDATION = "RETRY_REPLAY_VALIDATION"
    
    API_REQUEST = "RETRY_API_REQUEST"
    API_VALIDATION = "RETRY_API_VALIDATION"


@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay in seconds
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    jitter_enabled: bool = True  # Add jitter to prevent thundering herd
    jitter_factor: float = 0.1  # Jitter factor (0.1 = ±10% jitter)
    
    # Retryable exceptions (default to retry on all exceptions)
    retryable_exceptions: List[type] = field(default_factory=lambda: [Exception])
    
    # Non-retryable exceptions (override retryable_exceptions)
    non_retryable_exceptions: List[type] = field(default_factory=list)


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    max_attempts: int
    delay: float
    exception: Optional[Exception] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    
    def __init__(self, category: RetryCategory, attempts: List[RetryAttempt], operation: str):
        self.category = category
        self.attempts = attempts
        self.operation = operation
        super().__init__(f"Operation '{operation}' failed after {len(attempts)} attempts ({category.value})")


class IdempotencyManager:
    """
    Durable idempotency protection for retry operations
    
    Rule R2: Retries must be finite, policy-driven, jittered, and auditable.
    Rule R2: Retry attempts must be idempotent.
    """
    
    def __init__(self):
        self._idempotency_store: Dict[str, Dict[str, Any]] = {}
        logger.info("IdempotencyManager initialized")
    
    def compute_idempotency_key(
        self,
        operation: str,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute deterministic idempotency key
        
        Args:
            operation: Operation description
            tenant_id: Tenant context
            correlation_id: Correlation ID
            additional_params: Additional parameters for uniqueness
            
        Returns:
            Deterministic idempotency key
        """
        canonical = {
            "operation": operation,
            "tenant_id": tenant_id or "",
            "correlation_id": correlation_id or "",
            "additional_params": additional_params or {}
        }
        
        # Sort keys for deterministic ordering
        canonical_str = str(sorted(canonical.items()))
        return hashlib.sha256(canonical_str.encode()).hexdigest()
    
    async def check_idempotency(self, idempotency_key: str) -> Optional[Any]:
        """
        Check if operation already processed
        
        Args:
            idempotency_key: Idempotency key to check
            
        Returns:
            Previous result if already processed, None otherwise
        """
        if idempotency_key in self._idempotency_store:
            entry = self._idempotency_store[idempotency_key]
            logger.debug(f"Idempotency hit for key: {idempotency_key[:8]}...")
            return entry.get("result")
        return None
    
    async def record_result(self, idempotency_key: str, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Record operation result for idempotency
        
        Args:
            idempotency_key: Idempotency key
            result: Operation result
            metadata: Additional metadata
        """
        self._idempotency_store[idempotency_key] = {
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.debug(f"Recorded result for idempotency key: {idempotency_key[:8]}...")
    
    async def clear_idempotency(self, idempotency_key: str):
        """Clear idempotency entry (for testing or cleanup)"""
        if idempotency_key in self._idempotency_store:
            del self._idempotency_store[idempotency_key]
            logger.debug(f"Cleared idempotency key: {idempotency_key[:8]}...")


class RetryManager:
    """
    Bounded retry policy manager with idempotency protection
    
    Rule R2: Retries must be finite, policy-driven, jittered, and auditable.
    """
    
    def __init__(self, idempotency_manager: Optional[IdempotencyManager] = None):
        self.idempotency_manager = idempotency_manager or IdempotencyManager()
        self._audit_emitter = None
        logger.info("RetryManager initialized with bounded retry policy")
    
    def set_audit_emitter(self, emitter: Callable):
        """Set audit emitter for retry events"""
        self._audit_emitter = emitter
    
    def get_policy(self, category: Union[RetryCategory, str]) -> RetryPolicy:
        """Get retry policy for operation category"""
        # Default policies for different categories
        default_policies = {
            # NATS operations - moderate retry with backoff
            RetryCategory.NATS_CONNECT: RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=30.0),
            RetryCategory.NATS_PUBLISH: RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=10.0),
            RetryCategory.NATS_SUBSCRIBE: RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=10.0),
            RetryCategory.NATS_STREAM_CREATE: RetryPolicy(max_attempts=2, base_delay=2.0, max_delay=60.0),
            
            # KV operations - conservative retry
            RetryCategory.KV_CREATE: RetryPolicy(max_attempts=2, base_delay=1.0, max_delay=30.0),
            RetryCategory.KV_GET: RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=10.0),
            RetryCategory.KV_PUT: RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=10.0),
            RetryCategory.KV_DELETE: RetryPolicy(max_attempts=2, base_delay=1.0, max_delay=30.0),
            
            # Execution operations - limited retry
            RetryCategory.EXECUTION_INTENT: RetryPolicy(max_attempts=2, base_delay=2.0, max_delay=60.0),
            RetryCategory.EXECUTION_CONTAINMENT: RetryPolicy(max_attempts=2, base_delay=2.0, max_delay=60.0),
            RetryCategory.EXECUTION_EXPIRATION: RetryPolicy(max_attempts=1, base_delay=1.0, max_delay=30.0),
            
            # Approval operations - conservative retry
            RetryCategory.APPROVAL_CHECK: RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0),
            RetryCategory.APPROVAL_GRANT: RetryPolicy(max_attempts=2, base_delay=2.0, max_delay=60.0),
            
            # Replay operations - limited retry
            RetryCategory.REPLAY_PROCESSING: RetryPolicy(max_attempts=1, base_delay=1.0, max_delay=30.0),
            RetryCategory.REPLAY_VALIDATION: RetryPolicy(max_attempts=2, base_delay=1.0, max_delay=30.0),
            
            # API operations - moderate retry
            RetryCategory.API_REQUEST: RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0),
            RetryCategory.API_VALIDATION: RetryPolicy(max_attempts=2, base_delay=0.5, max_delay=10.0),
        }
        
        if isinstance(category, str):
            try:
                category = RetryCategory(category)
            except ValueError:
                logger.warning(f"Unknown retry category: {category}, using default policy")
                return RetryPolicy()
        
        return default_policies.get(category, RetryPolicy())
    
    def _compute_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Compute delay with exponential backoff and jitter"""
        # Exponential backoff
        delay = policy.base_delay * (policy.backoff_multiplier ** (attempt - 1))
        
        # Cap at maximum delay
        delay = min(delay, policy.max_delay)
        
        # Add jitter if enabled
        if policy.jitter_enabled:
            jitter_range = delay * policy.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter)
        
        return delay
    
    def _is_retryable_exception(self, exception: Exception, policy: RetryPolicy) -> bool:
        """Check if exception is retryable according to policy"""
        # Check non-retryable exceptions first
        for non_retryable in policy.non_retryable_exceptions:
            if isinstance(exception, non_retryable):
                return False
        
        # Check retryable exceptions
        for retryable in policy.retryable_exceptions:
            if isinstance(exception, retryable):
                return True
        
        # Default: retry all exceptions
        return True
    
    async def execute_with_retry(
        self,
        category: RetryCategory,
        operation: str,
        coro,
        policy: Optional[RetryPolicy] = None,
        idempotency_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute coroutine with retry policy and idempotency protection
        
        Args:
            category: Retry category for deterministic classification
            operation: Description of operation
            coro: Coroutine to execute
            policy: Optional retry policy override
            idempotency_key: Optional idempotency key for duplicate detection
            tenant_id: Tenant context for audit
            correlation_id: Correlation ID for audit
            trace_id: Trace ID for audit
            additional_context: Additional context for audit
            
        Returns:
            Result of coroutine execution
            
        Raises:
            RetryError: If all retry attempts are exhausted
        """
        effective_policy = policy or self.get_policy(category)
        
        # Check idempotency first
        if idempotency_key:
            existing_result = await self.idempotency_manager.check_idempotency(idempotency_key)
            if existing_result is not None:
                logger.info(f"Idempotency hit for {operation}, returning cached result")
                await self._emit_idempotency_audit(
                    category, operation, idempotency_key, "hit", tenant_id, correlation_id, trace_id
                )
                return existing_result
        
        attempts = []
        
        for attempt in range(1, effective_policy.max_attempts + 1):
            try:
                # Execute operation
                result = await coro
                
                # Record result for idempotency
                if idempotency_key:
                    await self.idempotency_manager.record_result(
                        idempotency_key, result, {"attempts": len(attempts)}
                    )
                    await self._emit_idempotency_audit(
                        category, operation, idempotency_key, "record", tenant_id, correlation_id, trace_id
                    )
                
                # Log success
                if len(attempts) > 0:
                    logger.info(f"Operation {operation} succeeded after {len(attempts)} retries")
                
                return result
                
            except Exception as e:
                # Check if exception is retryable
                if not self._is_retryable_exception(e, effective_policy):
                    logger.error(f"Non-retryable exception for {operation}: {e}")
                    raise
                
                # Create retry attempt record
                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    max_attempts=effective_policy.max_attempts,
                    delay=0.0,  # Will be set below
                    exception=e
                )
                attempts.append(retry_attempt)
                
                # Check if this was the last attempt
                if attempt >= effective_policy.max_attempts:
                    logger.error(f"Operation {operation} failed after {len(attempts)} attempts")
                    await self._emit_retry_exhausted_audit(
                        category, operation, attempts, tenant_id, correlation_id, trace_id
                    )
                    raise RetryError(category, attempts, operation)
                
                # Compute delay for next attempt
                delay = self._compute_delay(attempt, effective_policy)
                retry_attempt.delay = delay
                
                # Emit retry audit event
                await self._emit_retry_attempt_audit(
                    category, operation, retry_attempt, tenant_id, correlation_id, trace_id
                )
                
                logger.warning(f"Attempt {attempt}/{effective_policy.max_attempts} failed for {operation}: {e}. Retrying in {delay:.2f}s")
                
                # Wait before retry
                await asyncio.sleep(delay)
    
    async def _emit_retry_attempt_audit(
        self,
        category: RetryCategory,
        operation: str,
        attempt: RetryAttempt,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Emit audit event for retry attempt"""
        if not self._audit_emitter:
            return
        
        try:
            audit_data = {
                "event_type": "retry_attempt",
                "retry_category": category.value,
                "operation": operation,
                "attempt_number": attempt.attempt_number,
                "max_attempts": attempt.max_attempts,
                "delay_seconds": attempt.delay,
                "exception_type": type(attempt.exception).__name__ if attempt.exception else None,
                "exception_message": str(attempt.exception) if attempt.exception else None,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "timestamp": attempt.timestamp.isoformat()
            }
            
            await self._audit_emitter(audit_data)
            
        except Exception as e:
            logger.error(f"Failed to emit retry attempt audit: {e}")
    
    async def _emit_retry_exhausted_audit(
        self,
        category: RetryCategory,
        operation: str,
        attempts: List[RetryAttempt],
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Emit audit event for retry exhaustion"""
        if not self._audit_emitter:
            return
        
        try:
            audit_data = {
                "event_type": "retry_exhausted",
                "retry_category": category.value,
                "operation": operation,
                "total_attempts": len(attempts),
                "final_exception_type": type(attempts[-1].exception).__name__ if attempts and attempts[-1].exception else None,
                "final_exception_message": str(attempts[-1].exception) if attempts and attempts[-1].exception else None,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self._audit_emitter(audit_data)
            
        except Exception as e:
            logger.error(f"Failed to emit retry exhausted audit: {e}")
    
    async def _emit_idempotency_audit(
        self,
        category: RetryCategory,
        operation: str,
        idempotency_key: str,
        action: str,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Emit audit event for idempotency"""
        if not self._audit_emitter:
            return
        
        try:
            audit_data = {
                "event_type": "idempotency",
                "retry_category": category.value,
                "operation": operation,
                "idempotency_key": idempotency_key[:16] + "...",  # Truncate for audit
                "action": action,  # "hit" or "record"
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self._audit_emitter(audit_data)
            
        except Exception as e:
            logger.error(f"Failed to emit idempotency audit: {e}")


# Global retry manager instance
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance"""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


def with_retry(
    category: RetryCategory,
    operation: str,
    policy: Optional[RetryPolicy] = None,
    idempotency_key: Optional[str] = None,
    tenant_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for adding retry policy to async functions
    
    Args:
        category: Retry category for deterministic classification
        operation: Description of operation
        policy: Optional retry policy override
        idempotency_key: Optional idempotency key
        tenant_id: Tenant context for audit
        correlation_id: Correlation ID for audit
        trace_id: Trace ID for audit
        additional_context: Additional context for audit
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retry_mgr = get_retry_manager()
            
            # Extract context from kwargs if available
            ctx_tenant_id = kwargs.get('tenant_id') or tenant_id
            ctx_correlation_id = kwargs.get('correlation_id') or correlation_id
            ctx_trace_id = kwargs.get('trace_id') or trace_id
            
            return await retry_mgr.execute_with_retry(
                category=category,
                operation=operation,
                coro=func(*args, **kwargs),
                policy=policy,
                idempotency_key=idempotency_key,
                tenant_id=ctx_tenant_id,
                correlation_id=ctx_correlation_id,
                trace_id=ctx_trace_id,
                additional_context=additional_context
            )
        return wrapper
    return decorator


# Convenience functions for common operations
async def execute_with_nats_retry(
    operation: str,
    coro,
    policy: Optional[RetryPolicy] = None,
    **context
):
    """Execute with NATS retry policy"""
    retry_mgr = get_retry_manager()
    return await retry_mgr.execute_with_retry(
        RetryCategory.NATS_PUBLISH,
        operation,
        coro,
        policy=policy,
        **context
    )


async def execute_with_kv_retry(
    operation: str,
    coro,
    policy: Optional[RetryPolicy] = None,
    **context
):
    """Execute with KV retry policy"""
    retry_mgr = get_retry_manager()
    return await retry_mgr.execute_with_retry(
        RetryCategory.KV_GET,
        operation,
        coro,
        policy=policy,
        **context
    )
