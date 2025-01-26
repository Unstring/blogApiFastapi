import pytest

def test_like_post(client, test_post, auth_headers):
    """Test liking a post"""
    response = client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    assert response.status_code == 201

def test_like_post_twice(client, test_post, auth_headers):
    """Test liking a post that's already liked"""
    # Like first time
    client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    # Try to like again
    response = client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    assert response.status_code == 409

def test_unlike_post(client, test_post, auth_headers):
    """Test unliking a post"""
    # Like first
    client.post(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    # Then unlike
    response = client.delete(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    assert response.status_code == 200

def test_unlike_not_liked_post(client, test_post, auth_headers):
    """Test unliking a post that wasn't liked"""
    response = client.delete(f"/api/v1/posts/{test_post['id']}/like", headers=auth_headers)
    assert response.status_code == 404 