#!/usr/bin/env python3
"""Boundary enforcement for core/modules separation."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


def load_manifest(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_python_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if p.is_file()]


def extract_imports(file_path: Path) -> List[Tuple[int, str]]:
    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    imports: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                imports.append((node.lineno, node.module))
    return imports


def matches_prefix(name: str, prefixes: Iterable[str]) -> bool:
    for prefix in prefixes:
        if name == prefix or name.startswith(f"{prefix}."):
            return True
    return False


def gather_module_prefixes(module_prefixes: Dict[str, List[str]]) -> List[str]:
    prefixes: List[str] = []
    for values in module_prefixes.values():
        prefixes.extend(values)
    return prefixes


def check_core(
    core_paths: List[str],
    module_prefixes: Dict[str, List[str]],
    allowed_core_externals: List[str],
) -> List[str]:
    errors: List[str] = []
    module_prefix_list = gather_module_prefixes(module_prefixes)

    for core_path in core_paths:
        root = Path(core_path)
        for file_path in iter_python_files(root):
            for lineno, imported in extract_imports(file_path):
                if matches_prefix(imported, ["modules"]):
                    errors.append(
                        f"CORE_IMPORT_VIOLATION {file_path}:{lineno} imports '{imported}' (modules namespace)"
                    )
                    continue
                if matches_prefix(imported, module_prefix_list):
                    errors.append(
                        f"CORE_IMPORT_VIOLATION {file_path}:{lineno} imports '{imported}' (module prefix)"
                    )
                    continue
                if matches_prefix(imported, allowed_core_externals):
                    continue
    return errors


def check_modules(
    modules_root: Path,
    module_prefixes: Dict[str, List[str]],
    allowed_core_prefixes: List[str],
) -> List[str]:
    errors: List[str] = []
    if not modules_root.exists():
        return errors

    all_module_prefixes = gather_module_prefixes(module_prefixes)
    module_dirs = [p for p in modules_root.iterdir() if p.is_dir()]

    for module_dir in module_dirs:
        module_name = module_dir.name
        prefixes = module_prefixes.get(module_name)
        if prefixes is None:
            errors.append(
                f"MODULE_MANIFEST_MISSING {module_dir} is not declared in boundary_manifest.json"
            )
            continue

        for file_path in iter_python_files(module_dir):
            for lineno, imported in extract_imports(file_path):
                if matches_prefix(imported, ["modules"]):
                    errors.append(
                        f"MODULE_IMPORT_VIOLATION {file_path}:{lineno} imports '{imported}' (modules namespace)"
                    )
                    continue
                if matches_prefix(imported, allowed_core_prefixes):
                    continue
                if matches_prefix(imported, prefixes):
                    continue
                if matches_prefix(imported, all_module_prefixes):
                    errors.append(
                        f"MODULE_IMPORT_VIOLATION {file_path}:{lineno} imports '{imported}' (other module prefix)"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check core/module boundary imports.")
    parser.add_argument(
        "--manifest",
        default="tools/boundary_manifest.json",
        help="Path to boundary manifest JSON",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    core_paths = [str(Path(p)) for p in manifest.get("core_paths", [])]
    modules_root = Path(manifest.get("modules_root", "modules"))
    module_prefixes = manifest.get("module_prefixes", {})
    allowed_core_prefixes = manifest.get("allowed_core_prefixes", [])
    allowed_core_externals = manifest.get("allowed_core_externals", [])

    errors = []
    errors.extend(check_core(core_paths, module_prefixes, allowed_core_externals))
    errors.extend(check_modules(modules_root, module_prefixes, allowed_core_prefixes))

    if errors:
        print("Boundary check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Boundary check passed: no cross-module import violations detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
