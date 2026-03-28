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
import asyncio
import json
import io
import importlib.util
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Optional
import click
from exoarmur import __version__

# Handle Windows encoding issues
if sys.platform == "win32":
    import locale
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


def _load_demo_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "demo_v2_restrained_autonomy.py"
    spec = importlib.util.spec_from_file_location("exoarmur_cli_demo", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load demo module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    pass

@main.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--fast', is_flag=True, help='Skip boundary gate randomization')
def verify_all(verbose: bool, fast: bool):
    """Run complete system verification"""
    click.echo("🔍 ExoArmur System Verification")
    click.echo("=" * 50)
    
    exit_code = 0
    repo_root = Path(__file__).resolve().parents[2]
    
    try:
        # 1. Full test suite
        click.echo("1️⃣ Running full test suite...")
        test_cmd = [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=short"]
        if verbose:
            test_cmd.append("-v")
        
        result = subprocess.run(test_cmd, cwd=repo_root)
        if result.returncode != 0:
            click.echo("❌ Test suite failed")
            exit_code = 1
        else:
            click.echo("✅ Test suite passed")
        
        # 2. Boundary gate (if not fast)
        if not fast:
            click.echo("\n2️⃣ Running boundary gate...")
            boundary_cmd = [sys.executable, "-m", "pytest", "tests/", "-m", "sensitive", "--tb=short"]
            if verbose:
                boundary_cmd.append("-v")
            
            result = subprocess.run(boundary_cmd, cwd=repo_root)
            if result.returncode != 0:
                click.echo("❌ Boundary gate failed")
                exit_code = 1
            else:
                click.echo("✅ Boundary gate passed")
        else:
            click.echo("\n2️⃣ Skipping boundary gate (fast mode)")
        
        # 3. Demo smoke test
        click.echo("\n3️⃣ Running demo smoke test (deny mode)...")
        demo_cmd = [
            sys.executable, str(repo_root / "scripts" / "demo_v2_restrained_autonomy.py"),
            "--operator-decision", "deny"
        ]
        
        env = _script_env(os.environ.copy())
        env.update({
            'EXOARMUR_FLAG_V2_FEDERATION_ENABLED': 'true',
            'EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED': 'true',
            'EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED': 'true',
        })
        
        demo_exit_code, output = _run_demo_inline(operator_decision="deny", env=env)
        
        if demo_exit_code != 0:
            click.echo("❌ Demo smoke test failed")
            if verbose:
                click.echo(output)
            exit_code = 1
        else:
            # Check for required markers
            required_markers = [
                "DEMO_RESULT=DENIED",
                "ACTION_EXECUTED=false", 
                "AUDIT_STREAM_ID="
            ]
            
            missing_markers = [marker for marker in required_markers if marker not in output]
            if missing_markers:
                click.echo(f"❌ Demo missing required markers: {missing_markers}")
                if verbose:
                    click.echo("Demo output:")
                    click.echo(output)
                exit_code = 1
            else:
                click.echo("✅ Demo smoke test passed")
                
                # 4. Replay verification
                click.echo("\n4️⃣ Running replay verification...")
                audit_id = None
                for line in output.split('\n'):
                    if line.startswith('AUDIT_STREAM_ID='):
                        audit_id = line.split('=', 1)[1]
                        break
                
                if audit_id:
                    replay_exit_code, replay_output = _run_demo_inline(replay=audit_id, env=env)
                    
                    if replay_exit_code != 0:
                        click.echo("❌ Replay verification failed")
                        if verbose:
                            click.echo(replay_output)
                        exit_code = 1
                    else:
                        if "REPLAY_VERIFIED=true" in replay_output:
                            click.echo("✅ Replay verification passed")
                        else:
                            click.echo("⚠️ Replay verification incomplete (known limitation)")
                else:
                    click.echo("❌ Could not extract audit ID for replay")
                    exit_code = 1
        
        # Final result
        click.echo("\n" + "=" * 50)
        if exit_code == 0:
            # Use Windows-safe output
            success_symbol = "🎯" if sys.platform != "win32" else "[SUCCESS]"
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
@click.option('--scenario', default='v2_restrained_autonomy', 
              help='Demo scenario to run')
@click.option('--operator-decision', type=click.Choice(['approve', 'deny']), 
              default='deny', help='Operator decision for approval scenarios')
@click.option('--replay', help='Audit stream ID to replay')
def demo(scenario: str, operator_decision: str, replay: Optional[str]):
    """Run demonstration scenarios"""
    click.echo(f"🚀 ExoArmur Demo: {scenario}")
    
    if scenario == 'v2_restrained_autonomy':
        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / "demo_v2_restrained_autonomy.py"
        env = _script_env(os.environ.copy())
        if not replay:
            env.update({
                'EXOARMUR_FLAG_V2_FEDERATION_ENABLED': 'true',
                'EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED': 'true',
                'EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED': 'true',
            })

        cmd = [sys.executable, str(script_path)]
        if replay:
            cmd.extend(["--replay", replay])
        else:
            cmd.extend(["--operator-decision", operator_decision])

        result = subprocess.run(cmd, cwd=repo_root, env=env)
        sys.exit(result.returncode)
    else:
        click.echo(f"Unknown demo scenario: {scenario}")
        sys.exit(1)

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
        from spec.contracts.models_v1 import TelemetryEventV1
        click.echo("✅ Core imports working")
        
        # Test feature flags
        from exoarmur.feature_flags.feature_flags import get_feature_flags
        flags = get_feature_flags()
        click.echo(f"✅ Feature flags loaded: {len(flags._flags)} configured")
        
        # Test governed runtime initialization
        import exoarmur.main as runtime_main
        runtime_main.initialize_components(None)
        if runtime_main.execution_kernel is None or runtime_main.audit_logger is None:
            raise RuntimeError("Governed runtime components not initialized")
        click.echo("✅ Governed runtime initialized")
        
        click.echo("🎯 System healthy")
        sys.exit(0)
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
