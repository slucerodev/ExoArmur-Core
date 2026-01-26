"""
Timeout Enforcement - Phase 6 Reliability Substrate
Central timeout policy with deterministic audit codes for all operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from enum import Enum
from dataclasses import dataclass
import functools

logger = logging.getLogger(__name__)


class TimeoutCategory(str, Enum):
    """Timeout operation categories for deterministic audit codes"""
    NATS_CONNECT = "TIMEOUT_NATS_CONNECT"
    NATS_PUBLISH = "TIMEOUT_NATS_PUBLISH"
    NATS_SUBSCRIBE = "TIMEOUT_NATS_SUBSCRIBE"
    NATS_STREAM_CREATE = "TIMEOUT_NATS_STREAM_CREATE"
    
    KV_CREATE = "TIMEOUT_KV_CREATE"
    KV_GET = "TIMEOUT_KV_GET"
    KV_PUT = "TIMEOUT_KV_PUT"
    KV_DELETE = "TIMEOUT_KV_DELETE"
    
    EXECUTION_INTENT = "TIMEOUT_EXECUTION_INTENT"
    EXECUTION_CONTAINMENT = "TIMEOUT_EXECUTION_CONTAINMENT"
    EXECUTION_EXPIRATION = "TIMEOUT_EXECUTION_EXPIRATION"
    
    APPROVAL_CHECK = "TIMEOUT_APPROVAL_CHECK"
    APPROVAL_GRANT = "TIMEOUT_APPROVAL_GRANT"
    
    REPLAY_PROCESSING = "TIMEOUT_REPLAY_PROCESSING"
    REPLAY_VALIDATION = "TIMEOUT_REPLAY_VALIDATION"
    
    API_REQUEST = "TIMEOUT_API_REQUEST"
    API_VALIDATION = "TIMEOUT_API_VALIDATION"


@dataclass
class TimeoutConfig:
    """Timeout configuration for different operation categories"""
    # NATS operations (seconds)
    nats_connect: float = 10.0
    nats_publish: float = 5.0
    nats_subscribe: float = 5.0
    nats_stream_create: float = 15.0
    
    # KV operations (seconds)
    kv_create: float = 10.0
    kv_get: float = 5.0
    kv_put: float = 5.0
    kv_delete: float = 5.0
    
    # Execution operations (seconds)
    execution_intent: float = 30.0
    execution_containment: float = 60.0
    execution_expiration: float = 120.0
    
    # Approval operations (seconds)
    approval_check: float = 5.0
    approval_grant: float = 10.0
    
    # Replay operations (seconds)
    replay_processing: float = 300.0  # 5 minutes for large replays
    replay_validation: float = 60.0
    
    # API operations (seconds)
    api_request: float = 30.0
    api_validation: float = 10.0
    
    # Default timeout for unspecified operations
    default_timeout: float = 30.0


class TimeoutError(Exception):
    """Raised when operation times out"""
    
    def __init__(self, category: TimeoutCategory, timeout_seconds: float, operation: str):
        self.category = category
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        super().__init__(f"Operation '{operation}' timed out after {timeout_seconds}s ({category.value})")


class TimeoutManager:
    """
    Central timeout enforcement manager
    
    Rule R1: Every IO, NATS, KV, RPC, lock, or long-running operation must have an explicit timeout.
    Rule R6: Timeouts must emit deterministic audit reason codes.
    """
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._audit_emitter = None
        logger.info("TimeoutManager initialized with explicit timeout policy")
    
    def set_audit_emitter(self, emitter: Callable):
        """Set audit emitter for timeout events"""
        self._audit_emitter = emitter
    
    def get_timeout(self, category: Union[TimeoutCategory, str]) -> float:
        """Get timeout for operation category"""
        if isinstance(category, str):
            try:
                category = TimeoutCategory(category)
            except ValueError:
                logger.warning(f"Unknown timeout category: {category}, using default")
                return self.config.default_timeout
        
        # Map category to config field
        timeout_map = {
            TimeoutCategory.NATS_CONNECT: self.config.nats_connect,
            TimeoutCategory.NATS_PUBLISH: self.config.nats_publish,
            TimeoutCategory.NATS_SUBSCRIBE: self.config.nats_subscribe,
            TimeoutCategory.NATS_STREAM_CREATE: self.config.nats_stream_create,
            
            TimeoutCategory.KV_CREATE: self.config.kv_create,
            TimeoutCategory.KV_GET: self.config.kv_get,
            TimeoutCategory.KV_PUT: self.config.kv_put,
            TimeoutCategory.KV_DELETE: self.config.kv_delete,
            
            TimeoutCategory.EXECUTION_INTENT: self.config.execution_intent,
            TimeoutCategory.EXECUTION_CONTAINMENT: self.config.execution_containment,
            TimeoutCategory.EXECUTION_EXPIRATION: self.config.execution_expiration,
            
            TimeoutCategory.APPROVAL_CHECK: self.config.approval_check,
            TimeoutCategory.APPROVAL_GRANT: self.config.approval_grant,
            
            TimeoutCategory.REPLAY_PROCESSING: self.config.replay_processing,
            TimeoutCategory.REPLAY_VALIDATION: self.config.replay_validation,
            
            TimeoutCategory.API_REQUEST: self.config.api_request,
            TimeoutCategory.API_VALIDATION: self.config.api_validation,
        }
        
        return timeout_map.get(category, self.config.default_timeout)
    
    async def execute_with_timeout(
        self,
        category: TimeoutCategory,
        operation: str,
        coro,
        timeout: Optional[float] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """
        Execute coroutine with timeout enforcement and audit
        
        Args:
            category: Timeout category for deterministic classification
            operation: Description of operation being executed
            coro: Coroutine to execute
            timeout: Optional override timeout (use with caution)
            tenant_id: Tenant context for audit
            correlation_id: Correlation ID for audit
            trace_id: Trace ID for audit
            additional_context: Additional context for audit
            
        Returns:
            Result of coroutine execution
            
        Raises:
            TimeoutError: If operation times out
        """
        effective_timeout = timeout or self.get_timeout(category)
        
        logger.debug(f"Executing {operation} with {effective_timeout}s timeout ({category.value})")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(coro, timeout=effective_timeout)
            logger.debug(f"Operation {operation} completed successfully")
            return result
            
        except asyncio.TimeoutError:
            # Create structured timeout error
            timeout_error = TimeoutError(category, effective_timeout, operation)
            
            # Emit audit event for timeout
            await self._emit_timeout_audit(
                category=category,
                operation=operation,
                timeout_seconds=effective_timeout,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
                additional_context=additional_context
            )
            
            logger.warning(f"Operation {operation} timed out after {effective_timeout}s ({category.value})")
            raise timeout_error
    
    async def _emit_timeout_audit(
        self,
        category: TimeoutCategory,
        operation: str,
        timeout_seconds: float,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Emit audit event for timeout occurrence"""
        if not self._audit_emitter:
            logger.warning("No audit emitter configured for timeout events")
            return
        
        try:
            audit_data = {
                "event_type": "timeout_occurred",
                "timeout_category": category.value,
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "additional_context": additional_context or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self._audit_emitter(audit_data)
            logger.info(f"Audit event emitted for timeout: {category.value}")
            
        except Exception as e:
            logger.error(f"Failed to emit timeout audit: {e}")


# Global timeout manager instance
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get the global timeout manager instance"""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager


def with_timeout(
    category: TimeoutCategory,
    operation: str,
    timeout: Optional[float] = None,
    tenant_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for adding timeout enforcement to async functions
    
    Args:
        category: Timeout category for deterministic classification
        operation: Description of operation
        timeout: Optional override timeout
        tenant_id: Tenant context for audit
        correlation_id: Correlation ID for audit
        trace_id: Trace ID for audit
        additional_context: Additional context for audit
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            timeout_mgr = get_timeout_manager()
            
            # Extract context from kwargs if available
            ctx_tenant_id = kwargs.get('tenant_id') or tenant_id
            ctx_correlation_id = kwargs.get('correlation_id') or correlation_id
            ctx_trace_id = kwargs.get('trace_id') or trace_id
            
            return await timeout_mgr.execute_with_timeout(
                category=category,
                operation=operation,
                coro=func(*args, **kwargs),
                timeout=timeout,
                tenant_id=ctx_tenant_id,
                correlation_id=ctx_correlation_id,
                trace_id=ctx_trace_id,
                additional_context=additional_context
            )
        return wrapper
    return decorator


# Convenience functions for common operations
async def execute_with_nats_timeout(
    operation: str,
    coro,
    timeout: Optional[float] = None,
    **context
):
    """Execute with NATS timeout"""
    timeout_mgr = get_timeout_manager()
    return await timeout_mgr.execute_with_timeout(
        TimeoutCategory.NATS_PUBLISH,
        operation,
        coro,
        timeout=timeout,
        **context
    )


async def execute_with_kv_timeout(
    operation: str,
    coro,
    timeout: Optional[float] = None,
    **context
):
    """Execute with KV timeout"""
    timeout_mgr = get_timeout_manager()
    return await timeout_mgr.execute_with_timeout(
        TimeoutCategory.KV_GET,
        operation,
        coro,
        timeout=timeout,
        **context
    )


async def execute_with_execution_timeout(
    operation: str,
    coro,
    timeout: Optional[float] = None,
    **context
):
    """Execute with execution timeout"""
    timeout_mgr = get_timeout_manager()
    return await timeout_mgr.execute_with_timeout(
        TimeoutCategory.EXECUTION_INTENT,
        operation,
        coro,
        timeout=timeout,
        **context
    )
