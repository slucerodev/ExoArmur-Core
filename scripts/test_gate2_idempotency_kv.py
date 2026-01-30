#!/usr/bin/env python3
"""
Gate 2 Reality Test: Restart survival and idempotency enforcement with durable KV.
"""

import asyncio
import json
import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from nats_client import ExoArmurNATSClient, NATSConfig
from audit.audit_logger import AuditLogger


def get_nats_store_dir():
    """Get the actual JetStream store directory from running NATS"""
    try:
        # Try to get store dir from NATS server info
        result = subprocess.run(
            ["./nats-server-v2.10.9-linux-amd64/nats-server", "-report", "jetstream"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        if result.returncode == 0:
            # Parse output for store directory
            for line in result.stdout.split('\n'):
                if 'Store Directory' in line:
                    return line.split(':')[1].strip()
    except:
        pass
    
    # Fallback to known default
    return "data/jetstream"


def capture_store_dir_listing(store_dir, artifacts_dir):
    """Capture detailed store directory listing"""
    try:
        listing_file = artifacts_dir / "store_dir_listing.txt"
        with open(listing_file, 'w') as f:
            f.write(f"JetStream Store Directory: {store_dir}\n")
            f.write(f"Captured at: {datetime.now(timezone.utc).isoformat()}\n\n")
            
            # ls -la
            f.write("=== ls -la ===\n")
            result = subprocess.run(["ls", "-la", store_dir], capture_output=True, text=True)
            f.write(result.stdout + "\n")
            
            # find files
            f.write("=== find files ===\n") 
            result = subprocess.run(["find", store_dir, "-maxdepth", "3", "-type", "-print"], capture_output=True, text=True)
            f.write(result.stdout + "\n")
            
            # du -sh
            f.write("=== disk usage ===\n")
            result = subprocess.run(["du", "-sh", store_dir], capture_output=True, text=True)
            f.write(result.stdout + "\n")
            
        return True
    except Exception as e:
        print(f"Failed to capture store listing: {e}")
        return False


async def test_gate2_with_idempotency():
    """Test: Restart survival and idempotency enforcement with KV"""
    
    print("=== GATE 2 REALITY TEST: RESTART SURVIVAL + DURABLE IDEMPOTENCY ===")
    
    # Get run ID and timestamps
    run_id = "reality_run_004"
    pre_shutdown_utc = datetime.now(timezone.utc).isoformat()
    
    # Initialize NATS client and audit logger
    config = NATSConfig()
    nats_client = ExoArmurNATSClient(config)
    nats_start_cmd = "./nats-server-v2.10.9-linux-amd64/nats-server -js -sd data/jetstream -m 8222"
    nats_stop_cmd = "pkill -f nats-server"
    
    # Test idempotency key
    test_idempotency_key = "gate2_test_idemp_002"
    
    try:
        # Connect to NATS
        print("1. Connecting to NATS...")
        connected = await nats_client.connect()
        if not connected:
            print("FAIL: Could not connect to NATS")
            return False
        
        # Get store directory
        store_dir = get_nats_store_dir()
        print(f"   Store directory: {store_dir}")
        
        # Ensure streams exist
        print("2. Ensuring JetStream streams exist...")
        try:
            from nats.js.api import StreamConfig
            stream_config = StreamConfig(
                name="EXOARMUR_AUDIT_V1",
                subjects=["exoarmur.audit.append.v1"],
                retention="limits",
                max_age=365 * 24 * 3600,  # 1 year
                max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                storage="file"
            )
            await nats_client.js.add_stream(stream_config)
            print("   Audit stream ensured")
        except Exception as e:
            print(f"   Stream creation: {e}")
        
        # Get initial message count
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        initial_msg_count = stream_info.state.messages
        print(f"   Initial message count: {initial_msg_count}")
        
        # Initialize audit logger
        audit_logger = AuditLogger(nats_client)
        
        # Inject event FIRST time
        print("3. Injecting audit event (first time)...")
        audit_record1 = await audit_logger.emit_audit_record_async(
            event_kind="GATE2_TEST",
            payload_ref={"test": "restart_idempotency", "injection": 1},
            correlation_id="gate2_test_002",
            trace_id="trace_gate2_001",
            tenant_id="tenant_001",
            cell_id="cell_001",
            idempotency_key=test_idempotency_key
        )
        
        await asyncio.sleep(1)
        
        # Check message count after first injection
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        after_first_injection = stream_info.state.messages
        print(f"   After first injection: {after_first_injection}")
        
        # Inject event SECOND time (should be idempotent)
        print("4. Injecting audit event (second time - should be idempotent)...")
        audit_record2 = await audit_logger.emit_audit_record_async(
            event_kind="GATE2_TEST",
            payload_ref={"test": "restart_idempotency", "injection": 2},
            correlation_id="gate2_test_002",
            trace_id="trace_gate2_002",
            tenant_id="tenant_001",
            cell_id="cell_001",
            idempotency_key=test_idempotency_key
        )
        
        await asyncio.sleep(1)
        
        # Check message count after second injection
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        after_second_injection = stream_info.state.messages
        print(f"   After second injection: {after_second_injection}")
        print(f"   Idempotency enforced: {after_first_injection == after_second_injection}")
        
        pre_restart_msg_count = stream_info.state.messages
        
        # Capture artifacts
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / run_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        capture_store_dir_listing(store_dir, artifacts_dir)
        
        # Save storage state
        storage_state = {
            "storage_type": stream_info.config.storage,
            "stream_name": "EXOARMUR_AUDIT_V1",
            "store_dir": store_dir,
            "msg_count": stream_info.state.messages,
            "bytes": stream_info.state.bytes,
            "captured_at_utc": datetime.now(timezone.utc).isoformat()
        }
        
        with open(artifacts_dir / "storage_state.json", "w") as f:
            json.dump(storage_state, f, indent=2)
        
        with open(artifacts_dir / "audit_record.json", "w") as f:
            json.dump(audit_record1.model_dump(), f, indent=2)
        
        # Save idempotency evidence
        idempotency_evidence = {
            "test_idempotency_key": test_idempotency_key,
            "method": "jetstream_kv",
            "kv_bucket": "EXOARMUR_IDEMPOTENCY_V1",
            "first_injection_audit_id": audit_record1.audit_id,
            "second_injection_audit_id": audit_record2.audit_id,
            "idempotency_hit": (audit_record1.audit_id == audit_record2.audit_id),
            "msg_counts": {
                "initial": initial_msg_count,
                "after_first": after_first_injection,
                "after_second": after_second_injection
            }
        }
        
        with open(artifacts_dir / "idempotency_check.json", "w") as f:
            json.dump(idempotency_evidence, f, indent=2)
        
        print("5. SUCCESS: Pre-restart phase completed")
        return True, pre_restart_msg_count, after_second_injection, idempotency_evidence
        
    except Exception as e:
        print(f"FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0, {}
    
    finally:
        await nats_client.disconnect()


async def restart_and_verify(store_dir, pre_restart_msg_count):
    """Restart NATS and verify persistence"""
    print("6. Restarting NATS server...")
    
    # Stop NATS
    post_shutdown_utc = datetime.now(timezone.utc).isoformat()
    subprocess.run("pkill -f nats-server", shell=True)
    time.sleep(2)
    
    # Start NATS
    subprocess.run(
        "./nats-server-v2.10.9-linux-amd64/nats-server -js -sd data/jetstream -m 8222 &",
        shell=True, cwd=Path(__file__).parent.parent
    )
    time.sleep(3)
    
    post_restart_utc = datetime.now(timezone.utc).isoformat()
    
    # Verify restart
    config = NATSConfig()
    nats_client = ExoArmurNATSClient(config)
    
    try:
        await nats_client.connect()
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        post_restart_msg_count = stream_info.state.messages
        
        print(f"   Post-restart messages: {post_restart_msg_count}")
        print(f"   Pre-restart messages: {pre_restart_msg_count}")
        
        restart_confirmed = (post_restart_msg_count == pre_restart_msg_count)
        print(f"   Restart confirmed: {restart_confirmed}")
        
        await nats_client.disconnect()
        
        return {
            "post_restart_utc": post_restart_utc,
            "post_restart_msg_count": post_restart_msg_count,
            "restart_confirmed": restart_confirmed
        }
        
    except Exception as e:
        print(f"   Restart verification failed: {e}")
        return {
            "post_restart_utc": post_restart_utc,
            "post_restart_msg_count": 0,
            "restart_confirmed": False
        }


async def post_restart_duplicate_check():
    """Check idempotency after restart"""
    print("7. Post-restart duplicate injection check...")
    
    config = NATSConfig()
    nats_client = ExoArmurNATSClient(config)
    test_idempotency_key = "gate2_test_idemp_002"
    
    try:
        await nats_client.connect()
        
        # Inject event THIRD time (after restart)
        audit_logger = AuditLogger(nats_client)
        audit_record3 = await audit_logger.emit_audit_record_async(
            event_kind="GATE2_TEST",
            payload_ref={"test": "restart_idempotency", "injection": 3},
            correlation_id="gate2_test_002",
            trace_id="trace_gate2_003",
            tenant_id="tenant_001",
            cell_id="cell_001",
            idempotency_key=test_idempotency_key
        )
        
        await asyncio.sleep(1)
        
        # Check final message count
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        final_msg_count = stream_info.state.messages
        print(f"   Final message count: {final_msg_count}")
        
        await nats_client.disconnect()
        
        return final_msg_count, audit_record3.audit_id
        
    except Exception as e:
        print(f"   Post-restart check failed: {e}")
        return 0, ""


if __name__ == "__main__":
    # Get timestamps and run test
    pre_shutdown_utc = datetime.now(timezone.utc).isoformat()
    success, pre_restart_count, pre_duplicate_count, idempotency_evidence = asyncio.run(test_gate2_with_idempotency())
    
    if success:
        # Restart and verify
        run_id = "reality_run_004"
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / run_id
        
        restart_result = asyncio.run(restart_and_verify("data/jetstream", pre_restart_count))
        
        # Post-restart duplicate check
        final_count, final_audit_id = asyncio.run(post_restart_duplicate_check())
        
        # Write comprehensive evidence
        evidence = {
            "run_id": run_id,
            "pre_shutdown_utc": pre_shutdown_utc,
            "post_restart_utc": restart_result["post_restart_utc"],
            "nats_start_cmd": "./nats-server-v2.10.9-linux-amd64/nats-server -js -sd data/jetstream -m 8222",
            "nats_stop_cmd": "pkill -f nats-server",
            "store_dir": "data/jetstream",
            "restart_confirmed": restart_result["restart_confirmed"],
            "restart_method": "message_count_comparison",
            "pre_restart_msg_count": pre_restart_count,
            "post_restart_msg_count": restart_result["post_restart_msg_count"],
            "post_duplicate_injection_msg_count": pre_duplicate_count,
            "final_msg_count": final_count,
            "idempotency_enforced": (pre_duplicate_count == final_count),
            "idempotency_method": "jetstream_kv",
            "test_idempotency_key": "gate2_test_idemp_002",
            "final_audit_id": final_audit_id
        }
        
        with open(artifacts_dir / "evidence.json", "w") as f:
            json.dump(evidence, f, indent=2)
        
        # Write PASS_FAIL.txt
        gate2_pass = (
            restart_result["restart_confirmed"] and 
            (pre_duplicate_count == final_count) and
            idempotency_evidence.get("idempotency_hit", False)
        )
        
        with open(artifacts_dir / "PASS_FAIL.txt", "w") as f:
            if gate2_pass:
                f.write("GATE 2: PASS\n")
                f.write("Evidence: Restart survival and idempotency enforcement verified\n")
                f.write(f"Storage: file\n")
                f.write(f"Store directory: data/jetstream\n")
                f.write(f"Messages pre/post restart: {pre_restart_count}/{restart_result['post_restart_msg_count']}\n")
                f.write(f"Idempotency enforced: {pre_duplicate_count} -> {final_count}\n")
                f.write(f"Idempotency method: JetStream KV\n")
            else:
                f.write("GATE 2: FAIL\n")
                f.write("Evidence: Restart survival or idempotency failed\n")
    
    else:
        # Write failure PASS_FAIL.txt
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / "reality_run_004"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "PASS_FAIL.txt", "w") as f:
            f.write("GATE 2: FAIL\n")
            f.write("Evidence: Gate 2 test failed during execution\n")
    
    sys.exit(0 if success else 1)
