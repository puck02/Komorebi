from base64 import b64decode
from dataclasses import dataclass
from secrets import token_urlsafe
from threading import Lock
from time import monotonic

from app.services.journal_generator import JournalImageInput


@dataclass(frozen=True)
class RenderDraftImage:
    id: str
    media_type: str
    content: bytes


@dataclass(frozen=True)
class RenderDraft:
    layout: dict
    images: dict[str, RenderDraftImage]
    expires_at: float


class RenderDraftRegistry:
    def __init__(self, ttl_seconds: float = 120):
        self.ttl_seconds = ttl_seconds
        self._drafts: dict[str, RenderDraft] = {}
        self._lock = Lock()

    def create(self, layout: dict, images: list[JournalImageInput]) -> str:
        token = token_urlsafe(32)
        draft_images = {
            image.id: render_draft_image(image)
            for image in images
            if image.data_url
        }
        with self._lock:
            self._purge_expired()
            self._drafts[token] = RenderDraft(layout=layout, images=draft_images, expires_at=monotonic() + self.ttl_seconds)
        return token

    def get(self, token: str) -> RenderDraft | None:
        with self._lock:
            self._purge_expired()
            return self._drafts.get(token)

    def revoke(self, token: str) -> None:
        with self._lock:
            self._drafts.pop(token, None)

    def _purge_expired(self) -> None:
        now = monotonic()
        expired_tokens = [token for token, draft in self._drafts.items() if draft.expires_at <= now]
        for token in expired_tokens:
            self._drafts.pop(token, None)


render_draft_registry = RenderDraftRegistry()


def render_draft_image(image: JournalImageInput) -> RenderDraftImage:
    header, encoded = (image.data_url or "").split(",", 1)
    media_type = header.removeprefix("data:").split(";", 1)[0]
    return RenderDraftImage(id=image.id, media_type=media_type, content=b64decode(encoded))
