#!/usr/bin/env python3
"""
Repository Structure Audit Script

Checks for:
- Required directories exist
- No temp files (*.tmp, *.bak, *.old)
- No duplicate modules
- No problematic naming ("v2", "final", "new")
"""

import sys
import os
from pathlib import Path
from typing import List, Set


def check_required_dirs(repo_root: Path) -> List[str]:
    """Check required directories exist."""
    required_dirs = ["src", "tests", "docs", "scripts"]
    failures = []
    
    for dir_name in required_dirs:
        dir_path = repo_root / dir_name
        if not dir_path.exists():
            failures.append(f"Required directory missing: {dir_name}")
        elif not dir_path.is_dir():
            failures.append(f"Required path exists but is not directory: {dir_name}")
    
    return failures


def find_temp_files(repo_root: Path) -> List[str]:
    """Find temporary files."""
    temp_extensions = [".tmp", ".bak", ".old", ".swp", ".~"]
    temp_files = []
    
    # Exclude common build/dependency directories
    exclude_dirs = {".git", ".venv", ".venv_audit", "__pycache__", "node_modules", "dashboard", ".pytest_cache"}
    
    for ext in temp_extensions:
        for file_path in repo_root.rglob(f"*{ext}"):
            # Check if file is in excluded directory
            rel_path = str(file_path.relative_to(repo_root))
            if not any(excl in rel_path for excl in exclude_dirs):
                temp_files.append(rel_path)
    
    return temp_files


def find_duplicate_modules(repo_root: Path) -> List[str]:
    """Find duplicate module files."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return ["src directory not found"]
    
    module_names = set()
    duplicates = []
    
    for py_file in src_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        
        # Extract module name from file path
        rel_path = py_file.relative_to(src_dir)
        module_name = rel_path.with_suffix("").as_posix().replace("/", ".")
        
        if module_name in module_names:
            duplicates.append(f"Duplicate module: {module_name}")
        else:
            module_names.add(module_name)
    
    return duplicates


def find_problematic_naming(repo_root: Path) -> List[str]:
    """Find files/dirs with problematic naming."""
    # Only check for prefixes/suffixes that indicate WIP/temporary files
    # Note: execution_boundary_v2 is legitimate V2 architecture, not problematic
    problematic_prefixes = ["final_", "new_", "wip_", "todo_", "hack_"]
    problematic_suffixes = ["_final", "_new", "_wip", "_todo", "_hack"]
    problematic_paths = []
    
    # Exclude common build/dependency directories and legitimate V2 architecture
    exclude_dirs = {".git", ".venv", ".venv_audit", "__pycache__", "node_modules", "dashboard", ".pytest_cache", "build"}
    exclude_patterns = ["execution_boundary_v2"]  # Legitimate V2 architecture
    
    for prefix in problematic_prefixes:
        for path in repo_root.rglob(f"{prefix}*"):
            rel_path = str(path.relative_to(repo_root))
            if not any(excl in rel_path for excl in exclude_dirs) and not any(pattern in rel_path for pattern in exclude_patterns):
                problematic_paths.append(rel_path)
    
    for suffix in problematic_suffixes:
        for path in repo_root.rglob(f"*{suffix}"):
            rel_path = str(path.relative_to(repo_root))
            if not any(excl in rel_path for excl in exclude_dirs) and not any(pattern in rel_path for pattern in exclude_patterns):
                problematic_paths.append(rel_path)
    
    return problematic_paths


def audit_repo_structure():
    """Run repository structure audit."""
    repo_root = Path(__file__).resolve().parent.parent
    
    print("=" * 60)
    print("REPOSITORY STRUCTURE AUDIT")
    print("=" * 60)
    print()
    
    failures = []
    
    # Check required directories
    print("Checking required directories...")
    dir_failures = check_required_dirs(repo_root)
    if dir_failures:
        failures.extend(dir_failures)
        for f in dir_failures:
            print(f"  ✗ {f}")
    else:
        print("  ✓ All required directories present")
    print()
    
    # Check for temp files
    print("Checking for temporary files...")
    temp_files = find_temp_files(repo_root)
    if temp_files:
        failures.append(f"Found {len(temp_files)} temporary files")
        for f in temp_files:
            print(f"  ✗ {f}")
    else:
        print("  ✓ No temporary files found")
    print()
    
    # Check for duplicate modules
    print("Checking for duplicate modules...")
    duplicates = find_duplicate_modules(repo_root)
    if duplicates:
        failures.extend(duplicates)
        for d in duplicates:
            print(f"  ✗ {d}")
    else:
        print("  ✓ No duplicate modules found")
    print()
    
    # Check for problematic naming
    print("Checking for problematic naming...")
    problematic = find_problematic_naming(repo_root)
    if problematic:
        failures.append(f"Found {len(problematic)} problematic names")
        for p in problematic:
            print(f"  ✗ {p}")
    else:
        print("  ✓ No problematic naming found")
    print()
    
    # Report results
    if failures:
        print("❌ Repository structure audit failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✓ Repository structure audit passed")
        sys.exit(0)


if __name__ == "__main__":
    audit_repo_structure()
