from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.journals import recommend_journal_templates
from app.db.base import Base
from app.models import ai_settings, asset, generation_job, image as image_model, journal, user as user_model  # noqa: F401
from app.models.ai_settings import AiSettings
from app.models.image import Image
from app.models.user import User
from app.schemas.journal import JournalTemplateRecommendRequest
from app.services.template_recommender import (
    TemplateRecommendationImage,
    TemplateRecommendationRequest,
    recommend_templates,
)


def test_recommender_uses_image_understanding_for_template_match():
    request = TemplateRecommendationRequest(
        description="下午出门走了一圈",
        images=[image("img_1", 640, 480), image("img_2", 640, 480)],
        mood_tags=[],
    )

    result = recommend_templates(request, FakeVisionClient())

    assert result["source"] == "ai"
    assert result["imageUnderstanding"]
    assert [item["templateId"] for item in result["recommendations"]][:1] == ["ticket_day"]
    assert "票据" in result["recommendations"][0]["reason"] or "小票" in result["recommendations"][0]["reason"]


def test_recommender_falls_back_to_local_rules_when_ai_fails():
    request = TemplateRecommendationRequest(
        description="从早到晚的一整天，想讲成完整故事",
        images=[image(f"img_{index}", 640, 480) for index in range(1, 8)],
        mood_tags=[],
    )

    result = recommend_templates(request, FailingVisionClient())

    assert result["source"] == "local"
    assert result["message"]
    assert len(result["recommendations"]) == 3
    assert "chapter_scroll" in [item["templateId"] for item in result["recommendations"]]


def test_recommender_keeps_recommended_templates_narratively_distinct():
    request = TemplateRecommendationRequest(
        description="从早到晚的一整天，有路上、咖啡、展览和后来回家的片段",
        images=[image(f"img_{index}", 640, 480) for index in range(1, 8)],
        mood_tags=[],
    )

    result = recommend_templates(request)
    template_ids = [item["templateId"] for item in result["recommendations"]]

    assert len(template_ids) == 3
    assert "chapter_scroll" in template_ids
    assert len(template_ids) == len(set(template_ids))
    assert not {"chapter_scroll", "timeline_trip"}.issubset(set(template_ids))


def test_recommender_detects_two_scene_story_from_image_understanding():
    request = TemplateRecommendationRequest(
        description="上午和下午像两个状态",
        images=[image("img_1", 640, 480), image("img_2", 640, 480)],
        mood_tags=[],
    )

    result = recommend_templates(request, TwoSceneVisionClient())

    assert "split_scene" in [item["templateId"] for item in result["recommendations"]]
    assert any("两个场景" in item["reason"] for item in result["recommendations"])


def test_recommend_journal_templates_route_returns_local_fallback_without_testclient(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        with testing_session() as db:
            current_user = User(id="user_1", email="owner@example.com", password_hash="hash")
            image_dir = tmp_path / "image"
            image_dir.mkdir()
            original_path = image_dir / "original.png"
            display_path = image_dir / "display.webp"
            thumbnail_path = image_dir / "thumb.webp"
            original_path.write_bytes(b"original")
            display_path.write_bytes(b"display")
            thumbnail_path.write_bytes(b"thumb")
            db.add(current_user)
            db.add(
                Image(
                    id="img_1",
                    user_id=current_user.id,
                    original_path=str(original_path),
                    thumbnail_path=str(thumbnail_path),
                    content_type="image/png",
                    width=640,
                    height=480,
                )
            )
            db.add(AiSettings(id="default", base_url="https://provider.example/v1", api_key="", model="gpt-5.5", review_model="gpt-5.4-mini"))
            db.commit()

            result = recommend_journal_templates(
                JournalTemplateRecommendRequest(
                    imageIds=["img_1"],
                    description="咖啡店、展览和小票都想留下",
                    moodTags=[],
                ),
                current_user=current_user,
                db=db,
            )

        assert result.source == "local"
        assert len(result.recommendations) == 3
        assert "ticket_day" in [item.template_id for item in result.recommendations]
        assert result.message
    finally:
        Base.metadata.drop_all(bind=engine)
        get_settings.cache_clear()


class FakeVisionClient:
    def understand_images(self, request):
        return [
            {
                "imageId": "img_1",
                "summary": "桌上有一杯咖啡和一张小票",
                "scene": "咖啡店",
                "subjects": ["咖啡", "小票"],
                "mood": ["安静"],
            },
            {
                "imageId": "img_2",
                "summary": "展厅里的票根和照片",
                "scene": "展览",
                "subjects": ["展览", "票"],
                "mood": ["轻松"],
            },
        ]


class FailingVisionClient:
    def understand_images(self, request):
        from app.services.template_recommender import TemplateRecommendationError

        raise TemplateRecommendationError("failed")


class TwoSceneVisionClient:
    def understand_images(self, request):
        return [
            {
                "imageId": "img_1",
                "summary": "室内桌边有笔记本和茶杯",
                "scene": "室内",
                "subjects": ["笔记本", "茶杯"],
                "mood": ["安静"],
            },
            {
                "imageId": "img_2",
                "summary": "室外路边有路灯和街景",
                "scene": "室外",
                "subjects": ["路灯", "街景"],
                "mood": ["松快"],
            },
        ]


def image(image_id: str, width: int, height: int) -> TemplateRecommendationImage:
    return TemplateRecommendationImage(id=image_id, width=width, height=height)
