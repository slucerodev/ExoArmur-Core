import sys
import asyncio

import pytest

from exoarmur.core.phase_gate import PhaseGate
from exoarmur.federation.federation_manager import FederationConfig, FederationManager
from exoarmur.control_plane.control_api import ControlAPI, ControlAPIConfig
from exoarmur.control_plane.operator_interface import OperatorInterface, OperatorConfig
from exoarmur.control_plane.approval_service import ApprovalService, ApprovalConfig


@pytest.fixture(autouse=True)
def _reset_phase_gate(monkeypatch):
    # Ensure Phase 1 for all tests and reset cached state
    monkeypatch.setenv("EXOARMUR_PHASE", "1")
    monkeypatch.setattr(PhaseGate, "_current_phase", None)
    yield
    PhaseGate._current_phase = None


@pytest.mark.asyncio
async def test_federation_phase_gate_denies_before_transport(monkeypatch):
    connect_called = False

    def _fake_connect(*args, **kwargs):
        nonlocal connect_called
        connect_called = True
        raise AssertionError("transport should not be reached")

    # Guard nats.connect to verify it is not reached
    import exoarmur.federation.federation_manager as fm

    monkeypatch.setattr(fm, "nats", type("NATS", (), {"connect": staticmethod(_fake_connect)}))

    config = FederationConfig(enabled=True, cell_id="cell-test", nats_url="nats://example:4222")
    manager = FederationManager(config)

    with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
        await manager.initialize()

    assert connect_called is False, "PhaseGate should fire before any transport"


@pytest.mark.asyncio
async def test_control_api_phase_gate(monkeypatch):
    config = ControlAPIConfig(enabled=True)
    api = ControlAPI(config)

    with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
        await api.startup()


@pytest.mark.asyncio
async def test_operator_interface_phase_gate(monkeypatch):
    config = OperatorConfig(enabled=True)
    op = OperatorInterface(config)

    with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
        await op.initialize()


@pytest.fixture
def _patch_feature_flags(monkeypatch):
    # Provide a minimal stub for feature_flags module used by ApprovalService
    class _Flags:
        def is_v2_operator_approval_required(self):
            return False

    module_name = "feature_flags"
    stub_module = type(sys)(module_name)
    stub_module.get_feature_flags = lambda: _Flags()
    monkeypatch.setitem(sys.modules, module_name, stub_module)
    yield
    sys.modules.pop(module_name, None)


@pytest.mark.asyncio
async def test_approval_service_phase_gate_like_denial(_patch_feature_flags):
    # ApprovalService currently guards via feature flag check when enabled; ensure denial occurs and transport is untouched
    svc = ApprovalService(ApprovalConfig(enabled=True))
    with pytest.raises(NotImplementedError, match="Phase 2"):
        await svc.initialize()


def test_durable_storage_phase_gate_explicit():
    with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
        PhaseGate.check_phase_2_eligibility("DurableStorageBoundary")
