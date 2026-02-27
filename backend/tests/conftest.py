"""
conftest.py — shared pytest fixtures for the AI Video Summarizer backend.
Uses mongomock-motor to provide an in-memory async MongoDB substitute.
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

# Point at a test secret key before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-char-long!!")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.main import app
from app.core import database as db_module


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def mock_database():
    """Replace the real Motor client with an in-memory mongomock client."""
    mock_client = AsyncMongoMockClient()
    db_module.database.client = mock_client
    db_module.database.db = mock_client["test_db"]
    # Create indexes (idempotent on mock)
    await db_module.database._create_indexes()
    yield db_module.database.db
    # Cleanup
    db_module.database.client = None
    db_module.database.db = None


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register + login a test user and return Authorization headers."""
    await client.post("/api/auth/register", json={
        "email":    "test@example.com",
        "username": "testuser",
        "password": "securepassword123",
    })
    resp = await client.post("/api/auth/login", json={
        "email":    "test@example.com",
        "password": "securepassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
