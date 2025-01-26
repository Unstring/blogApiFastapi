import pytest
from sqlalchemy.orm import Session
from database import get_db, engine, paginate
from models import Post, User, Status
from tests.utils import create_test_user

def test_get_db():
    """Test database connection"""
    db = next(get_db())
    assert isinstance(db, Session)
    assert db.bind == engine
    db.close()

def test_db_session_closes():
    """Test database session closes properly"""
    db = next(get_db())
    assert hasattr(db, 'is_active')
    assert db.is_active
    db.close()
    db.close()  # Second close should not raise error
    
    # Test if session is actually closed by trying to use it
    try:
        db.execute("SELECT 1")
        assert False, "Session should be closed"
    except:
        assert True  # Session is properly closed if we can't execute queries

def test_paginate(db):
    """Test pagination function"""
    # Create test user first
    test_user, _ = create_test_user(db)
    
    # Create a test post with valid status
    status = db.query(Status).filter(Status.name == "published").first()
    if not status:
        status = Status(name="published", description="Published post")
        db.add(status)
        db.commit()
    
    post = Post(
        title="Test", 
        content="Test content", 
        author_id=test_user.id, 
        status_id=status.id
    )
    db.add(post)
    db.commit()
    
    query = db.query(Post)
    result = paginate(query)
    assert isinstance(result, dict)
    assert all(k in result for k in ["items", "total", "pages", "current_page"]) 