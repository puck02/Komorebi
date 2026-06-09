from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes.generation_jobs import get_generation_job_submitter
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models import asset, generation_job, image, journal, user  # noqa: F401
from app.models.generation_job import GenerationJob
from app.models.journal import Journal
from app.services.generation_jobs import run_generation_job


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
    submitted_job_ids = []

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_generation_job_submitter] = lambda: submitted_job_ids.append
    try:
        test_client = TestClient(app)
        test_client.submitted_job_ids = submitted_job_ids
        test_client.session_factory = testing_session
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


def test_create_generation_job_requires_auth(client):
    response = client.post("/api/journal-generation-jobs", json={"imageIds": ["img_1"], "description": "今天很好"})

    assert response.status_code == 401


def test_user_cannot_create_generation_job_with_another_users_images(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    image_id = upload_image(client, owner_token)

    response = create_generation_job(client, other_token, image_id)

    assert response.status_code == 404


def test_create_and_read_generation_job(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)

    create_response = create_generation_job(client, token, image_id)
    job = create_response.json()
    read_response = client.get(
        f"/api/journal-generation-jobs/{job['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 202
    assert job["status"] == "queued"
    assert job["stage"] == "queued"
    assert job["revisionRound"] == 0
    assert job["maxRevisionRounds"] == 3
    assert job["journalId"] is None
    assert client.submitted_job_ids == [job["id"]]
    assert read_response.status_code == 200
    assert read_response.json()["id"] == job["id"]


def test_create_generation_job_persists_selected_template_id(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)

    response = client.post(
        "/api/journal-generation-jobs",
        json={"imageIds": [image_id], "description": "周末一起散步", "templateId": "timeline_trip"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    with client.session_factory() as db:
        job = db.get(GenerationJob, response.json()["id"])
        assert job.payload_json["templateId"] == "timeline_trip"


def test_create_generation_job_returns_failed_job_when_submitter_fails(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)
    app.dependency_overrides[get_generation_job_submitter] = lambda: failing_submitter

    response = create_generation_job(client, token, image_id)
    job = response.json()

    assert response.status_code == 202
    assert job["status"] == "failed"
    assert job["stage"] == "failed"
    assert job["errorMessage"] == "生成任务启动失败，请稍后重试"
    with client.session_factory() as db:
        saved_job = db.get(GenerationJob, job["id"])
        assert saved_job.status == "failed"
        assert saved_job.error_message == "生成任务启动失败，请稍后重试"


def test_created_generation_job_completes_with_local_fallback_when_openai_key_missing(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)
    response = create_generation_job(client, token, image_id)
    job_id = response.json()["id"]

    run_generation_job(job_id, session_factory=client.session_factory)

    read_response = client.get(
        f"/api/journal-generation-jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert read_response.status_code == 200
    job = read_response.json()
    assert job["status"] == "completed"
    assert job["stage"] == "completed"
    assert job["errorMessage"] is None
    assert job["journalId"] is not None
    with client.session_factory() as db:
        journal = db.get(Journal, job["journalId"])
        assert journal.title == "周末一起散步"
        assert journal.layout_json["content"]["body"] == ["周末一起散步。"]
        section = journal.layout_json["layout"]["sections"][0]
        decoration_ids = {
            decoration["assetId"]
            for section in journal.layout_json["layout"]["sections"]
            for decoration in section["decorations"]
        }
        assert section["images"][0]["imageId"] == image_id
        assert any(asset_id.startswith("paper_") for asset_id in decoration_ids)
        assert any(asset_id.startswith("tape_") for asset_id in decoration_ids)
        assert any(asset_id.startswith("sticker_") for asset_id in decoration_ids)


def test_user_cannot_read_another_users_generation_job(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    image_id = upload_image(client, owner_token)
    job_id = create_generation_job(client, owner_token, image_id).json()["id"]

    response = client.get(
        f"/api/journal-generation-jobs/{job_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def register_and_login(client: TestClient, email: str) -> str:
    payload = {"email": email, "password": "strong-password"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/login", json=payload)
    return response.json()["access_token"]


def upload_image(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/images",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


def create_generation_job(client: TestClient, token: str, image_id: str):
    return client.post(
        "/api/journal-generation-jobs",
        json={"imageIds": [image_id], "description": "周末一起散步"},
        headers={"Authorization": f"Bearer {token}"},
    )


def failing_submitter(job_id: str):
    raise RuntimeError("executor unavailable")


def make_image_bytes() -> bytes:
    buffer = BytesIO()
    image = PillowImage.new("RGB", (64, 48), color=(210, 170, 140))
    image.save(buffer, format="PNG")
    return buffer.getvalue()
