"""
Feature Flags Implementation for ExoArmur ADMO V2
Controls activation of V2 capabilities while preserving V1 functionality
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlagContext:
    """Context for feature flag evaluation"""
    cell_id: str
    tenant_id: str
    environment: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class FeatureFlags:
    """Feature flag system for V2 capability control"""
    
    def __init__(self):
        self._flags: Dict[str, Dict[str, Any]] = {}
        self._config_loaded = False
        self._load_default_flags()
        self._load_configuration()
    
    def _load_default_flags(self):
        """Load default V2 feature flag definitions"""
        self._flags = {
            'v2_federation_enabled': {
                'description': 'Enable multi-cell federation capabilities',
                'default_value': False,
                'current_value': False,
                'rollout_strategy': 'disabled',
                'dependencies': [],
                'risk_level': 'medium',
                'owner': 'federation_team'
            },
            'v2_control_plane_enabled': {
                'description': 'Enable operator control plane and approval workflows',
                'default_value': False,
                'current_value': False,
                'rollout_strategy': 'disabled',
                'dependencies': ['v2_federation_enabled'],
                'risk_level': 'high',
                'owner': 'control_plane_team'
            },
            'v2_operator_approval_required': {
                'description': 'Require operator approval for A3 actions',
                'default_value': False,
                'current_value': False,
                'rollout_strategy': 'disabled',
                'dependencies': ['v2_control_plane_enabled'],
                'risk_level': 'high',
                'owner': 'safety_team'
            },
            'v2_federation_identity_enabled': {
                'description': 'Enable federation identity and trust management',
                'default_value': False,
                'current_value': False,
                'rollout_strategy': 'disabled',
                'dependencies': ['v2_federation_enabled'],
                'risk_level': 'medium',
                'owner': 'security_team'
            },
            'v2_audit_federation_enabled': {
                'description': 'Enable cross-cell audit consolidation',
                'default_value': False,
                'current_value': False,
                'rollout_strategy': 'disabled',
                'dependencies': ['v2_federation_enabled'],
                'risk_level': 'low',
                'owner': 'audit_team'
            }
        }
    
    def _load_configuration(self):
        """Load feature flag configuration from environment and files"""
        # Load from environment variables
        for flag_key in self._flags:
            env_value = os.getenv(f'EXOARMUR_FLAG_{flag_key.upper()}')
            if env_value is not None:
                self._flags[flag_key]['current_value'] = env_value.lower() in ('true', '1', 'yes', 'on')
        
        # Load from configuration file if exists
        config_file = os.getenv('EXOARMUR_FEATURE_FLAGS_CONFIG', '/etc/exoarmur/feature_flags.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    for flag_key, flag_config in file_config.items():
                        if flag_key in self._flags:
                            self._flags[flag_key].update(flag_config)
                logger.info(f"Loaded feature flags from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load feature flags from {config_file}: {e}")
        
        self._config_loaded = True
        self._log_flag_status()
    
    def _log_flag_status(self):
        """Log current feature flag status"""
        enabled_flags = [key for key, config in self._flags.items() if config['current_value']]
        logger.info(f"Feature flags loaded. Enabled: {enabled_flags}")
        logger.info(f"V2 Federation: {'ENABLED' if self.is_enabled('v2_federation_enabled') else 'DISABLED'}")
        logger.info(f"V2 Control Plane: {'ENABLED' if self.is_enabled('v2_control_plane_enabled') else 'DISABLED'}")
    
    def is_enabled(self, flag_key: str, context: Optional[FeatureFlagContext] = None) -> bool:
        """
        Check if a feature flag is enabled
        
        Args:
            flag_key: Feature flag key
            context: Optional context for conditional evaluation
            
        Returns:
            True if flag is enabled, False otherwise
        """
        if not self._config_loaded:
            logger.warning("Feature flags not loaded, returning False")
            return False
        
        if flag_key not in self._flags:
            logger.warning(f"Unknown feature flag: {flag_key}")
            return False
        
        flag_config = self._flags[flag_key]
        
        # Check if flag is currently enabled
        if not flag_config['current_value']:
            return False
        
        # Check dependencies
        for dependency in flag_config['dependencies']:
            if not self.is_enabled(dependency, context):
                logger.debug(f"Feature flag {flag_key} disabled due to dependency {dependency}")
                return False
        
        # TODO: Add conditional evaluation based on context when needed
        # For now, simple boolean evaluation
        
        return True
    
    def get_flag_info(self, flag_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a feature flag"""
        return self._flags.get(flag_key)
    
    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature flag configurations"""
        return self._flags.copy()
    
    def is_v2_federation_enabled(self, context: Optional[FeatureFlagContext] = None) -> bool:
        """Convenience method to check if V2 federation is enabled"""
        return self.is_enabled('v2_federation_enabled', context)
    
    def is_v2_control_plane_enabled(self, context: Optional[FeatureFlagContext] = None) -> bool:
        """Convenience method to check if V2 control plane is enabled"""
        return self.is_enabled('v2_control_plane_enabled', context)
    
    def is_v2_operator_approval_required(self, context: Optional[FeatureFlagContext] = None) -> bool:
        """Convenience method to check if V2 operator approval is required"""
        return self.is_enabled('v2_operator_approval_required', context)


# Global feature flags instance
_feature_flags_instance: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance"""
    global _feature_flags_instance
    if _feature_flags_instance is None:
        _feature_flags_instance = FeatureFlags()
    return _feature_flags_instance


def is_v2_federation_enabled(context: Optional[FeatureFlagContext] = None) -> bool:
    """Check if V2 federation is enabled (convenience function)"""
    return get_feature_flags().is_v2_federation_enabled(context)


def is_v2_control_plane_enabled(context: Optional[FeatureFlagContext] = None) -> bool:
    """Check if V2 control plane is enabled (convenience function)"""
    return get_feature_flags().is_v2_control_plane_enabled(context)


def is_v2_operator_approval_required(context: Optional[FeatureFlagContext] = None) -> bool:
    """Check if V2 operator approval is required (convenience function)"""
    return get_feature_flags().is_v2_operator_approval_required(context)
