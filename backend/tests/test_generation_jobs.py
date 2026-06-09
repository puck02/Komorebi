from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.auth import login, register
from app.api.routes.generation_jobs import create_generation_job, read_generation_job
from app.core.config import get_settings
from app.db.base import Base
from app.models import ai_settings, asset, generation_job, image, journal, user  # noqa: F401
from app.models.generation_job import GenerationJob
from app.models.image import Image as ImageModel
from app.models.journal import Journal
from app.schemas.auth import AuthCredentials
from app.schemas.journal import JournalGenerateRequest
from app.services.generation_jobs import run_generation_job
from app.services.storage import build_image_paths
from app.services.thumbnails import generate_display_image, generate_thumbnail


@dataclass
class GenerationJobTestContext:
    db: Session
    session_factory: sessionmaker
    storage_root: Path
    submitted_job_ids: list[str]


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
        yield GenerationJobTestContext(
            db=db,
            session_factory=testing_session,
            storage_root=tmp_path / "storage",
            submitted_job_ids=[],
        )
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


def test_create_generation_job_requires_auth(context):
    with pytest.raises(HTTPException) as error:
        get_current_user("", context.db)

    assert error.value.status_code == 401


def test_user_cannot_create_generation_job_with_another_users_images(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    image_id = create_image(context, owner.id)

    with pytest.raises(HTTPException) as error:
        create_generation_job_for_user(context, other, image_id)

    assert error.value.status_code == 404


def test_create_and_read_generation_job(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)

    job = create_generation_job_for_user(context, user, image_id)
    read_job = read_generation_job(job.id, user, context.db)

    assert job.status == "queued"
    assert job.stage == "queued"
    assert job.revision_round == 0
    assert job.max_revision_rounds == 3
    assert job.journal_id is None
    assert context.submitted_job_ids == [job.id]
    assert read_job.id == job.id


def test_create_generation_job_persists_selected_template_id(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)

    response = create_generation_job(
        JournalGenerateRequest(imageIds=[image_id], description="周末一起散步", templateId="timeline_trip"),
        user,
        context.db,
        context.submitted_job_ids.append,
    )

    job = context.db.get(GenerationJob, response.id)
    assert job.payload_json["templateId"] == "timeline_trip"


def test_create_generation_job_returns_failed_job_when_submitter_fails(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)

    job = create_generation_job_for_user(context, user, image_id, submit=failing_submitter)
    saved_job = context.db.get(GenerationJob, job.id)

    assert job.status == "failed"
    assert job.stage == "failed"
    assert job.error_message == "生成任务启动失败，请稍后重试"
    assert saved_job.status == "failed"
    assert saved_job.error_message == "生成任务启动失败，请稍后重试"


def test_created_generation_job_completes_with_local_fallback_when_openai_key_missing(context, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    job = create_generation_job_for_user(context, user, image_id)

    run_generation_job(job.id, session_factory=context.session_factory)
    read_job = read_generation_job(job.id, user, context.db)

    assert read_job.status == "completed"
    assert read_job.stage == "completed"
    assert read_job.error_message is None
    assert read_job.journal_id is not None
    journal = context.db.get(Journal, read_job.journal_id)
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


def test_user_cannot_read_another_users_generation_job(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    image_id = create_image(context, owner.id)
    job_id = create_generation_job_for_user(context, owner, image_id).id

    with pytest.raises(HTTPException) as error:
        read_generation_job(job_id, other, context.db)

    assert error.value.status_code == 404


def register_and_login(context: GenerationJobTestContext, email: str):
    payload = AuthCredentials(email=email, password="strong-password")
    register(payload, context.db)
    token = login(payload, context.db)
    return get_current_user(token.access_token, context.db)


def create_image(context: GenerationJobTestContext, user_id: str) -> str:
    image_id = f"img_{len(list(context.storage_root.glob('users/*/images/*'))) + 1}"
    paths = build_image_paths(str(context.storage_root), user_id, image_id, "png")
    paths.original.parent.mkdir(parents=True, exist_ok=True)
    paths.original.write_bytes(make_image_bytes())
    width, height = generate_thumbnail(paths.original, paths.thumbnail)
    generate_display_image(paths.original, paths.display)
    image = ImageModel(
        id=image_id,
        user_id=user_id,
        original_path=str(paths.original),
        thumbnail_path=str(paths.thumbnail),
        content_type="image/png",
        width=width,
        height=height,
    )
    context.db.add(image)
    context.db.commit()
    context.db.refresh(image)
    return image.id


def create_generation_job_for_user(context: GenerationJobTestContext, user, image_id: str, submit=None):
    return create_generation_job(
        JournalGenerateRequest(imageIds=[image_id], description="周末一起散步"),
        user,
        context.db,
        submit or context.submitted_job_ids.append,
    )


def failing_submitter(job_id: str):
    raise RuntimeError("executor unavailable")


def make_image_bytes() -> bytes:
    buffer = BytesIO()
    image = PillowImage.new("RGB", (64, 48), color=(210, 170, 140))
    image.save(buffer, format="PNG")
    return buffer.getvalue()
