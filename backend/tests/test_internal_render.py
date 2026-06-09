from base64 import b64encode
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes.internal_render import read_render_draft, read_render_draft_image
from app.services.journal_generator import JournalImageInput
from app.services.render_drafts import RenderDraftRegistry


def test_internal_render_token_serves_draft_and_image():
    registry = RenderDraftRegistry()
    token = registry.create(
        {"canvas": {"width": 1080, "height": 1440, "background": "#f8f1e8"}},
        [JournalImageInput(id="img_1", width=64, height=48, data_url=image_data_url(b"image-bytes"))],
    )
    request = request_with_registry(registry)

    draft_response = read_render_draft(token, request)
    image_response = read_render_draft_image(token, "img_1", request)

    assert draft_response["images"] == [{"id": "img_1", "src": f"/api/internal/render-drafts/{token}/images/img_1"}]
    assert image_response.body == b"image-bytes"
    assert image_response.media_type == "image/webp"


def test_internal_render_token_returns_not_found_after_revoke():
    registry = RenderDraftRegistry()
    token = registry.create({}, [])
    registry.revoke(token)

    with pytest.raises(HTTPException) as error:
        read_render_draft(token, request_with_registry(registry))

    assert error.value.status_code == 404


def test_internal_render_token_returns_not_found_after_expiry():
    registry = RenderDraftRegistry(ttl_seconds=-1)
    token = registry.create({}, [])

    with pytest.raises(HTTPException) as error:
        read_render_draft(token, request_with_registry(registry))

    assert error.value.status_code == 404


def request_with_registry(registry: RenderDraftRegistry):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(render_draft_registry=registry)))


def image_data_url(data: bytes) -> str:
    return f"data:image/webp;base64,{b64encode(data).decode('ascii')}"
