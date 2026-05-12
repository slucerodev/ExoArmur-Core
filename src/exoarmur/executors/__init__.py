"""
ExoArmur Executors Module

Production-grade executor implementations for the ProxyPipeline governance boundary.
"""

from .file_system_executor import FileSystemExecutor, RollbackPlan, RollbackResult

__all__ = [
    "FileSystemExecutor",
    "RollbackPlan",
    "RollbackResult"
]
