#!/usr/bin/env python3
"""
ExoArmur Repository Boundary Guard

Enforces repository hygiene and prevents committing forbidden artifacts.
Uses only Python standard library - no project imports.

Exit codes:
- 0: PASS (boundary clean)
- 2: FAIL (boundary violations detected)
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_git_command(args: List[str]) -> str:
    """Run git command and return stdout."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"BOUNDARY GUARD: ERROR - git command failed: {' '.join(args)}")
        print(f"Error: {e.stderr.strip()}")
        sys.exit(2)


def get_tracked_files() -> List[str]:
    """Get list of all Git-tracked files."""
    try:
        output = run_git_command(['ls-files'])
        return output.split('\n') if output else []
    except Exception:
        return []


def check_forbidden_patterns(tracked_files: List[str]) -> List[Tuple[str, str]]:
    """Check for forbidden file patterns in tracked files."""
    violations = []
    
    # Forbidden patterns and their reasons
    forbidden_patterns = [
        (r'^data/', 'Runtime state directory (data/) should not be committed'),
        (r'^logs/', 'Runtime logs directory (logs/) should not be committed'),
        (r'^artifacts/reality_run_.*', 'Evidence bundles (artifacts/reality_run_*) should not be committed'),
        (r'.*__pycache__/.*', 'Python bytecode (__pycache__/) should not be committed'),
        (r'.*\.pyc$', 'Compiled Python files (*.pyc) should not be committed'),
        (r'^\.venv/', 'Virtual environment (.venv/) should not be committed'),
        (r'^venv/', 'Virtual environment (venv/) should not be committed'),
        (r'.*\.log$', 'Log files (*.log) should not be committed'),
        (r'^\.pytest_cache/', 'pytest cache (.pytest_cache/) should not be committed'),
        (r'^\.mypy_cache/', 'MyPy cache (.mypy_cache/) should not be committed'),
        (r'^\.ruff_cache/', 'Ruff cache (.ruff_cache/) should not be committed'),
        (r'^\.coverage', 'Coverage files (.coverage) should not be committed'),
        (r'^htmlcov/', 'Coverage HTML reports (htmlcov/) should not be committed'),
    ]
    
    for file_path in tracked_files:
        for pattern, reason in forbidden_patterns:
            if re.match(pattern, file_path):
                violations.append((file_path, reason))
    
    return violations


def check_forbidden_directories() -> List[Tuple[str, str]]:
    """Check for forbidden directories in repository root."""
    violations = []
    repo_root = Path('.')
    
    forbidden_dirs = [
        ('experimental', 'Experimental code directory must not exist in core repo'),
        ('enterprise', 'Enterprise code directory must not exist in core repo'),
        ('proprietary', 'Proprietary code directory must not exist in core repo'),
    ]
    
    for dir_name, reason in forbidden_dirs:
        dir_path = repo_root / dir_name
        if dir_path.is_dir():
            violations.append((str(dir_path), reason))
    
    return violations


def check_disallowed_imports() -> List[Tuple[str, str]]:
    """Check for disallowed imports in Python source files."""
    violations = []
    
    # Disallowed import patterns and their reasons
    disallowed_imports = [
        (r'\bboto3\b', 'AWS SDK (boto3) - not allowed in core'),
        (r'\bgoogle\.cloud\b', 'Google Cloud SDK - not allowed in core'),
        (r'\bazure\b', 'Azure SDK - not allowed in core'),
        (r'\bkubernetes\b', 'Kubernetes client - not allowed in core'),
        (r'\bsklearn\b', 'Scikit-learn - not allowed in core'),
        (r'\btensorflow\b', 'TensorFlow - not allowed in core'),
        (r'\btorch\b', 'PyTorch - not allowed in core'),
        (r'\bpandas\b', 'Pandas - not allowed in core'),
        (r'\bnumpy\b', 'NumPy - not allowed in core'),
        (r'\bscipy\b', 'SciPy - not allowed in core'),
    ]
    
    src_dir = Path('src')
    if not src_dir.is_dir():
        return violations
    
    # Scan all Python files under src/
    for py_file in src_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern, reason in disallowed_imports:
                    if re.search(pattern, content):
                        violations.append((str(py_file), reason))
                        break  # One violation per file is enough
        except (OSError, UnicodeDecodeError):
            # Skip files we can't read
            continue
    
    return violations


def main():
    """Main boundary guard execution."""
    print("BOUNDARY GUARD: Checking repository boundaries...")
    
    violations = []
    
    # Check 1: Forbidden patterns in tracked files
    tracked_files = get_tracked_files()
    violations.extend(check_forbidden_patterns(tracked_files))
    
    # Check 2: Forbidden directories
    violations.extend(check_forbidden_directories())
    
    # Check 3: Disallowed imports
    violations.extend(check_disallowed_imports())
    
    if violations:
        print("BOUNDARY GUARD: FAIL")
        print("Repository boundary violations detected:")
        for file_path, reason in violations:
            print(f"  VIOLATION: {file_path} - {reason}")
        sys.exit(2)
    else:
        print("BOUNDARY GUARD: PASS")
        sys.exit(0)


if __name__ == '__main__':
    main()
