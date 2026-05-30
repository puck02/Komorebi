import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import asset, image, journal, user  # noqa: F401


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_register_creates_user(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert "password_hash" not in response.json()


def test_register_rejects_duplicate_email(client):
    payload = {"email": "user@example.com", "password": "strong-password"}
    client.post("/api/auth/register", json=payload)

    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 409


def test_login_returns_access_token(client):
    payload = {"email": "user@example.com", "password": "strong-password"}
    client.post("/api/auth/register", json=payload)

    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_token_and_returns_current_user(client):
    payload = {"email": "user@example.com", "password": "strong-password"}
    client.post("/api/auth/register", json=payload)
    login_response = client.post("/api/auth/login", json=payload)
    token = login_response.json()["access_token"]

    unauthorized_response = client.get("/api/auth/me")
    authorized_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert unauthorized_response.status_code == 401
    assert authorized_response.status_code == 200
    assert authorized_response.json()["email"] == "user@example.com"
