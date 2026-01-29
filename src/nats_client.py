"""
NATS JetStream client for ExoArmur ADMO
Phase 6: Enhanced with timeout enforcement and reliability
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

import nats
from nats.js.api import StreamConfig, ConsumerConfig

logger = logging.getLogger(__name__)


@dataclass
class NATSConfig:
    """NATS configuration"""
    url: str = "nats://localhost:4222"
    max_reconnect_attempts: int = 5
    reconnect_wait: float = 2.0
    connection_timeout: float = 10.0


class ExoArmurNATSClient:
    """NATS JetStream client for ExoArmur with timeout enforcement"""
    
    def __init__(self, config: NATSConfig):
        self.config = config
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.js.JetStream] = None
        self.connected = False
        
        # Subject mapping from contracts
        self.subjects = {
            "beliefs_emit": "exoarmur.beliefs.emit.v1",
            "audit_append": "exoarmur.audit.append.v1",
            "beliefs_stream": "exoarmur.beliefs.stream.v1",
            "audit_stream": "exoarmur.audit.stream.v1"
        }
        
        logger.info("ExoArmurNATSClient initialized")
    
    async def connect(self) -> bool:
        """Connect to NATS server with timeout enforcement"""
        from reliability import get_timeout_manager, TimeoutCategory, TimeoutError
        
        timeout_mgr = get_timeout_manager()
        
        try:
            # Use timeout enforcement for connection
            await timeout_mgr.execute_with_timeout(
                category=TimeoutCategory.NATS_CONNECT,
                operation="NATS connection establishment",
                coro=self._do_connect(),
                tenant_id=None,
                correlation_id=None,
                trace_id=None
            )
            
            logger.info(f"Connected to NATS at {self.config.url}")
            return True
            
        except TimeoutError as e:
            logger.error(f"NATS connection timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    async def _do_connect(self) -> None:
        """Internal connection logic without timeout"""
        self.nc = await nats.connect(
            self.config.url,
            max_reconnect_attempts=self.config.max_reconnect_attempts,
            reconnect_time_wait=self.config.reconnect_wait,
            connect_timeout=self.config.connection_timeout,
            error_cb=self._error_handler,
            closed_cb=self._closed_handler
        )
        
        self.js = self.nc.jetstream()
        self.connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        if self.nc:
            try:
                await asyncio.wait_for(self.nc.drain(), timeout=5.0)
                await asyncio.wait_for(self.nc.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("NATS disconnect timed out, forcing close")
                if self.nc:
                    self.nc.close()
            self.connected = False
            logger.info("Disconnected from NATS")
    
    async def ensure_streams(self) -> None:
        """Ensure required streams exist with timeout enforcement"""
        from reliability import get_timeout_manager, TimeoutCategory, TimeoutError
        
        timeout_mgr = get_timeout_manager()
        
        if not self.js:
            raise RuntimeError("Not connected to NATS")
        
        try:
            # Use timeout enforcement for stream creation
            await timeout_mgr.execute_with_timeout(
                category=TimeoutCategory.NATS_STREAM_CREATE,
                operation="JetStream stream creation",
                coro=self._do_ensure_streams(),
                tenant_id=None,
                correlation_id=None,
                trace_id=None
            )
            
        except TimeoutError as e:
            logger.error(f"Stream creation timed out: {e}")
            raise
        except Exception as e:
            logger.info(f"Stream creation failed (may already exist): {e}")
    
    async def _do_ensure_streams(self) -> None:
        """Internal stream creation logic without timeout"""
        # Create/update beliefs stream
        try:
            # Try to get existing stream info first
            try:
                existing_stream = await self.js.stream_info("EXOARMUR_BELIEFS_V1")
                logger.info(f"Found existing beliefs stream: {existing_stream.config.name}")
                
                # Update stream if needed to include our subject
                current_subjects = set(existing_stream.config.subjects)
                required_subject = self.subjects["beliefs_emit"]
                
                if required_subject not in current_subjects:
                    logger.info(f"Adding subject {required_subject} to existing beliefs stream")
                    current_subjects.add(required_subject)
                    await self.js.update_stream(
                        StreamConfig(
                            name="EXOARMUR_BELIEFS_V1",
                            subjects=list(current_subjects),
                            retention="limits",
                            max_age=24 * 3600,  # 24 hours
                            max_bytes=2 * 1024 * 1024 * 1024,  # 2GB
                            storage="file",
                            num_replicas=1
                        )
                    )
                else:
                    logger.info(f"Beliefs stream already includes subject {required_subject}")
                    
            except nats.js.errors.NotFoundError:
                # Stream doesn't exist, create it
                logger.info("Creating new beliefs stream")
                await self.js.add_stream(
                    StreamConfig(
                        name="EXOARMUR_BELIEFS_V1",
                        subjects=[self.subjects["beliefs_emit"]],
                        retention="limits",
                        max_age=24 * 3600,  # 24 hours
                        max_bytes=2 * 1024 * 1024 * 1024,  # 2GB
                        storage="file",
                        num_replicas=1
                    )
                )
                logger.info("Created beliefs stream")
                
        except Exception as e:
            logger.error(f"Failed to ensure beliefs stream: {e}")
            raise
        
        # Create audit stream
        try:
            try:
                existing_stream = await self.js.stream_info("EXOARMUR_AUDIT_V1")
                logger.info(f"Found existing audit stream: {existing_stream.config.name}")
                
                current_subjects = set(existing_stream.config.subjects)
                required_subject = self.subjects["audit_append"]
                
                if required_subject not in current_subjects:
                    logger.info(f"Adding subject {required_subject} to existing audit stream")
                    current_subjects.add(required_subject)
                    await self.js.update_stream(
                        StreamConfig(
                            name="EXOARMUR_AUDIT_V1",
                            subjects=list(current_subjects),
                            retention="limits",
                            max_age=365 * 24 * 3600,  # 1 year
                            max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                            storage="file",
                            num_replicas=1
                        )
                    )
                else:
                    logger.info(f"Audit stream already includes subject {required_subject}")
                    
            except nats.js.errors.NotFoundError:
                logger.info("Creating new audit stream")
                await self.js.add_stream(
                    StreamConfig(
                        name="EXOARMUR_AUDIT_V1",
                        subjects=[self.subjects["audit_append"]],
                        retention="limits",
                        max_age=365 * 24 * 3600,  # 1 year
                        max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                        storage="file",
                        num_replicas=1
                    )
                )
                logger.info("Created audit stream")
                
        except Exception as e:
            logger.error(f"Failed to ensure audit stream: {e}")
            # Don't raise for audit stream - beliefs stream is the critical one
    
    async def publish(self, subject: str, data: bytes, headers: Optional[Dict[str, str]] = None) -> bool:
        """Publish message to subject with timeout enforcement"""
        from reliability import get_timeout_manager, TimeoutCategory, TimeoutError
        
        if not self.nc or not self.connected:
            logger.error("Not connected to NATS")
            return False
        
        timeout_mgr = get_timeout_manager()
        
        try:
            # Use timeout enforcement for publishing
            await timeout_mgr.execute_with_timeout(
                category=TimeoutCategory.NATS_PUBLISH,
                operation=f"Publish to {subject}",
                coro=self._do_publish(subject, data, headers),
                tenant_id=None,
                correlation_id=None,
                trace_id=None
            )
            
            logger.debug(f"Published to {subject}")
            return True
            
        except TimeoutError as e:
            logger.error(f"Publish timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            return False
    
    async def _do_publish(self, subject: str, data: bytes, headers: Optional[Dict[str, str]] = None) -> None:
        """Internal publish logic without timeout"""
        await self.nc.publish(subject, data, headers=headers)
    
    async def publish_belief(self, belief) -> bool:
        """Publish a BeliefV1 to JetStream with timeout enforcement"""
        from reliability import get_timeout_manager, TimeoutCategory, TimeoutError
        
        if not self.nc or not self.connected:
            logger.error("Not connected to NATS")
            return False
        
        if not self.js:
            logger.error("JetStream context not initialized")
            return False
        
        timeout_mgr = get_timeout_manager()
        
        try:
            # Use timeout enforcement for belief publishing
            await timeout_mgr.execute_with_timeout(
                category=TimeoutCategory.NATS_PUBLISH,
                operation=f"Publish belief {belief.belief_id}",
                coro=self._do_publish_belief(belief),
                tenant_id=None,
                correlation_id=None,
                trace_id=None
            )
            
            logger.debug(f"Published belief {belief.belief_id} to {self.subjects['beliefs_emit']}")
            return True
            
        except TimeoutError as e:
            logger.error(f"Belief publish timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish belief: {e}")
            return False
    
    async def _do_publish_belief(self, belief) -> None:
        """Internal belief publish logic without timeout"""
        # Serialize belief deterministically
        belief_data = belief.model_dump(mode="json")
        belief_bytes = json.dumps(belief_data).encode('utf-8')
        
        # Publish via JetStream to beliefs emit subject
        await self.js.publish(
            subject=self.subjects["beliefs_emit"],
            payload=belief_bytes
        )
    
    async def get_beliefs(self, correlation_id: str, max_messages: int = 10, timeout_seconds: float = 2.0) -> list:
        """Get beliefs from JetStream stream filtered by correlation_id"""
        if not self.js:
            logger.error("JetStream context not initialized")
            return []
        
        try:
            logger.info(f"Looking for beliefs with correlation_id: {correlation_id}")
            
            # Get stream info to access messages
            stream_info = await self.js.stream_info("EXOARMUR_BELIEFS_V1")
            logger.info(f"Stream info: {stream_info.config.name}, subjects: {stream_info.config.subjects}")
            
            beliefs = []
            
            # Use the stream's get_last_for_subject method to find messages
            # This is a simpler approach for demo purposes
            try:
                # Try to get messages from the stream directly
                # We'll use a simple approach: get the last messages and filter
                for i in range(min(max_messages, 100)):  # Limit to prevent excessive calls
                    try:
                        # Get the last message (this is a simplified approach)
                        # In a real implementation, we'd use proper consumer filtering
                        msg = await self.js.get_last_msg(
                            stream_name="EXOARMUR_BELIEFS_V1",
                            subject=self.subjects["beliefs_emit"]
                        )
                        
                        if msg:
                            logger.info(f"Found message in stream, data length: {len(msg.data)}")
                            try:
                                # Parse belief data
                                belief_data = json.loads(msg.data.decode('utf-8'))
                                logger.info(f"Parsed belief data, correlation_id: {belief_data.get('correlation_id')}")
                                
                                # Validate correlation_id matches
                                if belief_data.get('correlation_id') == correlation_id:
                                    # Convert to BeliefV1
                                    from models_v1 import BeliefV1
                                    belief = BeliefV1.model_validate(belief_data)
                                    beliefs.append(belief)
                                    logger.info(f"Found matching belief: {belief.belief_id}")
                                    break  # For demo, just get one matching belief
                                else:
                                    logger.info(f"Correlation ID mismatch: {belief_data.get('correlation_id')} != {correlation_id}")
                                
                            except (json.JSONDecodeError, Exception) as e:
                                logger.warning(f"Failed to parse belief message: {e}")
                                continue
                        else:
                            logger.info("No more messages in stream")
                            break  # No more messages
                            
                    except Exception as e:
                        logger.error(f"Error getting message: {e}")
                        break  # Stop on any error
                        
            except Exception as e:
                logger.error(f"Error in simplified belief retrieval: {e}")
            
            logger.info(f"Retrieved {len(beliefs)} beliefs for correlation {correlation_id}")
            return beliefs
            
        except Exception as e:
            logger.error(f"Failed to get beliefs: {e}")
            return []
    
    async def subscribe(
        self,
        subject: str,
        handler: Callable,
        queue_group: Optional[str] = None
    ) -> bool:
        """Subscribe to subject with handler with timeout enforcement"""
        from reliability import get_timeout_manager, TimeoutCategory, TimeoutError
        
        if not self.nc or not self.connected:
            logger.error("Not connected to NATS")
            return False
        
        timeout_mgr = get_timeout_manager()
        
        try:
            # Use timeout enforcement for subscription
            await timeout_mgr.execute_with_timeout(
                category=TimeoutCategory.NATS_SUBSCRIBE,
                operation=f"Subscribe to {subject}",
                coro=self._do_subscribe(subject, handler, queue_group),
                tenant_id=None,
                correlation_id=None,
                trace_id=None
            )
            
            logger.info(f"Subscribed to {subject}")
            return True
            
        except TimeoutError as e:
            logger.error(f"Subscribe timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            return False
    
    async def _do_subscribe(self, subject: str, handler: Callable, queue_group: Optional[str] = None) -> None:
        """Internal subscribe logic without timeout"""
        await self.nc.subscribe(
            subject,
            queue=queue_group,
            cb=handler
        )
    
    async def _error_handler(self, e):
        """Handle NATS errors"""
        logger.error(f"NATS error: {e}")
    
    async def _closed_handler(self):
        """Handle NATS connection closed"""
        logger.warning("NATS connection closed")
        self.connected = False
