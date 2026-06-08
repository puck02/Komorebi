import json
from collections import Counter

import pytest
import httpx

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem, get_approved_assets, load_assets
from app.services.decoration_placement import overlaps_photo_safe_area
from app.services.journal_generator import (
    GenerationError,
    JournalGenerationRequest,
    JournalGenerator,
    JournalImageInput,
    check_layout_rules,
    normalize_canvas_height,
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

    assert layout.content.sections[0].body == "窗边咖啡和小票，今天就记这一点。"


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
    assert layout.content.image_understanding[1].summary == "第 2 张照片的生活片段"


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


def test_generator_normalizes_ai_style_copy():
    payload = valid_model_json()
    payload["content"]["title"] = "把这些珍贵回忆收藏在治愈的周末手帐里"
    payload["content"]["body"] = ["今天被温柔包裹，也很治愈，充满仪式感。咖啡还热着，窗边坐了一会儿。"]
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "值得被记住的珍贵回忆，咖啡还热着。"}]
    payload["content"]["sections"] = [
        {
            "id": "section_1",
            "title": "把时光收藏",
            "imageIds": ["img_1"],
            "body": "把时光收藏成珍贵回忆，咖啡还热着。",
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
    assert "把时光收藏" not in rendered_copy
    assert "珍贵回忆" not in rendered_copy
    assert "咖啡还热着" in rendered_copy


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


def test_generation_prompt_requests_section_structure():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "content.sections" in prompt
    assert "layout.sections" in prompt
    assert "imageUnderstanding" in prompt
    assert "先逐张理解图片" in prompt
    assert "只允许把相邻图片合并成章节" in prompt
    assert "hero_note、staggered_collage、timeline_strip、photo_wall、magazine_whitespace、ticket_memo" in prompt


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
    assert '"order": 1' in prompt
    assert '"order": 2' in prompt
    assert '"order": 3' in prompt


def test_generation_prompt_requests_rich_and_varied_asset_usage():
    prompt = build_generation_prompt(generation_request(images=three_images()))

    assert "12 到 22 个装饰" in prompt
    assert "尽量不要重复 assetId" in prompt
    assert "外部素材" in prompt


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
    assert "外部素材" in captured[0]
    assert "视觉焦点" in captured[0]
    assert "章节正文是否对应章节图片" in captured[0]
    assert "装饰是否有功能" in captured[0]
    assert "像电子手账" in captured[0]
    assert "可新增装饰" in captured[1]
    assert "只处理视觉评审 issues 中列出的 3 到 6 个主要问题" in captured[1]
    assert "不要改变未被点名的问题区域" in captured[1]


def test_layout_rules_report_sparse_repetitive_or_external_poor_decorations():
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
    assert "外部素材使用偏少，素材库丰富度没有体现出来" in issue_descriptions


def test_assets_sent_to_ai_alternate_between_internal_and_external_sources():
    assets = [
        asset_item("internal_1", "sticker"),
        asset_item("internal_2", "tape"),
        asset_item("external_1", "sticker", source="https://example.com/icons"),
        asset_item("external_2", "sticker", source="https://example.com/icons"),
    ]

    ordered_assets = order_assets_for_ai(assets)

    assert [asset.id for asset in ordered_assets] == ["internal_1", "external_1", "internal_2", "external_2"]


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


def generation_request(assets=None, images=None):
    return JournalGenerationRequest(
        description="周末一起散步，天气很好，喝了咖啡。",
        images=images or [JournalImageInput(id="img_1", width=640, height=480)],
        assets=assets or get_approved_assets(tags=["warm", "daily"]),
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
