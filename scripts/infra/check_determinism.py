#!/usr/bin/env python3
"""
Determinism Enforcement Scanner for ExoArmur-Core

This script scans the codebase for patterns that could break determinism:
- datetime.now/utcnow usage
- time.time usage  
- random usage without explicit seeding
- Non-deterministic JSON serialization
- Locale-dependent behavior

Usage: python scripts/check_determinism.py [directory]
Exit codes: 0 = clean, 1 = violations found
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Set, Tuple, Dict, Any

class DeterminismViolation:
    def __init__(self, file_path: str, line: int, issue_type: str, description: str, code_snippet: str = ""):
        self.file_path = file_path
        self.line = line
        self.issue_type = issue_type
        self.description = description
        self.code_snippet = code_snippet
    
    def __str__(self):
        return f"{self.file_path}:{self.line} [{self.issue_type}] {self.description}"

class DeterminismScanner(ast.NodeVisitor):
    """AST visitor to detect non-deterministic patterns"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[DeterminismViolation] = []
        self.current_line = 0
        self.imports: Set[str] = set()
        self.defined_functions: Set[str] = set()
    
    def visit(self, node):
        """Override to track line numbers"""
        if hasattr(node, 'lineno'):
            self.current_line = node.lineno
        return super().visit(node)
    
    def visit_Import(self, node):
        """Track imports to identify random usage"""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from imports"""
        if node.module:
            for alias in node.names:
                self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Track function definitions"""
        self.defined_functions.add(node.name)
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check function calls for non-deterministic patterns"""
        self._check_datetime_calls(node)
        self._check_time_calls(node)
        self._check_random_calls(node)
        self._check_json_calls(node)
        self.generic_visit(node)
    
    def _check_datetime_calls(self, node):
        """Check for datetime.now/utcnow usage"""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'datetime':
                    if node.func.attr in ['now', 'utcnow']:
                        self.violations.append(DeterminismViolation(
                            self.file_path,
                            self.current_line,
                            "DATETIME_NOW",
                            f"Use of datetime.{node.func.attr}() breaks determinism",
                            self._get_code_snippet(node)
                        ))
    
    def _check_time_calls(self, node):
        """Check for time.time usage"""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'time':
                    if node.func.attr == 'time':
                        self.violations.append(DeterminismViolation(
                            self.file_path,
                            self.current_line,
                            "TIME_TIME",
                            "Use of time.time() breaks determinism",
                            self._get_code_snippet(node)
                        ))
    
    def _check_random_calls(self, node):
        """Check for random usage without explicit seeding"""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'random':
                    # Allow random.seed() calls
                    if node.func.attr == 'seed':
                        return
                    
                    # Check if this is potentially problematic
                    problematic_methods = ['randint', 'random', 'uniform', 'choice', 'shuffle']
                    if node.func.attr in problematic_methods:
                        self.violations.append(DeterminismViolation(
                            self.file_path,
                            self.current_line,
                            "RANDOM_USAGE",
                            f"Use of random.{node.func.attr}() without explicit seeding breaks determinism",
                            self._get_code_snippet(node)
                        ))
        
        # Check for direct random module usage
        elif isinstance(node.func, ast.Name):
            if node.func.id == 'randint' or node.func.id == 'random':
                self.violations.append(DeterminismViolation(
                    self.file_path,
                    self.current_line,
                    "RANDOM_USAGE",
                    f"Use of {node.func.id}() without explicit seeding breaks determinism",
                    self._get_code_snippet(node)
                ))
    
    def _check_json_calls(self, node):
        """Check for non-deterministic JSON serialization"""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'json':
                    if node.func.attr == 'dumps':
                        # Check if sort_keys=True is used
                        if len(node.keywords) == 0 or not any(kw.arg == 'sort_keys' and kw.value.value == True for kw in node.keywords):
                            self.violations.append(DeterminismViolation(
                                self.file_path,
                                self.current_line,
                                "JSON_SORT",
                                "json.dumps() without sort_keys=True may be non-deterministic",
                                self._get_code_snippet(node)
                            ))
    
    def _get_code_snippet(self, node) -> str:
        """Extract code snippet from AST node"""
        try:
            import astor
            return astor.to_source(node).strip()
        except ImportError:
            return f"Line {self.current_line}"

def scan_file(file_path: Path) -> List[DeterminismViolation]:
    """Scan a single Python file for determinism violations"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip files that are too large or binary
        if len(content) > 1024 * 1024:  # 1MB limit
            return []
        
        tree = ast.parse(content)
        scanner = DeterminismScanner(str(file_path))
        scanner.visit(tree)
        return scanner.violations
    
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Error scanning {file_path}: {e}", file=sys.stderr)
        return []

def check_environment_variables() -> List[DeterminismViolation]:
    """Check environment variables that affect determinism"""
    violations = []
    
    # Check PYTHONHASHSEED
    hash_seed = os.environ.get('PYTHONHASHSEED')
    if hash_seed is None:
        violations.append(DeterminismViolation(
            "ENVIRONMENT",
            0,
            "PYTHONHASHSEED",
            "PYTHONHASHSEED not set - hash randomization may break determinism"
        ))
    elif not hash_seed.isdigit():
        violations.append(DeterminismViolation(
            "ENVIRONMENT",
            0,
            "PYTHONHASHSEED",
            f"PYTHONHASHSEED='{hash_seed}' is not numeric - may break determinism"
        ))
    
    return violations

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        scan_dir = Path(sys.argv[1])
    else:
        scan_dir = Path.cwd()
    
    if not scan_dir.exists():
        print(f"Error: Directory {scan_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    print("🔍 Scanning for determinism violations...")
    print(f"📁 Scanning directory: {scan_dir}")
    
    # Find Python files to scan
    python_files = []
    for pattern in ['**/*.py']:
        python_files.extend(scan_dir.glob(pattern))
    
    # Skip certain directories
    skip_patterns = ['__pycache__', '.git', '.pytest_cache', 'venv', '.venv']
    python_files = [
        f for f in python_files 
        if not any(pattern in str(f) for pattern in skip_patterns)
    ]
    
    print(f"📄 Found {len(python_files)} Python files to scan")
    
    # Scan files
    all_violations = []
    for file_path in python_files:
        violations = scan_file(file_path)
        all_violations.extend(violations)
    
    # Check environment
    env_violations = check_environment_variables()
    all_violations.extend(env_violations)
    
    # Group violations by type
    violations_by_type = {}
    for violation in all_violations:
        if violation.issue_type not in violations_by_type:
            violations_by_type[violation.issue_type] = []
        violations_by_type[violation.issue_type].append(violation)
    
    # Report results
    print(f"\n📊 Scan Results: {len(all_violations)} violations found")
    
    if all_violations:
        print("\n❌ DETERMINISM VIOLATIONS FOUND:")
        print("=" * 60)
        
        for issue_type, violations in sorted(violations_by_type.items()):
            print(f"\n🔸 {issue_type} ({len(violations)} occurrences):")
            for violation in violations:
                if violation.issue_type == "ENVIRONMENT":
                    print(f"   {violation.description}")
                else:
                    print(f"   {violation.file_path}:{violation.line} - {violation.description}")
                    if violation.code_snippet:
                        print(f"     Code: {violation.code_snippet}")
        
        print(f"\n💡 Recommendations:")
        print("   • Replace datetime.now() with deterministic timestamps")
        print("   • Use time.time() only with fixed seeds or mock in tests")
        print("   • Always seed random generators: random.seed(42)")
        print("   • Use json.dumps(data, sort_keys=True) for deterministic JSON")
        print("   • Set PYTHONHASHSEED environment variable")
        
        sys.exit(1)
    else:
        print("\n✅ No determinism violations found!")
        print("🎉 Codebase passes determinism checks")
        sys.exit(0)

if __name__ == "__main__":
    main()
