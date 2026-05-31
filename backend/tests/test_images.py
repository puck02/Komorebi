from io import BytesIO
import random

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models import asset, image, journal, user  # noqa: F401


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
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
        get_settings.cache_clear()


def test_authenticated_user_uploads_image_and_thumbnail_is_created(client, tmp_path):
    token = register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/images",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "image/png"
    assert body["width"] == 64
    assert body["height"] == 48
    assert body["file_url"] == f"/api/images/{body['id']}/file"
    assert body["thumbnail_url"] == f"/api/images/{body['id']}/thumbnail"
    assert list((tmp_path / "storage").glob("users/*/images/*/original.png"))
    assert list((tmp_path / "storage").glob("users/*/images/*/thumb.webp"))


def test_large_upload_creates_display_image_under_one_mb(client):
    token = register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/images",
        files={"file": ("large-photo.jpg", make_large_image_bytes(), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["display_url"] == f"/api/images/{body['id']}/display"

    display_response = client.get(
        body["display_url"],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert display_response.status_code == 200
    assert display_response.headers["content-type"] == "image/webp"
    assert len(display_response.content) <= 1024 * 1024


def test_upload_rejects_unsupported_content_type(client):
    token = register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/images",
        files={"file": ("note.txt", b"not an image", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_user_cannot_fetch_another_users_image_metadata(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    upload_response = client.post(
        "/api/images",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    image_id = upload_response.json()["id"]

    response = client.get(
        f"/api/images/{image_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def register_and_login(client: TestClient, email: str) -> str:
    payload = {"email": email, "password": "strong-password"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/login", json=payload)
    return response.json()["access_token"]


def make_image_bytes() -> bytes:
    buffer = BytesIO()
    image = PillowImage.new("RGB", (64, 48), color=(210, 170, 140))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_large_image_bytes() -> bytes:
    random_bytes = random.Random(42).randbytes(1400 * 1000 * 3)
    image = PillowImage.frombytes("RGB", (1400, 1000), random_bytes)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()
