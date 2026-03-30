"""Pytest plugin for deterministic failure classification and stability reporting."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import random
import re

import pytest

from .asyncio_policy import current_event_loop_policy_snapshot, ensure_default_event_loop_policy
from .reporting import (
    CLASSIFICATION_KEYS,
    StabilityReport,
    TestOutcomeRecord,
    summarize_top_failing_modules,
    write_report,
)

ASYNC_PATTERNS = [
    r"event loop",
    r"not awaited",
    r"attached to a different loop",
    r"coroutine was never awaited",
    r"task was destroyed but it is pending",
    r"asyncio",
]

ENVIRONMENT_PATTERNS = [
    r"modulenotfounderror",
    r"importerror",
    r"no module named",
    r"versionconflict",
    r"invalid version",
    r"requires-python",
    r"dependency resolution",
    r"distribution.*not found",
]

DETERMINISM_PATTERNS = [
    r"order mismatch",
    r"different order",
    r"non-deterministic",
    r"deterministic",
    r"snapshot mismatch",
    r"hash mismatch",
    r"state drift",
    r"flake",
    r"inconsistent",
]


@dataclass
class StabilityState:
    """Mutable state accumulated during a single pytest run."""

    run_label: str
    output_path: Path
    total_tests: int = 0
    failures_by_classification: Counter[str] = field(default_factory=Counter)
    outcomes: list[TestOutcomeRecord] = field(default_factory=list)


_STATE_ATTR = "_exoarmur_stability_state"


def _get_state(config: pytest.Config) -> StabilityState:
    state = getattr(config, _STATE_ATTR, None)
    if state is None:
        output_path = Path(os.environ.get("EXOARMUR_STABILITY_REPORT", "stability_report.json"))
        state = StabilityState(
            run_label=os.environ.get("EXOARMUR_STABILITY_RUN_LABEL", "pytest"),
            output_path=output_path,
        )
        setattr(config, _STATE_ATTR, state)
    return state


def _normalize(text: str) -> str:
    return text.lower().replace("\n", " ")


def classify_failure_text(text: str) -> str:
    """Classify a failure using simple deterministic heuristics."""

    normalized = _normalize(text)

    for pattern in ASYNC_PATTERNS:
        if re.search(pattern, normalized):
            return "ASYNC"

    for pattern in ENVIRONMENT_PATTERNS:
        if re.search(pattern, normalized):
            return "ENVIRONMENT"

    for pattern in DETERMINISM_PATTERNS:
        if re.search(pattern, normalized):
            return "DETERMINISM"

    return "TEST_DESIGN"


def _prefix_longrepr(report: pytest.TestReport, classification: str) -> None:
    prefix = f"[{classification}] "
    longrepr = getattr(report, "longrepr", None)

    if hasattr(longrepr, "reprcrash") and getattr(longrepr, "reprcrash", None) is not None:
        longrepr.reprcrash.message = f"{prefix}{longrepr.reprcrash.message}"
        return

    if isinstance(longrepr, str):
        report.longrepr = f"{prefix}{longrepr}"
        return

    report.longrepr = f"{prefix}{str(longrepr)}"


def pytest_configure(config: pytest.Config) -> None:
    """Install deterministic defaults at pytest startup."""

    ensure_default_event_loop_policy()
    random.seed(0)
    _get_state(config)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    """Classify failures and annotate failing reports."""

    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    state = _get_state(item.config)
    module_name = getattr(getattr(item, "module", None), "__name__", None)

    if report.failed:
        longrepr_text = getattr(report, "longreprtext", None) or str(report.longrepr)
        classification = classify_failure_text(longrepr_text)
        state.failures_by_classification[classification] += 1
        _prefix_longrepr(report, classification)
        report.user_properties.append(("stability_classification", classification))
        state.outcomes.append(
            TestOutcomeRecord(
                nodeid=report.nodeid,
                outcome="failed",
                classification=classification,
                duration_seconds=report.duration,
                module=module_name,
            )
        )
    elif report.passed:
        state.outcomes.append(
            TestOutcomeRecord(
                nodeid=report.nodeid,
                outcome="passed",
                duration_seconds=report.duration,
                module=module_name,
            )
        )
    elif report.skipped:
        state.outcomes.append(
            TestOutcomeRecord(
                nodeid=report.nodeid,
                outcome="skipped",
                duration_seconds=report.duration,
                module=module_name,
            )
        )

    state.total_tests += 1


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, exitstatus: int) -> None:
    """Print a deterministic stability summary and emit a JSON artifact."""

    config = terminalreporter.config
    state = _get_state(config)
    failures = {key: state.failures_by_classification.get(key, 0) for key in CLASSIFICATION_KEYS}
    report = StabilityReport(
        run_label=state.run_label,
        total_tests=state.total_tests,
        event_loop_policy=current_event_loop_policy_snapshot(),
        failures_by_classification=failures,
        test_outcomes=state.outcomes,
        top_failing_modules=summarize_top_failing_modules(state.outcomes),
        flake_rate=0.0,
        notes=["Single-run stability report; flake aggregation happens in CI runner script."],
    )
    write_report(report, state.output_path)

    terminalreporter.write_sep("=", "ExoArmur stability classification summary")
    terminalreporter.write_line(f"Total tests observed: {state.total_tests}")
    for key in CLASSIFICATION_KEYS:
        terminalreporter.write_line(f"{key}: {failures[key]}")
    terminalreporter.write_line(f"Stability report written to: {state.output_path}")
