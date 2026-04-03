#!/usr/bin/env python3
"""
Demo API Test Script

This script tests the ExoArmur demo API endpoints to ensure
they provide deterministic responses.
"""

import json
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def start_api_server():
    """Start the API server in background"""
    env = os.environ.copy()
    env['PYTHONHASHSEED'] = '0'
    
    cmd = [
        ".venv/bin/python", "-c", 
        """
import sys
sys.path.insert(0, '/home/oem/CascadeProjects/ExoArmur/src')
from exoarmur.demo_api import app
import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
"""
    ]
    
    process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(3)
    
    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8000/health")
        if response.status_code == 200:
            print("✅ API server started successfully")
            return process
        else:
            print(f"❌ API server health check failed: {response.status_code}")
            process.terminate()
            return None
    except Exception as e:
        print(f"❌ Failed to connect to API server: {e}")
        process.terminate()
        return None

def test_endpoint_determinism(endpoint: str, payload: dict = None):
    """Test that an endpoint returns deterministic responses"""
    url = f"http://127.0.0.1:8000{endpoint}"
    
    responses = []
    for i in range(3):
        try:
            if payload:
                response = requests.post(url, json=payload)
            else:
                response = requests.get(url)
            
            if response.status_code == 200:
                responses.append(response.json())
            else:
                print(f"❌ {endpoint} request {i+1} failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ {endpoint} request {i+1} error: {e}")
            return False
    
    # Check if all responses are identical
    first_response = responses[0]
    for i, response in enumerate(responses[1:], 1):
        if response != first_response:
            print(f"❌ {endpoint} - Response {i+1} differs from response 1")
            print(f"   Response 1: {json.dumps(first_response, sort_keys=True)}")
            print(f"   Response {i+1}: {json.dumps(response, sort_keys=True)}")
            return False
    
    print(f"✅ {endpoint} - Deterministic responses verified")
    return True

def main():
    """Run API tests"""
    print("🚀 Starting ExoArmur Demo API Tests")
    print("=" * 50)
    
    # Start API server
    server_process = start_api_server()
    if not server_process:
        sys.exit(1)
    
    try:
        # Test health endpoint
        print("\n🏥 Testing health endpoint...")
        if not test_endpoint_determinism("/health"):
            sys.exit(1)
        
        # Test root endpoint
        print("\n📄 Testing root endpoint...")
        if not test_endpoint_determinism("/"):
            sys.exit(1)
        
        # Test demo data endpoint
        print("\n📊 Testing demo data endpoint...")
        demo_response = requests.get("http://127.0.0.1:8000/demo-data")
        if demo_response.status_code != 200:
            print(f"❌ Failed to get demo data: {demo_response.status_code}")
            sys.exit(1)
        
        demo_data = demo_response.json()
        print(f"✅ Got demo data: {len(demo_data['events'])} events")
        
        # Test replay endpoint
        print("\n⚙️  Testing replay endpoint...")
        replay_payload = {
            "correlation_id": demo_data["correlation_id"],
            "events": demo_data["events"]
        }
        if not test_endpoint_determinism("/replay", replay_payload):
            sys.exit(1)
        
        # Test verification endpoint
        print("\n🔗 Testing verification endpoint...")
        if not test_endpoint_determinism("/verify", replay_payload):
            sys.exit(1)
        
        # Test Byzantine endpoint
        print("\n🛡️  Testing Byzantine endpoint...")
        byzantine_payload = {
            "correlation_id": demo_data["correlation_id"],
            "events": demo_data["events"],
            "scenario": "single_node",
            "node_count": 3,
            "deterministic_seed": 42
        }
        if not test_endpoint_determinism("/byzantine-test", byzantine_payload):
            sys.exit(1)
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ ExoArmur Demo API is fully deterministic")
        
        # Show sample responses
        print("\n📋 Sample Responses:")
        print("=" * 30)
        
        replay_resp = requests.post("http://127.0.0.1:8000/replay", json=replay_payload).json()
        print(f"Replay Hash: {replay_resp['replay_hash']}")
        print(f"Events Processed: {replay_resp['processed_events']}")
        
        verify_resp = requests.post("http://127.0.0.1:8000/verify", json=replay_payload).json()
        print(f"Consensus: {verify_resp['consensus']}")
        print(f"Node Count: {verify_resp['node_count']}")
        
        byzantine_resp = requests.post("http://127.0.0.1:8000/byzantine-test", json=byzantine_payload).json()
        print(f"Byzantine Consensus: {byzantine_resp['consensus']}")
        print(f"Divergence Detected: {byzantine_resp['divergence_detected']}")
        
    finally:
        # Clean up
        server_process.terminate()
        server_process.wait()
        print("\n🧹 API server stopped")

if __name__ == "__main__":
    main()
