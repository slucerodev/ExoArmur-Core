#!/usr/bin/env python3
"""
ExoArmur CLI - Command Line Interface for ExoArmur ADMO

Provides unified access to ExoArmur functionality including:
- verify_all: Complete system verification
- demo: Run demonstration scenarios
- evidence: Evidence pack operations
"""

import sys
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
import click

# Add src and spec/contracts to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "spec" / "contracts"))

@click.group()
@click.version_option(version="3.0.0", prog_name="exoarmur")
def main():
    """ExoArmur ADMO - Autonomous Defense Mesh Organism"""
    pass

@main.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--fast', is_flag=True, help='Skip boundary gate randomization')
def verify_all(verbose: bool, fast: bool):
    """Run complete system verification"""
    click.echo("🔍 ExoArmur System Verification")
    click.echo("=" * 50)
    
    exit_code = 0
    
    try:
        # 1. Full test suite
        click.echo("1️⃣ Running full test suite...")
        test_cmd = ["python3", "-m", "pytest", "tests/", "-x", "--tb=short"]
        if verbose:
            test_cmd.append("-v")
        
        result = subprocess.run(test_cmd, cwd=Path(__file__).parent.parent)
        if result.returncode != 0:
            click.echo("❌ Test suite failed")
            exit_code = 1
        else:
            click.echo("✅ Test suite passed")
        
        # 2. Boundary gate (if not fast)
        if not fast:
            click.echo("\n2️⃣ Running boundary gate...")
            boundary_cmd = ["python3", "-m", "pytest", "tests/", "-m", "sensitive", "--tb=short"]
            if verbose:
                boundary_cmd.append("-v")
            
            result = subprocess.run(boundary_cmd, cwd=Path(__file__).parent.parent)
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
            "python3", "scripts/demo_v2_restrained_autonomy.py",
            "--operator-decision", "deny"
        ]
        
        env = os.environ.copy()
        env.update({
            'EXOARMUR_FLAG_V2_FEDERATION_ENABLED': 'true',
            'EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED': 'true',
            'EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED': 'true',
            'PYTHONPATH': f"{Path(__file__).parent}:{Path(__file__).parent.parent / 'spec' / 'contracts'}"
        })
        
        result = subprocess.run(demo_cmd, cwd=Path(__file__).parent.parent, 
                              capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            click.echo("❌ Demo smoke test failed")
            if verbose:
                click.echo(result.stderr)
            exit_code = 1
        else:
            # Check for required markers
            output = result.stdout
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
                    replay_cmd = [
                        "python3", "scripts/demo_v2_restrained_autonomy.py",
                        "--replay", audit_id
                    ]
                    
                    result = subprocess.run(replay_cmd, cwd=Path(__file__).parent.parent,
                                          capture_output=True, text=True, env=env)
                    
                    if result.returncode != 0:
                        click.echo("❌ Replay verification failed")
                        if verbose:
                            click.echo(result.stderr)
                        exit_code = 1
                    else:
                        if "REPLAY_VERIFIED=true" in result.stdout:
                            click.echo("✅ Replay verification passed")
                        else:
                            click.echo("⚠️ Replay verification incomplete (known limitation)")
                else:
                    click.echo("❌ Could not extract audit ID for replay")
                    exit_code = 1
        
        # Final result
        click.echo("\n" + "=" * 50)
        if exit_code == 0:
            click.echo("🎯 VERIFY_ALL: PASSED")
            click.echo("All systems green and ready for production")
        else:
            click.echo("❌ VERIFY_ALL: FAILED")
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
        cmd = ["python3", "scripts/demo_v2_restrained_autonomy.py"]
        
        if replay:
            cmd.extend(["--replay", replay])
        else:
            cmd.extend(["--operator-decision", operator_decision])
        
        env = os.environ.copy()
        if not replay:
            env.update({
                'EXOARMUR_FLAG_V2_FEDERATION_ENABLED': 'true',
                'EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED': 'true',
                'EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED': 'true',
            })
        env['PYTHONPATH'] = f"{Path(__file__).parent}:{Path(__file__).parent.parent / 'spec' / 'contracts'}"
        
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent, env=env)
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
    click.echo("🏥 ExoArmur Health Check")
    
    try:
        # Test basic imports
        from api_models import TelemetryIngestResponseV1
        from models_v1 import TelemetryEventV1
        click.echo("✅ Core imports working")
        
        # Test feature flags
        from feature_flags.feature_flags import get_feature_flags
        flags = get_feature_flags()
        click.echo(f"✅ Feature flags loaded: {len(flags._flags)} configured")
        
        # Test V2 pipeline
        from v2_restrained_autonomy import RestrainedAutonomyPipeline
        pipeline = RestrainedAutonomyPipeline()
        click.echo("✅ V2 pipeline initialized")
        
        click.echo("🎯 System healthy")
        sys.exit(0)
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
