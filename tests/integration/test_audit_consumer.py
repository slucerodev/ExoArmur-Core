"""Audit logger JetStream consumer integration tests."""

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from exoarmur.audit.audit_logger import AuditLogger
from exoarmur.nats_client import ExoArmurNATSClient, NATSConfig


@pytest.fixture
async def nats_jetstream():
    repo_root = Path(__file__).resolve().parents[2]
    docker_compose_path = shutil.which("docker-compose")
    if not docker_compose_path:
        pytest.fail("docker-compose executable not found")
    result = subprocess.run(
        [docker_compose_path, "up", "-d", "nats"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        pytest.fail(f"Failed to start NATS: {result.stderr}")

    await asyncio.sleep(5)
    yield

    subprocess.run(
        [docker_compose_path, "down"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("nats_jetstream")
async def test_audit_consumer_persists_records():
    """AuditLogger should consume JetStream audit records into local storage."""
    nats_client = ExoArmurNATSClient(NATSConfig(url="nats://localhost:4222"))

    connected = await nats_client.connect()
    assert connected, "NATS must be running for audit consumer test"

    await nats_client.ensure_streams()

    audit_logger = AuditLogger(nats_client=nats_client)

    record = await audit_logger.emit_audit_record_async(
        event_kind="test_audit_event",
        payload_ref={"kind": "test", "ref": {"value": 1}},
        correlation_id="corr-audit-consumer-1",
        trace_id="trace-audit-consumer-1",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        idempotency_key="",
    )

    try:
        await audit_logger.consume_from_jetstream(
            correlation_id="corr-audit-consumer-1",
            max_messages=5,
            timeout_seconds=2.0,
        )

        records = audit_logger.get_audit_records("corr-audit-consumer-1")
        assert any(r.audit_id == record.audit_id for r in records)
    finally:
        await nats_client.disconnect()
