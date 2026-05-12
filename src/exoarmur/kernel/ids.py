"""
ID factory for deterministic identifier generation.

Provides a unified interface for generating deterministic ULIDs and
other identifiers that are consistent across replay and testing.
"""

import hashlib
import json
import ulid
from typing import Any, Dict, Optional
from datetime import datetime


class IDFactory:
    """Deterministic ID factory for generating consistent identifiers."""
    
    def __init__(self, seed: Optional[str] = None):
        """Initialize ID factory with optional seed."""
        self._seed = seed or "exoarmur-default"
    
    def make_id(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Generate deterministic ID for given kind and payload."""
        if payload is None:
            payload = {}
        
        # Create canonical input for hash
        canonical_input = {
            "seed": self._seed,
            "kind": kind,
            "payload": payload
        }
        
        # Generate canonical JSON
        canonical = json.dumps(
            canonical_input,
            sort_keys=True,
            separators=(",", ":"),
            default=str
        )
        
        # Create SHA-256 hash
        digest = hashlib.sha256(canonical.encode("utf-8")).digest()
        
        # Generate ULID from hash bytes
        return str(ulid.ULID.from_bytes(digest[:16]))
    
    def make_intent_id(self, actor_id: str, action_type: str, target: str, 
                      timestamp: Optional[datetime] = None) -> str:
        """Generate deterministic intent ID."""
        payload = {
            "actor_id": actor_id,
            "action_type": action_type,
            "target": target
        }
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        return self.make_id("intent", payload)
    
    def make_decision_id(self, intent_id: str, policy_version: Optional[str] = None) -> str:
        """Generate deterministic policy decision ID."""
        payload = {
            "intent_id": intent_id
        }
        if policy_version:
            payload["policy_version"] = policy_version
        
        return self.make_id("decision", payload)
    
    def make_trace_id(self, intent_id: str) -> str:
        """Generate deterministic execution trace ID."""
        payload = {
            "intent_id": intent_id
        }
        return self.make_id("trace", payload)
    
    def make_event_id(self, trace_id: str, stage: str, sequence: int) -> str:
        """Generate deterministic trace event ID."""
        payload = {
            "trace_id": trace_id,
            "stage": stage,
            "sequence": sequence
        }
        return self.make_id("event", payload)
    
    def make_dispatch_id(self, intent_id: str) -> str:
        """Generate deterministic execution dispatch ID."""
        payload = {
            "intent_id": intent_id
        }
        return self.make_id("dispatch", payload)
    
    def make_bundle_id(self, intent_id: str, replay_hash: str) -> str:
        """Generate deterministic proof bundle ID."""
        payload = {
            "intent_id": intent_id,
            "replay_hash": replay_hash
        }
        return self.make_id("bundle", payload)
    
    def make_audit_id(self, intent_id: str, event_type: str, outcome: str, 
                     details: Optional[Dict[str, Any]] = None) -> str:
        """Generate deterministic audit ID."""
        if details is None:
            details = {}
        
        payload = {
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details
        }
        return self.make_id("audit", payload)


# Global ID factory instance
_id_factory: Optional[IDFactory] = None


def get_id_factory() -> IDFactory:
    """Get global ID factory instance."""
    global _id_factory
    if _id_factory is None:
        _id_factory = IDFactory()
    return _id_factory


def set_id_factory(factory: IDFactory) -> None:
    """Set global ID factory instance."""
    global _id_factory
    _id_factory = factory


def make_id(kind: str, payload: Optional[Dict[str, Any]] = None) -> str:
    """Generate deterministic ID using global factory."""
    return get_id_factory().make_id(kind, payload)


def make_intent_id(actor_id: str, action_type: str, target: str, 
                  timestamp: Optional[datetime] = None) -> str:
    """Generate deterministic intent ID using global factory."""
    return get_id_factory().make_intent_id(actor_id, action_type, target, timestamp)


def make_decision_id(intent_id: str, policy_version: Optional[str] = None) -> str:
    """Generate deterministic decision ID using global factory."""
    return get_id_factory().make_decision_id(intent_id, policy_version)


def make_trace_id(intent_id: str) -> str:
    """Generate deterministic trace ID using global factory."""
    return get_id_factory().make_trace_id(intent_id)


def make_event_id(trace_id: str, stage: str, sequence: int) -> str:
    """Generate deterministic event ID using global factory."""
    return get_id_factory().make_event_id(trace_id, stage, sequence)


def make_dispatch_id(intent_id: str) -> str:
    """Generate deterministic dispatch ID using global factory."""
    return get_id_factory().make_dispatch_id(intent_id)


def make_bundle_id(intent_id: str, replay_hash: str) -> str:
    """Generate deterministic bundle ID using global factory."""
    return get_id_factory().make_bundle_id(intent_id, replay_hash)


def make_audit_id(intent_id: str, event_type: str, outcome: str, 
                 details: Optional[Dict[str, Any]] = None) -> str:
    """Generate deterministic audit ID using global factory."""
    return get_id_factory().make_audit_id(intent_id, event_type, outcome, details)
