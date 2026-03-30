from exoarmur.stability.asyncio_policy import (
    current_event_loop_policy_snapshot,
    ensure_default_event_loop_policy,
    is_explicit_default_event_loop_policy,
)


def test_ensure_default_event_loop_policy_installs_default_policy():
    snapshot = ensure_default_event_loop_policy()

    assert snapshot.class_name == current_event_loop_policy_snapshot().class_name
    assert is_explicit_default_event_loop_policy() is True
