"""
ExoArmur ADMO V2 Federation Manager
Multi-cell federation coordination - Phase 2 implementation
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    import nats
    from nats.js.api import StreamConfig
except ImportError:
    nats = None

from .federation_identity_manager import FederationIdentityManager, HandshakeConfig
from .audit_interface import AuditInterface

# Import Phase Gate for strict Phase isolation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.phase_gate import PhaseGate

logger = logging.getLogger(__name__)


@dataclass
class FederationConfig:
    """Federation configuration"""
    enabled: bool = False
    federation_id: Optional[str] = None
    cell_id: Optional[str] = None
    member_cells: List[str] = field(default_factory=list)
    nats_url: str = "nats://localhost:4222"
    heartbeat_interval: int = 30  # seconds
    jetstream_enabled: bool = True


@dataclass
class FederationMember:
    """Federation member information"""
    cell_id: str
    status: str  # "active", "inactive", "suspended", "decommissioned"
    last_heartbeat: datetime
    capabilities: List[str] = field(default_factory=list)
    trust_score: float = 0.8
    role: str = "member"  # "member", "coordinator", "observer"


class FederationManager:
    """Federation management and coordination - Phase 2 implementation"""
    
    def __init__(self, config: Optional[FederationConfig] = None):
        self.config = config or FederationConfig()
        self._initialized = False
        self._nc = None  # NATS connection
        self._js = None   # JetStream context
        self._heartbeat_task = None
        self._membership: Dict[str, FederationMember] = {}
        self._federation_id: Optional[str] = None
        self._shutdown_event = asyncio.Event()
        
        # V2 identity manager (Phase 2)
        self._identity_manager: Optional[FederationIdentityManager] = None
        
        if self.config.enabled:
            logger.info(f"FederationManager: enabled=True for cell {self.config.cell_id}")
        else:
            logger.debug("FederationManager: scaffolding mode (enabled=False)")
    
    async def initialize(self) -> None:
        """Initialize federation manager"""
        if not self.config.enabled:
            logger.debug("FederationManager.initialize() - no-op (scaffolding)")
            return
        
        # Phase Gate enforcement: enabled=True requires explicit Phase 2 gate
        PhaseGate.check_phase_2_eligibility("FederationManager")
        
        # Initialize V2 identity manager if feature flag is enabled
        await self._initialize_identity_manager()
        
        if not nats:
            raise ImportError("nats-py package required for federation functionality")
        
        try:
            # Connect to NATS
            self._nc = await nats.connect(self.config.nats_url)
            logger.info(f"Connected to NATS at {self.config.nats_url}")
            
            # Get JetStream context if enabled
            if self.config.jetstream_enabled:
                self._js = self._nc.jetstream()
                await self._setup_streams()
            
            # Subscribe to federation subjects
            await self._setup_subscriptions()
            
            # Generate or use provided federation ID
            self._federation_id = self.config.federation_id or str(uuid.uuid4())
            
            # Start heartbeat task
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self._initialized = True
            logger.info(f"FederationManager initialized for cell {self.config.cell_id}")
            
        except Exception as e:
            logger.error(f"FederationManager initialization failed: {e}")
            raise
    
    async def _setup_streams(self) -> None:
        """Setup JetStream streams for federation"""
        if not self._js:
            return
        
        try:
            # Check if stream already exists
            try:
                await self._js.stream_info("federation_membership")
                logger.debug("Federation membership stream already exists")
                return
            except:
                pass  # Stream doesn't exist, create it
            
            # Federation membership stream with proper StreamConfig
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType, DiscardPolicy
            
            stream_config = StreamConfig(
                name="federation_membership",
                subjects=["exoarmur.federation.membership.update.v2"],
                retention=RetentionPolicy.WORK_QUEUE,
                max_age=86400,  # 24 hours in seconds
                storage=StorageType.FILE,
                discard=DiscardPolicy.OLD
            )
            
            await self._js.add_stream(stream_config)
            logger.debug("Created federation membership stream")
        except Exception as e:
            logger.error(f"Failed to setup JetStream stream: {e}")
            # Explicit degradation - JetStream unavailable, continue with regular NATS
            logger.warning("JetStream unavailable - continuing without persistence")
    
    async def _initialize_identity_manager(self) -> None:
        """Initialize V2 identity manager if feature flag is enabled"""
        try:
            # Import feature flags to check V2 federation status
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from feature_flags import get_feature_flags
            
            flags = get_feature_flags()
            v2_federation_enabled = flags.get('v2_federation_enabled', {}).get('current_value', False)
            
            if v2_federation_enabled:
                # Create handshake config from federation config
                handshake_config = HandshakeConfig(
                    buffer_window_ms=5000,
                    step_timeout_ms=10000,
                    minimum_trust_score=0.7
                )
                
                # Initialize identity manager
                self._identity_manager = FederationIdentityManager(
                    config=handshake_config,
                    feature_flag_checker=lambda: v2_federation_enabled,
                    audit_interface=None  # Will be integrated later if needed
                )
                
                logger.info("V2 Federation Identity Manager initialized")
            else:
                logger.debug("V2 Federation Identity Manager not initialized - feature flag disabled")
                
        except ImportError as e:
            logger.warning(f"Could not check V2 federation feature flag: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize V2 identity manager: {e}")
    
    async def _setup_subscriptions(self) -> None:
        """Setup NATS subscriptions for federation messages"""
        if not self._nc:
            return
        
        # Subscribe to membership updates
        await self._nc.subscribe(
            "exoarmur.federation.membership.update.v2",
            cb=self._on_membership_update
        )
        
        # Subscribe to heartbeats
        await self._nc.subscribe(
            "exoarmur.federation.heartbeat.v2",
            cb=self._on_heartbeat
        )
        
        logger.debug("Federation subscriptions configured")
    
    async def _on_membership_update(self, msg) -> None:
        """Handle membership update messages"""
        try:
            data = json.loads(msg.data.decode())
            cell_id = data.get("cell_id")
            
            if cell_id == self.config.cell_id:
                return  # Ignore our own messages
            
            # Update membership table
            member = FederationMember(
                cell_id=cell_id,
                status=data.get("status", "active"),
                last_heartbeat=datetime.now(timezone.utc),
                capabilities=data.get("capabilities", []),
                trust_score=data.get("trust_score", 0.8),
                role=data.get("role", "member")
            )
            
            self._membership[cell_id] = member
            logger.debug(f"Updated membership for cell {cell_id}")
            
        except Exception as e:
            logger.error(f"Error processing membership update: {e}")
    
    async def _on_heartbeat(self, msg) -> None:
        """Handle heartbeat messages"""
        try:
            data = json.loads(msg.data.decode())
            cell_id = data.get("cell_id")
            
            if cell_id == self.config.cell_id:
                return  # Ignore our own heartbeats
            
            # Update last heartbeat time
            if cell_id in self._membership:
                self._membership[cell_id].last_heartbeat = datetime.now(timezone.utc)
                logger.debug(f"Received heartbeat from {cell_id}")
            
        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
    
    async def _heartbeat_loop(self) -> None:
        """Publish heartbeat messages at regular intervals"""
        while not self._shutdown_event.is_set():
            try:
                await self._publish_heartbeat()
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _publish_heartbeat(self) -> None:
        """Publish heartbeat message"""
        if not self._nc:
            return
        
        heartbeat_msg = {
            "cell_id": self.config.cell_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_number": 1,  # TODO: Implement proper sequence
            "status": "active",
            "federation_id": self._federation_id
        }
        
        try:
            await self._nc.publish(
                "exoarmur.federation.heartbeat.v2",
                json.dumps(heartbeat_msg).encode()
            )
            logger.debug(f"Published heartbeat for {self.config.cell_id}")
        except Exception as e:
            logger.error(f"Failed to publish heartbeat: {e}")
    
    async def _publish_join(self) -> None:
        """Publish JOIN message to federation"""
        if not self._nc:
            return
        
        join_msg = {
            "cell_id": self.config.cell_id,
            "federation_id": self._federation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": ["belief_aggregation", "policy_distribution"],
            "trust_score": 0.8,
            "role": "member",
            "status": "active"
        }
        
        try:
            await self._nc.publish(
                "exoarmur.federation.membership.update.v2",
                json.dumps(join_msg).encode()
            )
            logger.info(f"Published JOIN message for {self.config.cell_id}")
        except Exception as e:
            logger.error(f"Failed to publish JOIN message: {e}")
    
    async def form_federation(self, cells: Dict[str, Any]) -> str:
        """Form federation between cells"""
        if not self.config.enabled:
            logger.debug("FederationManager.form_federation() - no-op (scaffolding)")
            return "scaffold-federation-id"
        
        if not self._initialized:
            await self.initialize()
        
        # Generate federation ID if not provided
        if not self._federation_id:
            self._federation_id = str(uuid.uuid4())
        
        # Add self as a member
        self_member = FederationMember(
            cell_id=self.config.cell_id,
            status="active",
            last_heartbeat=datetime.now(timezone.utc),
            capabilities=["belief_aggregation", "policy_distribution"],
            trust_score=0.8,
            role="member"
        )
        self._membership[self.config.cell_id] = self_member
        
        # Add initial members to membership table
        for cell_id, cell_info in cells.items():
            if cell_id != self.config.cell_id:
                member = FederationMember(
                    cell_id=cell_id,
                    status="active",
                    last_heartbeat=datetime.now(timezone.utc),
                    capabilities=cell_info.get("capabilities", []),
                    trust_score=cell_info.get("trust_score", 0.8),
                    role=cell_info.get("role", "member")
                )
                self._membership[cell_id] = member
        
        # Publish JOIN message
        await self._publish_join()
        
        logger.info(f"Formed federation {self._federation_id} with {len(self._membership)} members")
        return self._federation_id
    
    async def join_federation(self, federation_id: str, cell_id: str) -> bool:
        """Join existing federation"""
        if not self.config.enabled:
            logger.debug("FederationManager.join_federation() - no-op (scaffolding)")
            return True
        
        if not self._initialized:
            await self.initialize()
        
        self._federation_id = federation_id
        self.config.cell_id = cell_id
        
        # Publish JOIN message
        await self._publish_join()
        
        logger.info(f"Joined federation {federation_id} as {cell_id}")
        return True
    
    async def leave_federation(self, federation_id: str, cell_id: str) -> bool:
        """Leave federation"""
        if not self.config.enabled:
            logger.debug("FederationManager.leave_federation() - no-op (scaffolding)")
            return True
        
        # Publish LEAVE message
        if self._nc:
            leave_msg = {
                "cell_id": self.config.cell_id,
                "federation_id": federation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "decommissioned"
            }
            
            try:
                await self._nc.publish(
                    "exoarmur.federation.membership.update.v2",
                    json.dumps(leave_msg).encode()
                )
                logger.info(f"Published LEAVE message for {cell_id}")
            except Exception as e:
                logger.error(f"Failed to publish LEAVE message: {e}")
        
        # Remove from membership table
        self._membership.pop(cell_id, None)
        
        logger.info(f"Left federation {federation_id}")
        return True
    
    async def get_federation_status(self) -> Dict[str, Any]:
        """Get federation status"""
        if not self.config.enabled:
            logger.debug("FederationManager.get_federation_status() - no-op (scaffolding)")
            return {
                "federation_id": self.config.federation_id or "scaffold-federation-id",
                "status": "scaffolding",
                "member_count": 0,
                "healthy_cells": [],
                "degraded_cells": []
            }
        
        # Count active members
        active_members = [
            cell_id for cell_id, member in self._membership.items()
            if member.status == "active" and 
               (datetime.now(timezone.utc) - member.last_heartbeat).seconds < 120
        ]
        
        return {
            "federation_id": self._federation_id,
            "status": "active" if self._initialized else "initializing",
            "member_count": len(self._membership),
            "healthy_cells": active_members,
            "degraded_cells": [],
            "cell_id": self.config.cell_id,
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
    
    async def add_member(self, cell_id: str, cell_info: Dict[str, Any]) -> bool:
        """Add member to federation"""
        if not self.config.enabled:
            logger.debug("FederationManager.add_member() - no-op (scaffolding)")
            return True
        
        member = FederationMember(
            cell_id=cell_id,
            status="active",
            last_heartbeat=datetime.now(timezone.utc),
            capabilities=cell_info.get("capabilities", []),
            trust_score=cell_info.get("trust_score", 0.8),
            role=cell_info.get("role", "member")
        )
        
        self._membership[cell_id] = member
        logger.info(f"Added member {cell_id} to federation")
        return True
    
    async def remove_member(self, cell_id: str) -> bool:
        """Remove member from federation"""
        if not self.config.enabled:
            logger.debug("FederationManager.remove_member() - no-op (scaffolding)")
            return True
        
        self._membership.pop(cell_id, None)
        logger.info(f"Removed member {cell_id} from federation")
        return True
    
    def is_federation_member(self, cell_id: str) -> bool:
        """Check if cell is federation member"""
        if not self.config.enabled:
            logger.debug("FederationManager.is_federation_member() - no-op (scaffolding)")
            return False
        
        return cell_id in self._membership
    
    def get_identity_manager(self) -> Optional[FederationIdentityManager]:
        """Get V2 identity manager instance"""
        return self._identity_manager
    
    async def shutdown(self) -> None:
        """Shutdown federation manager"""
        if not self.config.enabled:
            logger.debug("FederationManager.shutdown() - no-op (scaffolding)")
            return
        
        logger.info("Shutting down FederationManager")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown V2 identity manager
        if self._identity_manager:
            try:
                self._identity_manager.shutdown()
                self._identity_manager = None
                logger.info("V2 Identity Manager shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down V2 identity manager: {e}")
        
        # Close NATS connection
        if self._nc:
            try:
                await self._nc.close()
                logger.info("NATS connection closed")
            except Exception as e:
                logger.error(f"Error closing NATS connection: {e}")
        
        self._initialized = False
        logger.info("FederationManager shutdown complete")
