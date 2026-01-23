"""
Feature Flag Configuration for ExoArmur ADMO V2
Configuration management and validation for feature flags
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlagDefinition:
    """Definition of a feature flag"""
    key: str
    description: str
    default_value: bool
    rollout_strategy: str
    dependencies: List[str]
    risk_level: str
    owner: str


class FeatureFlagConfig:
    """Configuration management for feature flags"""
    
    def __init__(self):
        self.definitions = self._load_definitions()
    
    def _load_definitions(self) -> Dict[str, FeatureFlagDefinition]:
        """Load feature flag definitions from contracts"""
        definitions = {}
        
        # V2 Federation
        definitions['v2_federation_enabled'] = FeatureFlagDefinition(
            key='v2_federation_enabled',
            description='Enable multi-cell federation capabilities',
            default_value=False,
            rollout_strategy='disabled',
            dependencies=[],
            risk_level='medium',
            owner='federation_team'
        )
        
        # V2 Control Plane
        definitions['v2_control_plane_enabled'] = FeatureFlagDefinition(
            key='v2_control_plane_enabled',
            description='Enable operator control plane and approval workflows',
            default_value=False,
            rollout_strategy='disabled',
            dependencies=['v2_federation_enabled'],
            risk_level='high',
            owner='control_plane_team'
        )
        
        # V2 Operator Approval
        definitions['v2_operator_approval_required'] = FeatureFlagDefinition(
            key='v2_operator_approval_required',
            description='Require operator approval for A3 actions',
            default_value=False,
            rollout_strategy='disabled',
            dependencies=['v2_control_plane_enabled'],
            risk_level='high',
            owner='safety_team'
        )
        
        # V2 Federation Identity
        definitions['v2_federation_identity_enabled'] = FeatureFlagDefinition(
            key='v2_federation_identity_enabled',
            description='Enable federation identity and trust management',
            default_value=False,
            rollout_strategy='disabled',
            dependencies=['v2_federation_enabled'],
            risk_level='medium',
            owner='security_team'
        )
        
        # V2 Audit Federation
        definitions['v2_audit_federation_enabled'] = FeatureFlagDefinition(
            key='v2_audit_federation_enabled',
            description='Enable cross-cell audit consolidation',
            default_value=False,
            rollout_strategy='disabled',
            dependencies=['v2_federation_enabled'],
            risk_level='low',
            owner='audit_team'
        )
        
        return definitions
    
    def validate_dependencies(self, flag_key: str, enabled_flags: Dict[str, bool]) -> bool:
        """Validate that all dependencies are satisfied for a flag"""
        if flag_key not in self.definitions:
            return False
        
        definition = self.definitions[flag_key]
        for dependency in definition.dependencies:
            if not enabled_flags.get(dependency, False):
                logger.warning(f"Feature flag {flag_key} dependency {dependency} not satisfied")
                return False
        
        return True
    
    def get_definition(self, flag_key: str) -> Optional[FeatureFlagDefinition]:
        """Get definition for a specific flag"""
        return self.definitions.get(flag_key)
    
    def get_all_definitions(self) -> Dict[str, FeatureFlagDefinition]:
        """Get all feature flag definitions"""
        return self.definitions.copy()
    
    def validate_flag_value(self, flag_key: str, value: bool) -> bool:
        """Validate a flag value change"""
        if flag_key not in self.definitions:
            logger.error(f"Unknown feature flag: {flag_key}")
            return False
        
        # For now, all boolean values are valid
        # Could add more complex validation logic here
        return True
    
    def load_from_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        if not os.path.exists(config_path):
            logger.warning(f"Feature flag config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load feature flag config from {config_path}: {e}")
            return {}
    
    def load_from_environment(self) -> Dict[str, bool]:
        """Load configuration from environment variables"""
        config = {}
        
        for flag_key in self.definitions:
            env_var = f'EXOARMUR_FLAG_{flag_key.upper()}'
            env_value = os.getenv(env_var)
            if env_value is not None:
                config[flag_key] = env_value.lower() in ('true', '1', 'yes', 'on')
        
        return config
