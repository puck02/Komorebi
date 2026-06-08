from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem
from app.services.journal_agent import JournalAgent
from app.services.journal_generator import JournalGenerationRequest, JournalImageInput
from app.services.layout_rules import check_layout_rules


def test_layout_rules_report_image_order_mismatch():
    layout = JournalLayout.model_validate(layout_payload(image_ids=["img_2", "img_1"]))

    issues = check_layout_rules(layout, generation_request(images=two_images()))

    assert has_issue(issues, "imageOrder", "high", "图片集合或顺序与用户确认结果不一致")


def test_layout_rules_report_section_image_order_mismatch():
    payload = layout_payload(image_ids=["img_1", "img_2"])
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_2", "img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "staggered_collage",
            "y": 220,
            "height": 760,
            "images": [
                {"imageId": "img_2", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0},
                {"imageId": "img_1", "x": 568, "y": 320, "width": 420, "height": 320, "rotation": 0},
            ],
            "texts": [{"role": "body", "x": 112, "y": 720, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(images=two_images()))

    assert has_issue(issues, "imageOrder", "high", "图片集合或顺序与用户确认结果不一致")


def test_layout_rules_report_text_photo_overlap_and_decoration_overflow():
    payload = layout_payload()
    payload["layout"]["texts"].append({"role": "body", "x": 120, "y": 230, "width": 300, "fontSize": 32})
    payload["layout"]["decorations"].append(
        {"assetId": "sticker_approved", "x": 1030, "y": 1520, "width": 120, "height": 120, "rotation": 0}
    )
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(assets=[asset_item("sticker_approved", "sticker")]))

    assert has_issue(issues, "readability", "high", "文字与照片发生重叠")
    assert has_issue(issues, "decorationPlacement", "high", "素材超出画布范围")


def test_layout_rules_report_header_overlap_with_section_images():
    payload = layout_payload()
    payload["content"]["meta"] = "2026-05-20 / 上海 / 松快"
    payload["layout"]["images"] = []
    payload["layout"]["texts"] = [
        {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
        {"role": "meta", "x": 84, "y": 144, "width": 720, "fontSize": 24},
    ]
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 110,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 92, "y": 130, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 520, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "readability", "high", "文字与照片发生重叠")


def test_layout_rules_report_tape_not_attached_to_edge():
    payload = layout_payload()
    payload["layout"]["decorations"].append(
        {"assetId": "tape_approved", "x": 800, "y": 900, "width": 180, "height": 52, "rotation": 0}
    )
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(assets=[asset_item("tape_approved", "tape")]))

    assert has_issue(issues, "decorationPlacement", "high", "胶带没有贴近照片边缘")


def test_layout_rules_allow_tape_attached_to_section_paper():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 760,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 750, "width": 820, "fontSize": 32}],
            "decorations": [
                {"assetId": "paper_approved", "x": 70, "y": 720, "width": 904, "height": 160, "rotation": 0},
                {"assetId": "tape_approved", "x": 160, "y": 696, "width": 220, "height": 54, "rotation": -8},
            ],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(
        layout,
        generation_request(assets=[asset_item("paper_approved", "paper"), asset_item("tape_approved", "tape")]),
    )

    assert not has_issue(issues, "decorationPlacement", "high", "胶带没有贴近照片边缘")


def test_layout_rules_check_section_decoration_assets_and_placement():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 720,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [
                {"assetId": "missing_asset", "x": 20, "y": 20, "width": 120, "height": 120, "rotation": 0},
                {"assetId": "sticker_approved", "x": 1040, "y": 1600, "width": 120, "height": 120, "rotation": 0},
                {"assetId": "tape_approved", "x": 820, "y": 900, "width": 180, "height": 52, "rotation": 0},
            ],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(
        layout,
        generation_request(assets=[asset_item("sticker_approved", "sticker"), asset_item("tape_approved", "tape")]),
    )

    assert has_issue(issues, "asset", "high", "使用了未审核或不存在的素材")
    assert has_issue(issues, "decorationPlacement", "high", "素材超出画布范围")
    assert has_issue(issues, "decorationPlacement", "high", "胶带没有贴近照片边缘")


def test_layout_rules_count_section_decorations_for_density():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["decorations"] = []
    payload["layout"]["images"] = [
        {"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0},
        {"imageId": "img_2", "x": 92, "y": 960, "width": 420, "height": 320, "rotation": 0},
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 720,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [
                {"assetId": f"sticker_{index}", "x": 760, "y": 160 + index * 54, "width": 80, "height": 80, "rotation": 0}
                for index in range(12)
            ],
        }
    ]
    layout = JournalLayout.model_validate(payload)
    request = generation_request(
        assets=[asset_item(f"sticker_{index}", "sticker") for index in range(12)]
    )

    issues = check_layout_rules(layout, request)

    assert not has_issue(issues, "decorationDensity", "medium", "装饰数量偏少，画面丰富度不足")


def test_layout_rules_use_section_count_for_section_decoration_minimum():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []},
        {"id": "section_2", "title": "第二段", "imageIds": ["img_2"], "body": "第二段正文。", "mood": []},
    ]
    payload["layout"]["decorations"] = []
    payload["layout"]["images"] = [
        {"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0},
        {"imageId": "img_2", "x": 92, "y": 960, "width": 420, "height": 320, "rotation": 0},
    ]
    payload["layout"]["sections"] = [
        section_payload("section_1", "img_1", 220, [f"sticker_{index}" for index in range(3)]),
        section_payload("section_2", "img_2", 920, [f"sticker_{index}" for index in range(3, 6)]),
    ]
    layout = JournalLayout.model_validate(payload)
    request = generation_request(
        images=two_images(),
        assets=[asset_item(f"sticker_{index}", "sticker") for index in range(12)],
    )

    issues = check_layout_rules(layout, request)

    assert not has_issue(issues, "decorationDensity", "medium", "装饰数量偏少，画面丰富度不足")


def test_layout_rules_report_section_spacing_and_section_image_gap():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []},
        {"id": "section_2", "title": "第二段", "imageIds": ["img_2"], "body": "第二段正文。", "mood": []},
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "staggered_collage",
            "y": 200,
            "height": 520,
            "images": [
                {"imageId": "img_1", "x": 100, "y": 240, "width": 360, "height": 280, "rotation": 0},
                {"imageId": "img_2", "x": 430, "y": 250, "width": 360, "height": 280, "rotation": 0},
            ],
            "texts": [],
            "decorations": [],
        },
        {
            "sectionId": "section_2",
            "variant": "hero_note",
            "y": 680,
            "height": 420,
            "images": [{"imageId": "img_2", "x": 120, "y": 720, "width": 360, "height": 280, "rotation": 0}],
            "texts": [],
            "decorations": [],
        },
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(images=two_images()))

    assert has_issue(issues, "sectionSpacing", "medium", "章节之间间距不足")
    assert has_issue(issues, "imageSpacing", "medium", "章节内图片间距不足")


def test_layout_rules_report_section_content_beyond_declared_height():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 200,
            "height": 300,
            "images": [{"imageId": "img_1", "x": 100, "y": 240, "width": 360, "height": 420, "rotation": 0}],
            "texts": [],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "sectionBounds", "high", "章节高度没有覆盖内部内容")


def test_layout_rules_report_layout_section_without_content_section():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_2",
            "variant": "hero_note",
            "y": 220,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "sectionReference", "high", "版式章节没有对应的内容章节")


def test_layout_rules_report_section_image_content_mismatch():
    payload = layout_payload(image_ids=["img_1", "img_2"])
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_2"], "body": "第二张照片的正文。", "mood": []},
        {"id": "section_2", "title": "第二段", "imageIds": ["img_1"], "body": "第一张照片的正文。", "mood": []},
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [],
        },
        {
            "sectionId": "section_2",
            "variant": "hero_note",
            "y": 920,
            "height": 620,
            "images": [{"imageId": "img_2", "x": 92, "y": 960, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 1320, "width": 820, "fontSize": 32}],
            "decorations": [],
        },
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(images=two_images()))

    assert not has_issue(issues, "imageOrder", "high", "图片集合或顺序与用户确认结果不一致")
    assert has_issue(issues, "sectionImageMatch", "high", "版式章节图片与内容章节不一致")


def test_layout_rules_allow_subpixel_section_bound_rounding():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 276.8,
            "height": 707.3333333333333,
            "images": [{"imageId": "img_1", "x": 92, "y": 276.8, "width": 520, "height": 390, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 858.1333333333333, "width": 820, "fontSize": 32}],
            "decorations": [
                {"assetId": "paper_approved", "x": 70, "y": 824.1333333333333, "width": 904, "height": 160, "rotation": 0}
            ],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(assets=[asset_item("paper_approved", "paper")]))

    assert not has_issue(issues, "sectionBounds", "high", "章节高度没有覆盖内部内容")


def test_layout_rules_report_section_text_photo_overlap():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 200,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 100, "y": 240, "width": 360, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 120, "y": 280, "width": 300, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "readability", "high", "章节文字与照片发生重叠")


def test_layout_rules_allow_caption_on_photo_border():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "午后的咖啡"}]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 200,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 100, "y": 240, "width": 360, "height": 320, "rotation": 0}],
            "texts": [
                {"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32},
                {"role": "caption", "x": 128, "y": 522, "width": 304, "fontSize": 22},
            ],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert not has_issue(issues, "readability", "high", "章节文字与照片发生重叠")


def test_layout_rules_report_partial_section_caption_rendering():
    payload = layout_payload(image_ids=["img_1", "img_2"])
    payload["content"]["captions"] = [
        {"imageId": "img_1", "text": "窗边咖啡"},
        {"imageId": "img_2", "text": "路口灯光"},
    ]
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "两张照片", "imageIds": ["img_1", "img_2"], "body": "咖啡喝完后，走到路口。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "staggered_collage",
            "y": 220,
            "height": 760,
            "images": [
                {"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0},
                {"imageId": "img_2", "x": 568, "y": 320, "width": 420, "height": 320, "rotation": 0},
            ],
            "texts": [
                {"role": "body", "x": 112, "y": 700, "width": 820, "fontSize": 32},
                {"role": "caption", "x": 120, "y": 542, "width": 360, "fontSize": 22},
            ],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(images=two_images()))

    assert has_issue(issues, "captionCoverage", "medium", "章节照片说明没有完整渲染")


def test_layout_rules_use_actual_section_text_height_for_bounds():
    payload = layout_payload()
    long_body = "这是一段很长的正文，" * 30
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": long_body, "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 200,
            "height": 520,
            "images": [{"imageId": "img_1", "x": 100, "y": 240, "width": 360, "height": 240, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 500, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "sectionBounds", "high", "章节高度没有覆盖内部内容")


def test_layout_rules_report_cliche_copy_quality_issue():
    payload = layout_payload()
    payload["content"]["body"] = ["今天很治愈，像被温柔包裹，也很有仪式感。"]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "第一段",
            "imageIds": ["img_1"],
            "body": "把时光收藏成珍贵回忆。",
            "mood": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "copyQuality", "medium", "正文存在明显 AI 套话，手帐记录不够具体")


def test_layout_rules_report_placeholder_copy_quality_issue():
    payload = layout_payload()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "今天的照片"}]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "第一段",
            "imageIds": ["img_1"],
            "body": "这一组照片也想好好留下。",
            "mood": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request())

    assert has_issue(issues, "copyQuality", "medium", "正文存在占位式描述，手帐记录不够具体")


def test_layout_rules_report_multi_image_section_without_visual_focus():
    payload = layout_payload(image_ids=["img_1", "img_2", "img_3"])
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "三张照片",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "三张照片放在一起。",
            "mood": [],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "photo_wall",
            "y": 220,
            "height": 620,
            "images": [
                {"imageId": "img_1", "x": 92, "y": 260, "width": 300, "height": 260, "rotation": 0},
                {"imageId": "img_2", "x": 420, "y": 260, "width": 300, "height": 260, "rotation": 0},
                {"imageId": "img_3", "x": 748, "y": 260, "width": 300, "height": 260, "rotation": 0},
            ],
            "texts": [{"role": "body", "x": 112, "y": 560, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)

    issues = check_layout_rules(layout, generation_request(images=three_images()))

    assert has_issue(issues, "visualFocus", "medium", "多图章节缺少明确主图或视觉焦点")


def test_layout_rules_report_missing_functional_section_decorations():
    payload = layout_payload()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 620,
            "images": [{"imageId": "img_1", "x": 92, "y": 260, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    layout = JournalLayout.model_validate(payload)
    request = generation_request(assets=[asset_item("paper_approved", "paper"), asset_item("tape_approved", "tape")])

    issues = check_layout_rules(layout, request)

    assert has_issue(issues, "decorationFunction", "medium", "章节缺少承载文字或固定照片的功能性装饰")


def test_agent_revises_when_default_layout_rules_report_hard_failure():
    bad_layout = layout_payload(title="第一段")
    fixed_layout = layout_payload(title="修复后")
    client = FakeAgentClient(
        reviews=[review(score=95, passed=True), review(score=92, passed=True)],
        layouts=[bad_layout],
        revisions=[fixed_layout],
    )

    result = JournalAgent(client, FakeRenderer()).generate(generation_request())

    assert len(client.revision_inputs) == 1
    assert client.review_inputs[0]["rule_issues"]
    assert result.layout.content.title == "修复后"
    assert result.passed is True


def has_issue(issues, issue_type, severity, description):
    return any(
        issue["type"] == issue_type and issue["severity"] == severity and issue["description"] == description
        for issue in issues
    )


def generation_request(images=None, assets=None):
    return JournalGenerationRequest(
        description="周末一起散步。",
        images=images or [JournalImageInput(id="img_1", width=640, height=480)],
        assets=assets if assets is not None else [],
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


def asset_item(asset_id, category, source="internal"):
    return AssetItem(
        id=asset_id,
        name=asset_id,
        category=category,
        tags=["daily"],
        style=["soft-collage"],
        colors=["#fef6e4"],
        file=f"{asset_id}.svg",
        license="internal",
        source=source,
        quality_status="approved",
    )


def section_payload(section_id, image_id, y, decoration_ids):
    return {
        "sectionId": section_id,
        "variant": "hero_note",
        "y": y,
        "height": 620,
        "images": [{"imageId": image_id, "x": 92, "y": y + 40, "width": 420, "height": 320, "rotation": 0}],
        "texts": [{"role": "body", "x": 112, "y": y + 420, "width": 820, "fontSize": 32}],
        "decorations": [
            {"assetId": asset_id, "x": 760, "y": y + 40 + index * 72, "width": 80, "height": 80, "rotation": 0}
            for index, asset_id in enumerate(decoration_ids)
        ],
    }


class FakeAgentClient:
    def __init__(self, reviews, layouts, revisions):
        self.reviews = list(reviews)
        self.layouts = list(layouts)
        self.revisions = list(revisions)
        self.review_inputs = []
        self.revision_inputs = []

    def generate_layout(self, request):
        return self.layouts.pop(0)

    def review_layout(self, request, layout, screenshot_data_url, rule_issues):
        self.review_inputs.append({"layout": layout, "rule_issues": rule_issues})
        return self.reviews.pop(0)

    def revise_layout(self, request, layout, screenshot_data_url, review, revision_round, best_score):
        self.revision_inputs.append({"layout": layout, "review": review, "revision_round": revision_round})
        return self.revisions.pop(0)


class FakeRenderer:
    def render(self, layout, request):
        return "data:image/webp;base64,screenshot"


def review(score, passed=False):
    return {
        "score": score,
        "passed": passed,
        "scores": {"layout": 20, "photoTextMatch": 20, "decorationPlacement": 15, "readability": 15, "coherence": 8},
        "issues": [],
        "summary": "调整细节。",
    }


def layout_payload(title="初稿", image_ids=None):
    image_ids = image_ids or ["img_1"]
    return {
        "canvas": {"width": 1080, "height": 1600, "background": "#fef6e4"},
        "theme": {"style": "soft-collage", "palette": ["#fef6e4"], "mood": ["温柔"]},
        "content": {
            "title": title,
            "body": ["今天走了很久，回来时刚好喝到一杯热咖啡。"],
            "captions": [{"imageId": image_ids[0], "text": "热咖啡还在桌上"}],
        },
        "layout": {
            "variant": "long_collage",
            "images": [
                {"imageId": image_id, "x": 92 + index * 476, "y": 210, "width": 420, "height": 320, "rotation": 0}
                for index, image_id in enumerate(image_ids)
            ],
            "texts": [{"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56}],
            "decorations": [],
            "sections": [],
        },
    }
