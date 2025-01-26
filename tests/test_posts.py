import pytest
from tests.utils import random_string

@pytest.fixture
def test_post(client, test_author, auth_headers):
    """Create a test post"""
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 1,
        "tags": [random_string(5)]
    }
    response = client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    return response.json()

def test_create_post_success(client, test_author, auth_headers):
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 1,
        "tags": [random_string(5), random_string(5)]
    }
    response = client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == post_data["title"]
    assert len(data["tags"]) == len(post_data["tags"])

def test_list_posts_pagination(client, test_author, auth_headers):
    # Create multiple posts
    for _ in range(15):
        client.post(
            "/api/v1/posts",
            json={
                "title": random_string(20),
                "content": random_string(100),
                "status_id": 2,  # published
                "tags": []
            },
            headers=auth_headers
        )
    
    # Test first page
    response = client.get("/api/v1/posts?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] >= 15
    assert data["current_page"] == 1

def test_post_visibility(client, test_author, test_user, auth_headers):
    # Create a draft post
    draft_post = client.post(
        "/api/v1/posts",
        json={
            "title": random_string(20),
            "content": random_string(100),
            "status_id": 1,  # draft
            "tags": []
        },
        headers=auth_headers
    ).json()

    # Test visibility for different users
    # Author should see their draft
    response = client.get(f"/api/v1/posts/{draft_post['id']}", headers=auth_headers)
    assert response.status_code == 200

    # Other users shouldn't see draft
    response = client.get(f"/api/v1/posts/{draft_post['id']}")
    assert response.status_code == 404

def test_update_post(client, test_post, auth_headers):
    """Test updating a post"""
    update_data = {
        "title": random_string(20),
        "content": random_string(100)
    }
    response = client.put(
        f"/api/v1/posts/{test_post['id']}", 
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]

def test_delete_post(client, test_post, auth_headers):
    """Test deleting a post"""
    response = client.delete(
        f"/api/v1/posts/{test_post['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200

def test_search_posts(client, test_author, auth_headers):
    """Test searching posts"""
    # Create a post with specific title
    unique_title = f"Unique{random_string(10)}"
    post_data = {
        "title": unique_title,
        "content": random_string(100),
        "status_id": 2,  # published
        "tags": []
    }
    client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    
    # Search for the post
    response = client.get(f"/api/v1/posts?search={unique_title}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
    assert any(post["title"] == unique_title for post in data["items"])

def test_post_with_like_status(client, test_post, auth_headers):
    """Test getting post with like status"""
    # Like the post first
    client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    
    response = client.get(
        f"/api/v1/posts/{test_post['id']}/with-like",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is True
    assert data["likes_count"] == 1

def test_filter_published_posts_admin(client, test_admin, test_draft_post):
    """Test that admin can see draft posts"""
    # Login as admin
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin["user"].username,
            "password": test_admin["password"]
        }
    )
    admin_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Admin should see the draft post
    response = client.get(f"/api/v1/posts/{test_draft_post['id']}", headers=admin_headers)
    assert response.status_code == 200

def test_filter_published_posts_public(client, test_draft_post):
    """Test that public users cannot see draft posts"""
    # Public user should not see draft post
    response = client.get(f"/api/v1/posts/{test_draft_post['id']}")
    assert response.status_code == 404

def test_filter_published_posts_author(client, test_author, test_draft_post):
    """Test that authors can see their own draft posts"""
    headers = {"Authorization": f"Bearer {test_author['token']}"}
    response = client.get(f"/api/v1/posts/{test_draft_post['id']}", headers=headers)
    assert response.status_code == 200

def test_create_post_invalid_status(client, auth_headers):
    """Test creating post with invalid status"""
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 999,  # Invalid status
        "tags": []
    }
    response = client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    assert response.status_code == 404  # Changed from 422 to 404
    assert "Status not found" in response.json()["detail"]

def test_update_post_not_found(client, auth_headers):
    """Test updating non-existent post"""
    update_data = {
        "title": random_string(20),
        "content": random_string(100)
    }
    response = client.put("/api/v1/posts/999", json=update_data, headers=auth_headers)
    assert response.status_code == 404
    assert "Post not found" in response.json()["detail"]

def test_create_post_server_error(client, auth_headers, monkeypatch):
    """Test server error while creating post"""
    def mock_commit():
        raise Exception("Database error")
    
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", mock_commit)
    
    post_data = {
        "title": random_string(20),
        "content": random_string(100),
        "status_id": 1,
        "tags": []
    }
    response = client.post("/api/v1/posts", json=post_data, headers=auth_headers)
    assert response.status_code == 500
    assert "Could not create post" in response.json()["detail"]

def test_update_post_unauthorized(client, test_post):
    """Test updating post without authorization"""
    update_data = {"title": random_string(20)}
    response = client.put(f"/api/v1/posts/{test_post['id']}", json=update_data)
    assert response.status_code == 401

def test_delete_post_unauthorized(client, test_post):
    """Test deleting post without authorization"""
    response = client.delete(f"/api/v1/posts/{test_post['id']}")
    assert response.status_code == 401

def test_update_post_server_error(client, test_post, auth_headers, monkeypatch):
    """Test server error while updating post"""
    def mock_commit():
        raise Exception("Database error")
    
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", mock_commit)
    
    update_data = {"title": random_string(20)}
    response = client.put(
        f"/api/v1/posts/{test_post['id']}", 
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 500
    assert "Could not update post" in response.json()["detail"]

def test_delete_post_server_error(client, test_post, auth_headers, monkeypatch):
    """Test server error while deleting post"""
    def mock_commit():
        raise Exception("Database error")
    
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", mock_commit)
    
    response = client.delete(
        f"/api/v1/posts/{test_post['id']}",
        headers=auth_headers
    )
    assert response.status_code == 500
    assert "Could not delete post" in response.json()["detail"] 