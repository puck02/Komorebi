from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes.journals import get_journal_generator, normalized_journal_layout
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models import asset, image, journal, user  # noqa: F401
from app.models.image import Image as ImageModel
from app.models.journal import Journal
from app.schemas.journal import JournalLayout
from app.services.journal_generator import COMPACT_SECTION_CANVAS_HEIGHT, GenerationError


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
    fake_generator = FakeGenerator()

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_journal_generator] = lambda: fake_generator
    try:
        test_client = TestClient(app)
        test_client.fake_generator = fake_generator
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


@pytest.fixture
def client_without_generator_override(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("OPENAI_API_KEY", "")
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


def test_generate_journal_requires_auth(client):
    response = client.post("/api/journals/generate", json={"imageIds": ["img_1"], "description": "今天很好"})

    assert response.status_code == 401


def test_generate_journal_validates_image_count_and_description(client):
    token = register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/journals/generate",
        json={"imageIds": [], "description": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_generate_journal_saves_local_fallback_when_openai_key_missing(client_without_generator_override):
    token = register_and_login(client_without_generator_override, "owner@example.com")
    image_id = upload_image(client_without_generator_override, token)

    response = client_without_generator_override.post(
        "/api/journals/generate",
        json={"imageIds": [image_id], "description": "今天很好"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "今天很好"
    assert body["imageIds"] == [image_id]
    assert body["layout"]["content"]["body"] == ["今天很好。"]


def test_user_cannot_generate_with_another_users_images(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    image_id = upload_image(client, owner_token)

    response = client.post(
        "/api/journals/generate",
        json={"imageIds": [image_id], "description": "偷看别人的照片"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_generate_journal_saves_local_fallback_when_model_request_fails(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)
    client.fake_generator.error = GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")

    response = generate_journal(client, token, image_id, "周末一起散步")

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "周末一起散步"
    assert body["imageIds"] == [image_id]
    assert body["layout"]["content"]["body"] == ["周末一起散步。"]


def test_generate_journal_saves_and_lists_only_current_users_journals(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    owner_image_id = upload_image(client, owner_token)
    other_image_id = upload_image(client, other_token)

    owner_response = generate_journal(client, owner_token, owner_image_id, "周末一起散步")
    generate_journal(client, other_token, other_image_id, "另一个人的手帐")
    list_response = client.get("/api/journals", headers={"Authorization": f"Bearer {owner_token}"})

    assert owner_response.status_code == 201
    assert owner_response.json()["title"] == "慢下来的周末"
    assert owner_response.json()["imageIds"] == [owner_image_id]
    assert client.fake_generator.request.images[0].data_url.startswith("data:image/webp;base64,")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [owner_response.json()["id"]]


def test_generate_journal_passes_user_context_to_generator(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)

    response = client.post(
        "/api/journals/generate",
        json={
            "imageIds": [image_id],
            "description": "周末一起散步",
            "journalDate": "2026-05-20",
            "location": "上海",
            "moodTags": ["轻松"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert str(client.fake_generator.request.journal_date) == "2026-05-20"
    assert client.fake_generator.request.location == "上海"
    assert client.fake_generator.request.mood_tags == ["轻松"]


def test_generate_journal_saved_layout_contains_user_context_meta(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)

    response = client.post(
        "/api/journals/generate",
        json={
            "imageIds": [image_id],
            "description": "周末一起散步",
            "journalDate": "2026-05-20",
            "location": "上海",
            "moodTags": ["轻松"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["layout"]["content"]["meta"] == "2026-05-20 / 上海 / 轻松"


def test_normalized_journal_layout_trims_saved_single_section_to_compact_canvas_height():
    image = ImageModel(
        id="img_1",
        user_id="user_1",
        original_path="/tmp/original.png",
        thumbnail_path="/tmp/thumb.webp",
        content_type="image/png",
        width=64,
        height=48,
    )
    layout = layout_payload(image.id)
    layout["canvas"]["height"] = 3200
    journal = Journal(
        user_id="user_1",
        title="慢下来的周末",
        input_text="周末一起散步",
        mood_tags=[],
        layout_json=layout,
        images=[image],
    )

    normalized = normalized_journal_layout(journal)

    assert normalized["canvas"]["height"] == COMPACT_SECTION_CANVAS_HEIGHT


def test_journal_detail_enforces_ownership(client):
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    journal_id = generate_journal(client, owner_token, upload_image(client, owner_token), "周末一起散步").json()["id"]

    owner_response = client.get(f"/api/journals/{journal_id}", headers={"Authorization": f"Bearer {owner_token}"})
    other_response = client.get(f"/api/journals/{journal_id}", headers={"Authorization": f"Bearer {other_token}"})

    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_patch_journal_updates_title_body_and_layout_variant(client):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)
    journal_id = generate_journal(client, token, image_id, "周末一起散步").json()["id"]

    response = client.patch(
        f"/api/journals/{journal_id}",
        json={
            "title": "新的标题",
            "meta": "2026-06-09 / 上海 / 安静",
            "body": ["新的正文"],
            "captions": [{"imageId": image_id, "text": "新的照片说明"}],
            "sections": [
                {
                    "id": "section_1",
                    "title": "新的片段",
                    "imageIds": [image_id],
                    "body": "新的章节正文",
                    "mood": ["安静"],
                }
            ],
            "layoutVariant": "collage_b",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "新的标题"
    assert body["layout"]["content"]["meta"] == "2026-06-09 / 上海 / 安静"
    assert body["layout"]["content"]["body"] == ["新的正文"]
    assert body["layout"]["content"]["captions"] == [{"imageId": image_id, "text": "新的照片说明"}]
    assert body["layout"]["content"]["sections"][0]["body"] == "新的章节正文"
    assert body["layout"]["layout"]["variant"] == "collage_b"


def test_delete_journal_removes_associated_image_files(client, tmp_path):
    token = register_and_login(client, "owner@example.com")
    image_id = upload_image(client, token)
    journal_id = generate_journal(client, token, image_id, "周末一起散步").json()["id"]

    assert list((tmp_path / "storage").glob("users/*/images/*/original.png"))
    assert list((tmp_path / "storage").glob("users/*/images/*/thumb.webp"))

    response = client.delete(f"/api/journals/{journal_id}", headers={"Authorization": f"Bearer {token}"})
    image_response = client.get(f"/api/images/{image_id}", headers={"Authorization": f"Bearer {token}"})
    journal_response = client.get(f"/api/journals/{journal_id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204
    assert image_response.status_code == 404
    assert journal_response.status_code == 404
    assert not list((tmp_path / "storage").glob("users/*/images/*/original.png"))
    assert not list((tmp_path / "storage").glob("users/*/images/*/thumb.webp"))


class FakeGenerator:
    error = None

    def generate(self, request):
        if self.error is not None:
            raise self.error
        self.request = request
        return JournalLayout.model_validate(layout_payload(request.images[0].id))


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


def generate_journal(client: TestClient, token: str, image_id: str, description: str):
    return client.post(
        "/api/journals/generate",
        json={"imageIds": [image_id], "description": description},
        headers={"Authorization": f"Bearer {token}"},
    )


def make_image_bytes() -> bytes:
    buffer = BytesIO()
    image = PillowImage.new("RGB", (64, 48), color=(210, 170, 140))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def layout_payload(image_id: str):
    return {
        "canvas": {
            "width": 1080,
            "height": 1440,
            "background": "#f8f1e8",
        },
        "theme": {
            "style": "soft-collage",
            "palette": ["#f8f1e8", "#d9a98f", "#8f6b57", "#b9c7aa"],
            "mood": ["warm", "gentle"],
        },
        "content": {
            "title": "慢下来的周末",
            "body": ["照片里是被阳光放慢的一天。"],
            "captions": [{"imageId": image_id, "text": "午后的咖啡"}],
        },
        "layout": {
            "variant": "collage_a",
            "images": [
                {
                    "imageId": image_id,
                    "x": 92,
                    "y": 210,
                    "width": 420,
                    "height": 320,
                    "rotation": -3,
                }
            ],
            "texts": [
                {
                    "role": "title",
                    "x": 80,
                    "y": 72,
                    "width": 680,
                    "fontSize": 56,
                }
            ],
            "decorations": [
                {
                    "assetId": "tape_warm_grid_01",
                    "x": 60,
                    "y": 180,
                    "width": 220,
                    "height": 54,
                    "rotation": -8,
                }
            ],
        },
    }
