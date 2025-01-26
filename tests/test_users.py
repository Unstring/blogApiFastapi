import pytest
from .utils import random_string, random_email, random_password, create_test_user

def test_get_current_user(client, test_user, auth_headers):
    """Test getting current user profile"""
    response = client.get("/api/v1/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["user"].username
    assert data["email"] == test_user["user"].email

def test_update_user_profile(client, test_user, auth_headers):
    """Test updating user profile"""
    update_data = {
        "username": random_string(8),
        "email": random_email()
    }
    response = client.put("/api/v1/me", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["email"] == update_data["email"]

def test_list_user_posts(client, auth_headers):
    """Test listing user's posts"""
    # Create a post first using the same user
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 2,  # Published
        "tags": []
    }
    client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    
    # Now get the user's posts
    response = client.get("/api/v1/me/posts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0

def test_list_user_comments(client, test_comment, auth_headers):
    """Test listing user's comments"""
    response = client.get("/api/v1/me/comments", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_list_user_likes(client, test_post, auth_headers):
    """Test listing user's liked posts"""
    # First like a post
    client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    
    response = client.get("/api/v1/me/likes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_update_profile_server_error(client, auth_headers, monkeypatch):
    """Test server error while updating profile"""
    def mock_commit():
        raise Exception("Database error")
    
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", mock_commit)
    
    update_data = {
        "username": random_string(8),
        "email": random_email()
    }
    response = client.put("/api/v1/me", json=update_data, headers=auth_headers)
    assert response.status_code == 500
    assert "Could not update profile" in response.json()["detail"]

def test_update_profile_duplicate_username(client, test_user, auth_headers, db):
    """Test updating profile with existing username"""
    # Create another user first
    other_user, _ = create_test_user(db)
    
    # Try to update to that username
    update_data = {"username": other_user.username}
    response = client.put("/api/v1/me", json=update_data, headers=auth_headers)
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"] 