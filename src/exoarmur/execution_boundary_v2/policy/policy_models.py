"""
Policy models for execution governance boundary.

Defines policy rule structures and related data models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """Policy rule definition for ActionIntent evaluation."""
    
    rule_id: str = Field(description="Unique identifier for the policy rule")
    description: str = Field(description="Human-readable description of the rule")
    allowed_domains: Optional[List[str]] = Field(
        default=None,
        description="List of allowed domains. If None, all domains are allowed."
    )
    allowed_methods: Optional[List[str]] = Field(
        default=None,
        description="List of allowed HTTP methods. If None, all methods are allowed."
    )
    require_approval: bool = Field(
        default=False,
        description="Whether this rule requires explicit approval for execution."
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant policy isolation."
    )
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        str_strip_whitespace = True