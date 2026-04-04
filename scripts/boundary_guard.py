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
import subprocess
import sys
import ast
from pathlib import Path
from typing import List, Tuple, Set


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
    
    import re
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
    """Check for disallowed imports in Python source files using AST parsing."""
    violations = []
    
    # Disallowed import names and their reasons
    disallowed_imports = {
        'boto3': 'AWS SDK (boto3) - not allowed in core',
        'google.cloud': 'Google Cloud SDK - not allowed in core',
        'azure': 'Azure SDK - not allowed in core',
        'kubernetes': 'Kubernetes client - not allowed in core',
        'sklearn': 'Scikit-learn - not allowed in core',
        'tensorflow': 'TensorFlow - not allowed in core',
        'torch': 'PyTorch - not allowed in core',
        'pandas': 'Pandas - not allowed in core',
        'numpy': 'NumPy - not allowed in core',
        'scipy': 'SciPy - not allowed in core',
        'exoarmur.execution_boundary_v2': 'Direct execution_boundary_v2 import must route through exoarmur.feature_flags.resolver',
    }
    
    src_dir = Path('src/exoarmur')
    if not src_dir.is_dir():
        return violations

    allowed_boundary_file = src_dir / 'feature_flags' / 'resolver.py'
    py_files = sorted(src_dir.rglob('*.py'))
    print(f"Scanning {len(py_files)} Python files under {src_dir}")
    
    # Scan all Python files under src/exoarmur/
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find real import statements
            try:
                tree = ast.parse(content)
            except SyntaxError as exc:
                violations.append((str(py_file), f"Syntax error while parsing boundary scan: {exc.msg}"))
                continue
            
            # Walk AST to find import nodes
            for node in ast.walk(tree):
                module_name = None
                
                if isinstance(node, ast.Import):
                    # Handle: import module
                    for alias in node.names:
                        module_name = alias.name
                        break
                elif isinstance(node, ast.ImportFrom):
                    # Handle: from module import ...
                    if node.module:
                        module_name = node.module
                
                # Check if disallowed
                if module_name:
                    normalized_path = py_file.resolve()
                    if normalized_path == allowed_boundary_file.resolve() and module_name.startswith('exoarmur.execution_boundary_v2'):
                        continue

                    for disallowed, reason in disallowed_imports.items():
                        if module_name == disallowed or module_name.startswith(disallowed + '.'):
                            violations.append((str(py_file), reason))
                            break  # One violation per file is enough
                    
                    if violations and violations[-1][0] == str(py_file):
                        break  # Found violation for this file, move to next file
                        
        except (OSError, UnicodeDecodeError) as exc:
            violations.append((str(py_file), f"Unable to read file during boundary scan: {exc}"))
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
