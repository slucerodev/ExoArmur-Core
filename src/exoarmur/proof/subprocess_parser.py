"""
Subprocess output parser for determinism proof harness.

This module provides utilities for parsing output from subprocess executions
in the determinism proof harness, specifically for extracting execution hashes
from single-run CLI mode output.
"""

import re
from typing import Optional


class SubprocessParserError(Exception):
    """Raised when subprocess output parsing fails."""
    pass


def extract_execution_hash(output: str) -> str:
    """
    Extract execution hash from subprocess stdout output.
    
    Expected output format:
        EXECUTION HASH: <hash>
    
    Args:
        output: Stdout from subprocess execution
        
    Returns:
        The execution hash string
        
    Raises:
        SubprocessParserError: If hash cannot be found in output
    """
    # Pattern to match "EXECUTION HASH: <hash>"
    pattern = r"EXECUTION HASH:\s+([a-f0-9]+)"
    
    match = re.search(pattern, output)
    
    if not match:
        raise SubprocessParserError(
            f"Could not extract execution hash from subprocess output. "
            f"Expected format: 'EXECUTION HASH: <hash>'. "
            f"Got: {output[:200]}"
        )
    
    hash_value = match.group(1)
    
    # Validate hash format (64 hex characters for SHA-256)
    if not re.match(r'^[a-f0-9]{64}$', hash_value):
        raise SubprocessParserError(
            f"Invalid hash format extracted: {hash_value}. "
            f"Expected 64-character hex string."
        )
    
    return hash_value


def verify_subprocess_success(output: str, returncode: int) -> None:
    """
    Verify subprocess execution succeeded.
    
    Args:
        output: Stdout from subprocess execution
        returncode: Process return code
        
    Raises:
        SubprocessParserError: If subprocess failed
    """
    if returncode != 0:
        raise SubprocessParserError(
            f"Subprocess execution failed with return code {returncode}. "
            f"Output: {output[:500]}"
        )
