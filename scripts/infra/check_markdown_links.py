#!/usr/bin/env python3
"""Validate relative markdown links inside the repository."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

EXCLUDED_PATH_SUBSTRINGS: tuple[str, ...] = (
    "/history/archive-",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Markdown files or directories to scan for relative links.",
    )
    return parser


def _is_excluded(path: Path) -> bool:
    posix = path.as_posix()
    return any(fragment in posix for fragment in EXCLUDED_PATH_SUBSTRINGS)


def _iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                sorted(
                    candidate
                    for candidate in path.rglob("*.md")
                    if not _is_excluded(candidate)
                )
            )
        elif path.suffix.lower() == ".md" and not _is_excluded(path):
            files.append(path)
    return files


def _is_external_target(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme or parsed.netloc or target.startswith("#") or target.startswith("mailto:"))


def _resolve_target(source: Path, target: str) -> Path:
    path_part = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not path_part:
        return source
    if path_part.startswith("/"):
        return (REPO_ROOT / path_part.lstrip("/")).resolve()
    return (source.parent / path_part).resolve()


def scan_file(file_path: Path) -> list[str]:
    broken_links: list[str] = []
    contents = file_path.read_text(encoding="utf-8")
    for match in MARKDOWN_LINK_RE.finditer(contents):
        target = match.group(1).strip()
        if _is_external_target(target):
            continue
        resolved = _resolve_target(file_path, target)
        if not resolved.exists():
            broken_links.append(f"{file_path}: {target} -> {resolved}")
    return broken_links


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    markdown_files = _iter_markdown_files(args.paths)

    broken_links: list[str] = []
    for markdown_file in markdown_files:
        broken_links.extend(scan_file(markdown_file))

    if broken_links:
        print("Broken markdown links found:")
        for broken in broken_links:
            print(f"- {broken}")
        return 1

    print(f"Validated {len(markdown_files)} markdown files with no broken relative links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
