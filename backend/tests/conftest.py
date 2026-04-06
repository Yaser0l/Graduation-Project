import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from app.db.session import get_db
from app.core.deps import get_current_user
from main import app
from app.schemas.auth import UserOut
from datetime import datetime
from uuid import uuid4

# Setup basic test client
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db

@pytest.fixture
def override_get_db(mock_db):
    async def _get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def mock_user():
    return UserOut(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        created_at=datetime.utcnow()
    )

@pytest.fixture
def override_get_current_user(mock_user):
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
