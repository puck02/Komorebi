from base64 import b64encode
from io import BytesIO
from threading import Lock
from typing import Callable

from PIL import Image as PillowImage

from app.core.config import get_settings
from app.services.journal_generator import JournalGenerationRequest
from app.services.render_drafts import RenderDraftRegistry, render_draft_registry

CHROME_RENDER_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-zygote"]
SCREENSHOT_LOCK = Lock()


class PlaywrightJournalRenderer:
    def __init__(
        self,
        *,
        registry: RenderDraftRegistry = render_draft_registry,
        screenshot_page: Callable[[str], bytes] | None = None,
    ):
        self.registry = registry
        self.screenshot_page = screenshot_page or capture_journal_screenshot

    def render(self, layout: dict, request: JournalGenerationRequest) -> str:
        token = self.registry.create(layout, request.images)
        try:
            screenshot = self.screenshot_page(f"{get_settings().internal_render_url}?token={token}")
            return webp_data_url(screenshot)
        finally:
            self.registry.revoke(token)


def capture_journal_screenshot(url: str) -> bytes:
    from playwright.sync_api import sync_playwright

    settings = get_settings()
    with SCREENSHOT_LOCK:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=settings.playwright_chromium_executable,
                args=CHROME_RENDER_ARGS,
            )
            try:
                page = browser.new_page(viewport={"width": 1160, "height": 900})
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.locator('[data-render-ready="true"]').wait_for(timeout=30_000)
                return page.locator(".journal-canvas").screenshot(type="png")
            finally:
                browser.close()


def webp_data_url(image_bytes: bytes) -> str:
    output = BytesIO()
    with PillowImage.open(BytesIO(image_bytes)) as image:
        image.convert("RGB").save(output, format="WEBP", quality=82, method=4)
    return f"data:image/webp;base64,{b64encode(output.getvalue()).decode('ascii')}"
