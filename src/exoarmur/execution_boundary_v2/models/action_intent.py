"""
ActionIntent model for execution governance boundary.

Canonical action intent envelope for execution governance.
Note: intent_id will be deterministically derived in later phases.
"""

from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class ActionIntent(BaseModel):
    """Canonical action intent envelope for execution governance.
    
    Note: intent_id will be deterministically derived in later phases.
    For Phase 1, this is a placeholder schema without canonicalization.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    intent_id: str = Field(description="Intent identifier (will be deterministic ULID in later phases)")
    actor_id: str = Field(description="Actor identifier")
    actor_type: str = Field(description="Actor type (e.g., 'agent', 'human', 'automation')")
    action_type: str = Field(description="Type of action to execute")
    target: str = Field(description="Target specification")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    safety_context: Dict[str, Any] = Field(default_factory=dict, description="Safety evaluation context")
    timestamp: datetime = Field(description="Intent creation timestamp")
    tenant_id: str = Field(default="", description="Tenant identifier for multi-tenant isolation")
    cell_id: str = Field(default="", description="Cell identifier for multi-cell isolation")
