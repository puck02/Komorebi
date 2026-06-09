from dataclasses import dataclass
from io import BytesIO
import random

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import login, register
from app.api.routes.images import get_image, get_image_display, upload_image
from app.core.config import get_settings
from app.db.base import Base
from app.models import asset, generation_job, image, journal, user  # noqa: F401
from app.schemas.auth import AuthCredentials


@dataclass
class ImageTestContext:
    db: Session


@pytest.fixture
def context(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    try:
        yield ImageTestContext(db=db)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


def test_authenticated_user_uploads_image_and_thumbnail_is_created(context, tmp_path):
    user = register_and_login(context, "owner@example.com")

    body = upload_image(upload_file("photo.png", make_image_bytes(), "image/png"), user, context.db)

    assert body.content_type == "image/png"
    assert body.width == 64
    assert body.height == 48
    assert body.file_url == f"/api/images/{body.id}/file"
    assert body.thumbnail_url == f"/api/images/{body.id}/thumbnail"
    assert list((tmp_path / "storage").glob("users/*/images/*/original.png"))
    assert list((tmp_path / "storage").glob("users/*/images/*/thumb.webp"))


def test_large_upload_creates_display_image_under_one_mb(context):
    user = register_and_login(context, "owner@example.com")

    body = upload_image(upload_file("large-photo.jpg", make_large_image_bytes(), "image/jpeg"), user, context.db)
    display_response = get_image_display(body.id, user, context.db)

    assert body.display_url == f"/api/images/{body.id}/display"
    assert display_response.media_type == "image/webp"
    assert display_response.path.stat().st_size <= 1024 * 1024


def test_upload_rejects_unsupported_content_type(context):
    user = register_and_login(context, "owner@example.com")

    with pytest.raises(HTTPException) as error:
        upload_image(upload_file("note.txt", b"not an image", "text/plain"), user, context.db)

    assert error.value.status_code == 400


def test_user_cannot_fetch_another_users_image_metadata(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    image = upload_image(upload_file("photo.png", make_image_bytes(), "image/png"), owner, context.db)

    with pytest.raises(HTTPException) as error:
        get_image(image.id, other, context.db)

    assert error.value.status_code == 404


def register_and_login(context: ImageTestContext, email: str):
    payload = AuthCredentials(email=email, password="strong-password")
    register(payload, context.db)
    token = login(payload, context.db)
    from app.api.deps import get_current_user

    return get_current_user(token.access_token, context.db)


def upload_file(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(data), headers={"content-type": content_type})


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
