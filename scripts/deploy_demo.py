#!/usr/bin/env python3
"""
ExoArmur Demo Deployment Script

This script handles deployment of the ExoArmur deterministic governance demo.
It supports multiple deployment modes: local Docker, production-ready setup.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

class ExoArmurDemoDeployer:
    """Handles deployment of ExoArmur demo"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.determinism_env = {
            'PYTHONHASHSEED': '0',
            'PYTHONUNBUFFERED': '1',
            'PYTHONDONTWRITEBYTECODE': '1'
        }
    
    def check_prerequisites(self):
        """Check deployment prerequisites"""
        print("🔍 Checking deployment prerequisites...")
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            print(f"✅ Docker: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Docker not found. Please install Docker.")
            return False
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True)
            print(f"✅ Docker Compose: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Docker Compose not found. Please install Docker Compose.")
            return False
        
        # Check required files
        required_files = [
            'Dockerfile',
            'docker-compose.yml', 
            'demo_ui.html',
            'src/exoarmur',
            'scripts/demo_web_server.py'
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                print(f"❌ Required file not found: {file_path}")
                return False
        
        print("✅ All prerequisites satisfied")
        return True
    
    def build_image(self):
        """Build Docker image"""
        print("🏗️  Building ExoArmur demo image...")
        
        env = os.environ.copy()
        env.update(self.determinism_env)
        
        try:
            result = subprocess.run([
                'docker-compose', 'build'
            ], cwd=self.project_root, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Build failed: {result.stderr}")
                return False
            
            print("✅ Docker image built successfully")
            return True
            
        except Exception as e:
            print(f"❌ Build error: {e}")
            return False
    
    def start_services(self):
        """Start demo services"""
        print("🚀 Starting ExoArmur demo services...")
        
        env = os.environ.copy()
        env.update(self.determinism_env)
        
        try:
            # Start services
            result = subprocess.run([
                'docker-compose', 'up', '-d'
            ], cwd=self.project_root, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Start failed: {result.stderr}")
                return False
            
            print("✅ Services started")
            
            # Wait for health check
            print("⏳ Waiting for service to be healthy...")
            time.sleep(10)
            
            # Check health
            health_result = subprocess.run([
                'docker-compose', 'ps', '--format', 'json'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if health_result.returncode == 0:
                services = json.loads(health_result.stdout)
                for service in services:
                    if service.get('State') == 'running':
                        print(f"✅ {service['Service']}: running")
                    else:
                        print(f"⚠️  {service['Service']}: {service.get('State', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Start error: {e}")
            return False
    
    def verify_deployment(self):
        """Verify deployment is working"""
        print("🔍 Verifying deployment...")
        
        # Wait a bit more for startup
        time.sleep(5)
        
        try:
            # Test health endpoint
            result = subprocess.run([
                'curl', '-f', 'http://localhost:8080/api/health'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                print(f"✅ Health check: {health_data.get('status', 'unknown')}")
                print(f"📊 Service: {health_data.get('service', 'unknown')}")
                print(f"🔐 Determinism: {health_data.get('determinism', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
    
    def show_access_info(self):
        """Show access information"""
        print("\n🎉 DEPLOYMENT SUCCESSFUL!")
        print("=" * 50)
        print("🌐 Access the ExoArmur Demo:")
        print("   Web UI: http://localhost:8080")
        print("   API Health: http://localhost:8080/api/health")
        print("   Demo Data: http://localhost:8080/api/demo-data")
        print()
        print("🛡️  What you'll see:")
        print("   • Deterministic event replay")
        print("   • Multi-node consensus verification")
        print("   • Byzantine fault injection testing")
        print("   • 100% reproducible results")
        print()
        print("🎮 Demo Controls:")
        print("   • Run Complete Demo - Full end-to-end demonstration")
        print("   • Replay Events - Test deterministic replay")
        print("   • Verify Consensus - Test multi-node agreement")
        print("   • Byzantine Test - Test fault detection")
        print()
        print("🔐 Deterministic Guarantees:")
        print("   • Same input → identical output")
        print("   • No wall-clock dependencies")
        print("   • No hidden randomness")
        print("   • Hash-based integrity verification")
        print()
        print("⏹️  To stop: docker-compose down")
        print("📊 To view logs: docker-compose logs -f")
    
    def stop_services(self):
        """Stop demo services"""
        print("🛑 Stopping ExoArmur demo services...")
        
        try:
            result = subprocess.run([
                'docker-compose', 'down'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Stop failed: {result.stderr}")
                return False
            
            print("✅ Services stopped")
            return True
            
        except Exception as e:
            print(f"❌ Stop error: {e}")
            return False
    
    def deploy_local(self):
        """Deploy to local Docker"""
        print("🚀 ExoArmur Demo Local Deployment")
        print("=" * 50)
        
        if not self.check_prerequisites():
            return False
        
        if not self.build_image():
            return False
        
        if not self.start_services():
            return False
        
        if not self.verify_deployment():
            return False
        
        self.show_access_info()
        return True
    
    def cleanup(self):
        """Clean up deployment"""
        print("🧹 Cleaning up deployment...")
        
        try:
            # Stop and remove containers
            subprocess.run(['docker-compose', 'down', '-v'], 
                         cwd=self.project_root, capture_output=True)
            
            # Remove images
            subprocess.run(['docker-compose', 'down', '--rmi', 'all'], 
                         cwd=self.project_root, capture_output=True)
            
            print("✅ Cleanup completed")
            return True
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return False

def main():
    """Main entry point"""
    deployer = ExoArmurDemoDeployer()
    
    if len(sys.argv) < 2:
        print("Usage: python deploy_demo.py <command>")
        print("Commands:")
        print("  deploy    - Deploy demo locally")
        print("  stop      - Stop demo services")
        print("  cleanup   - Clean up deployment")
        print("  verify    - Verify deployment")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'deploy':
        success = deployer.deploy_local()
        sys.exit(0 if success else 1)
    elif command == 'stop':
        success = deployer.stop_services()
        sys.exit(0 if success else 1)
    elif command == 'cleanup':
        success = deployer.cleanup()
        sys.exit(0 if success else 1)
    elif command == 'verify':
        success = deployer.verify_deployment()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
