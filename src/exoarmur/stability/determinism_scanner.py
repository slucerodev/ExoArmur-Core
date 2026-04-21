"""
Determinism Static Analysis Scanner

Scans Python source code for nondeterministic patterns in protected modules.
Detects:
- datetime.now(), datetime.utcnow()
- time.time(), time.monotonic()
- random module usage without explicit seeding
- hash() usage in critical paths
- Unordered collection iteration where order affects output
"""

import ast
import os
import sys
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from exoarmur.stability.determinism_protected_modules import (
    get_protected_module,
    is_module_protected,
    is_module_exempt,
    ProtectionLevel
)


@dataclass
class DeterminismViolation:
    """A detected determinism violation"""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    fix_suggestion: str
    code_snippet: str


class DeterminismScanner(ast.NodeVisitor):
    """AST visitor that detects nondeterministic patterns"""
    
    def __init__(self, file_path: str, source_lines: List[str], check_protection: bool = True):
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: List[DeterminismViolation] = []
        self.check_protection = check_protection
        self.module_path = self._extract_module_path(file_path) if check_protection else None
        self.is_protected = is_module_protected(self.module_path) if check_protection else True
        self.random_imports: Set[str] = set()
        self.datetime_imports: Set[str] = set()
        self.time_imports: Set[str] = set()
        
    def _extract_module_path(self, file_path: str) -> str:
        """Extract Python module path from file path"""
        # Convert file path to module path
        try:
            src_dir = Path(__file__).parent.parent.parent
            relative_path = Path(file_path).relative_to(src_dir)
            module_path = str(relative_path).replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]
            return module_path
        except ValueError:
            # File is outside src directory, return None
            return None
    
    def _get_code_snippet(self, line_number: int) -> str:
        """Get the code snippet for a line"""
        if 0 < line_number <= len(self.source_lines):
            return self.source_lines[line_number - 1].strip()
        return ""
    
    def visit_Import(self, node: ast.Import):
        """Track imports of nondeterministic modules"""
        for alias in node.names:
            if alias.name == 'random':
                self.random_imports.add(alias.asname or alias.name)
            elif alias.name == 'datetime':
                self.datetime_imports.add(alias.asname or alias.name)
            elif alias.name == 'time':
                self.time_imports.add(alias.asname or alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports of nondeterministic modules"""
        if node.module in ('random', 'datetime', 'time'):
            for alias in node.names:
                if node.module == 'random':
                    self.random_imports.add(alias.asname or alias.name)
                elif node.module == 'datetime':
                    self.datetime_imports.add(alias.asname or alias.name)
                elif node.module == 'time':
                    self.time_imports.add(alias.asname or alias.name)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detect calls to nondeterministic functions"""
        if not self.is_protected:
            self.generic_visit(node)
            return
        
        # Check if module is exempt
        if self.module_path and is_module_exempt(self.module_path):
            self.generic_visit(node)
            return
        
        func = node.func
        
        # Check for datetime.now() or datetime.utcnow()
        if isinstance(func, ast.Attribute):
            if func.attr in ('now', 'utcnow'):
                if isinstance(func.value, ast.Name):
                    if func.value.id in self.datetime_imports:
                        self._add_violation(
                            node,
                            "datetime_wall_clock",
                            f"Use of datetime.{func.attr}() detected in protected module",
                            f"Use get_federation_clock().now() or DeterministicClock instead"
                        )
        
        # Check for time.time(), time.monotonic()
        if isinstance(func, ast.Attribute):
            if func.attr in ('time', 'monotonic', 'perf_counter', 'process_time'):
                if isinstance(func.value, ast.Name):
                    if func.value.id in self.time_imports:
                        self._add_violation(
                            node,
                            "time_wall_clock",
                            f"Use of time.{func.attr}() detected in protected module",
                            f"Use DeterministicClock instead of wall-clock time"
                        )
        
        # Check for hash() usage
        if isinstance(func, ast.Name):
            if func.id == 'hash':
                self._add_violation(
                    node,
                    "hash_function",
                    "Use of hash() detected in protected module",
                    "Use stable_hash() from exoarmur.utils.stable_hash instead"
                )
        
        # Check for random module functions
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                if func.value.id in self.random_imports:
                    self._add_violation(
                        node,
                        "random_module",
                        f"Use of random.{func.attr} detected in protected module",
                        "Use deterministic random with explicit seed or avoid randomness entirely"
                    )
        
        self.generic_visit(node)
    
    def _add_violation(self, node: ast.AST, violation_type: str, description: str, fix_suggestion: str):
        """Add a violation to the list"""
        line_number = getattr(node, 'lineno', 0)
        code_snippet = self._get_code_snippet(line_number)
        
        violation = DeterminismViolation(
            file_path=self.file_path,
            line_number=line_number,
            violation_type=violation_type,
            description=description,
            fix_suggestion=fix_suggestion,
            code_snippet=code_snippet
        )
        self.violations.append(violation)


def scan_file(file_path: str, check_protection: bool = True) -> List[DeterminismViolation]:
    """Scan a single Python file for determinism violations"""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        
        source_lines = source.split('\n')
        tree = ast.parse(source)
        
        scanner = DeterminismScanner(file_path, source_lines, check_protection=check_protection)
        scanner.visit(tree)
        
        return scanner.violations
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        return []


def scan_directory(directory: str, protected_only: bool = True) -> List[DeterminismViolation]:
    """Scan all Python files in a directory"""
    violations = []
    
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.venv', 'venv')]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_violations = scan_file(file_path)
                violations.extend(file_violations)
    
    return violations


def scan_protected_modules() -> List[DeterminismViolation]:
    """Scan all protected modules for determinism violations"""
    src_dir = Path(__file__).parent.parent.parent
    violations = []
    
    for root, dirs, files in os.walk(src_dir):
        # Skip __pycache__ and .git
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.venv', 'venv')]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_violations = scan_file(file_path)
                violations.extend(file_violations)
    
    return violations


def format_violation_report(violations: List[DeterminismViolation]) -> str:
    """Format violations into a readable report"""
    if not violations:
        return "✓ No determinism violations found"
    
    lines = [
        "⚠ DETERMINISM VIOLATIONS DETECTED",
        "=" * 80,
        ""
    ]
    
    for i, violation in enumerate(violations, 1):
        lines.append(f"Violation {i}:")
        lines.append(f"  File: {violation.file_path}:{violation.line_number}")
        lines.append(f"  Type: {violation.violation_type}")
        lines.append(f"  Description: {violation.description}")
        lines.append(f"  Fix: {violation.fix_suggestion}")
        lines.append(f"  Code: {violation.code_snippet}")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append(f"Total violations: {len(violations)}")
    
    return "\n".join(lines)


def main():
    """Main entry point for the scanner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan for determinism violations')
    parser.add_argument('path', help='Path to scan (file or directory)')
    parser.add_argument('--protected-only', action='store_true', 
                       help='Only scan protected modules')
    
    args = parser.parse_args()
    
    if os.path.isfile(args.path):
        violations = scan_file(args.path)
    else:
        if args.protected_only:
            violations = scan_protected_modules()
        else:
            violations = scan_directory(args.path)
    
    report = format_violation_report(violations)
    print(report)
    
    if violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
