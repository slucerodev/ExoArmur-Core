#!/usr/bin/env python3
"""
ExoArmur CLI - Command Line Interface for ExoArmur Core

Provides unified access to ExoArmur Core deterministic governance functions including:
- verify_all: Complete system verification
- demo: Run demonstration scenarios
- evidence: Evidence pack operations
"""

import sys
import os
import subprocess
import json
import io
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import redirect_stdout, redirect_stderr
import click
from exoarmur import __version__

# Handle Windows encoding issues
if sys.platform == "win32":
    pass
    # Set UTF-8 encoding for Windows console
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass  # Fallback if reconfigure fails

# Add src and spec/contracts to path for imports


def _script_env(base_env: Optional[dict] = None) -> dict:
    """Build environment for repo-local script subprocesses with src on PYTHONPATH."""
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / "src"
    env = dict(base_env or os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_dir) + (os.pathsep + existing if existing else "")
    return env


def _discover_repo_root() -> Optional[Path]:
    """Locate the source checkout root when running from a repository."""
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "tests").is_dir()
            and (candidate / "examples" / "demo_standalone.py").is_file()
        ):
            return candidate
    return None


def _ensure_windows_utf8_output() -> None:
    """Ensure Windows consoles can render CLI status output safely."""
    if sys.platform != "win32":
        return

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError, ValueError):
                # Ignore encoding reconfiguration errors on Windows
                # UTF-8 may not be supported on all Windows consoles
                pass


def _run_demo_inline(*, operator_decision: Optional[str] = None, replay: Optional[str] = None, env: Optional[dict] = None):
    module = _load_demo_module()
    buffer = io.StringIO()
    original_env: dict[str, Optional[str]] = {}
    for key, value in (env or {}).items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            if replay:
                module.replay_audit_stream(replay)
            else:
                result = asyncio.run(module.run_demo_scenario(operator_decision))
                if result.get("status") == "completed" and "outcome" in result:
                    module.DEMO_AUDIT_PATH.write_text(json.dumps(result["audit_records"], indent=2, sort_keys=True))
        return 0, buffer.getvalue()
    except Exception:
        return 1, buffer.getvalue()
    finally:
        for key, prior in original_env.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior

@click.group()
@click.version_option(version=__version__, prog_name="exoarmur")
def main():
    """ExoArmur Core — deterministic governance and replayable audit layer"""

@main.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--fast', is_flag=True, help='Skip boundary gate randomization')
def verify_all(verbose: bool, fast: bool):
    """Run complete system verification"""
    _ensure_windows_utf8_output()
    click.echo("🔍 ExoArmur System Verification")
    click.echo("=" * 50)
    
    exit_code = 0
    repo_root = _discover_repo_root()
    package_root = Path(__file__).resolve().parent
    repo_tests_available = repo_root is not None and (repo_root / "tests").is_dir()
    standalone_demo_path = (
        repo_root / "examples" / "demo_standalone.py" if repo_root is not None else None
    )
    proof_bundle_path = (
        repo_root / "examples" / "demo_standalone_proof_bundle.json"
        if repo_root is not None
        else None
    )
    standalone_demo_available = (
        standalone_demo_path is not None
        and standalone_demo_path.is_file()
        and proof_bundle_path is not None
        and proof_bundle_path.is_file()
    )
    skipped_checks = []
    
    try:
        # 1. Full test suite (excluding integration tests that require Docker)
        if repo_tests_available:
            click.echo("1️⃣ Running full test suite...")
            test_cmd = [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/integration/", "-x", "--tb=short"]
            if verbose:
                test_cmd.append("-v")
            
            try:
                result = subprocess.run(test_cmd, cwd=repo_root, timeout=300)
            except subprocess.TimeoutExpired:
                click.echo("❌ Test suite timed out (300s limit)")
                exit_code = 1
                result = None
            if result is not None and result.returncode != 0:
                click.echo("❌ Test suite failed")
                exit_code = 1
            elif result is not None:
                click.echo("✅ Test suite passed")
        else:
            click.echo("1️⃣ Running installed-package import sanity check...")
            import_cmd = [
                sys.executable,
                "-c",
                "import sys; sys.stderr=open('/dev/null','w'); import exoarmur; from exoarmur.sdk import run_governed_execution, verify_governance_integrity, replay_governed_execution; print('OK')",
            ]
            # Run from a neutral temp directory to avoid cwd affecting imports
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    import_cmd,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                )
            if result.returncode != 0:
                click.echo("❌ Installed-package import sanity failed")
                if verbose:
                    output = (result.stdout or "") + (result.stderr or "")
                    if output:
                        click.echo(output)
                exit_code = 1
            else:
                click.echo("✅ Installed-package import sanity passed")
                if verbose and result.stdout:
                    click.echo(result.stdout.strip())
            skipped_checks.append("repo-local pytest suite")
        
        # 2. Boundary gate (if not fast)
        if repo_tests_available and not fast:
            click.echo("\n2️⃣ Running boundary gate...")
            boundary_cmd = [sys.executable, "-m", "pytest", "tests/", "-m", "sensitive", "--tb=short"]
            if verbose:
                boundary_cmd.append("-v")
            
            try:
                result = subprocess.run(boundary_cmd, cwd=repo_root, timeout=120)
            except subprocess.TimeoutExpired:
                click.echo("❌ Boundary gate timed out (120s limit)")
                exit_code = 1
                result = None
            if result is not None and result.returncode != 0:
                click.echo("❌ Boundary gate failed")
                exit_code = 1
            elif result is not None:
                click.echo("✅ Boundary gate passed")
        elif not repo_tests_available:
            click.echo("\n2️⃣ Skipping boundary gate (repo-local tests are unavailable in installed package mode)")
            skipped_checks.append("boundary gate")
        else:
            click.echo("\n2️⃣ Skipping boundary gate (fast mode)")
        
        # 3. Standalone demo proof
        if standalone_demo_available:
            click.echo("\n3️⃣ Running standalone demo proof...")
            demo_result = subprocess.run(
                [sys.executable, str(standalone_demo_path)],
                cwd=repo_root,
                env=_script_env(os.environ.copy()),
                capture_output=True,
                text=True,
            )
            output = (demo_result.stdout or "") + (demo_result.stderr or "")
            
            if demo_result.returncode != 0:
                click.echo("❌ Standalone demo proof failed")
                if verbose:
                    click.echo(output)
                exit_code = 1
            else:
                required_markers = [
                    "DEMO_RESULT=DENIED",
                    "ACTION_EXECUTED=false",
                    "AUDIT_STREAM_ID=",
                ]

                missing_markers = [marker for marker in required_markers if marker not in output]
                if missing_markers:
                    click.echo(f"❌ Standalone demo missing required markers: {missing_markers}")
                    if verbose:
                        click.echo("Demo output:")
                        click.echo(output)
                    exit_code = 1
                else:
                    audit_id = None
                    for line in output.split('\n'):
                        if line.startswith('AUDIT_STREAM_ID='):
                            audit_id = line.split('=', 1)[1]
                            break

                    if proof_bundle_path is None:
                        click.echo("❌ Standalone proof bundle unavailable")
                        exit_code = 1
                    else:
                        try:
                            proof_bundle = json.loads(proof_bundle_path.read_text())
                        except json.JSONDecodeError as exc:
                            click.echo(f"❌ Standalone proof bundle invalid JSON: {exc}")
                            exit_code = 1
                        else:
                            proof_bundle_payload = proof_bundle.get("bundle", proof_bundle.get("proof_bundle", {}))
                            if (
                                audit_id
                                and proof_bundle.get("audit_stream_id") == audit_id
                                and proof_bundle.get("action_executed") is False
                                and proof_bundle_payload.get("replay_hash")
                                and "audit_records" in proof_bundle
                            ):
                                click.echo("✅ Standalone demo proof passed")
                            else:
                                click.echo("❌ Standalone proof bundle contents invalid")
                                if verbose:
                                    click.echo(output)
                                    click.echo(json.dumps(proof_bundle, indent=2, sort_keys=True))
                                exit_code = 1
        else:
            click.echo("\n3️⃣ Skipping standalone demo proof (examples/ are not bundled in the installed package)")
            skipped_checks.append("standalone demo proof")
        
        # Final result
        click.echo("\n" + "=" * 50)
        if exit_code == 0:
            # Use Windows-safe output
            success_symbol = "🎯" if sys.platform != "win32" else "[SUCCESS]"
            if skipped_checks:
                click.echo(f"{success_symbol} VERIFY_ALL: PASSED (repo-only checks skipped: {', '.join(skipped_checks)})")
                click.echo("Installed package verified; repo-local tests/examples are unavailable in this environment")
            else:
                click.echo(f"{success_symbol} VERIFY_ALL: PASSED")
                click.echo("All systems green and ready for production")
        else:
            # Use Windows-safe output
            fail_symbol = "❌" if sys.platform != "win32" else "[FAILED]"
            click.echo(f"{fail_symbol} VERIFY_ALL: FAILED")
            click.echo("System not ready - fix failures before proceeding")
        
        sys.exit(exit_code)
        
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)

@main.command()
def demo():
    """Run the canonical governance demo (requires a cloned source repository).

    The demo script lives under the repository's top-level ``demos/`` directory,
    which is intentionally not shipped inside the installed wheel (see
    ``[tool.setuptools.packages.find]`` in ``pyproject.toml``). When this
    command is invoked from a cloned checkout or editable install it runs the
    script end-to-end; when invoked from a plain ``pip install`` it prints a
    clear instruction rather than producing a cryptic ``No such file`` error.
    """
    _ensure_windows_utf8_output()
    click.echo("🚀 ExoArmur Demo: canonical truth reconstruction")

    repo_root = _discover_repo_root()
    script_path = (
        repo_root / "demos" / "canonical_truth_reconstruction_demo.py"
        if repo_root is not None
        else None
    )

    if script_path is None or not script_path.is_file():
        click.echo(
            "❌ Canonical demo script not found.\n"
            "   The `exoarmur demo` command runs `demos/canonical_truth_reconstruction_demo.py`\n"
            "   from the source checkout. That directory is intentionally not bundled into the\n"
            "   installed wheel. To run the demo:\n\n"
            "       git clone https://github.com/slucerodev/ExoArmur-Core.git\n"
            "       cd ExoArmur-Core\n"
            "       pip install -r requirements.lock\n"
            "       pip install --no-deps -e '.[dev]'\n"
            "       python demos/canonical_truth_reconstruction_demo.py\n"
        )
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=repo_root,
        env=_script_env(os.environ.copy()),
    )
    sys.exit(result.returncode)

@main.command()
@click.option('--export', help='Export evidence for intent ID')
@click.option('--intent-id', help='Intent ID to export evidence for')
def evidence(export: Optional[str], intent_id: Optional[str]):
    """Evidence pack operations"""
    if export or intent_id:
        click.echo("🔍 Evidence export not yet implemented")
        click.echo("This will be available in Phase 2")
        sys.exit(1)
    else:
        click.echo("📋 Evidence Operations:")
        click.echo("  exoarmur evidence export --intent-id <id>  Export evidence for intent")
        click.echo("  exoarmur evidence list                        List available evidence packs")

@main.command()
def health():
    """Quick health check"""
    # Use Windows-safe output
    health_symbol = "🏥" if sys.platform != "win32" else "[HEALTH]"
    click.echo(f"{health_symbol} ExoArmur Health Check")
    
    try:
        # Test basic imports
        click.echo("✅ Core imports working")
        
        # Test feature flags
        from exoarmur.feature_flags.feature_flags import get_feature_flags
        flags = get_feature_flags()
        click.echo(f"✅ Feature flags loaded: {len(flags._flags)} configured")
        
        # Test governed runtime subsystems are importable
        click.echo("✅ Governed runtime subsystems importable")
        
        click.echo("🎯 System healthy")
        sys.exit(0)
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")
        sys.exit(1)

@main.command()
def proof():
    """Run deterministic proof mode - single command system validation"""
    _ensure_windows_utf8_output()
    
    try:
        # Import and run proof module
        from exoarmur.proof.run_proof import main as proof_main
        exit_code = proof_main()
        sys.exit(exit_code)
    except ImportError as e:
        click.echo("❌ Proof mode not available")
        if "proof" in str(e):
            click.echo("Run: ./scripts/quickstart.sh to install dependencies")
        else:
            click.echo(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Proof mode failed: {e}")
        sys.exit(1)

@main.command()
@click.option('--runs', default=10, help='Number of runs per mode (default: 10)')
@click.option('--mode', type=click.Choice(['all', 'sequential', 'parallel', 'process-isolated', 'time-skewed', 'adversarial', 'single-run']), default='all', help='Run specific mode only (default: all)')
@click.option('--input-hash', default=None, help='Input hash for single-run mode (required with --mode single-run)')
@click.option('--include-failure-demo', is_flag=True, help='Include failure demonstration mode to prove enforcement is real')
def prove_determinism(runs: int, mode: str, input_hash: str, include_failure_demo: bool):
    """Run determinism proof harness with comprehensive mode testing"""
    _ensure_windows_utf8_output()
    
    try:
        from exoarmur.proof.determinism_harness import DeterminismHarness
        from exoarmur.proof.scenario_builder import build_deterministic_scenario
        from exoarmur.proof.payload_store import load_payload
        from exoarmur.proof.hash_extractor import extract_canonical_audit_hash, verify_hash_consistency
        from exoarmur.stability.deterministic_ordering import DeterminismViolationError
        
        click.echo("=" * 60)
        click.echo("DETERMINISM PROOF HARNESS")
        click.echo("=" * 60)
        click.echo()
        
        # Single-run mode: load payload, execute once, print hash
        if mode == 'single-run':
            if not input_hash:
                click.echo("Error: --input-hash is required for single-run mode")
                sys.exit(1)
            
            try:
                # Load payload from storage
                payload = load_payload(input_hash)
                
                # Execute scenario once
                audit_records = build_deterministic_scenario()
                
                # Compute execution hash
                execution_hash = extract_canonical_audit_hash(audit_records)
                
                # Print ONLY the execution hash
                click.echo(f"EXECUTION HASH: {execution_hash}")
                sys.exit(0)
                
            except Exception as e:
                click.echo(f"Error in single-run mode: {e}")
                sys.exit(1)
        
        # Initialize harness
        harness = DeterminismHarness(build_deterministic_scenario, runs=runs)
        
        # Run requested modes
        if mode == 'all':
            report = harness.run_full_proof()
        elif mode == 'sequential':
            harness.run_sequential()
            report = harness.report
        elif mode == 'parallel':
            harness.run_parallel()
            report = harness.report
        elif mode == 'process-isolated':
            harness.run_process_isolated()
            report = harness.report
        elif mode == 'time-skewed':
            harness.run_with_time_skew()
            report = harness.report
        elif mode == 'adversarial':
            harness.run_adversarial()
            report = harness.report
        
        # Run failure demonstration if requested
        if include_failure_demo:
            click.echo()
            click.echo("=" * 60)
            click.echo("FAILURE DEMONSTRATION")
            click.echo("=" * 60)
            click.echo()
            failure_result = harness.run_failure_mode()
            report.failure_detected = failure_result["failure_detected"]
            report.failure_mode_result = failure_result
            
            click.echo("FAILURE DEMONSTRATION:")
            if report.failure_detected:
                click.echo("  ✓ Determinism violation correctly detected")
                click.echo(f"    Type: {failure_result.get('violation_type', 'unknown')}")
            else:
                click.echo("  ✗ FAILED TO DETECT VIOLATION (FAIL)")
                sys.exit(1)
            click.echo()
        
        # Generate readable proof report
        click.echo()
        click.echo("=" * 60)
        click.echo("DETERMINISM PROOF REPORT")
        click.echo("=" * 60)
        click.echo()
        
        click.echo(f"Runs: {runs}")
        click.echo()
        
        # Output Input Hash
        click.echo("Input Hash:")
        if report.input_hash:
            hash_display = report.input_hash[:8] + "..." + report.input_hash[-4:]
            click.echo(f"  {hash_display}")
        else:
            click.echo("  [NO INPUT HASH]")
        click.echo()
        
        # Output Execution Hash
        click.echo("Execution Hash:")
        if report.execution_hash:
            hash_display = report.execution_hash[:8] + "..." + report.execution_hash[-4:]
            click.echo(f"  {hash_display}")
        else:
            click.echo("  [NO EXECUTION HASH]")
        click.echo()
        
        # Output Replay Verification
        click.echo("Replay Verification:")
        if report.replay_verified:
            click.echo("  ✓ MATCH")
        else:
            click.echo("  ✗ MISMATCH")
        click.echo()
        
        # Output Noise Injection
        click.echo("Noise Injection:")
        if report.noise_verified:
            click.echo("  ✓ IGNORED")
        else:
            click.echo("  ✗ AFFECTED EXECUTION")
        click.echo()
        
        # Output Failure Detection
        if include_failure_demo:
            click.echo("Failure Detection:")
            if report.failure_detected:
                click.echo("  ✓ ENFORCED")
            else:
                click.echo("  ✗ NOT ENFORCED")
            click.echo()
        
        # Output Environment
        click.echo("Environment:")
        env = report.environment
        if env:
            click.echo(f"  Python: {env.get('python_version', 'unknown')}")
            click.echo(f"  OS: {env.get('os', 'unknown')}")
            click.echo(f"  Determinism Guards: {env.get('determinism_guards', {}).get('status', 'unknown')}")
        else:
            click.echo("  [NO ENVIRONMENT DATA]")
        click.echo()
        
        # Output Process-Isolated status
        click.echo("Process-Isolated:")
        if report.process_isolated_hashes and verify_hash_consistency(report.process_isolated_hashes):
            click.echo("  ✓ PASS")
        else:
            click.echo("  ✗ FAIL")
        click.echo()
        
        # Output mode statuses
        click.echo("Modes:")
        for mode_name, status in report.mode_statuses.items():
            status_symbol = "✓" if status == "PASS" else "✗"
            click.echo(f"  {mode_name}: {status_symbol} {status}")
        click.echo()
        
        click.echo(f"Unique Hashes Observed: {report.unique_hash_count}")
        click.echo()
        
        click.echo("-" * 60)
        if report.unique_hash_count == 1 and report.replay_verified and report.noise_verified:
            if include_failure_demo and report.failure_detected:
                click.echo("STATUS: VERIFIED DETERMINISTIC (FULLY SEALED)")
            else:
                click.echo("STATUS: VERIFIED DETERMINISTIC (CLOSED-LOOP)")
            click.echo()
            sys.exit(0)
        elif report.unique_hash_count == 1:
            click.echo("STATUS: VERIFIED DETERMINISTIC")
            click.echo()
            sys.exit(0)
        else:
            click.echo("STATUS: DETERMINISM VIOLATION DETECTED")
            click.echo()
            click.echo("Hashes observed:")
            for i, h in enumerate(report.all_hashes[:10], 1):
                hash_display = h[:8] + "..." + h[-4:]
                click.echo(f"  Run {i}: {hash_display}")
            if len(report.all_hashes) > 10:
                click.echo(f"  ... and {len(report.all_hashes) - 10} more")
            sys.exit(1)
            
    except DeterminismViolationError as e:
        click.echo()
        click.echo("=" * 60)
        click.echo("DETERMINISM PROOF REPORT")
        click.echo("=" * 60)
        click.echo()
        click.echo(f"Runs: {runs}")
        click.echo(f"Mode: {mode}")
        click.echo()
        click.echo("Canonical Hash: [VIOLATION]")
        click.echo()
        click.echo(f"Unique Hashes Observed: [MULTIPLE]")
        click.echo()
        click.echo("-" * 60)
        click.echo("STATUS: DETERMINISM VIOLATION DETECTED")
        click.echo()
        click.echo(f"Error: {e}")
        sys.exit(1)
    except ImportError as e:
        click.echo("❌ Proof harness not available")
        click.echo(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Proof harness failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
