import pytest
from pathlib import Path
from run import create_app, check_environment, create_required_directories, main
from fastapi.testclient import TestClient

def test_check_environment(monkeypatch):
    """Test environment variables check"""
    # Test with all variables set
    assert check_environment() is True
    
    # Test with missing variable
    monkeypatch.delattr("config.settings.DB_HOST", raising=False)
    with pytest.raises(SystemExit):
        check_environment()

def test_create_required_directories(monkeypatch, tmp_path):
    """Test directory creation"""
    monkeypatch.setattr("run.Path", lambda x: tmp_path / x)
    assert create_required_directories() is True
    assert (tmp_path / "logs").exists()

def test_create_app(monkeypatch):
    """Test application creation"""
    # Mock settings
    class MockSettings:
        API_V1_PREFIX = "/api/v1"
        PROJECT_NAME = "Test API"
        VERSION = "1.0.0"
    monkeypatch.setattr("run.settings", MockSettings())
    
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "version" in response.json()

def test_cors_middleware(monkeypatch):
    """Test CORS middleware configuration"""
    # Mock settings
    class MockSettings:
        API_V1_PREFIX = "/api/v1"
        PROJECT_NAME = "Test API"
        VERSION = "1.0.0"
    monkeypatch.setattr("run.settings", MockSettings())
    
    app = create_app()
    client = TestClient(app)
    
    response = client.options(
        "/api/v1/",  # Changed from /health to root endpoint
        headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"

def test_main_success(monkeypatch):
    """Test successful application startup"""
    def mock_run(*args, **kwargs):
        return True
    
    def mock_init_db():
        return True
    
    def mock_check_env():
        return True
    
    def mock_create_dirs():
        return True
    
    monkeypatch.setattr("uvicorn.run", mock_run)
    monkeypatch.setattr("run.init_db", mock_init_db)
    monkeypatch.setattr("run.check_environment", mock_check_env)
    monkeypatch.setattr("run.create_required_directories", mock_create_dirs)
    
    # Should not raise any exception
    main()

def test_main_failure(monkeypatch):
    """Test application startup failure"""
    def mock_init_db():
        raise Exception("Database error")
    monkeypatch.setattr("run.init_db", mock_init_db)
    
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1 