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
    assert "咖啡" in result["recommendations"][0]["reason"] or "小票" in result["recommendations"][0]["reason"]


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


def image(image_id: str, width: int, height: int) -> TemplateRecommendationImage:
    return TemplateRecommendationImage(id=image_id, width=width, height=height)
