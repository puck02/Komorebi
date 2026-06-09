from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image as PillowImage
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.auth import login, register
from app.api.routes.journals import delete_journal, generate_journal, get_journal, list_journals, normalized_journal_layout, update_journal
from app.core.config import get_settings
from app.db.base import Base
from app.models import ai_settings, asset, generation_job, image, journal, user  # noqa: F401
from app.models.image import Image as ImageModel
from app.models.journal import Journal
from app.schemas.auth import AuthCredentials
from app.schemas.journal import JournalGenerateRequest, JournalLayout, JournalUpdateRequest
from app.services.journal_generator import (
    COMPACT_SECTION_CANVAS_HEIGHT,
    CANVAS_BOTTOM_PADDING,
    GenerationError,
    JournalGenerationRequest,
    JournalGenerator,
)
from app.services.storage import build_image_paths
from app.services.thumbnails import generate_display_image, generate_thumbnail


@dataclass
class JournalTestContext:
    db: Session
    fake_generator: "FakeGenerator"
    storage_root: Path


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
        yield JournalTestContext(
            db=db,
            fake_generator=FakeGenerator(),
            storage_root=tmp_path / "storage",
        )
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


def test_generate_journal_requires_auth(context):
    with pytest.raises(HTTPException) as error:
        get_current_user("", context.db)

    assert error.value.status_code == 401


def test_generate_journal_validates_image_count_and_description(context):
    register_and_login(context, "owner@example.com")

    with pytest.raises(ValidationError):
        JournalGenerateRequest.model_validate({"imageIds": [], "description": ""})


def test_generate_journal_saves_local_fallback_when_openai_key_missing(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    request = JournalGenerateRequest(imageIds=[image_id], description="今天很好")
    generator = JournalGenerator(UnavailableJournalClient())

    response = generate_journal(request, user, context.db, generator)

    assert response.title == "今天很好"
    assert response.image_ids == [image_id]
    assert response.layout["content"]["body"] == ["今天很好。"]


def test_user_cannot_generate_with_another_users_images(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    image_id = create_image(context, owner.id)

    with pytest.raises(HTTPException) as error:
        generate_journal(
            JournalGenerateRequest(imageIds=[image_id], description="偷看别人的照片"),
            other,
            context.db,
            context.fake_generator,
        )

    assert error.value.status_code == 404


def test_generate_journal_saves_local_fallback_when_model_request_fails(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    context.fake_generator.error = GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")

    response = generate_journal_for_user(context, user, image_id, "周末一起散步")

    assert response.title == "周末一起散步"
    assert response.image_ids == [image_id]
    assert response.layout["content"]["body"] == ["周末一起散步。"]


def test_generate_journal_saves_and_lists_only_current_users_journals(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    owner_image_id = create_image(context, owner.id)
    other_image_id = create_image(context, other.id)

    owner_response = generate_journal_for_user(context, owner, owner_image_id, "周末一起散步")
    generate_journal_for_user(context, other, other_image_id, "另一个人的手帐")
    journals = list_journals(owner, context.db)

    assert owner_response.title == "慢下来的周末"
    assert owner_response.image_ids == [owner_image_id]
    assert context.fake_generator.request.images[0].data_url.startswith("data:image/webp;base64,")
    assert [item.id for item in journals] == [owner_response.id]


def test_generate_journal_passes_user_context_to_generator(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)

    generate_journal(
        JournalGenerateRequest(
            imageIds=[image_id],
            description="周末一起散步",
            journalDate=date.fromisoformat("2026-05-20"),
            location="上海",
            moodTags=["轻松"],
        ),
        user,
        context.db,
        context.fake_generator,
    )

    assert str(context.fake_generator.request.journal_date) == "2026-05-20"
    assert context.fake_generator.request.location == "上海"
    assert context.fake_generator.request.mood_tags == ["轻松"]


def test_generate_journal_saved_layout_contains_user_context_meta(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)

    response = generate_journal(
        JournalGenerateRequest(
            imageIds=[image_id],
            description="周末一起散步",
            journalDate=date.fromisoformat("2026-05-20"),
            location="上海",
            moodTags=["轻松"],
        ),
        user,
        context.db,
        context.fake_generator,
    )

    assert response.layout["content"]["meta"] == "2026-05-20 / 上海 / 轻松"


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

    section = normalized["layout"]["sections"][0]
    section_bottom = section["y"] + section["height"]
    assert normalized["canvas"]["height"] < 3200
    assert normalized["canvas"]["height"] >= COMPACT_SECTION_CANVAS_HEIGHT
    assert normalized["canvas"]["height"] >= section_bottom + CANVAS_BOTTOM_PADDING


def test_journal_detail_enforces_ownership(context):
    owner = register_and_login(context, "owner@example.com")
    other = register_and_login(context, "other@example.com")
    journal_id = generate_journal_for_user(context, owner, create_image(context, owner.id), "周末一起散步").id

    owner_response = get_journal(journal_id, owner, context.db)
    with pytest.raises(HTTPException) as error:
        get_journal(journal_id, other, context.db)

    assert owner_response.id == journal_id
    assert error.value.status_code == 404


def test_patch_journal_updates_title_body_and_layout_variant(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    journal_id = generate_journal_for_user(context, user, image_id, "周末一起散步").id

    response = update_journal(
        journal_id,
        JournalUpdateRequest(
            title="新的标题",
            meta="2026-06-09 / 上海 / 安静",
            body=["新的正文"],
            captions=[{"imageId": image_id, "text": "新的照片说明"}],
            sections=[
                {
                    "id": "section_1",
                    "title": "新的片段",
                    "imageIds": [image_id],
                    "body": "新的章节正文",
                    "mood": ["安静"],
                }
            ],
            layoutVariant="collage_b",
        ),
        user,
        context.db,
    )

    assert response.title == "新的标题"
    assert response.layout["content"]["meta"] == "2026-06-09 / 上海 / 安静"
    assert response.layout["content"]["body"] == ["新的正文"]
    assert response.layout["content"]["captions"] == [{"imageId": image_id, "text": "新的照片说明"}]
    assert response.layout["content"]["sections"][0]["body"] == "新的章节正文"
    assert response.layout["layout"]["variant"] == "collage_b"
    context.db.expire_all()
    saved_journal = context.db.scalar(select(Journal).where(Journal.id == journal_id))
    assert saved_journal is not None
    assert saved_journal.layout_json["content"]["captions"] == [{"imageId": image_id, "text": "新的照片说明"}]
    assert saved_journal.layout_json["content"]["sections"][0]["body"] == "新的章节正文"


def test_normalized_journal_layout_preserves_user_edited_long_text(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    journal_id = generate_journal_for_user(context, user, image_id, "周末一起散步").id
    edited_title = "周末一起散步之后坐在窗边慢慢写下来的完整标题"
    edited_caption = "这张照片里有咖啡、窗边的光和后来聊到很晚的那段时间"
    edited_body = "这是用户自己补写的一整段记录，不应该在重新打开手帐时被模型清洗、分段或者截短。"

    update_journal(
        journal_id,
        JournalUpdateRequest(
            title=edited_title,
            body=[edited_body],
            captions=[{"imageId": image_id, "text": edited_caption}],
            sections=[
                {
                    "id": "section_1",
                    "title": edited_title,
                    "imageIds": [image_id],
                    "body": edited_body,
                    "mood": ["安静"],
                }
            ],
        ),
        user,
        context.db,
    )

    response = get_journal(journal_id, user, context.db)

    assert response.title == edited_title
    assert response.layout["content"]["title"] == edited_title
    assert response.layout["content"]["body"] == [edited_body]
    assert response.layout["content"]["captions"] == [{"imageId": image_id, "text": edited_caption}]
    assert response.layout["content"]["sections"][0]["title"] == edited_title
    assert response.layout["content"]["sections"][0]["body"] == edited_body


def test_patch_journal_rejects_text_updates_for_images_outside_journal(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    outside_image_id = create_image(context, user.id)
    journal_id = generate_journal_for_user(context, user, image_id, "周末一起散步").id

    with pytest.raises(HTTPException) as caption_error:
        update_journal(
            journal_id,
            JournalUpdateRequest(captions=[{"imageId": outside_image_id, "text": "不属于这页的说明"}]),
            user,
            context.db,
        )

    with pytest.raises(HTTPException) as section_error:
        update_journal(
            journal_id,
            JournalUpdateRequest(
                sections=[
                    {
                        "id": "section_1",
                        "title": "错误片段",
                        "imageIds": [outside_image_id],
                        "body": "这张图不属于当前手帐。",
                        "mood": [],
                    }
                ]
            ),
            user,
            context.db,
        )

    response = get_journal(journal_id, user, context.db)
    assert caption_error.value.status_code == 400
    assert section_error.value.status_code == 400
    assert response.image_ids == [image_id]
    assert response.layout["content"]["captions"] == [{"imageId": image_id, "text": "午后的咖啡"}]


def test_delete_journal_removes_associated_image_files(context):
    user = register_and_login(context, "owner@example.com")
    image_id = create_image(context, user.id)
    journal_id = generate_journal_for_user(context, user, image_id, "周末一起散步").id

    assert list(context.storage_root.glob("users/*/images/*/original.png"))
    assert list(context.storage_root.glob("users/*/images/*/thumb.webp"))

    response = delete_journal(journal_id, user, context.db)

    assert response.status_code == 204
    assert context.db.scalar(select(ImageModel).where(ImageModel.id == image_id)) is None
    assert context.db.scalar(select(Journal).where(Journal.id == journal_id)) is None
    assert not list(context.storage_root.glob("users/*/images/*/original.png"))
    assert not list(context.storage_root.glob("users/*/images/*/thumb.webp"))


class FakeGenerator:
    error = None

    def generate(self, request):
        if self.error is not None:
            raise self.error
        self.request = request
        return JournalLayout.model_validate(layout_payload(request.images[0].id))


class UnavailableJournalClient:
    def generate_layout(self, request: JournalGenerationRequest) -> dict:
        raise GenerationError("OPENAI_API_KEY is required to generate journals")


def register_and_login(context: JournalTestContext, email: str):
    payload = AuthCredentials(email=email, password="strong-password")
    register(payload, context.db)
    token = login(payload, context.db)
    return get_current_user(token.access_token, context.db)


def create_image(context: JournalTestContext, user_id: str) -> str:
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


def generate_journal_for_user(context: JournalTestContext, user, image_id: str, description: str):
    return generate_journal(
        JournalGenerateRequest(imageIds=[image_id], description=description),
        user,
        context.db,
        context.fake_generator,
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
