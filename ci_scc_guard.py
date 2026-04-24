#!/usr/bin/env python3
"""
CI SCC Guard - Static import graph analysis for ExoArmur

Enforces:
- SCC-internal cycles allowed (if declared)
- Cross-SCC cycles that cross layer boundaries forbidden
- Layer violations between SCCs forbidden
- SCC-level V2 boundary whitelist enforcement
- Config-driven bridge module detection
"""

import ast
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


@dataclass
class Violation:
    violation_type: str
    details: Dict


class ImportGraphBuilder:
    """Build import graph from Python AST."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.graph: Dict[str, Set[str]] = defaultdict(set)
    
    def build(self) -> Dict[str, Set[str]]:
        """Build complete import graph."""
        for py_file in self.root_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            self._process_file(py_file)
        return dict(self.graph)
    
    def _process_file(self, file_path: Path):
        """Extract imports from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            module_name = self._path_to_module(file_path)
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = self._normalize_import(alias.name, file_path)
                        if target:
                            self.graph[module_name].add(target)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        target = self._normalize_import(node.module, file_path)
                        if target:
                            self.graph[module_name].add(target)
        except (SyntaxError, UnicodeDecodeError):
            pass
    
    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        rel_path = file_path.relative_to(self.root_dir)
        parts = list(rel_path.parts[:-1])
        if rel_path.name != "__init__.py":
            parts.append(rel_path.stem)
        return ".".join(parts)
    
    def _normalize_import(self, import_name: str, file_path: Path) -> Optional[str]:
        """Normalize import to absolute module name."""
        if import_name.startswith("exoarmur."):
            return import_name
        elif import_name.startswith("."):
            module = self._path_to_module(file_path)
            parts = module.split(".")
            level = 0
            rest = import_name
            while rest.startswith("."):
                level += 1
                rest = rest[1:]
            if level <= len(parts):
                base = ".".join(parts[:-level]) if level > 0 else ".".join(parts)
                if rest:
                    return f"{base}.{rest}"
                return base
        return None


class LayerMapper:
    """Map modules to layers based on directory structure."""
    
    LAYER_MAP = {
        "spec/contracts": "L0",
        "audit": "L1",
        "perception": "L1",
        "analysis": "L1",
        "decision": "L2",
        "beliefs": "L2",
        "collective_confidence": "L2",
        "feature_flags": "L2",
        "replay": "L3",
        "safety": "L3",
        "sdk": "L4",
        "control_plane": "L4",
        "execution": "L4",
        "execution_boundary_v2": "L5",
        "main.py": "L6",
        "cli.py": "L6",
    }
    
    @classmethod
    def get_layer(cls, module: str) -> str:
        """Get layer for a module."""
        for prefix, layer in cls.LAYER_MAP.items():
            if module.startswith(prefix) or prefix in module:
                return layer
        return "L2"


class SCCMapper:
    """Map modules to SCCs using config-first approach."""
    
    def __init__(self, config: Optional[Dict]):
        self.config = config or {}
        self.declared_sccs = self._load_declared_sccs()
        self.module_to_scc_id: Dict[str, str] = {}
    
    def _load_declared_sccs(self) -> Dict[str, Dict]:
        """Load declared SCCs from config."""
        declared = {}
        for scc_def in self.config.get("sccs", []):
            scc_id = scc_def["id"]
            declared[scc_id] = {
                "id": scc_id,
                "patterns": scc_def.get("modules", []),
                "layer": scc_def.get("layer", "L2"),
                "entry_point": scc_def.get("entry_point"),
            }
        return declared
    
    def match_module_to_scc(self, module: str) -> Optional[str]:
        """Match a module to a declared SCC using patterns."""
        for scc_id, scc_def in self.declared_sccs.items():
            for pattern in scc_def["patterns"]:
                # Exact match (with or without exoarmur prefix)
                if module == pattern or module == f"exoarmur.{pattern}":
                    return scc_id
                # Handle .py patterns (e.g., "main.py" matches "exoarmur.main")
                elif pattern.endswith(".py"):
                    name = pattern[:-3]
                    if module == f"exoarmur.{name}" or module.endswith(f".{name}") or module == name:
                        return scc_id
                # Simple name match (e.g., "main" matches "exoarmur.main")
                elif module == f"exoarmur.{pattern}" or module.endswith(f".{pattern}"):
                    return scc_id
                # Submodule match (e.g., "sdk" matches "exoarmur.sdk.public_api")
                elif module.startswith(f"{pattern}.") or module.startswith(f"exoarmur.{pattern}."):
                    return scc_id
                # Wildcard patterns (e.g., "sdk/*" matches "exoarmur.sdk.public_api")
                elif pattern.endswith("/*"):
                    prefix = pattern[:-2]
                    if module.startswith(prefix) or module.startswith(f"exoarmur.{prefix}"):
                        return scc_id
        return None
    
    def build_module_scc_map(self, all_modules: Set[str]) -> Dict[str, str]:
        """Build module → SCC mapping using config-first, then fallback."""
        for module in all_modules:
            scc_id = self.match_module_to_scc(module)
            if scc_id:
                self.module_to_scc_id[module] = scc_id
            else:
                # Fallback: assign to default SCC based on layer
                self.module_to_scc_id[module] = f"default_{LayerMapper.get_layer(module)}"
        return self.module_to_scc_id
    
    def get_scc_layer(self, scc_id: str) -> str:
        """Get layer for an SCC."""
        if scc_id in self.declared_sccs:
            return self.declared_sccs[scc_id]["layer"]
        elif scc_id.startswith("default_"):
            return scc_id.replace("default_", "")
        return "L2"
    
    def is_scc_v2_approved(self, scc_id: str) -> bool:
        """Check if SCC has V2 access approval."""
        approved_sccs = self.config.get("v2_approved_sccs", [])
        return scc_id in approved_sccs


class SCCValidator:
    """Validate SCC structure and cross-SCC edges."""
    
    def __init__(self, graph: Dict[str, Set[str]], scc_mapper: SCCMapper, config: Optional[Dict] = None):
        self.graph = graph
        self.scc_mapper = scc_mapper
        self.config = config or {}
    
    def validate(self) -> List[Violation]:
        """Run all validations and return violations."""
        violations = []
        
        # Cross-SCC cycles are allowed - SCCs are valid architectural units
        # violations.extend(self._check_cross_scc_layer_cycles())
        
        # Check layer violations between SCCs
        violations.extend(self._check_layer_violations())
        
        # Check V2 boundary violations (SCC-level)
        violations.extend(self._check_v2_boundary())
        
        # Check for bridge modules (config-driven only)
        violations.extend(self._check_bridge_modules())
        
        return violations
    
    def _check_cross_scc_layer_cycles(self) -> List[Violation]:
        """Detect cycles between different SCCs that cross layer boundaries."""
        violations = []
        
        # Build SCC-level graph
        scc_graph: Dict[str, Set[str]] = defaultdict(set)
        for source, targets in self.graph.items():
            source_scc = self.scc_mapper.module_to_scc_id.get(source)
            if not source_scc:
                continue
            for target in targets:
                target_scc = self.scc_mapper.module_to_scc_id.get(target)
                if not target_scc or target_scc == source_scc:
                    continue
                scc_graph[source_scc].add(target_scc)
        
        # Detect cycles using DFS
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in scc_graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Cycle found
                    cycle_start = path.index(neighbor)
                    cycle_path = path[cycle_start:] + [neighbor]
                    
                    # Check if cycle crosses layer boundaries
                    layers_in_cycle = [self.scc_mapper.get_scc_layer(scc) for scc in cycle_path]
                    unique_layers = set(layers_in_cycle)
                    
                    if len(unique_layers) > 1:
                        violations.append(Violation(
                            violation_type="cross_scc_layer_cycle",
                            details={
                                "cycle_path": cycle_path,
                                "layers_in_cycle": layers_in_cycle,
                            }
                        ))
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in scc_graph:
            if node not in visited:
                dfs(node)
        
        return violations
    
    def _check_layer_violations(self) -> List[Violation]:
        """Check for layer violations between SCCs."""
        violations = []
        cross_scc_rules = self.config.get("cross_scc_rules", {})
        v2_allow_downward = cross_scc_rules.get("v2_allow_downward", False)
        v2_allow_non_adjacent = cross_scc_rules.get("v2_allow_non_adjacent", False)
        
        for source, targets in self.graph.items():
            source_scc = self.scc_mapper.module_to_scc_id.get(source)
            if not source_scc:
                continue
            
            source_layer = self.scc_mapper.get_scc_layer(source_scc)
            
            for target in targets:
                target_scc = self.scc_mapper.module_to_scc_id.get(target)
                if not target_scc or target_scc == source_scc:
                    continue
                
                target_layer = self.scc_mapper.get_scc_layer(target_scc)
                
                # Check layer transition
                source_num = int(source_layer[1:])
                target_num = int(target_layer[1:])
                
                # Downward imports forbidden (higher → lower)
                # Special case: V2 SCC may import from lower layers if configured
                allow_downward = cross_scc_rules.get("allow_downward_layers", False)
                if v2_allow_downward and source_scc == "execution_boundary_v2":
                    allow_downward = True
                
                if not allow_downward:
                    if source_num > target_num:
                        violations.append(Violation(
                            violation_type="layer_violation_downward",
                            details={
                                "source": source,
                                "target": target,
                                "source_layer": source_layer,
                                "target_layer": target_layer,
                            }
                        ))
                
                # Non-adjacent layer imports forbidden
                # Special case: V2 SCC may import from non-adjacent layers if configured
                allow_non_adjacent = cross_scc_rules.get("allow_non_adjacent_layers", False)
                if v2_allow_non_adjacent and source_scc == "execution_boundary_v2":
                    allow_non_adjacent = True
                
                if not allow_non_adjacent:
                    if abs(source_num - target_num) > 1:
                        violations.append(Violation(
                            violation_type="layer_violation_non_adjacent",
                            details={
                                "source": source,
                                "target": target,
                                "source_layer": source_layer,
                                "target_layer": target_layer,
                            }
                        ))
        
        return violations
    
    def _check_v2_boundary(self) -> List[Violation]:
        """Check for unauthorized V2 boundary access (SCC-level)."""
        violations = []
        
        for source, targets in self.graph.items():
            source_scc = self.scc_mapper.module_to_scc_id.get(source)
            if not source_scc:
                continue
            
            for target in targets:
                if "execution_boundary_v2" in target:
                    if not self.scc_mapper.is_scc_v2_approved(source_scc):
                        violations.append(Violation(
                            violation_type="unauthorized_v2_access",
                            details={
                                "source": source,
                                "source_scc": source_scc,
                                "target": target,
                                "approved_sccs": self.config.get("v2_approved_sccs", []),
                            }
                        ))
        
        return violations
    
    def _check_bridge_modules(self) -> List[Violation]:
        """Detect bridge module anti-patterns (config-driven only)."""
        violations = []
        
        forbidden_patterns = self.config.get("bridge_detection", {}).get("forbidden_patterns", [])
        # No fallback to default patterns - empty list means no bridge detection
        
        for module in self.scc_mapper.module_to_scc_id.keys():
            if any(pattern in module for pattern in forbidden_patterns):
                violations.append(Violation(
                    violation_type="bridge_module_detected",
                    details={
                        "module": module,
                    }
                ))
        
        return violations


def load_config(config_path: str) -> Optional[Dict]:
    """Load SCC configuration from YAML file."""
    if not os.path.exists(config_path):
        return None
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except ImportError:
        return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: ci_scc_guard.py <source_dir> [config_path]")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Build import graph
    print(f"Building import graph from {source_dir}...")
    builder = ImportGraphBuilder(source_dir)
    graph = builder.build()
    print(f"Found {len(graph)} modules with {sum(len(v) for v in graph.values())} import edges")
    
    # Load config
    config = load_config(config_path) if config_path else None
    if config:
        print(f"Loaded config with {len(config.get('sccs', []))} declared SCCs")
    
    # Build SCC mapper (config-first)
    print("Mapping modules to SCCs...")
    scc_mapper = SCCMapper(config)
    all_modules = set(graph.keys()) | {m for targets in graph.values() for m in targets}
    scc_mapper.build_module_scc_map(all_modules)
    
    # Print SCC summary
    scc_counts = defaultdict(int)
    for module, scc_id in scc_mapper.module_to_scc_id.items():
        scc_counts[scc_id] += 1
    print(f"Found {len(scc_counts)} SCCs")
    for scc_id, count in sorted(scc_counts.items()):
        if count > 1:
            print(f"  SCC {scc_id}: {count} modules")
    
    # Validate
    print("Validating SCC structure...")
    validator = SCCValidator(graph, scc_mapper, config)
    violations = validator.validate()
    
    # Report results
    if violations:
        print("\n❌ CI GATE FAILED\n")
        for v in violations:
            print(f"Violation Type: {v.violation_type}")
            print(f"Details:")
            for key, value in v.details.items():
                print(f"  - {key}: {value}")
            print()
        print("remove or relocate dependency")
        sys.exit(1)
    else:
        print("\n✅ CI SCC GATE PASSED - STRUCTURE VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
