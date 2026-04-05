"""
Intervention system for counterfactual replay.

Provides mechanisms to modify audit records for counterfactual analysis.
"""

import copy
from typing import Any
from dataclasses import dataclass

from spec.contracts.models_v1 import AuditRecordV1


@dataclass
class Intervention:
    """Represents a counterfactual intervention on an audit record."""
    
    field_path: str  # Dot-notation path to the field being modified, e.g. "payload.actor_id"
    original_value: Any  # The original value
    counterfactual_value: Any  # The value to substitute
    rationale: str  # Human readable explanation of what this intervention represents


def apply_intervention(record: AuditRecordV1, intervention: Intervention) -> AuditRecordV1:
    """
    Apply an intervention to an audit record.
    
    Args:
        record: Original audit record
        intervention: Intervention to apply
        
    Returns:
        Modified audit record with the intervention applied
    """
    # Make a deep copy to avoid modifying the original
    modified_record = copy.deepcopy(record)
    
    # Navigate to the target field using dot notation
    current_obj = modified_record
    path_parts = intervention.field_path.split('.')
    
    # Navigate to the parent of the target field
    for part in path_parts[:-1]:
        if hasattr(current_obj, part):
            current_obj = getattr(current_obj, part)
        elif isinstance(current_obj, dict) and part in current_obj:
            current_obj = current_obj[part]
        else:
            raise ValueError(f"Cannot navigate to field path: {intervention.field_path}")
    
    # Set the target field
    target_field = path_parts[-1]
    if hasattr(current_obj, target_field):
        setattr(current_obj, target_field, intervention.counterfactual_value)
    elif isinstance(current_obj, dict) and target_field in current_obj:
        current_obj[target_field] = intervention.counterfactual_value
    else:
        raise ValueError(f"Cannot set field: {target_field} in path: {intervention.field_path}")
    
    return modified_record
