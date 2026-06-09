import json
from collections import Counter

import pytest
import httpx

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem, get_approved_assets, load_assets
from app.services.decoration_placement import overlaps_photo_safe_area
from app.services.journal_generator import (
    build_fallback_layout,
    GenerationError,
    JournalGenerationRequest,
    JournalGenerator,
    JournalImageInput,
    check_layout_rules,
    normalize_canvas_height,
    sanitize_model_layout,
)
from app.services.openai_client import (
    OpenAIConfigurationError,
    OpenAIJournalClient,
    build_generation_prompt,
    order_assets_for_ai,
)


def test_generator_returns_valid_journal_layout():
    generator = JournalGenerator(FakeClient(valid_model_json()))
    request = generation_request()

    layout = generator.generate(request)

    assert isinstance(layout, JournalLayout)
    assert layout.canvas.width == 1080
    assert layout.canvas.height == 1120
    assert layout.canvas.height >= rendered_content_bottom(layout) + 80
    assert layout.content.title == "慢下来的周末"


def test_generator_adds_meta_text_from_user_context():
    generator = JournalGenerator(FakeClient(valid_model_json()))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步，天气很好，喝了咖啡。",
            journal_date="2026-05-20",
            location="上海",
            mood_tags=["松快"],
            images=[JournalImageInput(id="img_1", width=640, height=480)],
            assets=load_assets(),
        )
    )

    assert layout.content.meta == "2026-05-20 / 上海 / 松快"
    meta_text = next(text for text in layout.layout.texts if text.role == "meta")
    title_text = next(text for text in layout.layout.texts if text.role == "title")
    assert meta_text.y > title_text.y
    assert 18 <= meta_text.font_size <= 28


def test_fallback_layout_uses_selected_template_variant():
    request = generation_request(images=three_images(), template_id="timeline_trip")

    layout = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))

    assert layout.layout.variant == "timeline_trip"
    assert layout.layout.sections
    assert layout.layout.sections[0].variant == "timeline_trip"


def test_generator_enforces_selected_template_when_model_ignores_it():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "咖啡和小票",
            "imageIds": ["img_1", "img_2"],
            "body": "咖啡还热着，小票也压在杯子旁边。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "staggered_collage",
            "y": 220,
            "height": 820,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        generation_request(
            images=[
                JournalImageInput(id="img_1", width=640, height=480),
                JournalImageInput(id="img_2", width=900, height=1200),
            ],
            template_id="ticket_day",
        )
    )

    assert [section.variant for section in layout.layout.sections] == ["ticket_day"]


def test_fallback_pocket_grid_keeps_many_photos_in_one_story_section():
    request = generation_request(images=[JournalImageInput(id=f"img_{index}", width=640, height=480) for index in range(1, 7)], template_id="pocket_grid")

    layout = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))

    assert [section.image_ids for section in layout.content.sections] == [[f"img_{index}" for index in range(1, 7)]]
    assert layout.layout.sections[0].variant == "pocket_grid"


def test_generator_keeps_model_pocket_grid_story_section_larger_than_three_images():
    image_ids = [f"img_{index}" for index in range(1, 7)]
    payload = valid_model_json()
    payload["content"]["body"] = ["把这一天的小片段都收在同一页，每格是一件小事。"]
    payload["content"]["sections"] = [
        {
            "id": "pocket",
            "title": "一天几格",
            "imageIds": image_ids,
            "body": "把这一天的小片段都收在同一页，每格是一件小事。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "pocket",
            "variant": "pocket_grid",
            "y": 220,
            "height": 980,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        generation_request(
            images=[JournalImageInput(id=image_id, width=640, height=480) for image_id in image_ids],
            template_id="pocket_grid",
        )
    )

    assert [section.image_ids for section in layout.content.sections] == [image_ids]
    assert [section.variant for section in layout.layout.sections] == ["pocket_grid"]


def test_fallback_split_scene_creates_two_story_sections():
    request = generation_request(images=[JournalImageInput(id=f"img_{index}", width=640, height=480) for index in range(1, 5)], template_id="split_scene")

    layout = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))

    assert [section.image_ids for section in layout.content.sections] == [["img_1", "img_2"], ["img_3", "img_4"]]
    assert [section.variant for section in layout.layout.sections] == ["split_scene", "split_scene"]


def test_fallback_chapter_scroll_keeps_long_story_as_readable_chapters():
    request = generation_request(images=[JournalImageInput(id=f"img_{index}", width=640, height=480) for index in range(1, 8)], template_id="chapter_scroll")

    layout = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))

    assert [section.image_ids for section in layout.content.sections] == [
        ["img_1", "img_2", "img_3"],
        ["img_4", "img_5", "img_6"],
        ["img_7"],
    ]
    assert [section.variant for section in layout.layout.sections] == ["chapter_scroll", "chapter_scroll", "chapter_scroll"]


def test_fallback_chapter_scroll_with_mixed_orientation_avoids_caption_overlaps():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="周末一起出门，路上喝了咖啡，也把看到的小细节记下来。",
        images=[
            JournalImageInput(id=f"img_{index}", width=900 if index % 2 else 640, height=1200 if index % 2 else 480)
            for index in range(1, 8)
        ],
        assets=load_assets(),
        template_id="chapter_scroll",
    )

    layout = generator.generate(request)
    high_issues = [issue for issue in check_layout_rules(layout, request) if issue["severity"] == "high"]

    assert high_issues == []


def test_fallback_story_template_captions_do_not_repeat_section_body():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="想做拼贴剪贴风，把这些回忆和贴纸素材放在一起。",
        images=[JournalImageInput(id=f"img_{index}", width=640, height=480) for index in range(1, 6)],
        assets=load_assets(),
        template_id="scrapbook_story",
    )

    layout = generator.generate(request)
    issues = check_layout_rules(layout, request)

    assert not any(issue["type"] == "copyQuality" for issue in issues)


def test_fallback_map_journey_keeps_route_photos_spaced():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="这次小旅行想按地图路线和几个打卡点来记。",
        images=[
            JournalImageInput(id=f"img_{index}", width=900 if index % 2 else 640, height=1200 if index % 2 else 480)
            for index in range(1, 6)
        ],
        assets=load_assets(),
        template_id="map_journey",
    )

    layout = generator.generate(request)
    issues = check_layout_rules(layout, request)

    assert not any(issue["type"] == "imageSpacing" for issue in issues)


def test_fallback_dense_story_templates_use_sparse_captions_without_overlap():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="这几张没有严格顺序，就是今天几个开心的小碎片。",
        images=[
            JournalImageInput(id=f"img_{index}", width=900 if index % 2 else 640, height=1200 if index % 2 else 480)
            for index in range(1, 6)
        ],
        assets=load_assets(),
        template_id="moodboard_stack",
    )

    layout = generator.generate(request)
    section = layout.layout.sections[0]
    issues = check_layout_rules(layout, request)

    assert len([text for text in section.texts if text.role == "caption"]) < len(section.images)
    assert not any(issue["severity"] == "high" for issue in issues)
    assert not any(issue["type"] == "captionCoverage" for issue in issues)


@pytest.mark.parametrize(
    ("template_id", "expected_section_variant"),
    [
        ("quiet_story", "quiet_story"),
        ("hero_memory", "hero_memory"),
        ("timeline_trip", "timeline_trip"),
        ("pocket_grid", "pocket_grid"),
        ("ticket_day", "ticket_day"),
        ("magazine_note", "magazine_note"),
        ("before_after", "before_after"),
        ("moodboard_stack", "moodboard_stack"),
        ("recipe_memo", "recipe_memo"),
        ("letter_page", "letter_page"),
        ("chapter_scroll", "chapter_scroll"),
        ("field_notes", "field_notes"),
        ("split_scene", "split_scene"),
        ("detail_index", "detail_index"),
        ("map_journey", "map_journey"),
        ("weekly_spread", "weekly_spread"),
        ("day_dashboard", "day_dashboard"),
        ("scrapbook_story", "scrapbook_story"),
    ],
)
def test_fallback_layout_keeps_selected_template_as_real_section_variant(template_id, expected_section_variant):
    request = generation_request(images=three_images(), template_id=template_id)

    layout = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))

    assert layout.layout.sections
    assert layout.layout.sections[0].variant == expected_section_variant


def test_generator_expands_canvas_to_fit_long_section_placements():
    payload = valid_model_json()
    payload["canvas"]["height"] = 1500
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "走到很远的地方",
            "imageIds": ["img_1"],
            "body": "今天的照片排得很长，画布也要跟着延伸。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 1720,
            "height": 760,
            "images": [{"imageId": "img_1", "x": 110, "y": 1720, "width": 760, "height": 520, "rotation": 2}],
            "texts": [{"role": "body", "x": 112, "y": 2300, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    section = layout.layout.sections[0]
    assert layout.canvas.height >= section.y + section.height + 80


def test_generator_keeps_only_provided_image_ids():
    payload = valid_model_json()
    payload["layout"]["images"].append(
        {
            "imageId": "unknown_image",
            "x": 20,
            "y": 20,
            "width": 200,
            "height": 160,
            "rotation": 0,
        }
    )
    payload["content"]["captions"].append({"imageId": "unknown_image", "text": "不存在的照片"})
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert {placement.image_id for placement in layout.layout.images} == {"img_1"}
    assert {caption.image_id for caption in layout.content.captions} == {"img_1"}


def test_generator_replaces_decorations_with_approved_asset_ids():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "tape_charcoal_12",
            "x": 60,
            "y": 180,
            "width": 220,
            "height": 54,
            "rotation": -8,
        },
        {
            "assetId": "missing_asset",
            "x": 720,
            "y": 120,
            "width": 120,
            "height": 120,
            "rotation": 8,
        },
    ]
    request = generation_request(assets=load_assets())
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(request)

    approved_ids = {asset.id for asset in get_approved_assets()}
    assert layout.layout.decorations
    assert all(decoration.asset_id in approved_ids for decoration in layout.layout.decorations)


def test_generator_replaces_unknown_decoration_with_approved_asset_from_same_category():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "tape_missing_99",
            "x": 60,
            "y": 180,
            "width": 220,
            "height": 54,
            "rotation": -8,
        }
    ]
    assets = [
        asset_item("sticker_approved", "sticker"),
        asset_item("tape_approved", "tape"),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    assert layout.layout.decorations[0].asset_id == "tape_approved"


def test_generator_snaps_tape_to_photo_edge():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "tape_warm_grid_01",
            "x": 760,
            "y": 980,
            "width": 320,
            "height": 120,
            "rotation": 28,
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    image = layout.layout.images[0]
    tape = layout.layout.decorations[0]
    assert tape.asset_id == "tape_warm_grid_01"
    assert tape.width <= 260
    assert tape.height <= 70
    assert image.x - tape.width <= tape.x <= image.x + image.width
    assert image.y - tape.height <= tape.y <= image.y + image.height
    assert -12 <= tape.rotation <= 12


def test_generator_moves_stickers_away_from_photo_center():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "sticker_sun_01",
            "x": 220,
            "y": 300,
            "width": 180,
            "height": 180,
            "rotation": 0,
        },
        {
            "assetId": "sticker_cloud_02",
            "x": 760,
            "y": 240,
            "width": 120,
            "height": 90,
            "rotation": 0,
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    assert {decoration.asset_id for decoration in layout.layout.decorations} == {"sticker_sun_01", "sticker_cloud_02"}
    image_dicts = [image.model_dump(by_alias=True) for image in layout.layout.images]
    for decoration in layout.layout.decorations:
        assert not overlaps_photo_safe_area(decoration.model_dump(by_alias=True), image_dicts)


def test_generator_limits_decoration_density():
    payload = valid_model_json()
    decoration_asset_ids = [
        "paper_note_cream_01",
        "paper_note_blush_02",
        "paper_note_sage_03",
        "paper_note_sky_04",
        "texture_dots_01",
        "texture_grid_02",
        "texture_wave_03",
        "tape_warm_grid_01",
        "tape_warm_stripe_02",
        "tape_sage_dash_03",
        "tape_blush_dot_04",
        "tape_sunbeam_05",
        "tape_coffee_06",
        "tape_mist_07",
        "tape_olive_08",
        "tape_rose_line_09",
        "sticker_cloud_02",
        "sticker_heart_03",
        "sticker_leaf_05",
        "sticker_coffee_06",
        "sticker_camera_07",
        "sticker_star_08",
        "sticker_moon_09",
        "sticker_wave_10",
        "sticker_birthday_11",
        "sticker_spark_12",
        "texture_scribble_04",
    ]
    payload["layout"]["decorations"] = [
        {
            "assetId": asset_id,
            "x": 720 + index * 4,
            "y": 160 + index * 18,
            "width": 140,
            "height": 80,
            "rotation": 0,
        }
        for index, asset_id in enumerate(decoration_asset_ids)
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    asset_by_id = {asset.id: asset for asset in load_assets()}
    category_counts = Counter(asset_by_id[decoration.asset_id].category for decoration in layout.layout.decorations)
    assert len(layout.layout.decorations) == 22
    assert category_counts == {"paper": 4, "texture": 2, "tape": 8, "sticker": 8}


def test_generator_places_each_body_block_away_from_photos():
    payload = valid_model_json()
    payload["content"]["body"] = [
        "早餐和咖啡是一组，颜色很暖。",
        "路上的照片放在一起，像慢慢散步。",
        "最后的夜色收尾，适合写一点柔软的话。",
    ]
    payload["layout"]["images"] = [
        {"imageId": "img_1", "x": 80, "y": 220, "width": 420, "height": 320, "rotation": 0},
        {"imageId": "img_2", "x": 120, "y": 260, "width": 420, "height": 320, "rotation": 0},
        {"imageId": "img_3", "x": 160, "y": 300, "width": 420, "height": 320, "rotation": 0},
    ]
    payload["layout"]["texts"] = [
        {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
        {"role": "body", "x": 100, "y": 260, "width": 760, "fontSize": 30},
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    body_texts = [text for text in layout.layout.texts if text.role == "body"]
    assert len(body_texts) == 3
    assert [text.y for text in body_texts] == sorted(text.y for text in body_texts)
    for index, text in enumerate(body_texts):
        text_rect = (text.x, text.y, text.width, estimated_paragraph_height(layout.content.body[index], text.font_size, text.width))
        assert all(not overlaps(text_rect, (image.x, image.y, image.width, image.height)) for image in layout.layout.images)
    section_texts = [text for section in layout.layout.sections for text in section.texts if text.role == "body"]
    last_section_text = max(section_texts, key=lambda text: text.y)
    assert layout.canvas.height >= last_section_text.y + estimated_paragraph_height(
        layout.content.sections[-1].body, last_section_text.font_size, last_section_text.width
    )


def test_generator_adds_missing_image_placements_for_long_collage():
    payload = valid_model_json()
    payload["content"]["body"] = ["第一组照片轻轻展开。", "第二组照片留出呼吸感。"]
    payload["layout"]["images"] = [
        {"imageId": "img_1", "x": 80, "y": 220, "width": 420, "height": 320, "rotation": 0}
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert {image.image_id for image in layout.layout.images} == {"img_1", "img_2", "img_3"}
    assert layout.canvas.height > 1600


def test_generator_builds_sections_for_long_collage():
    payload = valid_model_json()
    payload["content"]["body"] = ["第一组照片轻轻展开。", "第二组照片留出呼吸感。"]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert len(layout.content.sections) == 2
    assert [section.id for section in layout.content.sections] == ["section_1", "section_2"]
    assert [image_id for section in layout.content.sections for image_id in section.image_ids] == ["img_1", "img_2", "img_3"]
    assert [section.section_id for section in layout.layout.sections] == ["section_1", "section_2"]
    assert all(section.variant for section in layout.layout.sections)
    assert all(section.height > 0 for section in layout.layout.sections)


def test_generator_rebuilds_section_pixel_layout_from_templates():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "咖啡和散步",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "咖啡还热着，路边的光也很好，适合把这些片段收成一页。",
            "mood": ["温柔"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "photo_wall",
            "y": 180,
            "height": 520,
            "images": [
                {"imageId": "img_1", "x": 20, "y": 200, "width": 920, "height": 120, "rotation": 0},
                {"imageId": "img_2", "x": 20, "y": 230, "width": 920, "height": 120, "rotation": 0},
                {"imageId": "img_3", "x": 20, "y": 260, "width": 920, "height": 120, "rotation": 0},
            ],
            "texts": [{"role": "body", "x": 20, "y": 250, "width": 920, "fontSize": 48}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    section = layout.layout.sections[0]
    assert section.variant == "photo_wall"
    assert [image.x for image in section.images] == [92, 622, 622]
    assert [image.width for image in section.images] == [430, 276, 276]
    body_text = section.texts[0]
    assert body_text.x == 112
    assert body_text.width == 820
    assert body_text.y > max(image.y + image.height for image in section.images)


def test_generator_ignores_single_photo_variant_for_multi_photo_section():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "咖啡和散步",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "咖啡还热着，路边的光也很好，适合把这些片段收成一页。",
            "mood": ["温柔"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 180,
            "height": 520,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    section = layout.layout.sections[0]
    assert section.variant != "hero_note"
    assert [image.image_id for image in section.images] == ["img_1", "img_2", "img_3"]


def test_generator_ignores_two_photo_variant_for_three_photo_section():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "咖啡和散步",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "咖啡还热着，路边的光也很好，适合把这些片段收成一页。",
            "mood": ["温柔"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "ticket_memo",
            "y": 180,
            "height": 520,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    section = layout.layout.sections[0]
    assert section.variant != "ticket_memo"
    assert [image.image_id for image in section.images] == ["img_1", "img_2", "img_3"]


def test_generator_adds_template_decorations_to_sections_without_model_decorations():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "咖啡和散步",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "咖啡还热着，路边的光也很好，适合把这些片段收成一页。",
            "mood": ["温柔"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "photo_wall",
            "y": 180,
            "height": 520,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("sticker_leaf_05", "sticker"),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images(), assets=assets))

    section = layout.layout.sections[0]
    decoration_ids = {decoration.asset_id for decoration in section.decorations}
    assert decoration_ids == {"paper_note_cream_01", "tape_warm_grid_01", "sticker_leaf_05"}
    paper = next(decoration for decoration in section.decorations if decoration.asset_id == "paper_note_cream_01")
    body_text = section.texts[0]
    assert paper.x <= body_text.x <= paper.x + paper.width
    assert paper.y <= body_text.y <= paper.y + paper.height


def test_generator_adds_limited_background_textures_to_template_sections():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []},
        {"id": "section_2", "title": "第二段", "imageIds": ["img_2"], "body": "第二段正文。", "mood": []},
        {"id": "section_3", "title": "第三段", "imageIds": ["img_3"], "body": "第三段正文。", "mood": []},
    ]
    payload["layout"]["sections"] = [
        {"sectionId": "section_1", "variant": "hero_note", "y": 220, "height": 720, "images": [], "texts": [], "decorations": []},
        {"sectionId": "section_2", "variant": "hero_note", "y": 980, "height": 720, "images": [], "texts": [], "decorations": []},
        {"sectionId": "section_3", "variant": "hero_note", "y": 1740, "height": 720, "images": [], "texts": [], "decorations": []},
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("sticker_leaf_05", "sticker"),
        asset_item("texture_receipt_flecks_09", "texture"),
        asset_item("texture_warm_stitches_10", "texture"),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images(), assets=assets))

    texture_decorations = [
        decoration
        for section in layout.layout.sections
        for decoration in section.decorations
        if decoration.asset_id.startswith("texture_")
    ]
    assert [decoration.asset_id for decoration in texture_decorations] == [
        "texture_receipt_flecks_09",
        "texture_warm_stitches_10",
    ]
    assert all(decoration.width >= 500 and decoration.height >= 300 for decoration in texture_decorations)


def test_generator_expands_template_paper_to_actual_body_height():
    payload = valid_model_json()
    long_body = "这是一段很长的正文，" * 30
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "长正文",
            "imageIds": ["img_1"],
            "body": long_body,
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 520,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    payload["layout"]["decorations"] = []
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=[asset_item("paper_note_cream_01", "paper")]))

    section = layout.layout.sections[0]
    paper = next(decoration for decoration in section.decorations if decoration.asset_id == "paper_note_cream_01")
    body_text = section.texts[0]
    text_bottom = body_text.y + estimated_paragraph_height(
        layout.content.sections[0].body,
        body_text.font_size,
        body_text.width,
    )
    assert paper.y <= body_text.y
    assert paper.y + paper.height >= text_bottom + 28


def test_generator_uses_section_theme_tags_for_template_decorations():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["放松"],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "窗边咖啡",
            "imageIds": ["img_1"],
            "body": "坐在咖啡店里，桌上有小票和一杯咖啡。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("paper_label_coffee_06", "paper", tags=["coffee", "title", "warm"]),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("tape_coffee_06", "tape", tags=["coffee", "warm", "daily"]),
        asset_item("sticker_leaf_05", "sticker", tags=["nature", "travel"]),
        asset_item("sticker_coffee_06", "sticker", tags=["coffee", "daily", "warm"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert {"paper_label_coffee_06", "tape_coffee_06", "sticker_coffee_06"}.issubset(decoration_ids)


def test_generator_uses_ticket_and_coffee_layers_for_cafe_receipt_scene():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["放松"],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "窗边咖啡",
            "imageIds": ["img_1"],
            "body": "坐在咖啡店里，桌上有小票和一杯咖啡。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("paper_receipt_blue_13", "paper", tags=["travel", "memory", "ticket"]),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("tape_coffee_06", "tape", tags=["coffee", "warm", "daily"]),
        asset_item("sticker_coffee_06", "sticker", tags=["coffee", "daily", "warm"]),
        asset_item("sticker_ticket_stub_24", "sticker", tags=["ticket", "travel", "memory"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert {"paper_receipt_blue_13", "tape_coffee_06", "sticker_ticket_stub_24", "sticker_coffee_06"}.issubset(decoration_ids)


def test_generator_uses_date_stamp_for_calendar_journal_scene():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "日期章和日历小记",
            "scene": "手账页",
            "subjects": ["日期章", "日历"],
            "mood": ["安静"],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "六月九日",
            "imageIds": ["img_1"],
            "body": "把日期章盖在这一页，旁边写了今天的日历小记。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_grid_14", "paper", tags=["daily", "collage", "note"]),
        asset_item("tape_linen_stitch_13", "tape", tags=["daily", "warm", "collage"]),
        asset_item("sticker_postage_stamp_29", "sticker", tags=["stamp", "travel", "memory"]),
        asset_item("sticker_date_stamp_35", "sticker", tags=["date", "stamp", "memory"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert "sticker_date_stamp_35" in decoration_ids


@pytest.mark.parametrize(
    ("summary", "scene", "subjects", "section_title", "section_body", "expected_sticker"),
    [
        (
            "桌面上的相片和照片角",
            "手账页",
            ["照片", "相册"],
            "照片拼贴",
            "把几张拍立得和相册小角贴在一起。",
            "sticker_photo_corner_21",
        ),
        (
            "展览门票和票根",
            "展览",
            ["票根"],
            "展览票根",
            "票根和小卡片都夹在这一页。",
            "sticker_ticket_stub_24",
        ),
        (
            "便签纸和手写记录",
            "桌面",
            ["便签"],
            "今日便签",
            "纸条上写了今天的几件小事。",
            "sticker_paperclip_note_26",
        ),
        (
            "照片旁边有邮票和胶片",
            "手账桌面",
            ["胶片", "邮票"],
            "冲印相片",
            "胶片边和旧邮票放在照片旁边。",
            "sticker_film_strip_30",
        ),
        (
            "信封和标签",
            "桌面",
            ["信封", "封蜡", "标签"],
            "写给今天",
            "信封、封蜡和牛皮纸标签压在便签下面。",
            "sticker_tiny_envelope_33",
        ),
        (
            "公交车票和路线",
            "公交站",
            ["公交车票"],
            "通勤车票",
            "公交车票夹在照片旁边，记一下今天的路线。",
            "paper_bus_ticket_16",
        ),
        (
            "钢笔、笔尖和便签",
            "桌面",
            ["钢笔"],
            "钢笔旁边",
            "钢笔和笔尖压着便签，旁边有一点墨水痕迹。",
            "sticker_fountain_pen_36",
        ),
        (
            "压叶和植物标本",
            "桌面",
            ["压叶"],
            "压叶",
            "干花和压叶像植物标本一样放在纸边。",
            "sticker_pressed_leaf_38",
        ),
        (
            "清单便签和勾选标记",
            "桌面",
            ["清单"],
            "待办清单",
            "便签上列了今天要做的几件事，还打了两个勾。",
            "paper_checklist_15",
        ),
        (
            "照片角和相片",
            "手账页",
            ["照片角"],
            "照片边角",
            "撕角照片角压住了这张相片。",
            "sticker_torn_photo_corner_37",
        ),
        (
            "影院电影票和票根",
            "电影院",
            ["电影票"],
            "电影散场",
            "电影票和爆米花小票还夹在这一页。",
            "paper_movie_ticket_17",
        ),
        (
            "购物小票和纸袋",
            "店里",
            ["小票", "纸袋"],
            "买到喜欢的",
            "购物小票、纸袋和收据放在照片旁边。",
            "paper_shopping_receipt_18",
        ),
        (
            "雨伞和雨滴",
            "街边",
            ["雨伞"],
            "雨天路上",
            "雨伞上还有雨滴，回来的路有点安静。",
            "sticker_umbrella_39",
        ),
        (
            "夜晚的台灯和窗",
            "房间",
            ["台灯"],
            "夜里写完",
            "窗边小灯亮着，夜晚的桌面很安静。",
            "sticker_window_lamp_40",
        ),
        (
            "猫和爪印",
            "家里",
            ["猫"],
            "猫趴着",
            "小猫趴在毯子上，爪印留在旁边。",
            "sticker_sleeping_cat_41",
        ),
        (
            "生日蛋糕和蜡烛",
            "餐桌",
            ["蛋糕", "蜡烛"],
            "生日蛋糕",
            "蛋糕、蜡烛和礼物都摆在桌上。",
            "sticker_birthday_cake_42",
        ),
        (
            "摊开的书和书签",
            "书桌",
            ["书", "书签"],
            "读到这里",
            "书页摊开，旁边夹着书签和几行笔记。",
            "sticker_bookmark_44",
        ),
        (
            "餐桌上的盘子和菜单",
            "餐桌",
            ["盘子", "菜单"],
            "晚饭桌上",
            "餐桌上有盘子、面包和一张菜单卡。",
            "sticker_table_plate_45",
        ),
        (
            "海边浪花和贝壳",
            "海边",
            ["贝壳", "海浪"],
            "海边这段",
            "海边的浪和贝壳都放进这一页。",
            "sticker_shell_46",
        ),
        (
            "公交车和站牌",
            "公交站",
            ["公交车", "站牌"],
            "早上通勤",
            "公交车和站牌在路边，今天的路线也记一下。",
            "sticker_bus_stop_47",
        ),
        (
            "小狗和牵引绳",
            "家里",
            ["狗"],
            "狗趴在地毯上",
            "小狗睡着了，旁边还放着牵引绳。",
            "sticker_sleeping_dog_48",
        ),
        (
            "窗边盆栽和绿植",
            "房间",
            ["盆栽", "绿植"],
            "窗边绿植",
            "盆栽和叶子靠在窗边，光落在桌面上。",
            "sticker_houseplant_49",
        ),
    ],
)
def test_generator_uses_scrapbook_recipe_stickers_for_template_decorations(
    summary,
    scene,
    subjects,
    section_title,
    section_body,
    expected_sticker,
):
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": summary,
            "scene": scene,
            "subjects": subjects,
            "mood": [],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": section_title,
            "imageIds": ["img_1"],
            "body": section_body,
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("sticker_leaf_05", "sticker", tags=["nature", "travel"]),
        asset_item("sticker_photo_corner_21", "sticker", tags=["photo", "memory", "collage"]),
        asset_item("sticker_ticket_stub_24", "sticker", tags=["ticket", "travel", "memory"]),
        asset_item("sticker_paperclip_note_26", "sticker", tags=["note", "daily", "collage"]),
        asset_item("sticker_postage_stamp_29", "sticker", tags=["stamp", "travel", "memory"]),
        asset_item("sticker_film_strip_30", "sticker", tags=["film", "photo", "memory"]),
        asset_item("sticker_wax_seal_31", "sticker", tags=["seal", "letter", "memory"]),
        asset_item("sticker_kraft_tag_32", "sticker", tags=["tag", "label", "collage"]),
        asset_item("sticker_tiny_envelope_33", "sticker", tags=["letter", "note", "memory"]),
        asset_item("sticker_binder_clip_34", "sticker", tags=["clip", "note", "collage"]),
        asset_item("paper_checklist_15", "paper", tags=["checklist", "note", "daily"]),
        asset_item("paper_bus_ticket_16", "paper", tags=["bus", "ticket", "travel"]),
        asset_item("sticker_fountain_pen_36", "sticker", tags=["pen", "hand", "note"]),
        asset_item("sticker_torn_photo_corner_37", "sticker", tags=["corner", "photo", "collage"]),
        asset_item("sticker_pressed_leaf_38", "sticker", tags=["pressed", "nature", "calm"]),
        asset_item("paper_movie_ticket_17", "paper", tags=["movie", "ticket", "night"]),
        asset_item("paper_shopping_receipt_18", "paper", tags=["shopping", "receipt", "daily"]),
        asset_item("sticker_umbrella_39", "sticker", tags=["umbrella", "rainy", "weather"]),
        asset_item("sticker_window_lamp_40", "sticker", tags=["lamp", "night", "calm"]),
        asset_item("sticker_sleeping_cat_41", "sticker", tags=["cat", "pet", "home"]),
        asset_item("sticker_birthday_cake_42", "sticker", tags=["cake", "birthday", "party"]),
        asset_item("sticker_bookmark_44", "sticker", tags=["book", "quiet", "note"]),
        asset_item("sticker_table_plate_45", "sticker", tags=["food", "table", "warm"]),
        asset_item("sticker_shell_46", "sticker", tags=["sea", "shell", "travel"]),
        asset_item("sticker_bus_stop_47", "sticker", tags=["commute", "bus", "travel"]),
        asset_item("sticker_sleeping_dog_48", "sticker", tags=["dog", "pet", "home"]),
        asset_item("sticker_houseplant_49", "sticker", tags=["plant", "home", "nature"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert expected_sticker in decoration_ids


def test_generator_places_photo_corner_recipe_sticker_on_photo_corner():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "桌面上的相片和照片角",
            "scene": "手账页",
            "subjects": ["照片", "相册"],
            "mood": [],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "照片拼贴",
            "imageIds": ["img_1"],
            "body": "把几张拍立得和相册小角贴在一起。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_note_cream_01", "paper"),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("sticker_photo_corner_21", "sticker", tags=["photo", "memory", "collage"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    section = layout.layout.sections[0]
    image = section.images[0]
    corner = next(decoration for decoration in section.decorations if decoration.asset_id == "sticker_photo_corner_21")
    assert corner.x < image.x
    assert corner.y < image.y
    assert corner.x + corner.width > image.x
    assert corner.y + corner.height > image.y
    assert not overlaps_photo_safe_area(corner.model_dump(by_alias=True), [image.model_dump(by_alias=True)])


def test_generator_avoids_stamp_paper_as_section_body_backing():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "桌面上的相片和照片角",
            "scene": "手账页",
            "subjects": ["照片", "相册"],
            "mood": [],
        }
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "照片拼贴",
            "imageIds": ["img_1"],
            "body": "把几张拍立得和相册小角贴在一起。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["decorations"] = []
    assets = [
        asset_item("paper_stamp_10", "paper", tags=["travel", "memory", "collage"]),
        asset_item("paper_receipt_blue_13", "paper", tags=["travel", "memory", "ticket"]),
        asset_item("paper_note_grid_14", "paper", tags=["daily", "collage", "note"]),
        asset_item("tape_warm_grid_01", "tape"),
        asset_item("sticker_photo_corner_21", "sticker", tags=["photo", "memory", "collage"]),
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=assets))

    paper = next(decoration for decoration in layout.layout.sections[0].decorations if decoration.asset_id.startswith("paper_"))
    assert paper.asset_id == "paper_receipt_blue_13"


def test_generator_repositions_model_section_decorations_around_template_content():
    payload = valid_model_json()
    payload["canvas"]["height"] = 3600
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "蓝色散步",
            "imageIds": ["img_1"],
            "body": "今天散步走到一片蓝蓝的光里，两个小朋友牵着手站在那里。",
            "mood": ["安静"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 2600,
            "images": [],
            "texts": [],
            "decorations": [
                {"assetId": "paper_note_cream_01", "x": 118, "y": 1382, "width": 850, "height": 1110, "rotation": 1},
                {"assetId": "tape_warm_grid_01", "x": 112, "y": 1266, "width": 220, "height": 54, "rotation": 8},
            ],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=[asset_item("paper_note_cream_01", "paper"), asset_item("tape_warm_grid_01", "tape")]))

    section = layout.layout.sections[0]
    paper = next(decoration for decoration in section.decorations if decoration.asset_id == "paper_note_cream_01")
    body_text = section.texts[0]
    assert paper.y <= body_text.y <= paper.y + paper.height
    assert paper.height < 300
    assert section.height < 1100
    assert layout.canvas.height < 1300


def test_generator_trims_excess_canvas_height_to_content_bottom():
    payload = valid_model_json()
    payload["canvas"]["height"] = 3200
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.canvas.height < 1800
    assert layout.canvas.height >= rendered_content_bottom(layout) + 80


def test_generator_clamps_unstable_text_font_sizes():
    payload = valid_model_json()
    payload["layout"]["texts"] = [
        {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 160},
        {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 8},
    ]
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []}
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 620,
            "images": [],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 8}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert 44 <= layout.layout.texts[0].font_size <= 72
    assert 24 <= layout.layout.texts[1].font_size <= 38
    assert 24 <= layout.layout.sections[0].texts[0].font_size <= 38


def test_generator_trims_excess_section_height_to_section_content_bottom():
    payload = valid_model_json()
    payload["canvas"]["height"] = 3600
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "慢慢坐一会儿",
            "imageIds": ["img_1"],
            "body": "咖啡还热着，下午也慢慢亮着。",
            "mood": ["安静"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 2600,
            "images": [{"imageId": "img_1", "x": 92, "y": 280, "width": 560, "height": 420, "rotation": -2}],
            "texts": [{"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    section = layout.layout.sections[0]
    body_text = section.texts[0]
    text_bottom = body_text.y + estimated_paragraph_height(layout.content.sections[0].body, body_text.font_size, body_text.width)
    assert section.y + section.height >= text_bottom
    assert section.height < 900
    assert layout.canvas.height < 1800


def test_generator_section_height_uses_actual_body_text_height():
    payload = valid_model_json()
    long_body = "这是一段很长的正文，" * 30
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "长正文",
            "imageIds": ["img_1"],
            "body": long_body,
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "ticket_memo",
            "y": 220,
            "height": 520,
            "images": [],
            "texts": [],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    section = layout.layout.sections[0]
    body_text = section.texts[0]
    text_bottom = body_text.y + estimated_paragraph_height(
        layout.content.sections[0].body,
        body_text.font_size,
        body_text.width,
    )
    assert section.y + section.height >= text_bottom


def test_generator_reflows_overlapping_model_sections_with_gap():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {"id": "section_1", "title": "第一段", "imageIds": ["img_1"], "body": "第一段正文。", "mood": []},
        {"id": "section_2", "title": "第二段", "imageIds": ["img_2"], "body": "第二段正文。", "mood": []},
    ]
    payload["layout"]["sections"] = [
        {"sectionId": "section_1", "variant": "hero_note", "y": 220, "height": 720, "images": [], "texts": [], "decorations": []},
        {"sectionId": "section_2", "variant": "hero_note", "y": 300, "height": 720, "images": [], "texts": [], "decorations": []},
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        generation_request(
            images=[
                JournalImageInput(id="img_1", width=640, height=480),
                JournalImageInput(id="img_2", width=900, height=1200),
            ]
        )
    )

    first, second = layout.layout.sections
    assert second.y >= first.y + first.height + 104


def test_generator_ignores_global_decorations_for_section_canvas_height_when_sections_have_decorations():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "慢慢坐一会儿",
            "imageIds": ["img_1"],
            "body": "咖啡还热着，下午也慢慢亮着。",
            "mood": ["安静"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 720,
            "images": [{"imageId": "img_1", "x": 92, "y": 280, "width": 560, "height": 420, "rotation": -2}],
            "texts": [{"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}],
            "decorations": [{"assetId": "paper_note_cream_01", "x": 88, "y": 708, "width": 900, "height": 170, "rotation": 0}],
        }
    ]
    payload["layout"]["decorations"] = [
        {"assetId": "paper_torn_09", "x": 56, "y": 2200, "width": 500, "height": 640, "rotation": 0}
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.canvas.height < 1800


def test_canvas_height_ignores_global_decorations_when_sections_have_decorations():
    layout = valid_model_json()
    layout["content"]["sections"] = [
        {"id": "section_1", "title": "小猫", "imageIds": ["img_1"], "body": "小猫一直在门口绕着我走。", "mood": ["温柔"]}
    ]
    layout["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 220,
            "height": 760,
            "images": [{"imageId": "img_1", "x": 92, "y": 280, "width": 560, "height": 420, "rotation": -2}],
            "texts": [{"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}],
            "decorations": [{"assetId": "paper_note_cream_01", "x": 88, "y": 708, "width": 900, "height": 170, "rotation": 0}],
        }
    ]
    layout["layout"]["decorations"] = [
        {"assetId": "paper_torn_09", "x": 56, "y": 2200, "width": 500, "height": 640, "rotation": 0}
    ]

    assert normalize_canvas_height(layout) < 1800


def test_generator_filters_model_sections_to_provided_images():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "custom_section",
            "title": "照片小组",
            "imageIds": ["img_1", "missing_image"],
            "body": "这里是模型给出的章节。",
            "mood": ["日常"],
        }
    ]
    payload["layout"]["sections"] = [
        {
            "sectionId": "custom_section",
            "variant": "hero_note",
            "y": 160,
            "height": 520,
            "images": [
                {"imageId": "img_1", "x": 92, "y": 210, "width": 420, "height": 320, "rotation": -3},
                {"imageId": "missing_image", "x": 520, "y": 210, "width": 420, "height": 320, "rotation": 2},
            ],
            "texts": [{"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.sections[0].id == "custom_section"
    assert layout.content.sections[0].image_ids == ["img_1"]
    assert [image.image_id for image in layout.layout.sections[0].images] == ["img_1"]


def test_generator_splits_non_adjacent_model_sections():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "mixed_section",
            "title": "模型乱分组",
            "imageIds": ["img_1", "img_3"],
            "body": "模型把不相邻的图片放在了一起。",
            "mood": ["日常"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [section.image_ids for section in layout.content.sections] == [["img_1"], ["img_2"], ["img_3"]]


def test_generator_makes_duplicate_section_ids_unique():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "same_section",
            "title": "第一组",
            "imageIds": ["img_1"],
            "body": "第一张照片的正文。",
            "mood": ["日常"],
        },
        {
            "id": "same_section",
            "title": "第二组",
            "imageIds": ["img_2"],
            "body": "第二张照片的正文。",
            "mood": ["日常"],
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        generation_request(
            images=[
                JournalImageInput(id="img_1", width=640, height=480),
                JournalImageInput(id="img_2", width=900, height=1200),
            ]
        )
    )

    content_section_ids = [section.id for section in layout.content.sections]
    layout_section_ids = [section.section_id for section in layout.layout.sections]
    assert content_section_ids == ["same_section", "same_section_2"]
    assert layout_section_ids == content_section_ids
    assert [section.body for section in layout.content.sections] == ["第一张照片的正文。", "第二张照片的正文。"]


def test_generator_rewrites_split_section_body_to_match_section_images():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "mixed_section",
            "title": "模型乱分组",
            "imageIds": ["img_1", "img_3"],
            "body": "窗边咖啡和晚饭都放在这一组。",
            "mood": ["日常"],
        }
    ]
    payload["content"]["imageUnderstanding"] = [
        {"imageId": "img_1", "summary": "窗边咖啡和小票", "scene": "咖啡店", "subjects": ["咖啡", "小票"], "mood": []},
        {"imageId": "img_2", "summary": "回程路上的云", "scene": "街边", "subjects": ["云", "路灯"], "mood": []},
        {"imageId": "img_3", "summary": "晚饭桌上的小碗", "scene": "餐桌", "subjects": ["晚饭", "小碗"], "mood": []},
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [section.body for section in layout.content.sections] == [
        "窗边咖啡和小票。",
        "回程路上的云。",
        "晚饭桌上的小碗。",
    ]


def test_generator_replaces_generic_section_title_with_image_understanding():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "第一段",
            "imageIds": ["img_1"],
            "body": "窗边咖啡和小票。",
            "mood": ["日常"],
        }
    ]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["轻松"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.sections[0].title == "窗边咖啡和小票"


def test_generator_replaces_generic_section_body_with_image_understanding():
    payload = valid_model_json()
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "第一段",
            "imageIds": ["img_1"],
            "body": "这一组照片也想好好留下。",
            "mood": ["日常"],
        }
    ]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["轻松"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.sections[0].body == "窗边咖啡和小票。"


def test_generator_normalizes_image_understanding_to_provided_images():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡",
            "scene": "咖啡店",
            "subjects": ["咖啡", "窗边"],
            "mood": ["轻松"],
        },
        {
            "imageId": "missing_image",
            "summary": "不存在的照片",
            "scene": "未知",
            "subjects": ["未知"],
            "mood": ["未知"],
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [item.image_id for item in layout.content.image_understanding] == ["img_1", "img_2", "img_3"]
    assert layout.content.image_understanding[0].summary == "窗边咖啡"
    assert layout.content.image_understanding[1].summary == "天气很好"


def test_generator_replaces_generic_image_understanding_with_description_phrases():
    payload = valid_model_json()
    payload["content"]["captions"] = []
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "今天的照片",
            "scene": "生活片段",
            "subjects": ["照片说明", "这张照片"],
            "mood": ["日常"],
        },
        {
            "imageId": "img_2",
            "summary": "照片说明",
            "scene": "日常",
            "subjects": ["生活片段"],
            "mood": ["日常"],
        },
        {
            "imageId": "img_3",
            "summary": "这张照片",
            "scene": "",
            "subjects": [],
            "mood": ["日常"],
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步。傍晚喝了咖啡。路口灯亮起来。",
            images=three_images(),
            assets=get_approved_assets(tags=["warm", "daily"]),
        )
    )

    assert [item.summary for item in layout.content.image_understanding] == [
        "周末一起散步",
        "傍晚喝了咖啡",
        "路口灯亮起来",
    ]
    assert [(caption.image_id, caption.text) for caption in layout.content.captions] == [
        ("img_1", "周末一起散步"),
        ("img_2", "傍晚喝了咖啡"),
        ("img_3", "路口灯亮起来"),
    ]


def test_generator_fills_missing_captions_from_image_understanding():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "窗边咖啡"}]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡",
            "scene": "咖啡店",
            "subjects": ["咖啡", "窗边"],
            "mood": ["轻松"],
        },
        {
            "imageId": "img_2",
            "summary": "回程路上的云",
            "scene": "街边",
            "subjects": ["云", "路灯"],
            "mood": ["安静"],
        },
        {
            "imageId": "img_3",
            "summary": "晚饭桌上的小碗",
            "scene": "餐桌",
            "subjects": ["晚饭", "小碗"],
            "mood": ["日常"],
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [(caption.image_id, caption.text) for caption in layout.content.captions] == [
        ("img_1", "窗边咖啡"),
        ("img_2", "回程路上的云"),
        ("img_3", "晚饭桌上的小碗"),
    ]


def test_generator_drops_repeated_generated_captions():
    payload = valid_model_json()
    payload["content"]["captions"] = []
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡",
            "scene": "咖啡店",
            "subjects": ["咖啡", "窗边"],
            "mood": ["轻松"],
        },
        {
            "imageId": "img_2",
            "summary": "窗边咖啡",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["轻松"],
        },
        {
            "imageId": "img_3",
            "summary": "回程路上的云",
            "scene": "街边",
            "subjects": ["云", "路灯"],
            "mood": ["安静"],
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [(caption.image_id, caption.text) for caption in layout.content.captions] == [
        ("img_1", "窗边咖啡"),
        ("img_3", "回程路上的云"),
    ]


def test_generator_replaces_generic_caption_with_image_understanding():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "今天的照片"}]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["轻松"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.captions[0].text == "窗边咖啡和小票"


def test_generator_shortens_generic_caption_replacement_from_understanding():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "今天的照片"}]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "值得被记住的珍贵回忆，咖啡还热着，窗边坐了一会儿。",
            "scene": "咖啡店",
            "subjects": ["咖啡", "窗边"],
            "mood": ["轻松"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.captions[0].text == "咖啡还热着"


def test_generator_uses_subjects_when_understanding_summary_is_numbered_photo_label():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "今天的照片"}]
    payload["content"]["imageUnderstanding"] = [
        {
            "imageId": "img_1",
            "summary": "第 2 张照片",
            "scene": "海边",
            "subjects": ["蓝色遮阳伞", "长椅"],
            "mood": ["轻松"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.captions[0].text == "蓝色遮阳伞、长椅"


def test_generator_replaces_missing_understanding_caption_with_description_phrases():
    payload = valid_model_json()
    payload["content"].pop("captions")
    payload["content"].pop("imageUnderstanding", None)
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步。傍晚喝了咖啡。路口灯亮起来。",
            images=three_images(),
            assets=get_approved_assets(tags=["warm", "daily"]),
        )
    )

    assert [(caption.image_id, caption.text) for caption in layout.content.captions] == [
        ("img_1", "周末一起散步"),
        ("img_2", "傍晚喝了咖啡"),
        ("img_3", "路口灯亮起来"),
    ]


def test_generator_replaces_missing_understanding_caption_from_single_sentence_phrases():
    payload = valid_model_json()
    payload["content"].pop("captions")
    payload["content"].pop("imageUnderstanding", None)
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步，傍晚喝了咖啡，路口灯亮起来。",
            images=three_images(),
            assets=get_approved_assets(tags=["warm", "daily"]),
        )
    )

    assert [(caption.image_id, caption.text) for caption in layout.content.captions] == [
        ("img_1", "周末一起散步"),
        ("img_2", "傍晚喝了咖啡"),
        ("img_3", "路口灯亮起来"),
    ]


def test_generator_normalizes_common_model_field_variants():
    payload = valid_model_json()
    payload["canvas"]["background"] = {"type": "solid", "color": "#fff7ef"}
    payload["content"].pop("body")
    payload["content"].pop("captions")
    payload["content"]["notes"] = ["把今天的轻松小事收好。"]
    payload["content"]["images"] = [{"id": "img_1", "caption": "温柔的一刻"}]
    payload["layout"]["images"][0]["id"] = payload["layout"]["images"][0].pop("imageId")
    payload["layout"]["decorations"][0]["id"] = payload["layout"]["decorations"][0].pop("assetId")
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.canvas.background == "#fff7ef"
    assert layout.content.body == ["把今天的轻松小事收好。"]
    assert layout.content.captions[0].image_id == "img_1"
    assert layout.layout.images[0].image_id == "img_1"
    assert layout.layout.decorations[0].asset_id == "tape_warm_grid_01"


def test_generator_uses_user_description_when_model_body_is_missing():
    payload = valid_model_json()
    payload["content"].pop("body")
    payload["content"].pop("captions")
    payload["layout"]["texts"] = [{"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56}]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.body == ["周末一起散步，天气很好，喝了咖啡。"]
    assert "今天的照片先放在这里" not in " ".join(layout.content.body)


def test_generator_fallback_sections_use_natural_diary_sentences_after_grouping():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="咖啡还热着，窗边坐了一会儿，路口灯亮起来，回程路上的云压得很低。",
            images=[
                JournalImageInput(id=f"img_{index}", width=640, height=480)
                for index in range(1, 7)
            ],
            assets=get_approved_assets(tags=["warm", "daily"]),
        )
    )

    section_bodies = [section.body for section in layout.content.sections]
    assert len(section_bodies) == 2
    assert all("：" not in body and ":" not in body for body in section_bodies)
    assert section_bodies[0] == "咖啡还热着，窗边坐了一会儿。"
    assert section_bodies[1] == "路口灯亮起来，回程路上的云压得很低。"


def test_generator_replaces_generic_multi_photo_section_title_with_story_title():
    payload = valid_model_json()
    payload["content"]["imageUnderstanding"] = [
        {"imageId": "img_1", "summary": "咖啡还热着", "scene": "咖啡店", "subjects": ["咖啡"], "mood": []},
        {"imageId": "img_2", "summary": "窗边坐了一会儿", "scene": "咖啡店", "subjects": ["窗边"], "mood": []},
        {"imageId": "img_3", "summary": "路口灯亮起来", "scene": "街口", "subjects": ["路灯"], "mood": []},
    ]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "第一段",
            "imageIds": ["img_1", "img_2", "img_3"],
            "body": "咖啡还热着，窗边坐了一会儿，后来路口灯亮起来。",
            "mood": ["日常"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert layout.content.sections[0].title == "咖啡、窗边和路灯"


def test_generator_normalizes_ai_style_copy():
    payload = valid_model_json()
    payload["content"]["title"] = "把这些珍贵回忆收藏在治愈的周末手帐里"
    payload["content"]["body"] = ["今天被温柔包裹，也很治愈，充满仪式感。照片里是被阳光放慢的一天，咖啡还热着，窗边坐了一会儿。"]
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "值得被记住的珍贵回忆，咖啡还热着。"}]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "把时光收藏",
            "imageIds": ["img_1"],
            "body": "把时光收藏成珍贵回忆，适合把这些片段收成一页，咖啡还热着。",
            "mood": ["日常"],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    rendered_copy = " ".join(
        [
            layout.content.title,
            *layout.content.body,
            *(caption.text for caption in layout.content.captions),
            *(section.body for section in layout.content.sections),
        ]
    )
    assert "治愈" not in rendered_copy
    assert "仪式感" not in rendered_copy
    assert "被温柔包裹" not in rendered_copy
    assert "被阳光放慢" not in rendered_copy
    assert "把时光收藏" not in rendered_copy
    assert "收成一页" not in rendered_copy
    assert "珍贵回忆" not in rendered_copy
    assert "刚刚好" not in rendered_copy
    assert "咖啡还热着" in rendered_copy


def test_generator_shortens_long_caption_to_one_observation():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "值得被记住的珍贵回忆，咖啡还热着，窗边坐了一会儿。"}]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.content.captions[0].text == "咖啡还热着"


def test_generator_story_planner_ignores_duplicate_model_image_ids():
    payload = valid_model_json()
    payload["content"]["body"] = ["第一组照片。", "第二组照片。"]
    payload["content"]["sections"] = [
        {"id": "a", "title": "A", "imageIds": ["img_1", "img_2"], "body": "第一组照片。", "mood": []},
        {"id": "b", "title": "B", "imageIds": ["img_2", "img_3"], "body": "第二组照片。", "mood": []},
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(images=three_images()))

    assert [image_id for section in layout.content.sections for image_id in section.image_ids] == ["img_1", "img_2", "img_3"]


def test_invalid_model_json_is_converted_to_generation_error():
    generator = JournalGenerator(FakeClient({"canvas": {"width": 1080, "height": 1440}}))

    with pytest.raises(GenerationError):
        generator.generate(generation_request())


def test_generator_returns_fallback_layout_when_model_connection_fails():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(generation_request())

    assert layout.content.title == "周末一起散步"
    assert layout.content.body == ["周末一起散步，天气很好，喝了咖啡。"]
    assert layout.content.captions[0].text == "周末一起散步"
    assert layout.layout.sections


def test_fallback_layout_uses_location_and_mood_context():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步，天气很好，喝了咖啡。",
            journal_date="2026-05-20",
            location="上海",
            mood_tags=["轻松"],
            images=[JournalImageInput(id="img_1", width=640, height=480)],
            assets=load_assets(),
        )
    )

    assert layout.content.title == "上海小记"
    assert layout.theme.mood == ["轻松"]
    assert layout.content.image_understanding[0].mood == ["轻松"]
    assert layout.content.sections[0].mood == ["轻松"]


@pytest.mark.parametrize(
    ("description", "expected_asset_ids"),
    [
        ("今天把冲印照片、胶片和旧邮票夹在这一页。", {"sticker_film_strip_30", "sticker_postage_stamp_29"}),
        (
            "信封、封蜡和牛皮纸标签都贴在便签旁边。",
            {
                "sticker_tiny_envelope_33",
                "sticker_wax_seal_31",
                "sticker_kraft_tag_32",
                "sticker_string_tag_53",
                "sticker_pressed_seal_54",
            },
        ),
        ("今天去看展览，装置作品旁边留着门票和导览图。", {"sticker_gallery_map_50", "sticker_gallery_label_51"}),
    ],
)
def test_fallback_layout_uses_theme_recipe_stickers_when_ai_is_unavailable(description, expected_asset_ids):
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description=description,
            images=[JournalImageInput(id="img_1", width=640, height=480)],
            assets=load_assets(),
        )
    )

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert len(decoration_ids.intersection(expected_asset_ids)) >= 2


def test_fallback_cafe_receipt_scene_does_not_use_exhibition_assets():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="下午坐在咖啡店窗边，杯子旁边压着小票。外面下过雨，桌面那点反光很好看。",
            images=[
                JournalImageInput(id="img_1", width=3024, height=4032),
                JournalImageInput(id="img_2", width=4032, height=3024),
            ],
            assets=load_assets(),
        )
    )

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert {"paper_exhibition_ticket_19", "sticker_gallery_map_50"}.isdisjoint(decoration_ids)
    assert {"tape_coffee_06", "sticker_coffee_06"}.issubset(decoration_ids)
    assert {"paper_label_coffee_06", "paper_cafe_receipt_20"}.intersection(decoration_ids)


def test_fallback_letter_template_uses_letter_materials_when_copy_is_plain():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="这一天想慢慢记住，把照片和几句话放在一起。",
            images=[JournalImageInput(id="img_1", width=900, height=1200)],
            assets=load_assets(),
            template_id="letter_page",
        )
    )

    decoration_ids = {decoration.asset_id for decoration in layout.layout.sections[0].decorations}
    assert len(
        decoration_ids.intersection(
            {
                "sticker_tiny_envelope_33",
                "sticker_wax_seal_31",
                "sticker_kraft_tag_32",
                "sticker_string_tag_53",
                "sticker_pressed_seal_54",
            }
        )
    ) >= 2


@pytest.mark.parametrize(
    ("template_id", "image_count"),
    [
        ("moodboard_stack", 2),
        ("chapter_scroll", 3),
        ("detail_index", 3),
        ("map_journey", 4),
        ("weekly_spread", 6),
        ("day_dashboard", 3),
        ("scrapbook_story", 5),
    ],
)
def test_fallback_template_layouts_do_not_have_high_rule_issues(template_id, image_count):
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="周末一起出门，路上喝了咖啡，也把看到的小细节记下来。",
        images=[
            JournalImageInput(id=f"img_{index}", width=900 if index % 2 else 640, height=1200 if index % 2 else 480)
            for index in range(1, image_count + 1)
        ],
        assets=load_assets(),
        template_id=template_id,
    )

    layout = generator.generate(request)
    high_issues = [issue for issue in check_layout_rules(layout, request) if issue["severity"] == "high"]

    assert high_issues == []


def test_fallback_multisection_theme_decorations_avoid_repeating_asset_ids():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))
    request = JournalGenerationRequest(
        description="今天去看展览，装置作品旁边留着门票和导览图。出来的时候天有点暗，我把展签和票根都收进手账里。",
        images=[
            JournalImageInput(id=f"img_{index}", width=4032 if index % 2 else 3024, height=3024 if index % 2 else 4032)
            for index in range(1, 5)
        ],
        assets=load_assets(),
    )

    layout = generator.generate(request)

    decoration_ids = [
        decoration.asset_id
        for section in layout.layout.sections
        for decoration in section.decorations
    ]
    repeated_decoration_ids = {asset_id for asset_id in decoration_ids if decoration_ids.count(asset_id) > 1}
    issues = check_layout_rules(layout, request)
    assert repeated_decoration_ids == set()
    assert not any(issue["type"] == "decorationVariety" for issue in issues)
    first_section_paper_ids = [
        decoration.asset_id
        for decoration in layout.layout.sections[0].decorations
        if decoration.asset_id.startswith("paper_")
    ]
    second_section_paper_ids = [
        decoration.asset_id
        for decoration in layout.layout.sections[1].decorations
        if decoration.asset_id.startswith("paper_")
    ]
    assert "paper_exhibition_ticket_19" not in first_section_paper_ids
    assert "paper_exhibition_ticket_19" in second_section_paper_ids


def test_sanitize_model_layout_preserves_theme_sticker_combo_on_second_pass():
    request = JournalGenerationRequest(
        description="今天把冲印照片、胶片和旧邮票夹在这一页，旁边还贴了便签。",
        images=[JournalImageInput(id="img_1", width=640, height=480)],
        assets=load_assets(),
        journal_date="2026-06-09",
        location="工作室",
        mood_tags=["安静"],
    )
    first_pass = sanitize_model_layout(build_fallback_layout(request), request)

    second_pass = sanitize_model_layout(first_pass, request)

    decoration_ids = {
        decoration["assetId"]
        for section in second_pass["layout"]["sections"]
        for decoration in section["decorations"]
    }
    assert {"sticker_film_strip_30", "sticker_postage_stamp_29"}.issubset(decoration_ids)


def test_fallback_layout_uses_human_section_note_instead_of_template_phrase():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步，傍晚喝了咖啡，路口的灯亮起来。",
            images=three_images(),
            assets=load_assets(),
        )
    )

    section_body = layout.content.sections[0].body
    assert section_body == "这一组放在一起看，周末一起散步、傍晚喝了咖啡、路口的灯亮起来。"
    assert "：" not in section_body
    assert "这几张先放在一起" not in section_body


def test_fallback_layout_rotates_human_section_note_prefixes():
    generator = JournalGenerator(FailingClient(GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")))

    layout = generator.generate(
        JournalGenerationRequest(
            description="早上整理照片，午后喝了茶，傍晚去了车站，夜里看了电影，回家写了便签，睡前把票根夹好。",
            images=[
                JournalImageInput(id=f"img_{index}", width=640, height=480)
                for index in range(1, 7)
            ],
            assets=load_assets(),
        )
    )

    assert [section.body for section in layout.content.sections] == [
        "这一组放在一起看，早上整理照片、午后喝了茶、傍晚去了车站。",
        "后面几张接着记，夜里看了电影、回家写了便签、睡前把票根夹好。",
    ]


def test_openai_client_requires_api_key_only_when_constructed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(OpenAIConfigurationError):
        OpenAIJournalClient(api_key="")


def test_openai_client_uses_configured_base_url(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    layout = client.generate_layout(generation_request())

    assert client.model == "gpt-5.5"
    assert client.review_model == "gpt-5.4-mini"
    assert layout["content"]["title"] == "慢下来的周末"
    assert captured["url"] == "https://provider.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "gpt-5.5"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["trust_env"] is True


def test_openai_client_retries_without_response_format_for_compatible_provider(monkeypatch):
    captured_payloads = []

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured_payloads.append(kwargs["json"])
        if len(captured_payloads) == 1:
            return httpx.Response(
                400,
                request=request,
                json={"error": {"message": "response_format is not supported"}},
            )
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    layout = client.generate_layout(generation_request())

    assert layout["content"]["title"] == "慢下来的周末"
    assert captured_payloads[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in captured_payloads[1]


def test_generation_prompt_requests_section_structure():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "content.sections" in prompt
    assert "layout.sections" in prompt
    assert "imageUnderstanding" in prompt
    assert "先逐张理解图片" in prompt
    assert "只允许把相邻图片合并成章节" in prompt
    assert "普通章节绑定 1 到 3 张图片" in prompt
    assert "可以按模板容量保留更多相邻图片" in prompt
    assert "hero_note、staggered_collage、timeline_strip、photo_wall、magazine_whitespace、ticket_memo" in prompt
    assert "quiet_story、hero_memory、timeline_trip、pocket_grid、ticket_day、magazine_note、before_after、moodboard_stack、recipe_memo、letter_page、chapter_scroll、field_notes、split_scene、detail_index" in prompt
    assert "templateId" in prompt


@pytest.mark.parametrize(
    ("template_id", "expected_phrases"),
    [
        ("pocket_grid", ("Project Life", "每格是一张照片、标题卡或记录卡", "不要做成普通九宫格相册")),
        ("ticket_day", ("票根备忘", "票据、小票、门票和便签", "停在哪里")),
        ("letter_page", ("写给今天", "像信纸或便笺", "照片是旁证")),
        ("field_notes", ("观察手记", "日期章、笔、便签", "记录具体细节")),
    ],
)
def test_generation_prompt_includes_selected_template_story_guide(template_id, expected_phrases):
    prompt = build_generation_prompt(generation_request(images=three_images(), template_id=template_id))

    assert f'"templateId": "{template_id}"' in prompt
    assert "当前用户选择的模板说明" in prompt
    for phrase in expected_phrases:
        assert phrase in prompt


def test_openai_client_sends_visual_review_request_with_screenshot_and_images(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured.update(kwargs)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_review_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    review = client.review_layout(
        generation_request(images=[JournalImageInput(id="img_1", width=640, height=480, data_url="data:image/webp;base64,photo")]),
        valid_model_json(),
        "data:image/webp;base64,screenshot",
        [{"type": "readability", "severity": "high", "description": "文字遮挡图片"}],
    )

    content = captured["json"]["messages"][0]["content"]
    assert captured["json"]["model"] == "gpt-5.4-mini"
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/webp;base64,screenshot"}}
    assert content[2] == {"type": "image_url", "image_url": {"url": "data:image/webp;base64,photo"}}
    assert review["score"] == 78


def test_openai_client_sends_targeted_revision_request(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured.update(kwargs)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    layout = client.revise_layout(
        generation_request(images=[JournalImageInput(id="img_1", width=640, height=480, data_url="data:image/webp;base64,photo")]),
        valid_model_json(),
        "data:image/webp;base64,screenshot",
        valid_review_json(),
        revision_round=2,
        best_score=84,
    )

    content = captured["json"]["messages"][0]["content"]
    assert captured["json"]["model"] == "gpt-5.5"
    assert "第 2/3 轮修订" in content[0]["text"]
    assert "当前最佳得分：84" in content[0]["text"]
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/webp;base64,screenshot"}}
    assert layout["content"]["title"] == "慢下来的周末"


def test_openai_client_sends_image_content_when_available(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured.update(kwargs)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    client.generate_layout(generation_request(images=[JournalImageInput(id="img_1", width=640, height=480, data_url="data:image/webp;base64,abc")]))

    content = captured["json"]["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/webp;base64,abc"}}


def test_generation_prompt_requests_natural_diary_text_and_preserves_image_order():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "真实的日记记录" in prompt
    assert "具体短句" in prompt
    assert "不要写成 AI 总结" in prompt
    assert "不要替用户发明没有证据的地点、关系、天气或情绪" in prompt
    assert "图片数组顺序就是用户上传或拖拽排序后的顺序" in prompt
    assert "被阳光放慢" not in prompt
    assert "刚刚好" not in prompt
    assert "收成一页" not in prompt
    assert "窗边坐了一会儿" in prompt
    assert '"order": 1' in prompt
    assert '"order": 2' in prompt
    assert '"order": 3' in prompt


def test_generation_prompt_includes_user_context():
    prompt = build_generation_prompt(
        JournalGenerationRequest(
            description="周末一起散步，天气很好，喝了咖啡。",
            journal_date="2026-05-20",
            location="上海",
            mood_tags=["轻松", "开心"],
            images=three_images(),
            assets=load_assets(),
        )
    )

    assert "用户补充信息" in prompt
    assert "2026-05-20" in prompt
    assert "上海" in prompt
    assert "轻松" in prompt
    assert "开心" in prompt
    assert "如果和照片冲突，以照片和用户描述为准" in prompt


def test_generation_prompt_requests_rich_and_varied_asset_usage():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "12 到 22 个装饰" in prompt
    assert "尽量不要重复 assetId" in prompt
    assert "优先使用内部手绘素材和功能素材" in prompt
    assert "不要为了体现素材库数量强行混入外部图标" in prompt


def test_generation_prompt_treats_stationery_assets_as_functional_layers():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "固定照片" in prompt
    assert "承载文字" in prompt
    assert "分隔层次" in prompt


def test_review_and_revision_prompts_check_asset_richness(monkeypatch):
    captured = []

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured.append(kwargs["json"]["messages"][0]["content"][0]["text"])
        payload = valid_review_json() if len(captured) == 1 else valid_model_json()
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    request = generation_request(images=[JournalImageInput(id="img_1", width=640, height=480, data_url="data:image/webp;base64,photo")])
    client.review_layout(request, valid_model_json(), "data:image/webp;base64,screenshot", [])
    client.revise_layout(request, valid_model_json(), "data:image/webp;base64,screenshot", valid_review_json(), revision_round=1, best_score=70)

    assert "素材丰富度" in captured[0]
    assert "内部手绘和功能素材是否优先" in captured[0]
    assert "视觉焦点" in captured[0]
    assert "章节正文是否对应章节图片" in captured[0]
    assert "装饰是否有功能" in captured[0]
    assert "像电子手账" in captured[0]
    assert "可新增装饰" in captured[1]
    assert "优先替换为更贴合的内部手绘或功能素材" in captured[1]
    assert "只处理视觉评审 issues 中列出的 3 到 6 个主要问题" in captured[1]
    assert "不要改变未被点名的问题区域" in captured[1]


def test_review_and_revision_prompts_include_user_context(monkeypatch):
    captured = []

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured.append(kwargs["json"]["messages"][0]["content"][0]["text"])
        payload = valid_review_json() if len(captured) == 1 else valid_model_json()
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    request = JournalGenerationRequest(
        description="周末一起散步，天气很好，喝了咖啡。",
        journal_date="2026-05-20",
        location="上海",
        mood_tags=["轻松"],
        images=[JournalImageInput(id="img_1", width=640, height=480, data_url="data:image/webp;base64,photo")],
        assets=load_assets(),
    )

    client.review_layout(request, valid_model_json(), "data:image/webp;base64,screenshot", [])
    client.revise_layout(request, valid_model_json(), "data:image/webp;base64,screenshot", valid_review_json(), revision_round=1, best_score=70)

    for prompt in captured:
        assert "用户补充信息" in prompt
        assert "2026-05-20" in prompt
        assert "上海" in prompt
        assert "轻松" in prompt


def test_layout_rules_report_sparse_or_repetitive_decorations_without_requiring_external_assets():
    request = generation_request(
        assets=[
            asset_item("internal_sticker_1", "sticker"),
            asset_item("internal_sticker_2", "sticker"),
            asset_item("external_sticker_1", "sticker", source="https://example.com/icons"),
            asset_item("external_sticker_2", "sticker", source="https://example.com/icons"),
            asset_item("tape_approved", "tape"),
            asset_item("paper_approved", "paper"),
            asset_item("paper_approved_2", "paper"),
            asset_item("paper_approved_3", "paper"),
            asset_item("tape_approved_2", "tape"),
            asset_item("tape_approved_3", "tape"),
            asset_item("texture_approved", "texture"),
            asset_item("texture_approved_2", "texture"),
        ]
    )
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {"assetId": "internal_sticker_1", "x": 720, "y": 160 + index * 60, "width": 120, "height": 80, "rotation": 0}
        for index in range(4)
    ]
    layout = JournalGenerator(FakeClient(payload)).generate(request)

    issues = check_layout_rules(layout, request)

    issue_descriptions = [issue["description"] for issue in issues]
    assert "素材重复使用过多，画面变化不足" in issue_descriptions
    assert "外部素材使用偏少，素材库丰富度没有体现出来" not in issue_descriptions


def test_assets_sent_to_ai_prioritize_internal_handdrawn_assets():
    assets = [
        asset_item("internal_1", "sticker"),
        asset_item("internal_2", "tape"),
        asset_item("external_1", "sticker", source="https://example.com/icons"),
        asset_item("external_2", "sticker", source="https://example.com/icons"),
    ]

    ordered_assets = order_assets_for_ai(assets)

    assert [asset.id for asset in ordered_assets] == ["internal_1", "internal_2", "external_1", "external_2"]


def test_openai_client_converts_connection_errors_to_generation_error(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    with pytest.raises(GenerationError, match="AI 服务连接失败"):
        client.generate_layout(generation_request())


def test_openai_client_retries_transient_connection_errors(monkeypatch):
    attempts = 0

    def fake_post(url, **kwargs):
        nonlocal attempts
        attempts += 1
        request = httpx.Request("POST", url)
        if attempts == 1:
            raise httpx.ConnectError("connection failed", request=request)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    layout = client.generate_layout(generation_request())

    assert attempts == 2
    assert layout["content"]["title"] == "慢下来的周末"


def test_openai_client_retries_transient_status_errors(monkeypatch):
    attempts = 0

    def fake_post(url, **kwargs):
        nonlocal attempts
        attempts += 1
        request = httpx.Request("POST", url)
        if attempts == 1:
            return httpx.Response(503, request=request, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    layout = client.generate_layout(generation_request())

    assert attempts == 2
    assert layout["content"]["title"] == "慢下来的周末"


def test_openai_client_converts_invalid_json_content_to_generation_error(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    with pytest.raises(GenerationError, match="AI 服务返回格式异常"):
        client.generate_layout(generation_request())


def test_openai_client_accepts_json_wrapped_in_code_fence(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": f"```json\n{json.dumps(valid_model_json())}\n```"}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    layout = client.generate_layout(generation_request())

    assert layout["content"]["title"] == "慢下来的周末"


def test_openai_client_converts_status_errors_to_generation_error(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(403, request=request, json={"error": {"message": "blocked"}})

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    with pytest.raises(GenerationError, match="AI 服务返回 403"):
        client.generate_layout(generation_request())


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def generate_layout(self, request):
        self.request = request
        return self.payload


class FailingClient:
    def __init__(self, error):
        self.error = error

    def generate_layout(self, request):
        raise self.error


def generation_request(assets=None, images=None, template_id=None):
    return JournalGenerationRequest(
        description="周末一起散步，天气很好，喝了咖啡。",
        images=images or [JournalImageInput(id="img_1", width=640, height=480)],
        assets=assets or get_approved_assets(tags=["warm", "daily"]),
        template_id=template_id,
    )


def three_images():
    return [
        JournalImageInput(id="img_1", width=640, height=480),
        JournalImageInput(id="img_2", width=900, height=1200),
        JournalImageInput(id="img_3", width=1200, height=900),
    ]


def asset_item(asset_id, category, source="internal", tags=None):
    return AssetItem(
        id=asset_id,
        name=asset_id,
        category=category,
        tags=tags or ["daily"],
        style=["soft-collage"],
        colors=["#fef6e4"],
        file=f"{asset_id}.svg",
        license="internal",
        source=source,
        quality_status="approved",
    )


def estimated_paragraph_height(paragraph, font_size, width):
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    return max((len(paragraph) + characters_per_line - 1) // characters_per_line, 1) * font_size * 1.8


def rendered_content_bottom(layout):
    if layout.layout.sections:
        body_by_section_id = {section.id: section.body for section in layout.content.sections}
        section_bottoms = []
        for section in layout.layout.sections:
            section_bottoms.extend(image.y + image.height for image in section.images)
            section_bottoms.extend(decoration.y + decoration.height for decoration in section.decorations)
            section_bottoms.extend(
                text.y + estimated_paragraph_height(body_by_section_id.get(section.section_id, ""), text.font_size, text.width)
                for text in section.texts
                if text.role == "body"
            )
        return max(section_bottoms, default=0)

    image_bottom = max((image.y + image.height for image in layout.layout.images), default=0)
    text_bottom = max(
        (
            text.y + estimated_paragraph_height(layout.content.body[0], text.font_size, text.width)
            for text in layout.layout.texts
            if text.role == "body"
        ),
        default=0,
    )
    return max(image_bottom, text_bottom)


def overlaps(first, second):
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def valid_model_json():
    return {
        "canvas": {
            "width": 1200,
            "height": 1600,
            "background": "#f8f1e8",
        },
        "theme": {
            "style": "soft-collage",
            "palette": ["#f8f1e8", "#d9a98f", "#8f6b57", "#b9c7aa"],
            "mood": ["warm", "gentle"],
        },
        "content": {
            "title": "慢下来的周末",
            "body": ["照片里是被阳光放慢的一天，咖啡、散步和好天气都刚刚好。"],
            "captions": [{"imageId": "img_1", "text": "午后的咖啡"}],
        },
        "layout": {
            "variant": "collage_a",
            "images": [
                {
                    "imageId": "img_1",
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
                },
                {
                    "role": "body",
                    "x": 92,
                    "y": 1030,
                    "width": 760,
                    "fontSize": 30,
                },
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


def valid_review_json():
    return {
        "score": 78,
        "passed": False,
        "scores": {
            "layout": 19,
            "photoTextMatch": 20,
            "decorationPlacement": 13,
            "readability": 17,
            "coherence": 9,
        },
        "issues": [
            {
                "type": "decorationPlacement",
                "severity": "high",
                "targetIds": ["sticker_camera_07", "img_1"],
                "description": "贴纸覆盖了照片主体区域",
                "instruction": "将贴纸移动到照片外侧空白处",
            }
        ],
        "summary": "保留整体布局，只移动遮挡主体的贴纸。",
    }
