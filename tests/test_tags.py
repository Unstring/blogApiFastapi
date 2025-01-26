import pytest
from tests.utils import random_string

@pytest.fixture
def test_tag(client, auth_headers):
    """Create a test tag"""
    tag_data = {"name": random_string(8)}
    response = client.post("/api/v1/tags", json=tag_data, headers=auth_headers)
    return response.json()

def test_create_tag(client, auth_headers):
    """Test creating a new tag"""
    tag_data = {"name": random_string(8)}
    response = client.post("/api/v1/tags", json=tag_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == tag_data["name"]

def test_create_duplicate_tag(client, test_tag, auth_headers):
    """Test creating a duplicate tag"""
    tag_data = {"name": test_tag["name"]}
    response = client.post("/api/v1/tags", json=tag_data, headers=auth_headers)
    assert response.status_code == 409

def test_list_tags(client, test_tag):
    """Test listing all tags"""
    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(tag["name"] == test_tag["name"] for tag in data)

def test_get_posts_by_tag(client, test_post, test_tag):
    """Test getting posts by tag"""
    response = client.get(f"/api/v1/tags/{test_tag['id']}/posts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data 