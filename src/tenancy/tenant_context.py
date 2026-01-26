"""
Tenant Context - Phase 5 Operational Safety Hardening
Enforces tenant isolation and context propagation throughout the system.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Tenant context that must be present for all state operations"""
    tenant_id: str
    cell_id: Optional[str] = None
    principal_id: Optional[str] = None  # Who is acting on behalf of tenant
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate tenant context is complete"""
        if not self.tenant_id:
            raise ValueError("TenantContext: tenant_id is required")
        if not self.tenant_id.strip():
            raise ValueError("TenantContext: tenant_id cannot be empty")


class TenantIsolationError(Exception):
    """Raised when tenant isolation requirements are violated"""
    pass


class TenantContextManager:
    """
    Manages tenant context propagation and isolation enforcement
    
    Rule R3: Tenant context is mandatory for all state operations
    """
    
    def __init__(self):
        self._active_context: Optional[TenantContext] = None
        self._context_stack: List[TenantContext] = []
    
    def set_context(self, context: TenantContext) -> None:
        """Set the active tenant context"""
        context.validate()
        self._active_context = context
        logger.debug(f"Tenant context set: {context.tenant_id}")
    
    def get_context(self) -> Optional[TenantContext]:
        """Get the active tenant context"""
        return self._active_context
    
    def require_context(self, operation: str = "operation") -> TenantContext:
        """
        Get active tenant context or raise error
        
        Args:
            operation: Description of operation requiring context
            
        Returns:
            Active tenant context
            
        Raises:
            TenantIsolationError: If no context is available
        """
        if not self._active_context:
            raise TenantIsolationError(
                f"Tenant context required for {operation} but none is available"
            )
        
        return self._active_context
    
    def push_context(self, context: TenantContext) -> None:
        """Push context onto stack (for nested operations)"""
        context.validate()
        self._context_stack.append(self._active_context)
        self._active_context = context
        logger.debug(f"Tenant context pushed: {context.tenant_id}")
    
    def pop_context(self) -> TenantContext:
        """Pop context from stack"""
        if not self._context_stack:
            raise TenantIsolationError("Cannot pop context: stack is empty")
        
        old_context = self._active_context
        self._active_context = self._context_stack.pop()
        logger.debug(f"Tenant context popped: {old_context.tenant_id} -> {self._active_context.tenant_id}")
        return old_context
    
    def clear_context(self) -> None:
        """Clear all tenant context"""
        self._active_context = None
        self._context_stack.clear()
        logger.debug("Tenant context cleared")


# Global tenant context manager
_tenant_manager: Optional[TenantContextManager] = None


def get_tenant_manager() -> TenantContextManager:
    """Get the global tenant context manager"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantContextManager()
    return _tenant_manager


def require_tenant_context(operation: str = "operation") -> TenantContext:
    """
    Convenience function to require tenant context
    
    Args:
        operation: Description of operation requiring context
        
    Returns:
        Active tenant context
        
    Raises:
        TenantIsolationError: If no context is available
    """
    return get_tenant_manager().require_context(operation)


def set_tenant_context(context: TenantContext) -> None:
    """Convenience function to set tenant context"""
    get_tenant_manager().set_context(context)


def get_tenant_context() -> Optional[TenantContext]:
    """Convenience function to get tenant context"""
    return get_tenant_manager().get_context()


class TenantScopedOperations:
    """
    Base class for tenant-scoped operations
    
    Enforces tenant isolation at the operation level
    """
    
    def __init__(self):
        self.tenant_manager = get_tenant_manager()
    
    def _require_tenant_context(self, operation: str) -> TenantContext:
        """Require tenant context for operation"""
        return self.tenant_manager.require_context(operation)
    
    def _validate_tenant_access(self, target_tenant_id: str, operation: str) -> None:
        """
        Validate that current tenant context can access target tenant
        
        Args:
            target_tenant_id: Target tenant ID
            operation: Description of operation
            
        Raises:
            TenantIsolationError: If access is not allowed
        """
        context = self._require_tenant_context(operation)
        
        if context.tenant_id != target_tenant_id:
            raise TenantIsolationError(
                f"Tenant isolation violation: {context.tenant_id} cannot {operation} "
                f"tenant {target_tenant_id}"
            )
    
    def _tenant_scoped_key(self, base_key: str) -> str:
        """
        Generate tenant-scoped key for storage operations
        
        Args:
            base_key: Base key without tenant prefix
            
        Returns:
            Tenant-scoped key
        """
        context = self._require_tenant_context("key generation")
        return f"{context.tenant_id}:{base_key}"
    
    def _tenant_scoped_subject(self, base_subject: str) -> str:
        """
        Generate tenant-scoped subject for messaging
        
        Args:
            base_subject: Base subject without tenant prefix
            
        Returns:
            Tenant-scoped subject
        """
        context = self._require_tenant_context("subject generation")
        return f"exoarmur.{context.tenant_id}.{base_subject}"


class TenantScopedKVStore(TenantScopedOperations):
    """
    Tenant-scoped key-value store operations
    
    Enforces tenant isolation at the KV level
    """
    
    def __init__(self, kv_store):
        super().__init__()
        self.kv_store = kv_store
    
    async def get(self, key: str) -> Any:
        """Get value with tenant scoping"""
        tenant_key = self._tenant_scoped_key(key)
        context = self._require_tenant_context("KV get")
        
        logger.debug(f"KV get: {tenant_key} for tenant {context.tenant_id}")
        return await self.kv_store.get(tenant_key)
    
    async def put(self, key: str, value: Any) -> None:
        """Put value with tenant scoping"""
        tenant_key = self._tenant_scoped_key(key)
        context = self._require_tenant_context("KV put")
        
        logger.debug(f"KV put: {tenant_key} for tenant {context.tenant_id}")
        await self.kv_store.put(tenant_key, value)
    
    async def delete(self, key: str) -> None:
        """Delete value with tenant scoping"""
        tenant_key = self._tenant_scoped_key(key)
        context = self._require_tenant_context("KV delete")
        
        logger.debug(f"KV delete: {tenant_key} for tenant {context.tenant_id}")
        await self.kv_store.delete(tenant_key)


class TenantScopedStream(TenantScopedOperations):
    """
    Tenant-scoped stream operations
    
    Enforces tenant isolation at the stream level
    """
    
    def __init__(self, stream_manager):
        super().__init__()
        self.stream_manager = stream_manager
    
    def get_stream_name(self, base_name: str) -> str:
        """Get tenant-scoped stream name"""
        context = self._require_tenant_context("stream access")
        return f"EXOARMUR_{context.tenant_id.upper()}_{base_name.upper()}"
    
    def get_subject(self, base_subject: str) -> str:
        """Get tenant-scoped subject"""
        return self._tenant_scoped_subject(base_subject)
    
    async def publish(self, subject: str, data: Any) -> None:
        """Publish with tenant scoping"""
        tenant_subject = self.get_subject(subject)
        context = self._require_tenant_context("publish")
        
        logger.debug(f"Publish: {tenant_subject} for tenant {context.tenant_id}")
        await self.stream_manager.publish(tenant_subject, data)
    
    async def subscribe(self, subject: str, handler: callable) -> None:
        """Subscribe with tenant scoping"""
        tenant_subject = self.get_subject(subject)
        context = self._require_tenant_context("subscribe")
        
        logger.debug(f"Subscribe: {tenant_subject} for tenant {context.tenant_id}")
        await self.stream_manager.subscribe(tenant_subject, handler)


# Decorator for functions requiring tenant context
def requires_tenant_context(operation: str = "operation"):
    """
    Decorator to require tenant context for functions
    
    Args:
        operation: Description of operation requiring context
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Ensure tenant context exists
            require_tenant_context(operation)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Decorator for tenant-scoped functions
def tenant_scoped(operation: str = "operation"):
    """
    Decorator for tenant-scoped operations
    
    Automatically extracts tenant context and validates access
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = require_tenant_context(operation)
            
            # Add context to kwargs if function expects it
            if 'tenant_context' in func.__code__.co_varnames:
                kwargs['tenant_context'] = context
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
