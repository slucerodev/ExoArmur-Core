"""
ExoArmur Executors Module

Production-grade executor implementations for the ProxyPipeline governance boundary.

Core includes:
- FileSystemExecutor — governs file operations with rollback and state verification
- DatabaseExecutor — governs database operations with transaction rollback

Platform executor scaffolds (reference implementations only):
- langchain_executor.py — Scaffold for LangChain agent governance
- openai_executor.py — Scaffold for OpenAI API governance
- anthropic_executor.py — Scaffold for Anthropic API governance
- huggingface_executor.py — Scaffold for HuggingFace model governance

Real platform integrations belong in optional addon packages (e.g., exoarmur-openai-executor).
"""

from .database_executor import DatabaseExecutor
from .file_system_executor import FileSystemExecutor, RollbackPlan, RollbackResult

# Platform executor scaffolds are NOT exported from public API
# They are reference implementations for optional addon packages
# Import directly from module if needed for testing or reference:
# from exoarmur.executors.openai_executor import OpenAIExecutor

__all__ = ["FileSystemExecutor", "RollbackPlan", "RollbackResult", "DatabaseExecutor"]
