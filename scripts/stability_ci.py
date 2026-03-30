#!/usr/bin/env python3
"""Run the full pytest suite three times and fail on any non-determinism."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from exoarmur.stability.asyncio_policy import current_event_loop_policy_snapshot
from exoarmur.stability.reporting import FlakeRecord, StabilityReport, TestOutcomeRecord, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="How many times to execute the pytest suite.",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Additional arguments to pass to pytest.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path(os.environ.get("EXOARMUR_STABILITY_REPORT", "stability_report.json")),
        help="Final aggregated stability report location.",
    )
    parser.add_argument(
        "--run-report-dir",
        type=Path,
        default=Path(".stability-runs"),
        help="Directory for per-run JSON reports.",
    )
    return parser


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_pytest_once(*, run_index: int, total_runs: int, run_report_dir: Path, pytest_args: list[str]) -> tuple[int, Path]:
    run_report_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_report_dir / f"run-{run_index}.json"
    env = os.environ.copy()
    env["EXOARMUR_STABILITY_RUN_LABEL"] = f"run-{run_index}-of-{total_runs}"
    env["EXOARMUR_STABILITY_REPORT"] = str(report_path)
    env.setdefault("PYTHONHASHSEED", "0")

    cmd = [sys.executable, "-m", "pytest", "-q", *pytest_args]
    print(f"\n=== Stability run {run_index}/{total_runs} ===")
    print(" ".join(cmd))
    completed = subprocess.run(cmd, env=env, check=False)
    if not report_path.exists():
        raise RuntimeError(f"Pytest did not write a stability report at {report_path}")
    return completed.returncode, report_path


def _index_outcomes(report: dict[str, Any]) -> dict[str, str]:
    outcomes = {}
    for record in report.get("test_outcomes", []):
        classification = record.get("classification")
        outcome = record.get("outcome", "unknown")
        nodeid = record.get("nodeid")
        if classification:
            outcomes[nodeid] = f"{outcome}[{classification}]"
        else:
            outcomes[nodeid] = outcome
    return outcomes


def _aggregate_reports(run_reports: list[dict[str, Any]], run_exit_codes: list[int]) -> StabilityReport:
    outcome_sequences: dict[str, list[str]] = defaultdict(list)
    aggregated_outcomes: list[TestOutcomeRecord] = []
    aggregated_failures: Counter[str] = Counter()
    flaky_tests: list[FlakeRecord] = []

    for report in run_reports:
        for record in report.get("test_outcomes", []):
            classification = record.get("classification")
            outcome = record.get("outcome", "unknown")
            nodeid = record.get("nodeid")
            if classification:
                outcome_sequences[nodeid].append(f"{outcome}[{classification}]")
                aggregated_failures[classification] += 1 if outcome == "failed" else 0
            else:
                outcome_sequences[nodeid].append(outcome)
            aggregated_outcomes.append(
                TestOutcomeRecord(
                    nodeid=nodeid,
                    outcome=outcome,
                    classification=classification,
                    duration_seconds=record.get("duration_seconds"),
                    module=record.get("module"),
                )
            )

    for nodeid, outcomes in sorted(outcome_sequences.items()):
        if len(set(outcomes)) > 1:
            flaky_tests.append(FlakeRecord(nodeid=nodeid, outcomes=outcomes))

    total_tests = max((report.get("total_tests", 0) for report in run_reports), default=0)
    flake_rate = (len(flaky_tests) / total_tests) if total_tests else 0.0
    top_failing_modules = []
    module_counter: Counter[str] = Counter()
    for outcome in aggregated_outcomes:
        if outcome.outcome == "failed":
            module_counter[outcome.module or outcome.nodeid.split("::", 1)[0]] += 1
    for module, count in module_counter.most_common():
        top_failing_modules.append({"module": module, "failures": count})

    notes = [f"Run exit codes: {run_exit_codes}"]
    if flaky_tests:
        notes.append(f"Flaky tests detected: {len(flaky_tests)}")
    else:
        notes.append("No outcome divergence detected across runs.")

    return StabilityReport(
        run_label="three-run-aggregate",
        total_tests=total_tests,
        event_loop_policy=current_event_loop_policy_snapshot(),
        failures_by_classification=dict(aggregated_failures),
        test_outcomes=aggregated_outcomes,
        flaky_tests=flaky_tests,
        flake_rate=flake_rate,
        top_failing_modules=top_failing_modules,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_reports: list[dict[str, Any]] = []
    run_exit_codes: list[int] = []

    for run_index in range(1, args.runs + 1):
        exit_code, report_path = _run_pytest_once(
            run_index=run_index,
            total_runs=args.runs,
            run_report_dir=args.run_report_dir,
            pytest_args=args.pytest_args,
        )
        run_exit_codes.append(exit_code)
        run_reports.append(_load_report(report_path))

    aggregate_report = _aggregate_reports(run_reports, run_exit_codes)
    write_report(aggregate_report, args.report_file)

    print("\n=== Stability aggregate summary ===")
    print(f"Runs: {args.runs}")
    print(f"Aggregate report: {args.report_file}")
    print(f"Flaky tests: {len(aggregate_report.flaky_tests)}")
    print(f"Flake rate: {aggregate_report.flake_rate:.6f}")
    print(f"Top failing modules: {aggregate_report.top_failing_modules}")

    if any(exit_code != 0 for exit_code in run_exit_codes):
        print("At least one pytest run failed.")
        return 1

    if aggregate_report.flaky_tests:
        print("Outcome divergence detected across repeated runs.")
        for flaky in aggregate_report.flaky_tests[:10]:
            print(f"- {flaky.nodeid}: {flaky.outcomes}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
