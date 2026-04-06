"""
ActionIntent model for execution governance boundary.

Canonical action intent envelope for execution governance.
Note: intent_id will be deterministically derived in later phases.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from exoarmur.clock import utc_now
from exoarmur.ids import make_intent_id


class ActionIntent(BaseModel):
    """Canonical action intent envelope for execution governance.
    
    Note: intent_id will be deterministically derived in later phases.
    For Phase 1, this is a placeholder schema without canonicalization.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    intent_id: str = Field(description="Intent identifier (deterministic ULID)")
    actor_id: str = Field(description="Actor identifier")
    actor_type: str = Field(description="Actor type (e.g., 'agent', 'human', 'automation')")
    action_type: str = Field(description="Type of action to execute")
    target: str = Field(description="Target specification")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    safety_context: Dict[str, Any] = Field(default_factory=dict, description="Safety evaluation context")
    timestamp: datetime = Field(description="Intent creation timestamp")
    tenant_id: str = Field(default="", description="Tenant identifier for multi-tenant isolation")
    cell_id: str = Field(default="", description="Cell identifier for multi-cell isolation")
    
    @classmethod
    def create(cls, actor_id: str, actor_type: str, action_type: str, target: str,
               parameters: Optional[Dict[str, Any]] = None,
               safety_context: Optional[Dict[str, Any]] = None,
               tenant_id: str = "", cell_id: str = "") -> "ActionIntent":
        """Create ActionIntent with deterministic ID and timestamp."""
        if parameters is None:
            parameters = {}
        if safety_context is None:
            safety_context = {}
        
        timestamp = utc_now()
        intent_id = make_intent_id(actor_id, action_type, target, timestamp)
        
        return cls(
            intent_id=intent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action_type=action_type,
            target=target,
            parameters=parameters,
            safety_context=safety_context,
            timestamp=timestamp,
            tenant_id=tenant_id,
            cell_id=cell_id
        )
