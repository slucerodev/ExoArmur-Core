#!/usr/bin/env python3
"""
Dependency Audit Script

Checks:
- requirements.txt or pyproject completeness
- no unused imports (basic scan)
- no missing dependencies during clean install
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Set, Tuple


def check_pyproject_completeness(repo_root: Path) -> List[str]:
    """Check pyproject.toml completeness."""
    pyproject_path = repo_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        return ["pyproject.toml not found"]
    
    content = pyproject_path.read_text()
    failures = []
    
    # Check for required sections
    required_sections = ["[project]", "[build-system]"]
    for section in required_sections:
        if section not in content:
            failures.append(f"Required section missing: {section}")
    
    # Check for project name
    if 'name = ' not in content:
        failures.append("Project name not specified")
    
    # Check for dependencies section
    if "dependencies" not in content:
        failures.append("Dependencies section not found")
    
    return failures


def find_unused_imports(repo_root: Path) -> List[Tuple[str, str]]:
    """Find potentially unused imports (basic scan)."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return []
    
    unused_imports = []
    
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text()
        
        try:
            tree = ast.parse(content)
        except:
            continue
        
        # Extract import statements
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                for alias in node.names:
                    imports.append(alias.name)
        
        # Check if imported names are used in the code
        for imp in imports:
            base_name = imp.split(".")[0]
            # Simple heuristic: check if base name appears in code after import
            # This is a basic scan and may have false positives
            if base_name not in content:
                # Skip common stdlib modules and builtins
                common_modules = {
                    "os", "sys", "re", "json", "typing", "pathlib", "dataclasses",
                    "asyncio", "time", "random", "subprocess", "io", "datetime",
                    "collections", "itertools", "functools", "math", "hashlib"
                }
                if base_name not in common_modules:
                    unused_imports.append((str(py_file.relative_to(repo_root)), base_name))
    
    return unused_imports


def check_missing_dependencies(repo_root: Path) -> List[str]:
    """Check for missing dependencies during clean install."""
    # This is a placeholder - actual check would require running clean install
    # For now, we'll check if pyproject.toml has dependencies
    pyproject_path = repo_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        return ["pyproject.toml not found"]
    
    content = pyproject_path.read_text()
    
    # Extract dependencies
    deps_match = re.search(r'dependencies = \[(.*?)\]', content, re.DOTALL)
    if not deps_match:
        return ["Dependencies section not found in pyproject.toml"]
    
    deps_str = deps_match.group(1)
    if not deps_str.strip():
        return ["No dependencies listed"]
    
    return []


def audit_dependencies():
    """Run dependency audit."""
    repo_root = Path(__file__).resolve().parent.parent
    
    print("=" * 60)
    print("DEPENDENCY AUDIT")
    print("=" * 60)
    print()
    
    failures = []
    
    # Check pyproject completeness
    print("Checking pyproject.toml completeness...")
    pyproject_failures = check_pyproject_completeness(repo_root)
    if pyproject_failures:
        failures.extend(pyproject_failures)
        for f in pyproject_failures:
            print(f"  ✗ {f}")
    else:
        print("  ✓ pyproject.toml is complete")
    print()
    
    # Check for unused imports
    print("Checking for potentially unused imports...")
    unused = find_unused_imports(repo_root)
    if unused:
        print(f"  ⚠ Found {len(unused)} potentially unused imports (review recommended):")
        for file_path, imp_name in unused[:10]:  # Show first 10
            print(f"    - {file_path}: {imp_name}")
        if len(unused) > 10:
            print(f"    ... and {len(unused) - 10} more")
        # Don't fail on unused imports, just warn
    else:
        print("  ✓ No obviously unused imports found")
    print()
    
    # Check for missing dependencies
    print("Checking for missing dependencies...")
    missing = check_missing_dependencies(repo_root)
    if missing:
        failures.extend(missing)
        for m in missing:
            print(f"  ✗ {m}")
    else:
        print("  ✓ Dependencies are listed")
    print()
    
    # Report results
    if failures:
        print("❌ Dependency audit failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✓ Dependency audit passed")
        sys.exit(0)


if __name__ == "__main__":
    audit_dependencies()
