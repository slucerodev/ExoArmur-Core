"""
Auth module initialization
"""

from .auth_service import (
    AuthError,
    Permission,
    APIKey,
    AuthContext,
    APIKeyStore,
    AuthService,
    get_auth_service,
    requires_auth,
    create_api_key,
    revoke_api_key,
    _auth_service  # Export for testing
)

__all__ = [
    "AuthError",
    "Permission",
    "APIKey",
    "AuthContext",
    "APIKeyStore",
    "AuthService",
    "get_auth_service",
    "requires_auth",
    "create_api_key",
    "revoke_api_key",
    "_auth_service"
]
