"""Shared stability report models and serialization helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import platform
import sys

from .asyncio_policy import EventLoopPolicySnapshot


@dataclass(frozen=True)
class TestOutcomeRecord:
    """Single test outcome captured during a stability run."""

    nodeid: str
    outcome: str
    classification: str | None = None
    duration_seconds: float | None = None
    module: str | None = None


@dataclass(frozen=True)
class FlakeRecord:
    """A test whose outcomes differed across stability runs."""

    nodeid: str
    outcomes: list[str]


@dataclass
class StabilityReport:
    """Structured stability report emitted by CI or pytest hooks."""

    run_label: str
    total_tests: int
    python_version: str = sys.version.split()[0]
    platform_system: str = platform.system()
    platform_release: str = platform.release()
    event_loop_policy: EventLoopPolicySnapshot | None = None
    failures_by_classification: dict[str, int] = field(default_factory=dict)
    test_outcomes: list[TestOutcomeRecord] = field(default_factory=list)
    flaky_tests: list[FlakeRecord] = field(default_factory=list)
    flake_rate: float = 0.0
    top_failing_modules: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


CLASSIFICATION_KEYS = ("DETERMINISM", "ASYNC", "TEST_DESIGN", "ENVIRONMENT")


def summarize_top_failing_modules(outcomes: Iterable[TestOutcomeRecord]) -> list[dict[str, Any]]:
    """Return modules sorted by failure count, descending."""

    counter: Counter[str] = Counter()
    for outcome in outcomes:
        if outcome.outcome != "failed":
            continue
        module = outcome.module or outcome.nodeid.split("::", 1)[0]
        counter[module] += 1

    return [
        {"module": module, "failures": count}
        for module, count in counter.most_common()
    ]


def normalize_report_payload(report: StabilityReport) -> dict[str, Any]:
    payload = asdict(report)
    if report.event_loop_policy is not None:
        payload["event_loop_policy"] = asdict(report.event_loop_policy)
    return payload


def write_report(report: StabilityReport, output_path: Path) -> Path:
    """Write a structured stability report to JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(normalize_report_payload(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
