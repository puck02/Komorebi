from base64 import b64encode

from fastapi.testclient import TestClient

from app.main import app
from app.services.journal_generator import JournalImageInput
from app.services.render_drafts import RenderDraftRegistry


def test_internal_render_token_serves_draft_and_image():
    registry = RenderDraftRegistry()
    token = registry.create(
        {"canvas": {"width": 1080, "height": 1440, "background": "#f8f1e8"}},
        [JournalImageInput(id="img_1", width=64, height=48, data_url=image_data_url(b"image-bytes"))],
    )
    app.state.render_draft_registry = registry
    client = TestClient(app)

    draft_response = client.get(f"/api/internal/render-drafts/{token}")
    image_response = client.get(f"/api/internal/render-drafts/{token}/images/img_1")

    assert draft_response.status_code == 200
    assert draft_response.json()["images"] == [{"id": "img_1", "src": f"/api/internal/render-drafts/{token}/images/img_1"}]
    assert image_response.status_code == 200
    assert image_response.content == b"image-bytes"
    assert image_response.headers["content-type"] == "image/webp"


def test_internal_render_token_returns_not_found_after_revoke():
    registry = RenderDraftRegistry()
    token = registry.create({}, [])
    registry.revoke(token)
    app.state.render_draft_registry = registry

    response = TestClient(app).get(f"/api/internal/render-drafts/{token}")

    assert response.status_code == 404


def test_internal_render_token_returns_not_found_after_expiry():
    registry = RenderDraftRegistry(ttl_seconds=-1)
    token = registry.create({}, [])
    app.state.render_draft_registry = registry

    response = TestClient(app).get(f"/api/internal/render-drafts/{token}")

    assert response.status_code == 404


def image_data_url(data: bytes) -> str:
    return f"data:image/webp;base64,{b64encode(data).decode('ascii')}"
