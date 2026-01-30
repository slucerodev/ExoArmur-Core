"""
Circuit Breakers - Phase 6 Reliability Substrate
Circuit breaker logic for external dependencies with observable and auditable transitions.
"""

import asyncio
import functools
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar, Set
from enum import Enum
from dataclasses import dataclass, field
import weakref

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"      # Normal operation, requests pass through
    OPEN = "OPEN"          # Circuit is open, requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing if service has recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    
    def __init__(self, service_name: str, state: CircuitState, failure_count: int):
        self.service_name = service_name
        self.state = state
        self.failure_count = failure_count
        super().__init__(f"Circuit breaker OPEN for {service_name} (failures: {failure_count})")


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    # Failure thresholds
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Successes in half-open before closing
    
    # Time windows
    failure_window_seconds: float = 60.0  # Window for counting failures
    success_window_seconds: float = 60.0  # Window for counting successes
    
    # Monitoring
    monitor_interval: float = 10.0  # Health check interval
    health_check_timeout: float = 5.0  # Health check timeout
    
    # State persistence
    state_ttl: float = 3600.0  # How long to keep state without activity


@dataclass
class CircuitStateTransition:
    """Record of circuit state transition"""
    from_state: CircuitState
    to_state: CircuitState
    timestamp: datetime
    reason: str
    failure_count: int
    success_count: int


class CircuitBreaker:
    """
    Circuit breaker for external dependencies
    
    Rule R6: Circuit breakers are required.
    Rule R6: Breaker transitions must be observable and auditable.
    Rule R6: Classification must be deterministic.
    """
    
    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._state_lock = asyncio.Lock()
        self._last_state_change = datetime.now(timezone.utc)
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        
        # History for monitoring
        self._state_history: List[CircuitStateTransition] = []
        self._failure_history: List[datetime] = []
        self._success_history: List[datetime] = []
        
        # Health check
        self._health_check_func: Optional[Callable] = None
        self._audit_emitter: Optional[Callable] = None
        
        # Track background tasks for cleanup
        self._background_tasks: Set[asyncio.Task] = set()
        
        logger.info(f"Circuit breaker initialized for {service_name}: "
                   f"threshold={config.failure_threshold}, "
                   f"timeout={config.recovery_timeout}s")
    
    def set_health_check(self, health_check_func: Callable):
        """Set health check function for the service"""
        self._health_check_func = health_check_func
        logger.info(f"Health check set for {self.service_name}")
    
    def set_audit_emitter(self, emitter: Callable):
        """Set audit emitter for circuit breaker events"""
        self._audit_emitter = emitter
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)"""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self.state == CircuitState.HALF_OPEN
    
    def _record_failure(self):
        """Record a failure occurrence"""
        now = datetime.now(timezone.utc)
        self._failure_history.append(now)
        self._last_failure_time = now
        self._failure_count += 1
        
        # Clean old failures outside window
        cutoff = now - timedelta(seconds=self.config.failure_window_seconds)
        self._failure_history = [f for f in self._failure_history if f > cutoff]
        
        logger.debug(f"Recorded failure for {self.service_name}: {self._failure_count} total")
    
    def _record_success(self):
        """Record a success occurrence"""
        now = datetime.now(timezone.utc)
        self._success_history.append(now)
        self._last_success_time = now
        self._success_count += 1
        
        # Clean old successes outside window
        cutoff = now - timedelta(seconds=self.config.success_window_seconds)
        self._success_history = [s for s in self._success_history if s > cutoff]
        
        logger.debug(f"Recorded success for {self.service_name}: {self._success_count} total")
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should open based on failures"""
        return len(self._failure_history) >= self.config.failure_threshold
    
    def _should_close_circuit(self) -> bool:
        """Check if circuit should close based on successes"""
        return len(self._success_history) >= self.config.success_threshold
    
    def _should_try_half_open(self) -> bool:
        """Check if circuit should try half-open state"""
        if self._last_failure_time is None:
            return False
        
        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    async def _change_state(self, new_state: CircuitState, reason: str):
        """Change circuit state with audit trail"""
        old_state = self._state
        
        async with self._state_lock:
            self._state = new_state
            self._last_state_change = datetime.now(timezone.utc)
        
        # Record state transition
        transition = CircuitStateTransition(
            from_state=old_state,
            to_state=new_state,
            timestamp=self._last_state_change,
            reason=reason,
            failure_count=self._failure_count,
            success_count=self._success_count
        )
        self._state_history.append(transition)
        
        # Keep history manageable
        if len(self._state_history) > 100:
            self._state_history = self._state_history[-50:]
        
        logger.info(f"Circuit breaker {self.service_name}: {old_state.value} → {new_state.value} ({reason})")
        
        # Emit audit event
        task = asyncio.create_task(self._emit_state_transition_audit(transition))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def _emit_state_transition_audit(self, transition: CircuitStateTransition):
        """Emit audit event for state transition"""
        if not self._audit_emitter:
            return
        
        try:
            audit_data = {
                "event_type": "circuit_breaker_state_change",
                "service_name": self.service_name,
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "reason": transition.reason,
                "failure_count": transition.failure_count,
                "success_count": transition.success_count,
                "timestamp": transition.timestamp.isoformat()
            }
            
            await self._audit_emitter(audit_data)
            
        except Exception as e:
            logger.error(f"Failed to emit circuit breaker audit: {e}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function execution fails
        """
        # Check circuit state
        if self.is_open:
            # Check if we should try half-open
            if self._should_try_half_open():
                await self._change_state(CircuitState.HALF_OPEN, "Recovery timeout reached")
            else:
                raise CircuitBreakerError(self.service_name, self.state, self._failure_count)
        
        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            self._record_success()
            
            # Check if we should close circuit (from half-open)
            if self.is_half_open and self._should_close_circuit():
                await self._change_state(CircuitState.CLOSED, "Recovery confirmed")
            
            return result
            
        except Exception as e:
            # Record failure
            self._record_failure()
            
            # Check if we should open circuit
            if self.is_closed and self._should_open_circuit():
                await self._change_state(CircuitState.OPEN, f"Failure threshold reached ({self._failure_count})")
            elif self.is_half_open:
                await self._change_state(CircuitState.OPEN, f"Recovery test failed ({self._failure_count})")
            
            # Re-raise the original exception
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "last_success_time": self._last_success_time.isoformat() if self._last_success_time else None,
            "last_state_change": self._last_state_change.isoformat(),
            "recent_failures": [dt.isoformat() for dt in self._failure_history[-10:]],
            "recent_successes": [dt.isoformat() for dt in self._success_history[-10:]],
            "state_history_count": len(self._state_history)
        }
    
    async def health_check(self) -> bool:
        """Perform health check on the service"""
        if not self._health_check_func:
            return self.is_closed  # Default: assume healthy if closed
        
        try:
            if asyncio.iscoroutinefunction(self._health_check_func):
                result = await asyncio.wait_for(
                    self._health_check_func(),
                    timeout=self.config.health_check_timeout
                )
            else:
                result = self._health_check_func()
            
            if result:
                self._record_success()
                if self.is_half_open and self._should_close_circuit():
                    await self._change_state(CircuitState.CLOSED, "Health check passed")
            else:
                self._record_failure()
                if self.is_closed and self._should_open_circuit():
                    await self._change_state(CircuitState.OPEN, "Health check failed")
            
            return result
            
        except Exception as e:
            self._record_failure()
            if self.is_closed and self._should_open_circuit():
                await self._change_state(CircuitState.OPEN, f"Health check exception: {e}")
            return False
    
    async def reset(self):
        """Reset circuit breaker to closed state"""
        await self._change_state(CircuitState.CLOSED, "Manual reset")
        self._failure_count = 0
        self._success_count = 0
        self._failure_history.clear()
        self._success_history.clear()
        logger.info(f"Circuit breaker {self.service_name} reset to CLOSED state")
    
    async def cleanup(self):
        """Cancel all background tasks"""
        # Cancel audit tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info(f"Circuit breaker {self.service_name} background tasks cleaned up")


class CircuitBreakerManager:
    """
    Central circuit breaker management
    
    Rule R6: Circuit breakers are required.
    Rule R6: Breaker transitions must be observable and auditable.
    """
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._audit_emitter = None
        self.default_config = CircuitBreakerConfig()
        
        # Background health check task
        self._health_check_task = None
        self._health_check_interval = 10.0  # Default interval
        
        logger.info("CircuitBreakerManager initialized")
    
    def set_audit_emitter(self, emitter: Callable):
        """Set audit emitter for circuit breaker events"""
        self._audit_emitter = emitter
        
        # Set audit emitter on existing breakers
        for breaker in self.breakers.values():
            breaker.set_audit_emitter(emitter)
    
    def get_breaker(self, service_name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.breakers:
            effective_config = config or self.default_config
            breaker = CircuitBreaker(service_name, effective_config)
            
            if self._audit_emitter:
                breaker.set_audit_emitter(self._audit_emitter)
            
            self.breakers[service_name] = breaker
            logger.info(f"Created circuit breaker for {service_name}")
        
        return self.breakers[service_name]
    
    async def call_with_breaker(self, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        breaker = self.get_breaker(service_name)
        return await breaker.call(func, *args, **kwargs)
    
    def start_health_checks(self):
        """Start background health check task"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started circuit breaker health check task")
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Perform health checks on all breakers
                tasks = []
                for breaker in self.breakers.values():
                    if breaker._health_check_func:
                        tasks.append(breaker.health_check())
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                logger.debug("Circuit breaker health checks completed")
                
            except Exception as e:
                logger.error(f"Circuit breaker health check failed: {e}")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            service_name: breaker.get_stats()
            for service_name, breaker in self.breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            await breaker.reset()
        logger.info("All circuit breakers reset")
    
    async def cleanup(self):
        """Cleanup background tasks"""
        # Cleanup all breakers first
        breaker_cleanup_tasks = []
        for breaker in self.breakers.values():
            breaker_cleanup_tasks.append(breaker.cleanup())
        
        if breaker_cleanup_tasks:
            await asyncio.gather(*breaker_cleanup_tasks, return_exceptions=True)
        
        # Cancel manager's health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("CircuitBreakerManager background task cancelled")


# Global circuit breaker manager instance
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
        # Don't auto-start health checks to prevent hanging in tests
        # _circuit_breaker_manager.start_health_checks()
    return _circuit_breaker_manager


# Decorator for circuit breaker protection
def with_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """
    Decorator for adding circuit breaker protection to functions
    
    Args:
        service_name: Name of the service being protected
        config: Optional circuit breaker configuration
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            return await manager.call_with_breaker(service_name, func, *args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for common operations
async def call_with_breaker(
    service_name: str,
    func: Callable,
    *args,
    **kwargs
):
    """Execute function with circuit breaker protection"""
    manager = get_circuit_breaker_manager()
    return await manager.call_with_breaker(service_name, func, *args, **kwargs)


def create_breaker(
    service_name: str,
    health_check_func: Optional[Callable] = None,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Create and configure a circuit breaker"""
    manager = get_circuit_breaker_manager()
    breaker = manager.get_breaker(service_name, config)
    
    if health_check_func:
        breaker.set_health_check(health_check_func)
    
    return breaker
