#!/usr/bin/env python3
"""
Simple Web Server for ExoArmur Demo UI

This script serves the demo HTML page and provides API endpoints
for the web interface to interact with the ExoArmur backend.
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

class ExoArmurAPIHandler(SimpleHTTPRequestHandler):
    """Custom handler for ExoArmur demo API"""
    
    def __init__(self, *args, **kwargs):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Serve the demo UI from parent directory
            self.serve_file('../demo_ui.html', 'text/html')
        elif parsed_path.path == '/api/demo-data':
            self.serve_demo_data()
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
        elif parsed_path.path == '/api/consensus':
            self.handle_consensus()
        elif parsed_path.path == '/api/byzantine':
            self.handle_byzantine()
        elif parsed_path.path == '/api/demo':
            self.handle_complete_demo()
        else:
            self.send_error(404, "API endpoint not found")
    
    def serve_file(self, filename, content_type):
        """Serve a static file"""
        base_dir = Path(__file__).parent.resolve()
        
        # Sanitize filename to prevent path traversal
        filename = Path(filename).name
        
        file_path = (base_dir / filename).resolve()
        
        # Explicit containment check (Python 3.9+: is_relative_to, 3.8: try/except)
        try:
            file_path.relative_to(base_dir)
        except ValueError:
            self.send_error(403, "Access denied")
            return

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
    
    def serve_demo_data(self):
        """Serve demo data for the UI"""
        try:
            events = self.create_demo_events()
            events_data = [event.to_dict() for event in events]
            
            response = {
                'correlation_id': 'demo-scenario-001',
                'events': events_data,
                'usage': {
                    'replay': 'POST /api/replay',
                    'consensus': 'POST /api/consensus',
                    'byzantine': 'POST /api/byzantine',
                    'demo': 'POST /api/demo'
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Error creating demo data: {e}")
    
    def serve_health(self):
        """Serve health check"""
        response = {
            'status': 'healthy',
            'service': 'exoarmur-demo-ui',
            'version': '1.0.0',
            'determinism': 'enforced'
        }
        
        self.send_json_response(response)
    
    def handle_replay(self):
        """Handle replay request"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            # Run replay
            audit_store = {"demo-correlation-001": events}
            replay_engine = ReplayEngine(audit_store=audit_store)
            report = replay_engine.replay_correlation("demo-correlation-001")
            
            # Generate deterministic hash
            replay_output = report.to_dict()
            replay_hash = stable_hash(canonical_json(replay_output))
            
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
                'failures': report.failures,
                'warnings': report.warnings
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Replay failed: {e}")
    
    def handle_consensus(self):
        """Handle consensus verification request"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            # Run multi-node verification
            verifier = MultiNodeReplayVerifier(node_count=3)
            divergence_report = verifier.verify_consensus(events, "demo-correlation-001")
            
            response = {
                'correlation_id': "demo-correlation-001",
                'node_count': verifier.node_count,
                'consensus': not divergence_report.has_divergence(),
                'consensus_result': divergence_report.consensus_result.value,
                'node_hashes': divergence_report.node_hashes,
                'divergent_nodes': divergence_report.divergent_nodes,
                'consensus_nodes': divergence_report.get_consensus_nodes()
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Consensus verification failed: {e}")
    
    def handle_byzantine(self):
        """Handle Byzantine fault injection request"""
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
            
            # Run Byzantine test
            test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
            result = test_runner.run_byzantine_test(events, scenario)
            
            # Extract corrupted nodes
            corrupted_nodes = []
            for node_result in result.injection_results:
                if node_result.corrupted_events:
                    corrupted_nodes.append(f"corrupted-node-{len(corrupted_nodes)+1}")
            
            response = {
                'correlation_id': "demo-correlation-001",
                'scenario': result.scenario.value,
                'baseline_hash': result.baseline_hash,
                'consensus': not result.divergence_report.has_divergence(),
                'consensus_result': result.divergence_report.consensus_result.value,
                'corrupted_nodes': corrupted_nodes,
                'divergence_detected': result.divergence_report.has_divergence(),
                'node_count': len(result.divergence_report.node_hashes)
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Byzantine test failed: {e}")
    
    def handle_complete_demo(self):
        """Handle complete demo request"""
        try:
            # Create demo events
            events = self.create_demo_events()
            events_data = [event.to_dict() for event in events]
            
            # Run replay
            audit_store = {"demo-correlation-001": events}
            replay_engine = ReplayEngine(audit_store=audit_store)
            report = replay_engine.replay_correlation("demo-correlation-001")
            replay_output = report.to_dict()
            replay_hash = stable_hash(canonical_json(replay_output))
            
            # Run consensus
            verifier = MultiNodeReplayVerifier(node_count=3)
            divergence_report = verifier.verify_consensus(events, "demo-correlation-001")
            
            # Run Byzantine tests
            test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
            clean_result = test_runner.run_byzantine_test(events, ByzantineScenario.CLEAN)
            single_result = test_runner.run_byzantine_test(events, ByzantineScenario.SINGLE_NODE)
            
            response = {
                'demo_completed': True,
                'replay': {
                    'events_processed': report.processed_events,
                    'total_events': report.total_events,
                    'result': report.result.value,
                    'hash': replay_hash,
                    'safety_gates_verified': report.safety_gate_verified
                },
                'consensus': {
                    'node_count': verifier.node_count,
                    'consensus': not divergence_report.has_divergence(),
                    'agreeing_nodes': len(divergence_report.get_consensus_nodes()),
                    'hash': list(divergence_report.node_hashes.values())[0] if divergence_report.node_hashes else None
                },
                'byzantine': {
                    'clean_scenario': not clean_result.divergence_report.has_divergence(),
                    'fault_detected': single_result.divergence_report.has_divergence(),
                    'baseline_hash': clean_result.baseline_hash,
                    'corrupted_nodes': len([r for r in single_result.injection_results if r.corrupted_events])
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Complete demo failed: {e}")
    
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
    
    def create_demo_events(self):
        """Create demonstration canonical events"""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='demo-tenant',
                cell_id='demo-cell-01',
                idempotency_key='demo-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'security-event-001',
                    'source': 'edr-sensor-01',
                    'severity': 'high',
                    'event_type': 'suspicious_process'
                }}},
                hashes={'sha256': 'demo-telemetry-hash-001'},
                correlation_id='demo-scenario-001',
                trace_id='demo-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345672',
                tenant_id='demo-tenant',
                cell_id='demo-cell-01',
                idempotency_key='demo-key-001',
                recorded_at=base_time,
                event_kind='safety_gate_evaluated',
                payload_ref={'kind': {'ref': {
                    'verdict': 'require_human_approval',
                    'risk_level': 'high',
                    'policy_rules': ['human_approval_required'],
                    'automated_checks': ['passed']
                }}},
                hashes={'sha256': 'demo-safety-hash-001'},
                correlation_id='demo-scenario-001',
                trace_id='demo-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345673',
                tenant_id='demo-tenant',
                cell_id='demo-cell-01',
                idempotency_key='demo-key-001',
                recorded_at=base_time,
                event_kind='approval_requested',
                payload_ref={'kind': {'ref': {
                    'approval_id': 'approval-001',
                    'operator': 'security-ops-01',
                    'approval_type': 'manual_review'
                }}},
                hashes={'sha256': 'demo-approval-hash-001'},
                correlation_id='demo-scenario-001',
                trace_id='demo-trace-001'
            )
        ]
        
        return [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]

def main():
    """Main entry point"""
    port = 8080
    host = 'localhost'
    
    print("🚀 ExoArmur Demo Web Server")
    print("=" * 40)
    print(f"🌐 Starting server on http://{host}:{port}")
    print("🛡️  Demonstrating deterministic governance")
    print()
    
    # Create server
    server = HTTPServer((host, port), ExoArmurAPIHandler)
    
    # Open browser in a separate thread
    def open_browser():
        import time
        time.sleep(1)  # Wait for server to start
        webbrowser.open(f'http://{host}:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print(f"✅ Server running at http://{host}:{port}")
        print("📱 Demo UI will open in your browser")
        print("⏹️  Press Ctrl+C to stop the server")
        print()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
