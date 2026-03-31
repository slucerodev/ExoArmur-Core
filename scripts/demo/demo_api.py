"""
FastAPI Demo API for ExoArmur Deterministic Governance

This API provides deterministic endpoints for demonstrating ExoArmur's
core capabilities: replay, verification, and Byzantine fault testing.

All responses are 100% deterministic - no timestamps, no environment
dependencies, no random values.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.byzantine_fault_injection import (
    ByzantineTestRunner, 
    ByzantineScenario,
    FaultType
)
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event

# Ensure deterministic environment
os.environ['PYTHONHASHSEED'] = '0'

app = FastAPI(
    title="ExoArmur Deterministic Demo API",
    description="Deterministic demonstration of ExoArmur governance capabilities",
    version="1.0.0"
)

# Request/Response Models
class CanonicalEventRequest(BaseModel):
    """Request model for canonical events"""
    correlation_id: str = Field(..., description="Correlation ID for events")
    events: List[Dict[str, Any]] = Field(..., description="List of canonical events")

class ReplayResponse(BaseModel):
    """Response model for replay operations"""
    correlation_id: str
    replay_hash: str
    replay_output: Dict[str, Any]
    total_events: int
    processed_events: int
    result: str

class VerificationResponse(BaseModel):
    """Response model for multi-node verification"""
    correlation_id: str
    consensus: bool
    consensus_result: str
    node_count: int
    node_hashes: Dict[str, str]
    divergent_nodes: List[str]
    consensus_nodes: List[str]

class ByzantineTestRequest(BaseModel):
    """Request model for Byzantine fault testing"""
    correlation_id: str
    events: List[Dict[str, Any]]
    scenario: str = Field(default="single_node", description="Byzantine scenario")
    node_count: int = Field(default=3, description="Number of nodes")
    deterministic_seed: int = Field(default=42, description="Deterministic seed")

class ByzantineTestResponse(BaseModel):
    """Response model for Byzantine fault testing"""
    correlation_id: str
    scenario: str
    baseline_hash: str
    consensus: bool
    consensus_result: str
    corrupted_nodes: List[str]
    divergence_detected: bool

# Helper Functions
def convert_to_canonical_events(events_data: List[Dict[str, Any]]) -> List[CanonicalEvent]:
    """Convert event data to CanonicalEvent objects"""
    events = []
    for event_data in events_data:
        try:
            event = CanonicalEvent(**event_data)
            events.append(event)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid event data: {e}")
    return events

# API Endpoints
@app.post("/replay", response_model=ReplayResponse)
async def replay_events(request: CanonicalEventRequest):
    """
    Replay canonical events deterministically
    
    This endpoint demonstrates the core replay capability of ExoArmur.
    Same input always produces identical output and hash.
    """
    try:
        # Convert to CanonicalEvent objects
        events = convert_to_canonical_events(request.events)
        
        # Create audit store
        audit_store = {request.correlation_id: events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        
        # Run replay
        report = replay_engine.replay_correlation(request.correlation_id)
        
        # Generate deterministic output
        replay_output = report.to_dict()
        replay_hash = stable_hash(canonical_json(replay_output))
        
        return ReplayResponse(
            correlation_id=request.correlation_id,
            replay_hash=replay_hash,
            replay_output=replay_output,
            total_events=report.total_events,
            processed_events=report.processed_events,
            result=report.result.value
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {e}")

@app.post("/verify", response_model=VerificationResponse)
async def verify_consensus(request: CanonicalEventRequest):
    """
    Run multi-node consensus verification
    
    This endpoint demonstrates ExoArmur's ability to verify that
    multiple independent nodes produce identical results.
    """
    try:
        # Convert to CanonicalEvent objects
        events = convert_to_canonical_events(request.events)
        
        # Run multi-node verification
        verifier = MultiNodeReplayVerifier(node_count=3)
        divergence_report = verifier.verify_consensus(events, request.correlation_id)
        
        return VerificationResponse(
            correlation_id=request.correlation_id,
            consensus=not divergence_report.has_divergence(),
            consensus_result=divergence_report.consensus_result.value,
            node_count=verifier.node_count,
            node_hashes=divergence_report.node_hashes,
            divergent_nodes=divergence_report.divergent_nodes,
            consensus_nodes=divergence_report.get_consensus_nodes()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")

@app.post("/byzantine-test", response_model=ByzantineTestResponse)
async def test_byzantine_faults(request: ByzantineTestRequest):
    """
    Run Byzantine fault injection test
    
    This endpoint demonstrates ExoArmur's resilience to adversarial
    conditions by injecting deterministic faults and detecting divergence.
    """
    try:
        # Convert to CanonicalEvent objects
        events = convert_to_canonical_events(request.events)
        
        # Parse scenario
        try:
            scenario = ByzantineScenario(request.scenario)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid scenario: {request.scenario}")
        
        # Run Byzantine test
        test_runner = ByzantineTestRunner(
            node_count=request.node_count,
            deterministic_seed=request.deterministic_seed
        )
        
        result = test_runner.run_byzantine_test(events, scenario)
        
        # Extract corrupted nodes
        corrupted_nodes = []
        for node_id, node_result in result.injection_results.items():
            if node_result.corrupted_events:
                corrupted_nodes.append(node_id)
        
        return ByzantineTestResponse(
            correlation_id=request.correlation_id,
            scenario=result.scenario.value,
            baseline_hash=result.baseline_hash,
            consensus=not result.divergence_report.has_divergence(),
            consensus_result=result.divergence_report.consensus_result.value,
            corrupted_nodes=corrupted_nodes,
            divergence_detected=result.divergence_report.has_divergence()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Byzantine test failed: {e}")

@app.get("/demo-data")
async def get_demo_data():
    """
    Get sample data for testing endpoints
    
    Returns pre-configured canonical events that can be used
    with the replay, verify, and byzantine-test endpoints.
    """
    try:
        # Load golden artifacts if available
        artifacts_path = "/home/oem/CascadeProjects/ExoArmur/tests/artifacts/demo_canonical_events.json"
        
        if os.path.exists(artifacts_path):
            with open(artifacts_path, 'r') as f:
                events = json.load(f)
        else:
            # Fallback to generated events
            events = _create_sample_events()
        
        return {
            "correlation_id": "demo-correlation-001",
            "events": events,
            "usage": {
                "replay": "POST /replay with this data",
                "verify": "POST /verify with this data", 
                "byzantine-test": "POST /byzantine-test with this data"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load demo data: {e}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns deterministic health status without timestamps.
    """
    return {
        "status": "healthy",
        "service": "exoarmur-demo-api",
        "version": "1.0.0",
        "determinism": "enforced"
    }

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "ExoArmur Deterministic Demo API",
        "description": "Demonstrates ExoArmur's deterministic governance capabilities",
        "version": "1.0.0",
        "endpoints": {
            "POST /replay": "Replay events deterministically",
            "POST /verify": "Verify multi-node consensus", 
            "POST /byzantine-test": "Test Byzantine fault resilience",
            "GET /demo-data": "Get sample test data",
            "GET /health": "Health check",
            "GET /": "This information"
        },
        "guarantees": [
            "Same input always produces identical output",
            "All responses are 100% deterministic",
            "No timestamps or environment dependencies",
            "Hash-based verification of integrity"
        ]
    }

def _create_sample_events() -> List[Dict[str, Any]]:
    """Create sample canonical events"""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    records = [
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345671',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='telemetry_ingested',
            payload_ref={'kind': {'ref': {'event_id': 'demo-event-001', 'source': 'test'}}},
            hashes={'sha256': 'demo-hash-001'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        ),
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345672',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='safety_gate_evaluated',
            payload_ref={'kind': {'ref': {'verdict': 'require_human', 'risk_score': 'medium'}}},
            hashes={'sha256': 'demo-hash-002'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        ),
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345673',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='approval_requested',
            payload_ref={'kind': {'ref': {'approval_id': 'demo-approval-001', 'operator': 'demo-operator'}}},
            hashes={'sha256': 'demo-hash-003'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        )
    ]
    
    return [to_canonical_event(record, sequence_number=i) 
            for i, record in enumerate(records)]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
