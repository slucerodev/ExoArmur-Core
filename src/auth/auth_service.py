"""
Minimal Authentication/Authorization - Phase 5 Operational Safety Hardening
Implements API key authentication for execution-triggering endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication/authorization fails"""
    pass


class Permission(str, Enum):
    """Permission types for authorization"""
    # Execution permissions
    EXECUTE_A0 = "execute:A0"  # Observe actions
    EXECUTE_A1 = "execute:A1"  # Soft containment
    EXECUTE_A2 = "execute:A2"  # Hard containment
    EXECUTE_A3 = "execute:A3"  # Irreversible actions
    
    # Approval permissions
    REQUEST_APPROVAL = "approval:request"
    GRANT_APPROVAL = "approval:grant"
    DENY_APPROVAL = "approval:deny"
    
    # Management permissions
    VIEW_STATUS = "status:view"
    MANAGE_KILL_SWITCH = "kill_switch:manage"
    MANAGE_TENANTS = "tenant:manage"


@dataclass
class APIKey:
    """API key for authentication"""
    key_id: str
    key_hash: str  # SHA-256 hash of the actual key
    tenant_ids: List[str]  # Tenants this key can access
    permissions: Set[Permission]  # Permissions granted
    principal_id: str  # Who owns this key
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    description: Optional[str] = None
    last_used_at: Optional[datetime] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if key has specific permission"""
        return permission in self.permissions
    
    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if key can access specific tenant"""
        return tenant_id in self.tenant_ids
    
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()


@dataclass
class AuthContext:
    """Authentication context after successful auth"""
    api_key: APIKey
    tenant_id: str  # Tenant being accessed in this request
    principal_id: str
    permissions: Set[Permission]
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


class APIKeyStore:
    """In-memory API key store for testing"""
    
    def __init__(self):
        self.keys: Dict[str, APIKey] = {}
        self.key_hashes: Dict[str, str] = {}  # hash -> key_id mapping
    
    def create_key(
        self,
        key_id: str,
        tenant_ids: List[str],
        permissions: List[Permission],
        principal_id: str,
        expires_at: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> str:
        """Create new API key and return the actual key value"""
        # Generate random key
        actual_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            tenant_ids=tenant_ids,
            permissions=set(permissions),
            principal_id=principal_id,
            expires_at=expires_at,
            description=description
        )
        
        self.keys[key_id] = api_key
        self.key_hashes[key_hash] = key_id
        
        logger.info(f"Created API key {key_id} for principal {principal_id}")
        return actual_key
    
    def get_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash"""
        key_id = self.key_hashes.get(key_hash)
        if key_id is None:
            return None
        return self.keys.get(key_id)
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id not in self.keys:
            return False
        
        key = self.keys[key_id]
        key.is_active = False
        
        # Remove from hash mapping
        if key.key_hash in self.key_hashes:
            del self.key_hashes[key.key_hash]
        
        logger.info(f"Revoked API key {key_id}")
        return True
    
    def update_last_used(self, key_hash: str) -> None:
        """Update last used timestamp"""
        key = self.get_key_by_hash(key_hash)
        if key:
            key.last_used_at = datetime.now(timezone.utc)


class AuthService:
    """
    Authentication and authorization service
    
    Rule R5: AUTHN/Z required for execution-triggering endpoints
    """
    
    def __init__(self, key_store: Optional[APIKeyStore] = None):
        self.key_store = key_store or APIKeyStore()
        logger.info("AuthService initialized")
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage/comparison"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def authenticate(self, api_key: str) -> AuthContext:
        """
        Authenticate API key and return context
        
        Args:
            api_key: API key string from request
            
        Returns:
            Authentication context
            
        Raises:
            AuthError: If authentication fails
        """
        if not api_key:
            raise AuthError("Missing API key")
        
        key_hash = self.hash_api_key(api_key)
        stored_key = self.key_store.get_key_by_hash(key_hash)
        
        if not stored_key:
            raise AuthError("Invalid API key")
        
        if not stored_key.is_valid():
            if not stored_key.is_active:
                raise AuthError("API key is inactive")
            else:
                raise AuthError("API key has expired")
        
        # Update last used
        self.key_store.update_last_used(key_hash)
        
        logger.debug(f"Authenticated API key {stored_key.key_id} for principal {stored_key.principal_id}")
        
        # Return context (tenant_id will be set during authorization)
        return AuthContext(
            api_key=stored_key,
            tenant_id="",  # Will be set during authorization
            principal_id=stored_key.principal_id,
            permissions=stored_key.permissions
        )
    
    async def authorize(
        self,
        auth_context: AuthContext,
        required_permission: Permission,
        tenant_id: str
    ) -> AuthContext:
        """
        Authorize request for specific tenant and permission
        
        Args:
            auth_context: Authentication context
            required_permission: Permission required
            tenant_id: Tenant being accessed
            
        Returns:
            Updated authentication context
            
        Raises:
            AuthError: If authorization fails
        """
        # Check tenant access
        if not auth_context.api_key.can_access_tenant(tenant_id):
            raise AuthError(f"API key not authorized for tenant {tenant_id}")
        
        # Check permission
        if not auth_context.api_key.has_permission(required_permission):
            raise AuthError(f"API key missing required permission: {required_permission}")
        
        # Update context with tenant
        auth_context.tenant_id = tenant_id
        
        logger.debug(f"Authorized {auth_context.principal_id} for {required_permission} on tenant {tenant_id}")
        
        return auth_context
    
    async def authenticate_and_authorize(
        self,
        api_key: str,
        required_permission: Permission,
        tenant_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AuthContext:
        """
        Combined authenticate and authorize
        
        Args:
            api_key: API key string
            required_permission: Permission required
            tenant_id: Tenant being accessed
            correlation_id: Correlation ID
            trace_id: Trace ID
            
        Returns:
            Authentication and authorization context
            
        Raises:
            AuthError: If auth or authz fails
        """
        # Authenticate
        auth_context = await self.authenticate(api_key)
        
        # Add correlation/trace IDs
        auth_context.correlation_id = correlation_id
        auth_context.trace_id = trace_id
        
        # Authorize
        auth_context = await self.authorize(auth_context, required_permission, tenant_id)
        
        return auth_context


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# Decorator for authenticated endpoints
def requires_auth(required_permission: Permission):
    """
    Decorator for endpoints requiring authentication and authorization
    
    Args:
        required_permission: Permission required for this endpoint
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract API key and tenant_id from kwargs or request
            api_key = kwargs.get('api_key')
            tenant_id = kwargs.get('tenant_id')
            correlation_id = kwargs.get('correlation_id')
            trace_id = kwargs.get('trace_id')
            
            if not api_key:
                raise AuthError("Missing API key")
            
            if not tenant_id:
                raise AuthError("Missing tenant_id")
            
            # Authenticate and authorize
            auth_service = get_auth_service()
            auth_context = await auth_service.authenticate_and_authorize(
                api_key=api_key,
                required_permission=required_permission,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Add auth context to kwargs
            kwargs['auth_context'] = auth_context
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for common operations
async def create_api_key(
    key_id: str,
    tenant_ids: List[str],
    permissions: List[Permission],
    principal_id: str,
    expires_at: Optional[datetime] = None,
    description: Optional[str] = None
) -> str:
    """Create new API key"""
    auth_service = get_auth_service()
    return auth_service.key_store.create_key(
        key_id=key_id,
        tenant_ids=tenant_ids,
        permissions=permissions,
        principal_id=principal_id,
        expires_at=expires_at,
        description=description
    )


async def revoke_api_key(key_id: str) -> bool:
    """Revoke API key"""
    auth_service = get_auth_service()
    return auth_service.key_store.revoke_key(key_id)
