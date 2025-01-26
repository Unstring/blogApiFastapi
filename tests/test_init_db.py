import pytest
from init_db import init_db
from database import SessionLocal
from models import User, Status
from config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_init_db(monkeypatch):
    """Test database initialization"""
    # Mock password hash
    def mock_hash():
        return pwd_context.hash("admin123")
    
    monkeypatch.setattr("config.settings.ADMIN_PASSWORD_HASH", mock_hash())
    
    # Run initialization
    init_db()
    
    # Check results
    db = SessionLocal()
    try:
        # Verify admin user
        admin = db.query(User).filter(User.role == "admin").first()
        assert admin is not None
        assert admin.username == "admin"
        
        # Verify statuses
        statuses = db.query(Status).all()
        assert len(statuses) >= 2
        status_names = [s.name for s in statuses]
        assert "draft" in status_names
        assert "published" in status_names
    finally:
        db.close() 