"""
FastAPI Health Check Test
Bootstrap verification - Phase 0.4
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from exoarmur.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test /health endpoint returns 200 OK"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ExoArmur ADMO"

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "ExoArmur ADMO" in data["message"]

def test_openapi_docs_available():
    """Test OpenAPI docs are available"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "info" in data
    assert data["info"]["title"] == "ExoArmur ADMO v1 API"