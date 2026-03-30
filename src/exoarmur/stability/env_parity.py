"""Environment parity checks for CI and local stability validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Iterable
import os
import platform
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .asyncio_policy import default_event_loop_policy_snapshot, current_event_loop_policy_snapshot

DEFAULT_EVENT_LOOP_POLICY_NAME = default_event_loop_policy_snapshot().class_name


@dataclass(frozen=True)
class LockedDependency:
    """Exact pinned package version from the lock file."""

    name: str
    version: str


@dataclass
class EnvironmentParityReport:
    """Structured result for environment parity validation."""

    expected_python_version: str
    actual_python_version: str
    expected_platform: str
    actual_platform: str
    expected_policy: str
    actual_policy: str
    expected_hash_seed: str
    actual_hash_seed: str | None
    locked_dependencies: list[LockedDependency] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)


class EnvironmentParityError(RuntimeError):
    """Raised when the local environment does not match the locked CI environment."""


IGNORED_REQUIREMENT_PREFIXES = ("#", "-r ", "--")


def _read_locked_dependency_lines(lock_file: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in lock_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(IGNORED_REQUIREMENT_PREFIXES):
            continue
        lines.append(line)
    return lines


def load_locked_dependencies(lock_file: Path) -> list[LockedDependency]:
    """Parse a simple exact-pin requirements lock file."""

    locked_dependencies: list[LockedDependency] = []
    for line in _read_locked_dependency_lines(lock_file):
        requirement = Requirement(line)
        if requirement.specifier:
            for specifier in requirement.specifier:
                if specifier.operator == "==":
                    locked_dependencies.append(
                        LockedDependency(
                            name=canonicalize_name(requirement.name),
                            version=specifier.version,
                        )
                    )
                    break
            else:
                raise EnvironmentParityError(
                    f"Lock file entry is not an exact pin: {line!r}"
                )
        else:
            raise EnvironmentParityError(f"Lock file entry is missing a version pin: {line!r}")
    return locked_dependencies


def validate_locked_dependencies(locked_dependencies: Iterable[LockedDependency]) -> list[str]:
    """Return human-readable mismatch messages for locked dependency versions."""

    mismatches: list[str] = []
    for locked in locked_dependencies:
        try:
            installed_version = metadata.version(locked.name)
        except metadata.PackageNotFoundError:
            mismatches.append(f"missing package: {locked.name}=={locked.version}")
            continue

        if installed_version != locked.version:
            mismatches.append(
                f"version mismatch: {locked.name} expected {locked.version} but found {installed_version}"
            )
    return mismatches


def validate_environment_parity(
    *,
    lock_file: Path,
    expected_python_version: str,
    expected_platform: str,
    expected_policy: str = DEFAULT_EVENT_LOOP_POLICY_NAME,
    expected_hash_seed: str = "0",
) -> EnvironmentParityReport:
    """Validate the current runtime environment against the locked CI environment."""

    actual_python_version = platform.python_version()
    actual_platform = platform.system()
    actual_policy = current_event_loop_policy_snapshot().class_name
    actual_hash_seed = os.environ.get("PYTHONHASHSEED")
    locked_dependencies = load_locked_dependencies(lock_file)
    mismatches = validate_locked_dependencies(locked_dependencies)

    if actual_python_version != expected_python_version:
        mismatches.append(
            f"python version mismatch: expected {expected_python_version} but found {actual_python_version}"
        )

    if actual_platform != expected_platform:
        mismatches.append(
            f"platform mismatch: expected {expected_platform} but found {actual_platform}"
        )

    if actual_policy != expected_policy:
        mismatches.append(
            f"event loop policy mismatch: expected {expected_policy} but found {actual_policy}"
        )

    if actual_hash_seed != expected_hash_seed:
        mismatches.append(
            f"PYTHONHASHSEED mismatch: expected {expected_hash_seed} but found {actual_hash_seed!r}"
        )

    return EnvironmentParityReport(
        expected_python_version=expected_python_version,
        actual_python_version=actual_python_version,
        expected_platform=expected_platform,
        actual_platform=actual_platform,
        expected_policy=expected_policy,
        actual_policy=actual_policy,
        expected_hash_seed=expected_hash_seed,
        actual_hash_seed=actual_hash_seed,
        locked_dependencies=locked_dependencies,
        mismatches=mismatches,
    )


def ensure_environment_parity(
    *,
    lock_file: Path,
    expected_python_version: str,
    expected_platform: str,
    expected_policy: str = DEFAULT_EVENT_LOOP_POLICY_NAME,
    expected_hash_seed: str = "0",
) -> EnvironmentParityReport:
    """Validate environment parity and raise if any mismatch is detected."""

    report = validate_environment_parity(
        lock_file=lock_file,
        expected_python_version=expected_python_version,
        expected_platform=expected_platform,
        expected_policy=expected_policy,
        expected_hash_seed=expected_hash_seed,
    )
    if report.mismatches:
        raise EnvironmentParityError("\n".join(report.mismatches))
    return report


def default_expected_platform() -> str:
    """Return the expected platform for the current CI gate.

    The primary invariant gate currently runs on Linux runners.
    """

    return "Linux"


def default_expected_python_version() -> str:
    """Return the exact Python version the primary invariant gate expects.

    This defaults to the version currently used by the core invariant workflow.
    """

    return sys.version.split()[0]


def default_event_loop_policy_name() -> str:
    """Return the explicit default event-loop policy class name."""

    return DEFAULT_EVENT_LOOP_POLICY_NAME
