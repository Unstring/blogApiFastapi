import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from config import settings
from run import create_app
from models import User, Status
from passlib.context import CryptContext
from tests.utils import create_test_user, random_string
import models
import random

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_test_db():
    """Get test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def app():
    """Create test app instance"""
    app = create_app()
    app.dependency_overrides[get_db] = get_test_db
    return app

@pytest.fixture(scope="session")
def client(app):
    """Create test client"""
    return TestClient(app)

@pytest.fixture(autouse=True)
def db():
    """Create test database tables and cleanup after tests"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create test statuses
        statuses = [
            {"name": "draft", "description": "Draft post"},
            {"name": "published", "description": "Published post"}
        ]
        for status_data in statuses:
            if not db.query(Status).filter(Status.name == status_data["name"]).first():
                status = Status(**status_data)
                db.add(status)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        password=pwd_context.hash("testpass123"),
        role="reader"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user": user,
        "password": "testpass123"
    }

@pytest.fixture
def test_admin(db):
    """Create an admin test user"""
    user = User(
        username="admin",
        email="admin@example.com",
        password=pwd_context.hash("adminpass123"),
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user": user,
        "password": "adminpass123"
    }

@pytest.fixture
def test_author(db, client):
    """Create an author test user"""
    user = User(
        username="author",
        email="author@example.com",
        password=pwd_context.hash("authorpass123"),
        role="author"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": user.username,
            "password": "authorpass123"
        }
    )
    token = response.json()["access_token"]
    
    return {
        "user": user,
        "password": "authorpass123",
        "token": token
    }

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["user"].username,
            "password": test_user["password"]
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin["user"].username,
            "password": test_admin["password"]
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def author_headers(client, test_author):
    """Get authentication headers for author user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_author["user"].username,
            "password": test_author["password"]
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_post(client, test_author, author_headers):
    """Create a test post"""
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 2,  # Published status
        "tags": []
    }
    response = client.post(
        "/api/v1/posts",
        json=post_data,
        headers=author_headers
    )
    assert response.status_code == 201
    return response.json()

@pytest.fixture(scope="session")
def test_status(db):
    """Create test statuses"""
    statuses = [
        models.Status(id=1, name="draft", description="Draft post"),
        models.Status(id=2, name="published", description="Published post")
    ]
    for status in statuses:
        if not db.query(models.Status).filter_by(name=status.name).first():
            db.add(status)
    db.commit()
    return statuses 

@pytest.fixture
def test_comment(client, test_post, auth_headers):
    """Create a test comment"""
    comment_data = {"content": random_string(50)}
    response = client.post(
        f"/api/v1/posts/{test_post['id']}/comments",
        json=comment_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()

@pytest.fixture
def test_draft_post(client, test_author, author_headers):
    """Create a draft test post"""
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 1,  # Draft status
        "tags": []
    }
    response = client.post(
        "/api/v1/posts",
        json=post_data,
        headers=author_headers
    )
    assert response.status_code == 201
    return response.json() 