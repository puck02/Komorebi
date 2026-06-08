from copy import deepcopy
import json
import logging

from app.schemas.journal import JournalLayout
from app.services.assets import get_approved_assets
from app.services.journal_agent import JournalAgent
from app.services.journal_generator import GenerationError, JournalGenerationRequest, JournalImageInput


def test_agent_stops_after_first_review_when_quality_threshold_passes():
    client = FakeAgentClient(reviews=[review(score=90, passed=True)])
    renderer = FakeRenderer()

    result = JournalAgent(client, renderer, rule_checker=no_rule_issues).generate(generation_request())

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

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request())

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


def test_agent_returns_best_candidate_when_revision_ai_connection_fails():
    client = FakeAgentClient(
        reviews=[review(score=74)],
        revisions=[GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")],
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request())

    assert result.layout.content.title == "初稿"
    assert result.score == 74
    assert result.revision_round == 0
    assert result.passed is False
    assert len(client.revision_inputs) == 1


def test_agent_returns_draft_when_initial_review_ai_connection_fails():
    client = FakeAgentClient(
        reviews=[GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")],
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request())

    assert result.layout.content.title == "初稿"
    assert result.score == 0
    assert result.revision_round == 0
    assert result.passed is False
    assert client.revision_inputs == []


def test_agent_returns_draft_when_visual_rendering_fails():
    client = FakeAgentClient(reviews=[review(score=90, passed=True)])
    renderer = FailingRenderer(RuntimeError("Page.goto: Page crashed"))

    result = JournalAgent(client, renderer, rule_checker=no_rule_issues).generate(generation_request())

    assert result.layout.content.title == "初稿"
    assert result.score == 0
    assert result.revision_round == 0
    assert result.passed is False
    assert client.review_inputs == []
    assert client.revision_inputs == []


def test_agent_returns_fallback_when_unreviewed_draft_has_hard_rule_issues():
    client = FakeAgentClient(reviews=[review(score=90, passed=True)])
    renderer = FailingRenderer(RuntimeError("Page.goto: Page crashed"))
    hard_rule_issues = [{"type": "readability", "severity": "high", "description": "文字遮挡图片"}]

    result = JournalAgent(client, renderer, rule_checker=lambda _layout, _request: hard_rule_issues).generate(
        generation_request()
    )

    assert result.layout.content.title == "周末一起散步"
    assert result.layout.content.body == ["周末一起散步。"]
    assert result.score == 0
    assert result.revision_round == 0
    assert result.passed is False
    assert client.review_inputs == []
    assert client.revision_inputs == []


def test_agent_returns_fallback_layout_when_initial_generation_ai_connection_fails():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request())

    assert result.layout.content.title == "周末一起散步"
    assert result.layout.content.body == ["周末一起散步。"]
    assert result.layout.content.captions[0].image_id == "img_1"
    assert result.layout.content.captions[0].text == "周末一起散步"
    assert result.layout.layout.images[0].image_id == "img_1"
    assert result.score == 0
    assert result.revision_round == 0
    assert result.passed is False
    assert client.review_inputs == []
    assert client.revision_inputs == []


def test_agent_fallback_layout_uses_ordered_captions_for_multiple_images():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
        JournalGenerationRequest(
            description="周末一起散步。傍晚喝了咖啡。",
            images=two_images(),
            assets=get_approved_assets(),
        )
    )

    assert [caption.image_id for caption in result.layout.content.captions] == ["img_1", "img_2"]
    assert [caption.text for caption in result.layout.content.captions] == ["周末一起散步", "傍晚喝了咖啡"]
    assert [image.image_id for image in result.layout.layout.images] == ["img_1", "img_2"]


def test_agent_fallback_layout_splits_single_sentence_captions():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
        JournalGenerationRequest(
            description="周末一起散步，傍晚喝了咖啡，路口的灯亮起来。",
            images=three_images(),
            assets=get_approved_assets(),
        )
    )

    assert [caption.text for caption in result.layout.content.captions] == [
        "周末一起散步",
        "傍晚喝了咖啡",
        "路口的灯亮起来",
    ]


def test_agent_fallback_section_body_is_not_caption_list():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
        JournalGenerationRequest(
            description="周末一起散步，傍晚喝了咖啡，路口的灯亮起来。",
            images=three_images(),
            assets=get_approved_assets(),
        )
    )

    section_body = result.layout.content.sections[0].body
    assert section_body != "周末一起散步，傍晚喝了咖啡，路口的灯亮起来。"
    assert section_body == "这一组放在一起看，周末一起散步、傍晚喝了咖啡、路口的灯亮起来。"


def test_agent_fallback_layout_adds_functional_section_decorations():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request())

    decoration_ids = {decoration.asset_id for decoration in result.layout.layout.sections[0].decorations}
    assert any(asset_id.startswith("paper_") for asset_id in decoration_ids)
    assert any(asset_id.startswith("tape_") for asset_id in decoration_ids)
    assert any(asset_id.startswith("sticker_") for asset_id in decoration_ids)


def test_agent_fallback_layout_splits_large_image_sets_without_repeating_body():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
        JournalGenerationRequest(
            description="周末一起散步。傍晚喝了咖啡，路口的灯亮起来。",
            images=four_images(),
            assets=get_approved_assets(),
        )
    )

    assert [section.image_ids for section in result.layout.content.sections] == [
        ["img_1", "img_2", "img_3"],
        ["img_4"],
    ]
    assert [section.body for section in result.layout.content.sections] == [
        "周末一起散步，傍晚喝了咖啡。",
        "路口的灯亮起来。",
    ]


def test_agent_fallback_layout_splits_single_sentence_into_human_section_notes():
    client = FakeAgentClient(
        reviews=[],
        generation_error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置"),
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
        JournalGenerationRequest(
            description="周末一起散步，傍晚喝了咖啡，路口的灯亮起来。",
            images=four_images(),
            assets=get_approved_assets(),
        )
    )

    assert [section.body for section in result.layout.content.sections] == [
        "周末一起散步，傍晚喝了咖啡。",
        "路口的灯亮起来。",
    ]


def test_agent_restores_user_image_order_after_revision():
    reversed_layout = layout_payload(title="修订后", image_ids=["img_2", "img_1"])
    client = FakeAgentClient(
        reviews=[review(score=70), review(score=90, passed=True)],
        revisions=[reversed_layout],
    )

    result = JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(generation_request(images=two_images()))

    assert [image.image_id for image in result.layout.layout.images] == ["img_1", "img_2"]


def test_agent_logs_structured_review_events(caplog):
    client = FakeAgentClient(reviews=[review(score=90, passed=True)])

    with caplog.at_level(logging.INFO, logger="komorebi.agent"):
        JournalAgent(client, FakeRenderer(), rule_checker=no_rule_issues).generate(
            generation_request(),
            log_context={"job_id": "job_123"},
        )

    payloads = [json.loads(record.message) for record in caplog.records]
    reviewed = next(payload for payload in payloads if payload["event"] == "agent.candidate_reviewed")
    assert reviewed["job_id"] == "job_123"
    assert reviewed["revision_round"] == 0
    assert reviewed["score"] == 90
    assert reviewed["passed"] is True
    assert reviewed["decorations"] == {"total": 0, "unique_assets": 0, "external": 0}
    assert reviewed["rule_issues"] == {"count": 0, "types": [], "severities": []}
    assert reviewed["review_issues"] == {"count": 0, "types": [], "severities": []}


class FakeAgentClient:
    def __init__(self, reviews, revisions=None, generation_error=None):
        self.reviews = list(reviews)
        self.revisions = list(revisions or [])
        self.generation_error = generation_error
        self.review_inputs = []
        self.revision_inputs = []

    def generate_layout(self, request):
        if self.generation_error:
            raise self.generation_error
        return layout_payload()

    def review_layout(self, request, layout, screenshot_data_url, rule_issues):
        self.review_inputs.append(
            {
                "layout": deepcopy(layout),
                "screenshot_data_url": screenshot_data_url,
                "rule_issues": deepcopy(rule_issues),
            }
        )
        review_result = self.reviews.pop(0)
        if isinstance(review_result, Exception):
            raise review_result
        return review_result

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
        revision = self.revisions.pop(0)
        if isinstance(revision, Exception):
            raise revision
        return revision


class FakeRenderer:
    def __init__(self):
        self.layouts = []

    def render(self, layout, request):
        self.layouts.append(deepcopy(layout))
        return "data:image/webp;base64,screenshot"


class FailingRenderer:
    def __init__(self, error):
        self.error = error

    def render(self, layout, request):
        raise self.error


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


def three_images():
    return [
        JournalImageInput(id="img_1", width=640, height=480),
        JournalImageInput(id="img_2", width=900, height=1200),
        JournalImageInput(id="img_3", width=1200, height=900),
    ]


def four_images():
    return [
        JournalImageInput(id="img_1", width=640, height=480),
        JournalImageInput(id="img_2", width=900, height=1200),
        JournalImageInput(id="img_3", width=1200, height=900),
        JournalImageInput(id="img_4", width=720, height=960),
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


def no_rule_issues(_layout, _request):
    return []


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
