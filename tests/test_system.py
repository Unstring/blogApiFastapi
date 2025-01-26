def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data 

def test_root_endpoint_content(client):
    """Test root endpoint content"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "/api/docs" in data["docs"]

def test_health_check_error_handling(client, monkeypatch):
    """Test health check error handling"""
    from datetime import datetime
    
    class MockDateTime:
        @staticmethod
        def utcnow():
            return datetime(2025, 1, 26)
    
    monkeypatch.setattr("main.datetime", MockDateTime)
    
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "2025-01-26" in data["timestamp"] 