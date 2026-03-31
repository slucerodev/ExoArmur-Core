#!/usr/bin/env python3
"""Validate that the active environment matches the locked CI environment."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from exoarmur.stability.asyncio_policy import ensure_default_event_loop_policy
from exoarmur.stability.asyncio_policy import current_event_loop_policy_snapshot
from exoarmur.stability.env_parity import (
    EnvironmentParityError,
    default_event_loop_policy_name,
    default_expected_platform,
    default_expected_python_version,
    ensure_environment_parity,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("requirements.lock"),
        help="Exact-pinned requirements lock file to validate against.",
    )
    parser.add_argument(
        "--expected-python-version",
        default=os.environ.get("EXOARMUR_EXPECTED_PYTHON_VERSION", default_expected_python_version()),
        help="Exact Python version expected by the CI gate.",
    )
    parser.add_argument(
        "--expected-platform",
        default=os.environ.get("EXOARMUR_EXPECTED_PLATFORM", default_expected_platform()),
        help="Expected platform name (for example, Linux).",
    )
    parser.add_argument(
        "--expected-policy",
        default=os.environ.get("EXOARMUR_EXPECTED_EVENT_LOOP_POLICY", default_event_loop_policy_name()),
        help="Expected asyncio event-loop policy class name.",
    )
    parser.add_argument(
        "--expected-hash-seed",
        default=os.environ.get("PYTHONHASHSEED", "0"),
        help="Expected PYTHONHASHSEED value.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path(os.environ.get("EXOARMUR_STABILITY_REPORT", "stability_report.json")),
        help="Path where the JSON parity report should be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    ensure_default_event_loop_policy()

    try:
        report = ensure_environment_parity(
            lock_file=args.lock_file,
            expected_python_version=args.expected_python_version,
            expected_platform=args.expected_platform,
            expected_policy=args.expected_policy,
            expected_hash_seed=args.expected_hash_seed,
        )
    except EnvironmentParityError as exc:
        payload = {
            "status": "failed",
            "expected_python_version": args.expected_python_version,
            "actual_python_version": platform.python_version(),
            "expected_platform": args.expected_platform,
            "actual_platform": platform.system(),
            "expected_policy": args.expected_policy,
            "actual_policy": current_event_loop_policy_snapshot().class_name,
            "expected_hash_seed": args.expected_hash_seed,
            "actual_hash_seed": os.environ.get("PYTHONHASHSEED"),
            "lock_file": str(args.lock_file),
            "mismatches": str(exc).splitlines(),
        }
        args.report_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Environment parity check failed:")
        for mismatch in payload["mismatches"]:
            print(f"- {mismatch}")
        print(f"Report written to: {args.report_file}")
        return 1

    payload = asdict(report)
    payload.update(
        {
            "status": "passed",
            "lock_file": str(args.lock_file),
        }
    )
    args.report_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Environment parity check passed.")
    print(f"Python: {report.actual_python_version}")
    print(f"Platform: {report.actual_platform}")
    print(f"Event loop policy: {report.actual_policy}")
    print(f"PYTHONHASHSEED: {report.actual_hash_seed}")
    print(f"Locked dependencies validated: {len(report.locked_dependencies)}")
    print(f"Report written to: {args.report_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
