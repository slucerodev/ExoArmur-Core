"""
ExoArmur ADMO V2 Federation Handshake Context
Dependency injection container for handshake operations
"""

from typing import Optional
from dataclasses import dataclass

from .clock import Clock
from .federate_identity_store import FederateIdentityStore
from .crypto import VerificationResult
from .messages import FederationSignedMessage
from .protocol_enforcer import ProtocolEnforcer


@dataclass
class HandshakeContext:
    """Context for federation handshake operations"""
    
    identity_store: FederateIdentityStore
    clock: Clock
    protocol_enforcer: ProtocolEnforcer
    
    def verify_signed_message(self, message: FederationSignedMessage) -> tuple:
        """
        Centralized verification function
        
        Args:
            message: Message to verify
            
        Returns:
            Tuple of (success, failure_reason, audit_event)
        """
        return self.protocol_enforcer.verify_handshake_message(message)
    
    def create_handshake_controller(self, config=None):
        """
        Create a handshake controller using this context
        
        Args:
            config: Optional configuration override
            
        Returns:
            HandshakeController instance
        """
        from .handshake_controller import HandshakeController
        return HandshakeController(self, self.clock, config)


@dataclass
class VerificationResult:
    """Result of message verification"""
    
    success: bool
    failure_reason: Optional[str] = None
    audit_event: Optional[dict] = None
    
    @classmethod
    def success_result(cls, audit_event: dict) -> 'VerificationResult':
        """Create successful verification result"""
        return cls(success=True, audit_event=audit_event)
    
    @classmethod
    def failure_result(cls, failure_reason: str, audit_event: dict) -> 'VerificationResult':
        """Create failed verification result"""
        return cls(success=False, failure_reason=failure_reason, audit_event=audit_event)
