import pytest
from unittest.mock import patch, MagicMock
from app.core.security import verify_password, get_password_hash, create_access_token
from main import app
from fastapi.testclient import TestClient
import uuid
from datetime import datetime

client = TestClient(app)

def test_register_success(override_get_db, mock_db):
    mock_db.execute.return_value.first.side_effect = [
        None,  # User doesn't exist
        MagicMock(id=uuid.uuid4(), name="Test User", email="test@example.com", created_at=datetime.utcnow()) # Insert result
    ]
    
    response = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"

def test_register_duplicate_email(override_get_db, mock_db):
    mock_db.execute.return_value.first.return_value = MagicMock(id=uuid.uuid4())
    
    response = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_success(override_get_db, mock_db):
    hashed_pwd = get_password_hash("password123")
    mock_user = MagicMock(id=uuid.uuid4(), name="Test", email="test@example.com", password_hash=hashed_pwd, created_at=datetime.utcnow())
    mock_db.execute.return_value.first.return_value = mock_user

    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(override_get_db, mock_db):
    hashed_pwd = get_password_hash("password123")
    mock_user = MagicMock(password_hash=hashed_pwd)
    mock_db.execute.return_value.first.return_value = mock_user

    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_token_decode_valid():
    token = create_access_token(subject="user_id_123")
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "user_id_123"
