"""
NATS JetStream client for ExoArmur ADMO
"""

import logging
import asyncio
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
    """NATS JetStream client for ExoArmur"""
    
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
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(
                self.config.url,
                max_reconnect_attempts=self.config.max_reconnect_attempts,
                reconnect_wait=self.config.reconnect_wait,
                connect_timeout=self.config.connection_timeout,
                error_cb=self._error_handler,
                closed_cb=self._closed_handler
            )
            
            self.js = self.nc.jetstream()
            self.connected = True
            
            logger.info(f"Connected to NATS at {self.config.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            self.connected = False
            logger.info("Disconnected from NATS")
    
    async def ensure_streams(self) -> None:
        """Ensure required streams exist"""
        if not self.js:
            raise RuntimeError("Not connected to NATS")
        
        # Create beliefs stream
        try:
            await self.js.add_stream(
                name="EXOARMUR_BELIEFS_V1",
                subjects=[self.subjects["beliefs_emit"]],
                config=StreamConfig(
                    retention="limits",
                    max_age=24 * 3600,  # 24 hours
                    max_bytes=2 * 1024 * 1024 * 1024,  # 2GB
                    storage="file",
                    replicas=1
                )
            )
            logger.info("Created beliefs stream")
        except Exception as e:
            logger.info(f"Beliefs stream may already exist: {e}")
        
        # Create audit stream
        try:
            await self.js.add_stream(
                name="EXOARMUR_AUDIT_V1",
                subjects=[self.subjects["audit_append"]],
                config=StreamConfig(
                    retention="limits",
                    max_age=365 * 24 * 3600,  # 1 year
                    max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                    storage="file",
                    replicas=1
                )
            )
            logger.info("Created audit stream")
        except Exception as e:
            logger.info(f"Audit stream may already exist: {e}")
    
    async def publish(self, subject: str, data: bytes, headers: Optional[Dict[str, str]] = None) -> bool:
        """Publish message to subject"""
        if not self.nc or not self.connected:
            logger.error("Not connected to NATS")
            return False
        
        try:
            await self.nc.publish(subject, data, headers=headers)
            logger.debug(f"Published to {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            return False
    
    async def subscribe(
        self,
        subject: str,
        handler: Callable,
        queue_group: Optional[str] = None
    ) -> bool:
        """Subscribe to subject with handler"""
        if not self.nc or not self.connected:
            logger.error("Not connected to NATS")
            return False
        
        try:
            sub = await self.nc.subscribe(
                subject,
                queue=queue_group,
                cb=handler
            )
            logger.info(f"Subscribed to {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            return False
    
    def _error_handler(self, e):
        """Handle NATS errors"""
        logger.error(f"NATS error: {e}")
    
    def _closed_handler(self):
        """Handle NATS connection closed"""
        logger.warning("NATS connection closed")
        self.connected = False
