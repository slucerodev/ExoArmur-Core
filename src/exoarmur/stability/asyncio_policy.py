"""Explicit asyncio policy helpers for deterministic entrypoints and tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class EventLoopPolicySnapshot:
    """Snapshot of the active event loop policy."""

    class_name: str
    module: str


def explicit_default_event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Return the platform default event loop policy explicitly."""

    return asyncio.DefaultEventLoopPolicy()


def ensure_default_event_loop_policy() -> EventLoopPolicySnapshot:
    """Install the explicit default asyncio policy and return a snapshot."""

    policy = explicit_default_event_loop_policy()
    asyncio.set_event_loop_policy(policy)
    return EventLoopPolicySnapshot(
        class_name=policy.__class__.__name__,
        module=policy.__class__.__module__,
    )


def current_event_loop_policy_snapshot() -> EventLoopPolicySnapshot:
    """Inspect the currently active asyncio policy without changing it."""

    policy = asyncio.get_event_loop_policy()
    return EventLoopPolicySnapshot(
        class_name=policy.__class__.__name__,
        module=policy.__class__.__module__,
    )


def default_event_loop_policy_snapshot() -> EventLoopPolicySnapshot:
    """Return the platform default asyncio policy snapshot without installing it."""

    policy = explicit_default_event_loop_policy()
    return EventLoopPolicySnapshot(
        class_name=policy.__class__.__name__,
        module=policy.__class__.__module__,
    )


def is_explicit_default_event_loop_policy() -> bool:
    """Return True when the active policy matches the explicit default policy."""

    return current_event_loop_policy_snapshot() == default_event_loop_policy_snapshot()
