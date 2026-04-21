"""
Payload Store for Canonical Input Persistence

This module provides functions for persisting and loading canonical input payloads,
ensuring exact payload persistence for replay without reconstruction drift.
"""

import os
import json
from typing import Dict, Any
from pathlib import Path

from exoarmur.replay.canonical_utils import canonical_json


PROOFS_DIR = "/tmp/exoarmur_proofs"


def persist_payload(input_hash: str, payload: Dict[str, Any]) -> str:
    """
    Persist canonical input payload to disk.
    
    This function:
    - Serializes payload using canonical_json
    - Stores in deterministic location based on hash
    - Ensures payload can be exactly reconstructed for replay
    
    Args:
        input_hash: Hash of the input payload (used as filename)
        payload: Canonical input payload dictionary
        
    Returns:
        Path to the persisted payload file
    """
    # Ensure proofs directory exists
    os.makedirs(PROOFS_DIR, exist_ok=True)
    
    # Serialize payload with canonical_json
    canonical_payload = canonical_json(payload)
    
    # Determine file path
    file_path = os.path.join(PROOFS_DIR, f"{input_hash}.json")
    
    # Write payload to file
    with open(file_path, 'w') as f:
        f.write(canonical_payload)
    
    return file_path


def load_payload(input_hash: str) -> Dict[str, Any]:
    """
    Load canonical input payload from disk.
    
    This function:
    - Loads payload from deterministic location based on hash
    - Deserializes payload
    - Returns exact payload used for original execution
    
    Args:
        input_hash: Hash of the input payload (used as filename)
        
    Returns:
        Canonical input payload dictionary
        
    Raises:
        FileNotFoundError: If payload file does not exist
        ValueError: If payload cannot be deserialized
    """
    file_path = os.path.join(PROOFS_DIR, f"{input_hash}.json")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Payload file not found: {file_path}")
    
    # Read payload from file
    with open(file_path, 'r') as f:
        canonical_payload = f.read()
    
    # Deserialize payload
    try:
        payload = json.loads(canonical_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to deserialize payload: {e}")
    
    return payload


def payload_exists(input_hash: str) -> bool:
    """
    Check if payload exists for given input hash.
    
    Args:
        input_hash: Hash of the input payload
        
    Returns:
        True if payload exists, False otherwise
    """
    file_path = os.path.join(PROOFS_DIR, f"{input_hash}.json")
    return os.path.exists(file_path)


def cleanup_payload(input_hash: str) -> None:
    """
    Remove persisted payload for given input hash.
    
    Args:
        input_hash: Hash of the input payload
    """
    file_path = os.path.join(PROOFS_DIR, f"{input_hash}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
