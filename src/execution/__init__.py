"""
Execution Module - Execution Intent Processing

Creates ExecutionIntentV1 and routes to execution kernel with idempotency.
"""

from .execution_kernel import ExecutionKernel

__all__ = ['ExecutionKernel']
