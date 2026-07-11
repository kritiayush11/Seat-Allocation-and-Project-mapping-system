"""
Unit and integration tests for Authentication and endpoint protection.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user
from app.models.user import User


@pytest.fixture(autouse=True)
def remove_auth_override(client):
    """
    By default, conftest overrides get_current_user with mock_get_current_user.
    For auth tests, we want to test the actual JWT validation, so we remove the override.
    """
    app.dependency_overrides.pop(get_current_user, None)
    yield
    # conftest will clear overrides on exit, no need to manually restore


def test_signup_success(client: TestClient):
    payload = {
        "username": "newadmin",
        "email": "newadmin@ethara.ai",
        "password": "strongpassword123",
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newadmin"
    assert data["email"] == "newadmin@ethara.ai"
    assert "password" not in data
    assert data["is_admin"] is True


def test_signup_duplicate_username(client: TestClient):
    payload1 = {
        "username": "dupuser",
        "email": "dup1@ethara.ai",
        "password": "password123",
    }
    response1 = client.post("/auth/signup", json=payload1)
    assert response1.status_code == 201

    payload2 = {
        "username": "dupuser",  # Same username
        "email": "dup2@ethara.ai",
        "password": "password456",
    }
    response2 = client.post("/auth/signup", json=payload2)
    assert response2.status_code == 409
    assert "Username is already registered" in response2.json()["detail"]


def test_signup_duplicate_email(client: TestClient):
    payload1 = {
        "username": "user1",
        "email": "dup_email@ethara.ai",
        "password": "password123",
    }
    response1 = client.post("/auth/signup", json=payload1)
    assert response1.status_code == 201

    payload2 = {
        "username": "user2",
        "email": "dup_email@ethara.ai",  # Same email
        "password": "password456",
    }
    response2 = client.post("/auth/signup", json=payload2)
    assert response2.status_code == 409
    assert "Email address is already registered" in response2.json()["detail"]


def test_login_success(client: TestClient):
    # Signup first
    payload_signup = {
        "username": "loginuser",
        "email": "loginuser@ethara.ai",
        "password": "testpassword",
    }
    client.post("/auth/signup", json=payload_signup)

    # Login
    payload_login = {
        "username_or_email": "loginuser",
        "password": "testpassword",
    }
    response = client.post("/auth/login", json=payload_login)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    # Try login on non-existent user
    payload_login = {
        "username_or_email": "nonexistent",
        "password": "somepassword",
    }
    response = client.post("/auth/login", json=payload_login)
    assert response.status_code == 401
    assert "Invalid username/email or password" in response.json()["detail"]


def test_me_endpoint_success(client: TestClient):
    # Register
    payload_signup = {
        "username": "profileuser",
        "email": "profile@ethara.ai",
        "password": "profilepassword",
    }
    client.post("/auth/signup", json=payload_signup)

    # Login to get token
    payload_login = {
        "username_or_email": "profileuser",
        "password": "profilepassword",
    }
    login_resp = client.post("/auth/login", json=payload_login)
    token = login_resp.json()["access_token"]

    # Request /auth/me with token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "profileuser"
    assert data["email"] == "profile@ethara.ai"


def test_me_endpoint_invalid_token(client: TestClient):
    # Request without token
    response = client.get("/auth/me")
    assert response.status_code == 401

    # Request with invalid token
    headers = {"Authorization": "Bearer invalid_token_value"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401


def test_endpoint_protection(client: TestClient):
    """
    Test that endpoints are actually protected when no authentication is provided.
    """
    # /employees should return 401 since override is removed
    response = client.get("/employees")
    assert response.status_code == 401
