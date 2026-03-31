#!/usr/bin/env python3
"""
External Validation Web Server for ExoArmur

This server provides the external validation interface with enhanced
trust signal extraction and clear visibility of deterministic behavior.
"""

import os
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import webbrowser

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.byzantine_fault_injection import (
    ByzantineTestRunner, 
    ByzantineScenario
)
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event
from datetime import datetime, timezone

class ExternalValidationAPIHandler(SimpleHTTPRequestHandler):
    """Custom handler for ExoArmur external validation API"""
    
    def __init__(self, *args, **kwargs):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Serve the external validation UI
            self.serve_file('external_validation_ui.html', 'text/html')
        elif parsed_path.path == '/api/health':
            self.serve_health()
        else:
            # Try to serve static files
            self.serve_file(parsed_path.path.lstrip('/'), 'text/html')
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/replay':
            self.handle_replay()
        elif parsed_path.path == '/api/verify':
            self.handle_consensus()
        elif parsed_path.path == '/api/byzantine-test':
            self.handle_byzantine()
        else:
            self.send_error(404, "API endpoint not found")
    
    def serve_file(self, filename, content_type):
        """Serve a static file"""
        file_path = Path(__file__).parent / filename
        
        if not file_path.exists():
            self.send_error(404, f"File not found: {filename}")
            return
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")
    
    def serve_health(self):
        """Serve health check"""
        response = {
            'status': 'healthy',
            'service': 'exoarmur-external-validation',
            'version': '1.0.0',
            'determinism': 'enforced',
            'validation_mode': 'external'
        }
        
        self.send_json_response(response)
    
    def handle_replay(self):
        """Handle replay request with trust signal extraction"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            # Log the canonical input for visibility
            print(f"📋 CANONICAL INPUT RECEIVED:")
            print(f"   Correlation ID: {request_data.get('correlation_id', 'unknown')}")
            print(f"   Events: {len(events)} canonical events")
            for i, event in enumerate(events):
                print(f"   Event {i+1}: {event.event_type} (ID: {event.event_id[:16]}...)")
            
            # Run replay
            audit_store = {"external-validation-001": events}
            replay_engine = ReplayEngine(audit_store=audit_store)
            report = replay_engine.replay_correlation("external-validation-001")
            
            # Generate deterministic hash
            replay_output = report.to_dict()
            replay_hash = stable_hash(canonical_json(replay_output))
            
            # Log the trust signal
            print(f"🔐 TRUST SIGNAL - REPLAY HASH: {replay_hash}")
            
            response = {
                'correlation_id': report.correlation_id,
                'replay_hash': replay_hash,
                'total_events': report.total_events,
                'processed_events': report.processed_events,
                'failed_events': report.failed_events,
                'result': report.result.value,
                'intent_hash_verified': report.intent_hash_verified,
                'safety_gate_verified': report.safety_gate_verified,
                'audit_integrity_verified': report.audit_integrity_verified,
                'reconstructed_intents': len(report.reconstructed_intents),
                'reconstructed_decisions': len(report.reconstructed_decisions),
                'failures': report.failures,
                'warnings': report.warnings,
                'trust_signal': {
                    'type': 'replay_hash',
                    'value': replay_hash,
                    'deterministic': True,
                    'input_events': len(events)
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Replay failed: {e}")
    
    def handle_consensus(self):
        """Handle consensus verification with trust signal extraction"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            print(f"🔗 CONSENSUS VERIFICATION STARTED")
            print(f"   Node count: 3")
            print(f"   Events: {len(events)} canonical events")
            
            # Run multi-node verification
            verifier = MultiNodeReplayVerifier(node_count=3)
            divergence_report = verifier.verify_consensus(events, "external-validation-001")
            
            # Log node-by-node results for visibility
            print(f"📊 NODE-BY-NODE RESULTS:")
            for node_id, hash_value in divergence_report.node_hashes.items():
                consensus_status = "✅ CONSENSUS" if node_id in divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
                print(f"   {node_id}: {hash_value[:16]}... {consensus_status}")
            
            # Log consensus trust signal
            consensus_achieved = not divergence_report.has_divergence()
            print(f"🔐 TRUST SIGNAL - CONSENSUS: {consensus_achieved}")
            
            response = {
                'correlation_id': "external-validation-001",
                'node_count': verifier.node_count,
                'consensus': consensus_achieved,
                'consensus_result': divergence_report.consensus_result.value,
                'node_hashes': divergence_report.node_hashes,
                'divergent_nodes': divergence_report.divergent_nodes,
                'consensus_nodes': divergence_report.get_consensus_nodes(),
                'trust_signal': {
                    'type': 'consensus',
                    'value': consensus_achieved,
                    'node_count': verifier.node_count,
                    'agreeing_nodes': len(divergence_report.get_consensus_nodes()),
                    'deterministic': True
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Consensus verification failed: {e}")
    
    def handle_byzantine(self):
        """Handle Byzantine fault injection with trust signal extraction"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            # Parse scenario
            scenario_name = request_data.get('scenario', 'single_node')
            scenario = ByzantineScenario(scenario_name)
            
            print(f"🛡️ BYZANTINE FAULT INJECTION: {scenario_name.upper()}")
            
            # Run Byzantine test
            test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
            result = test_runner.run_byzantine_test(events, scenario)
            
            # Extract corrupted nodes
            corrupted_nodes = []
            for node_result in result.injection_results:
                if node_result.corrupted_events:
                    corrupted_nodes.append(f"corrupted-node-{len(corrupted_nodes)+1}")
            
            # Log fault detection trust signal
            divergence_detected = result.divergence_report.has_divergence()
            print(f"🔐 TRUST SIGNAL - FAULT DETECTION: {divergence_detected}")
            print(f"   Corrupted nodes: {len(corrupted_nodes)}")
            
            response = {
                'correlation_id': "external-validation-001",
                'scenario': result.scenario.value,
                'baseline_hash': result.baseline_hash,
                'consensus': not result.divergence_report.has_divergence(),
                'consensus_result': result.divergence_report.consensus_result.value,
                'corrupted_nodes': corrupted_nodes,
                'divergence_detected': divergence_detected,
                'node_count': len(result.divergence_report.node_hashes),
                'trust_signal': {
                    'type': 'fault_detection',
                    'value': divergence_detected,
                    'scenario': scenario_name,
                    'corrupted_nodes': len(corrupted_nodes),
                    'resilience_verified': scenario_name == 'single_node' and divergence_detected
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Byzantine test failed: {e}")
    
    def send_json_response(self, data):
        """Send JSON response"""
        json_data = json.dumps(data, indent=2, sort_keys=True)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-length', str(len(json_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    """Main entry point"""
    port = 8080
    host = 'localhost'
    
    print("🎯 EXOARMUR EXTERNAL VALIDATION SERVER")
    print("=" * 50)
    print(f"🌐 Starting external validation server on http://{host}:{port}")
    print("🛡️  Demonstrating provably deterministic governance")
    print("🔐 Extracting and displaying trust signals")
    print()
    
    # Create server
    server = HTTPServer((host, port), ExternalValidationAPIHandler)
    
    # Open browser in a separate thread
    def open_browser():
        import time
        time.sleep(1)  # Wait for server to start
        webbrowser.open(f'http://{host}:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print(f"✅ External validation server running at http://{host}:{port}")
        print("📱 External validation UI will open in your browser")
        print("⏹️  Press Ctrl+C to stop the server")
        print()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 External validation server stopped by user")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
