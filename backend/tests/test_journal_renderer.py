from io import BytesIO
from urllib.parse import parse_qs, urlparse

from PIL import Image as PillowImage

from app.services.journal_generator import JournalGenerationRequest, JournalImageInput
from app.services.journal_renderer import PlaywrightJournalRenderer
from app.services.render_drafts import RenderDraftRegistry


def test_renderer_registers_short_lived_draft_and_revokes_it_after_screenshot():
    registry = RenderDraftRegistry()
    captured = {}

    def screenshot_page(url):
        token = parse_qs(urlparse(url).query)["token"][0]
        captured["token"] = token
        captured["draft"] = registry.get(token)
        return png_bytes()

    renderer = PlaywrightJournalRenderer(registry=registry, screenshot_page=screenshot_page)

    data_url = renderer.render({"canvas": {"width": 1080, "height": 1440}}, generation_request())

    assert data_url.startswith("data:image/webp;base64,")
    assert captured["draft"].layout["canvas"]["height"] == 1440
    assert registry.get(captured["token"]) is None


def generation_request():
    return JournalGenerationRequest(
        description="周末一起散步。",
        images=[JournalImageInput(id="img_1", width=64, height=48, data_url="data:image/webp;base64,aW1hZ2U=")],
        assets=[],
    )


def png_bytes() -> bytes:
    buffer = BytesIO()
    PillowImage.new("RGB", (32, 24), color=(250, 240, 220)).save(buffer, format="PNG")
    return buffer.getvalue()
