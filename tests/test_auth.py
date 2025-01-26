import pytest
from tests.utils import random_string, random_email, random_password

def test_register_user_success(client):
    user_data = {
        "username": random_string(8),
        "email": random_email(),
        "password": random_password()
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data["username"]
    assert "password" not in data

def test_register_user_duplicate_username(client, test_user):
    user_data = {
        "username": test_user["user"].username,
        "email": random_email(),
        "password": random_password()
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["user"].username,
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert all(k in data for k in ["access_token", "token_type", "expires_in", "user"])
    assert data["user"]["username"] == test_user["user"].username

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "wrong"
        }
    )
    assert response.status_code == 401

def test_register_invalid_password(client):
    """Test registration with invalid password"""
    user_data = {
        "username": random_string(8),
        "email": random_email(),
        "password": "weak"  # Too weak
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 422  # FastAPI validation error
    data = response.json()
    assert "password" in data["detail"][0]["loc"]

def test_register_invalid_email(client):
    """Test registration with invalid email"""
    user_data = {
        "username": random_string(8),
        "email": "invalid-email",
        "password": random_password()
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 422  # FastAPI validation error
    data = response.json()
    assert "email" in data["detail"][0]["loc"] 