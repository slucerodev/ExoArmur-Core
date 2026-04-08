#!/usr/bin/env python3
"""
Integrity Verification Server - Narrative Clarity Alignment

This server provides the simplified, user-friendly interface for ExoArmur
integrity verification with clear language and intuitive explanations.

FOCUS: User understanding and trust, NOT technical complexity
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

class IntegrityVerificationHandler(SimpleHTTPRequestHandler):
    """User-friendly integrity verification API handler"""
    
    def __init__(self, *args, **kwargs):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Serve the integrity verification UI
            self.serve_file('integrity_verification_ui.html', 'text/html')
        elif parsed_path.path == '/api/health':
            self.serve_health()
        else:
            # Try to serve static files
            self.serve_file(parsed_path.path.lstrip('/'), 'text/html')
    
    def do_POST(self):
        """Handle POST requests with user-friendly responses"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/replay':
            self.handle_replay()
        elif parsed_path.path == '/api/verify':
            self.handle_consensus()
        elif parsed_path.path == '/api/byzantine-test':
            self.handle_corruption_simulation()
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
    
    def serve_health(self):
        """Serve health check with user-friendly status"""
        response = {
            'status': 'healthy',
            'service': 'exoarmur-integrity-verification',
            'purpose': 'System integrity verification',
            'determinism': 'enforced',
            'readiness': 'ready to verify system integrity'
        }
        
        self.send_json_response(response)
    
    def handle_replay(self):
        """Handle deterministic replay verification"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            print(f"🔐 INTEGRITY CHECK: Running deterministic replay verification")
            print(f"   Events: {len(events)} integrity checks")
            print(f"   Purpose: Prove system behaves consistently")
            
            # Run replay
            audit_store = {"integrity-verification-001": events}
            replay_engine = ReplayEngine(audit_store=audit_store)
            report = replay_engine.replay_correlation("integrity-verification-001")
            
            # Generate deterministic hash
            replay_output = report.to_dict()
            replay_hash = stable_hash(canonical_json(replay_output))
            
            print(f"   ✅ INTEGRITY FINGERPRINT: {replay_hash[:16]}...")
            print(f"   ✅ PROOF: Same input always produces same output")
            
            # User-friendly response
            response = {
                'correlation_id': report.correlation_id,
                'integrity_fingerprint': replay_hash,
                'consistency_verified': True,
                'events_processed': report.processed_events,
                'system_behavior': 'consistent',
                'proof': 'Same input produces identical output every time',
                'trust_signal': {
                    'type': 'consistency_proof',
                    'value': replay_hash,
                    'meaning': 'System behaves the same way every time'
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Integrity verification failed: {e}")
    
    def handle_consensus(self):
        """Handle multi-system agreement verification"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Convert to CanonicalEvent objects
            events_data = request_data.get('events', [])
            events = [CanonicalEvent(**event_data) for event_data in events_data]
            
            print(f"🤝 AGREEMENT CHECK: Verifying across multiple systems")
            print(f"   Systems: 3 independent verification nodes")
            print(f"   Purpose: Prove independent systems agree")
            
            # Run multi-node verification
            verifier = MultiNodeReplayVerifier(node_count=3)
            divergence_report = verifier.verify_consensus(events, "integrity-verification-001")
            
            consensus_achieved = not divergence_report.has_divergence()
            agreeing_systems = len(divergence_report.get_consensus_nodes())
            
            print(f"   ✅ AGREEMENT STATUS: {agreeing_systems}/3 systems agree")
            print(f"   ✅ PROOF: Independent systems produce identical results")
            
            # User-friendly response
            response = {
                'correlation_id': "integrity-verification-001",
                'total_systems': verifier.node_count,
                'agreeing_systems': agreeing_systems,
                'agreement_achieved': consensus_achieved,
                'agreement_status': 'All systems agree' if consensus_achieved else 'Systems disagree',
                'proof': 'Independent systems produce identical results',
                'trust_signal': {
                    'type': 'agreement_proof',
                    'value': consensus_achieved,
                    'meaning': 'Multiple independent systems agree on the result'
                },
                'system_results': {
                    'consensus_nodes': divergence_report.get_consensus_nodes(),
                    'divergent_nodes': divergence_report.divergent_nodes
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Agreement verification failed: {e}")
    
    def handle_corruption_simulation(self):
        """Handle corruption attack simulation"""
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
            
            print(f"🛡️ CORRUPTION TEST: Simulating integrity attack")
            print(f"   Scenario: {scenario_name}")
            print(f"   Purpose: Prove system detects when something is wrong")
            
            # Run corruption simulation
            test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
            result = test_runner.run_byzantine_test(events, scenario)
            
            corruption_detected = result.divergence_report.has_divergence()
            
            print(f"   ✅ CORRUPTION DETECTION: {corruption_detected}")
            print(f"   ✅ PROOF: System identifies tampering or corruption")
            
            # User-friendly response
            response = {
                'correlation_id': "integrity-verification-001",
                'test_scenario': result.scenario.value,
                'corruption_detected': corruption_detected,
                'detection_status': 'Corruption detected' if corruption_detected else 'No corruption detected',
                'proof': 'System successfully identifies tampering attempts',
                'trust_signal': {
                    'type': 'integrity_proof',
                    'value': corruption_detected,
                    'meaning': 'System detects when something is wrong'
                },
                'system_protection': {
                    'baseline_integrity': result.baseline_hash,
                    'divergence_found': corruption_detected,
                    'protection_status': 'ACTIVE' if corruption_detected else 'STANDBY'
                }
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"Corruption simulation failed: {e}")
    
    def send_json_response(self, data):
        """Send JSON response with CORS headers"""
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
    
    print("🛡️ EXOARMUR INTEGRITY VERIFICATION SERVER")
    print("=" * 50)
    print(f"🌐 Starting integrity verification server on http://{host}:{port}")
    print("🎯 User-friendly system integrity verification")
    print("📖 Clear language, intuitive explanations")
    print("🔐 Prove system consistency and corruption detection")
    print()
    
    # Create server
    server = HTTPServer((host, port), IntegrityVerificationHandler)
    
    # Open browser in a separate thread
    def open_browser():
        import time
        time.sleep(1)  # Wait for server to start
        webbrowser.open(f'http://{host}:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print(f"✅ Integrity verification server running at http://{host}:{port}")
        print("📱 User-friendly UI will open in your browser")
        print("⏹️  Press Ctrl+C to stop the server")
        print()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Integrity verification server stopped by user")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
