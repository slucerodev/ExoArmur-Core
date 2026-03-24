"""Live JetStream belief publishing integration tests."""

import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exoarmur.beliefs.belief_generator import BeliefGenerator
from exoarmur.nats_client import ExoArmurNATSClient, NATSConfig
from exoarmur.spec.contracts.models_v1 import LocalDecisionV1


@pytest.fixture
async def nats_jetstream():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["docker-compose", "up", "-d", "nats"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        pytest.fail(f"Failed to start NATS: {result.stderr}")

    await asyncio.sleep(5)
    yield

    subprocess.run(
        ["docker-compose", "down"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )


@pytest.mark.asyncio
async def test_belief_publish_hits_jetstream(nats_jetstream):
    """BeliefGenerator.publish_belief should publish to JetStream and be retrievable."""
    nats_client = ExoArmurNATSClient(NATSConfig(url="nats://localhost:4222"))

    connected = await nats_client.connect()
    assert connected, "NATS must be running for belief publish test"

    await nats_client.ensure_streams()

    decision = LocalDecisionV1(
        schema_version="1.0.0",
        decision_id="01J4NR5X9Z8GABCDEF12345670",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        subject={"subject_type": "host", "subject_id": "host-123"},
        classification="suspicious",
        severity="high",
        confidence=0.92,
        recommended_intents=[
            {
                "intent_type": "isolate_host",
                "action_class": "A2_hard_containment",
                "ttl_seconds": 3600,
                "parameters": {"isolation_type": "network"},
            }
        ],
        evidence_refs={"event_ids": ["evt-1"], "belief_ids": [], "feature_hashes": []},
        correlation_id="belief-publish-demo-1",
        trace_id="trace-belief-demo-1",
    )

    generator = BeliefGenerator(nats_client=nats_client)
    belief = generator.generate_belief(decision)

    try:
        published = await generator.publish_belief(belief)
        assert published is True

        beliefs = await nats_client.get_beliefs(
            correlation_id=decision.correlation_id,
            max_messages=10,
            timeout_seconds=2.0,
        )
        assert any(b.belief_id == belief.belief_id for b in beliefs)
    finally:
        await nats_client.disconnect()
