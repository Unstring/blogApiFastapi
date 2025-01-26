import pytest
from tests.utils import random_string

@pytest.fixture
def test_comment(client, test_post, auth_headers):
    """Create a test comment"""
    comment_data = {"content": random_string(50)}
    response = client.post(
        f"/api/v1/posts/{test_post['id']}/comments",
        json=comment_data,
        headers=auth_headers
    )
    return response.json()

def test_create_comment_success(client, test_post, auth_headers):
    comment_data = {"content": random_string(50)}
    response = client.post(
        f"/api/v1/posts/{test_post['id']}/comments",
        json=comment_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == comment_data["content"]

def test_update_comment(client, test_comment, auth_headers):
    new_content = random_string(50)
    response = client.put(
        f"/api/v1/posts/{test_comment['post_id']}/comments/{test_comment['id']}",
        json={"content": new_content},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["content"] == new_content

def test_delete_comment(client, test_comment, auth_headers):
    response = client.delete(
        f"/api/v1/posts/{test_comment['post_id']}/comments/{test_comment['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200 