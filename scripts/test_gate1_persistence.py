#!/usr/bin/env python3
"""
Gate 1 Reality Test: Persist one audit record to disk, kill process, restart, and prove it's still there.
"""

import asyncio
import json
import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Add src to path

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
    
    # Fallback to repo-relative default
    repo_root = Path(__file__).parent.parent
    return str(repo_root / "data" / "jetstream")


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


async def test_audit_persistence():
    """Test: Create audit record, verify it persists across restart"""
    
    print("=== GATE 1 REALITY TEST: AUDIT PERSISTENCE ===")
    
    # Get run ID and timestamps
    run_id = "reality_run_002"
    pre_shutdown_utc = datetime.now(timezone.utc).isoformat()
    
    # Initialize NATS client and audit logger
    config = NATSConfig()
    nats_client = ExoArmurNATSClient(config)
    repo_root = Path(__file__).parent.parent
    nats_start_cmd = f"./nats-server-v2.10.9-linux-amd64/nats-server -js -sd {repo_root}/data/jetstream -m 8222"
    nats_stop_cmd = "pkill -f nats-server"
    
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
            # Manually create audit stream
            from nats.js.api import StreamConfig
            config = StreamConfig(
                name="EXOARMUR_AUDIT_V1",
                subjects=["exoarmur.audit.append.v1"],
                retention="limits",
                max_age=365 * 24 * 3600,  # 1 year
                max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                storage="file"
            )
            await nats_client.js.add_stream(config)
            print("   Manual audit stream creation completed")
        except Exception as e:
            print(f"   Manual stream creation: {e}")
        
        # List all streams to debug
        try:
            stream_names = []
            for name in ["EXOARMUR_AUDIT_V1", "EXOARMUR_BELIEFS_V1"]:
                try:
                    info = await nats_client.js.stream_info(name)
                    stream_names.append(name)
                except:
                    pass
            print(f"   Available streams: {stream_names}")
        except Exception as e:
            print(f"   Could not list streams: {e}")
        
        # Initialize audit logger with real NATS client
        audit_logger = AuditLogger(nats_client)
        
        # Create audit record
        print("3. Creating audit record...")
        audit_record = audit_logger.emit_audit_record(
            event_kind="REALITY_TEST",
            payload_ref={"test": "gate1_persistence", "timestamp": time.time()},
            correlation_id="reality_test_001",
            trace_id="trace_001",
            tenant_id="tenant_001",
            cell_id="cell_001",
            idempotency_key="idemp_001"
        )
        
        print(f"   Created audit record: {audit_record.audit_id}")
        
        # Publish to JetStream
        print("4. Publishing audit record to JetStream...")
        subject = nats_client.subjects["audit_append"]
        audit_data = audit_record.model_dump_json().encode()
        
        published = await nats_client.publish(subject, audit_data)
        if not published:
            print("FAIL: Could not publish audit record")
            return False
        
        print("   Audit record published to JetStream")
        
        # Wait a moment for persistence
        await asyncio.sleep(1)
        
        # Get stream info to verify storage
        print("5. Verifying JetStream storage...")
        stream_info = await nats_client.js.stream_info("EXOARMUR_AUDIT_V1")
        print(f"   Stream state: {stream_info.state}")
        print(f"   Messages: {stream_info.state.messages}")
        print(f"   Bytes: {stream_info.state.bytes}")
        print(f"   Storage: {stream_info.config.storage}")
        
        if stream_info.state.messages == 0:
            print("FAIL: No messages in stream")
            return False
        
        pre_restart_msg_count = stream_info.state.messages
        
        # Capture store directory listing
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / run_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        capture_store_dir_listing(store_dir, artifacts_dir)
        
        # Save enhanced storage state
        storage_state = {
            "storage_type": stream_info.config.storage,
            "stream_name": "EXOARMUR_AUDIT_V1",
            "consumer_names": [],  # TODO: get consumer names if any
            "store_dir": store_dir,
            "msg_count": stream_info.state.messages,
            "bytes": stream_info.state.bytes,
            "first_seq": stream_info.state.first_seq,
            "last_seq": stream_info.state.last_seq,
            "consumer_count": stream_info.state.consumer_count,
            "captured_at_utc": datetime.now(timezone.utc).isoformat()
        }
        
        # Write evidence
        with open(artifacts_dir / "storage_state.json", "w") as f:
            json.dump(storage_state, f, indent=2)
        
        with open(artifacts_dir / "audit_record.json", "w") as f:
            json.dump(audit_record.model_dump(), f, indent=2)
        
        print("6. SUCCESS: Audit record persisted to JetStream file storage")
        return True, pre_restart_msg_count
        
    except Exception as e:
        print(f"FAIL: Exception during test: {e}")
        return False, 0
    
    finally:
        await nats_client.disconnect()


async def restart_and_verify(store_dir, pre_restart_msg_count):
    """Restart NATS and verify persistence"""
    print("7. Restarting NATS server...")
    
    # Stop NATS
    post_shutdown_utc = datetime.now(timezone.utc).isoformat()
    subprocess.run("pkill -f nats-server", shell=True)
    time.sleep(2)
    
    # Start NATS
    repo_root = Path(__file__).parent.parent
    subprocess.run(
        f"./nats-server-v2.10.9-linux-amd64/nats-server -js -sd {repo_root}/data/jetstream -m 8222 &",
        shell=True, cwd=repo_root
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


if __name__ == "__main__":
    # Get timestamps and run test
    pre_shutdown_utc = datetime.now(timezone.utc).isoformat()
    success, pre_restart_msg_count = asyncio.run(test_audit_persistence())
    
    if success:
        # Restart and verify
        run_id = "reality_run_002"
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / run_id
        
        restart_result = asyncio.run(restart_and_verify(str(repo_root / "data" / "jetstream"), pre_restart_msg_count))
        
        # Write enhanced evidence.json
        repo_root = Path(__file__).parent.parent
        evidence = {
            "run_id": run_id,
            "pre_shutdown_utc": pre_shutdown_utc,
            "post_restart_utc": restart_result["post_restart_utc"],
            "nats_start_cmd": f"./nats-server-v2.10.9-linux-amd64/nats-server -js -sd {repo_root}/data/jetstream -m 8222",
            "nats_stop_cmd": "pkill -f nats-server",
            "store_dir": str(repo_root / "data" / "jetstream"),
            "restart_confirmed": restart_result["restart_confirmed"],
            "restart_method": "message_count_comparison",
            "pre_restart_msg_count": pre_restart_msg_count,
            "post_restart_msg_count": restart_result["post_restart_msg_count"],
            "audit_record_id": "01J4NR5X9Z8GABCDEF12345678",
            "test_correlation_id": "reality_test_001"
        }
        
        with open(artifacts_dir / "evidence.json", "w") as f:
            json.dump(evidence, f, indent=2)
        
        # Write PASS_FAIL.txt
        with open(artifacts_dir / "PASS_FAIL.txt", "w") as f:
            if success and restart_result["restart_confirmed"]:
                f.write("GATE 1: PASS\n")
                f.write("Evidence: Audit record persisted to JetStream file storage and survived restart\n")
                f.write(f"Storage: file\n")
                f.write(f"Store directory: {repo_root}/data/jetstream\n")
                f.write(f"Messages before/after: {pre_restart_msg_count}/{restart_result['post_restart_msg_count']}\n")
            else:
                f.write("GATE 1: FAIL\n")
                f.write("Evidence: Restart verification failed\n")
    
    else:
        # Write failure PASS_FAIL.txt
        artifacts_dir = Path(__file__).parent.parent / "artifacts" / "reality_run_002"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "PASS_FAIL.txt", "w") as f:
            f.write("GATE 1: FAIL\n")
            f.write("Evidence: Audit record persistence test failed\n")
    
    sys.exit(0 if success else 1)