from copy import deepcopy

from app.schemas.journal import JournalLayout
from app.services.assets import get_approved_assets
from app.services.journal_agent import JournalAgent
from app.services.journal_generator import JournalGenerationRequest, JournalImageInput


def test_agent_stops_after_first_review_when_quality_threshold_passes():
    client = FakeAgentClient(reviews=[review(score=90, passed=True)])
    renderer = FakeRenderer()

    result = JournalAgent(client, renderer).generate(generation_request())

    assert result.score == 90
    assert result.revision_round == 0
    assert result.passed is True
    assert client.revision_inputs == []
    assert renderer.layouts


def test_agent_revises_from_best_version_when_new_version_scores_lower():
    client = FakeAgentClient(
        reviews=[review(score=82), review(score=60), review(score=88, passed=True)],
        revisions=[layout_payload(title="较差版本"), layout_payload(title="最终版本")],
    )

    result = JournalAgent(client, FakeRenderer()).generate(generation_request())

    assert result.layout.content.title == "最终版本"
    assert client.revision_inputs[0]["layout"]["content"]["title"] == "初稿"
    assert client.revision_inputs[1]["layout"]["content"]["title"] == "初稿"


def test_agent_runs_at_most_three_revision_rounds_and_returns_best_version():
    client = FakeAgentClient(
        reviews=[review(score=70), review(score=72), review(score=74), review(score=73)],
        revisions=[layout_payload(title=f"修订 {index}") for index in range(1, 4)],
    )

    result = JournalAgent(client, FakeRenderer()).generate(generation_request())

    assert len(client.revision_inputs) == 3
    assert len(client.review_inputs) == 4
    assert result.layout.content.title == "修订 2"
    assert result.score == 74
    assert result.revision_round == 2
    assert result.passed is False


def test_agent_continues_when_program_rules_report_hard_failure():
    client = FakeAgentClient(
        reviews=[review(score=95, passed=True), review(score=90, passed=True)],
        revisions=[layout_payload(title="修复后")],
    )
    rule_results = [[{"type": "readability", "severity": "high", "description": "文字遮挡图片"}], []]

    result = JournalAgent(client, FakeRenderer(), rule_checker=lambda _layout, _request: rule_results.pop(0)).generate(
        generation_request()
    )

    assert len(client.revision_inputs) == 1
    assert result.layout.content.title == "修复后"


def test_agent_restores_user_image_order_after_revision():
    reversed_layout = layout_payload(title="修订后", image_ids=["img_2", "img_1"])
    client = FakeAgentClient(
        reviews=[review(score=70), review(score=90, passed=True)],
        revisions=[reversed_layout],
    )

    result = JournalAgent(client, FakeRenderer()).generate(generation_request(images=two_images()))

    assert [image.image_id for image in result.layout.layout.images] == ["img_1", "img_2"]


class FakeAgentClient:
    def __init__(self, reviews, revisions=None):
        self.reviews = list(reviews)
        self.revisions = list(revisions or [])
        self.review_inputs = []
        self.revision_inputs = []

    def generate_layout(self, request):
        return layout_payload()

    def review_layout(self, request, layout, screenshot_data_url, rule_issues):
        self.review_inputs.append(
            {
                "layout": deepcopy(layout),
                "screenshot_data_url": screenshot_data_url,
                "rule_issues": deepcopy(rule_issues),
            }
        )
        return self.reviews.pop(0)

    def revise_layout(self, request, layout, screenshot_data_url, review, revision_round, best_score):
        self.revision_inputs.append(
            {
                "layout": deepcopy(layout),
                "screenshot_data_url": screenshot_data_url,
                "review": deepcopy(review),
                "revision_round": revision_round,
                "best_score": best_score,
            }
        )
        return self.revisions.pop(0)


class FakeRenderer:
    def __init__(self):
        self.layouts = []

    def render(self, layout, request):
        self.layouts.append(deepcopy(layout))
        return "data:image/webp;base64,screenshot"


def generation_request(images=None):
    return JournalGenerationRequest(
        description="周末一起散步。",
        images=images or [JournalImageInput(id="img_1", width=640, height=480)],
        assets=get_approved_assets(),
    )


def two_images():
    return [
        JournalImageInput(id="img_1", width=640, height=480),
        JournalImageInput(id="img_2", width=900, height=1200),
    ]


def review(score, passed=False):
    return {
        "score": score,
        "passed": passed,
        "scores": {
            "layout": 20,
            "photoTextMatch": 20,
            "decorationPlacement": 15,
            "readability": 15,
            "coherence": 8,
        },
        "issues": [],
        "summary": "调整细节。",
    }


def layout_payload(title="初稿", image_ids=None):
    image_ids = image_ids or ["img_1"]
    return {
        "canvas": {"width": 1080, "height": 1600, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8"], "mood": ["温柔"]},
        "content": {
            "title": title,
            "body": ["今天走了很久，回来时刚好喝到一杯热咖啡。"],
            "captions": [{"imageId": image_ids[0], "text": "今天的照片"}],
        },
        "layout": {
            "variant": "long_collage",
            "images": [
                {"imageId": image_id, "x": 92 + index * 476, "y": 210, "width": 420, "height": 320, "rotation": 0}
                for index, image_id in enumerate(image_ids)
            ],
            "texts": [{"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56}],
            "decorations": [],
        },
    }
