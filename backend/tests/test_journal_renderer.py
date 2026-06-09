from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Event, Lock
from time import sleep
from urllib.parse import parse_qs, urlparse

from PIL import Image as PillowImage

from app.services.journal_generator import JournalGenerationRequest, JournalImageInput
from app.services.journal_renderer import PlaywrightJournalRenderer, capture_journal_screenshot
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


def test_capture_journal_screenshot_uses_stable_chrome_flags(monkeypatch):
    captured = {}

    class FakeLocator:
        def __init__(self, selector):
            self.selector = selector

        def wait_for(self, timeout):
            captured["wait_timeout"] = timeout

        def bounding_box(self):
            captured["bounding_box_selector"] = self.selector
            return {"x": 0, "y": 0, "width": 1080, "height": 1600}

        def screenshot(self, type):
            captured["locator_screenshot_type"] = type
            return png_bytes()

    class FakePage:
        def goto(self, url, wait_until, timeout):
            captured["url"] = url
            captured["wait_until"] = wait_until
            captured["goto_timeout"] = timeout

        def locator(self, selector):
            captured.setdefault("selectors", []).append(selector)
            return FakeLocator(selector)

        def set_viewport_size(self, viewport):
            captured["resized_viewport"] = viewport

        def screenshot(self, type, clip):
            captured["screenshot_type"] = type
            captured["screenshot_clip"] = clip
            return png_bytes()

    class FakeBrowser:
        def new_page(self, viewport):
            captured["viewport"] = viewport
            return FakePage()

        def close(self):
            captured["closed"] = True

    class FakeChromium:
        def launch(self, executable_path, args, chromium_sandbox=None):
            captured["executable_path"] = executable_path
            captured["args"] = args
            captured["chromium_sandbox"] = chromium_sandbox
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeSyncPlaywright:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc, traceback):
            return False

    import playwright.sync_api

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: FakeSyncPlaywright())

    result = capture_journal_screenshot("http://127.0.0.1:52897/internal/render?token=test")

    assert result == png_bytes()
    assert "--no-sandbox" in captured["args"]
    assert "--disable-dev-shm-usage" in captured["args"]
    assert "--disable-gpu" in captured["args"]
    assert "--no-zygote" in captured["args"]
    assert "--disable-setuid-sandbox" in captured["args"]
    assert "--disable-crash-reporter" in captured["args"]
    assert "--disable-features=VizDisplayCompositor" in captured["args"]
    assert captured["chromium_sandbox"] is False
    assert captured["bounding_box_selector"] == ".journal-canvas"
    assert captured["resized_viewport"] == {"width": 1160, "height": 1600}
    assert captured["screenshot_type"] == "png"
    assert captured["screenshot_clip"] == {"x": 0, "y": 0, "width": 1080, "height": 1600}
    assert "locator_screenshot_type" not in captured
    assert captured["closed"] is True


def test_capture_journal_screenshot_serializes_chrome_sessions(monkeypatch):
    active_sessions = 0
    max_active_sessions = 0
    active_lock = Lock()
    start_event = Event()

    class FakeLocator:
        def wait_for(self, timeout):
            pass

        def bounding_box(self):
            return {"x": 0, "y": 0, "width": 1080, "height": 1600}

    class FakePage:
        def goto(self, url, wait_until, timeout):
            pass

        def locator(self, selector):
            return FakeLocator()

        def set_viewport_size(self, viewport):
            pass

        def screenshot(self, type, clip):
            return png_bytes()

    class FakeBrowser:
        def new_page(self, viewport):
            return FakePage()

        def close(self):
            nonlocal active_sessions
            with active_lock:
                active_sessions -= 1

    class FakeChromium:
        def launch(self, executable_path, args, chromium_sandbox=None):
            nonlocal active_sessions, max_active_sessions
            assert chromium_sandbox is False
            with active_lock:
                active_sessions += 1
                max_active_sessions = max(max_active_sessions, active_sessions)
            sleep(0.08)
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeSyncPlaywright:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc, traceback):
            return False

    import playwright.sync_api

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: FakeSyncPlaywright())

    def render_once():
        start_event.wait()
        return capture_journal_screenshot("http://127.0.0.1:52897/internal/render?token=test")

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(render_once)
        second = executor.submit(render_once)
        start_event.set()
        assert first.result(timeout=2) == png_bytes()
        assert second.result(timeout=2) == png_bytes()

    assert max_active_sessions == 1


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
