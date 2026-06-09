from app.services.journal_generator import (
    JournalGenerationRequest,
    JournalGenerator,
    JournalImageInput,
)
from app.services.layout_rules import text_overlaps_image
from app.services.layout_variants import (
    ALLOWED_SECTION_VARIANTS,
    build_section_layout,
    choose_section_variant,
    estimated_caption_height,
)


def test_choose_section_variant_uses_hero_note_for_single_photo():
    images = [image("img_1", 900, 1200)]
    section = content_section("section_1", ["img_1"], body="今天只想记住这一张照片。")

    variant = choose_section_variant(section, images, [], section_index=0, total_sections=1)

    assert variant == "hero_note"


def test_choose_section_variant_uses_ticket_memo_for_cafe_or_exhibition_scene():
    images = [image("img_1", 900, 1200)]
    section = content_section("section_1", ["img_1"], body="坐在咖啡店里慢慢聊天。")
    understanding = [
        {
            "imageId": "img_1",
            "summary": "窗边咖啡和小票",
            "scene": "咖啡店",
            "subjects": ["咖啡", "小票"],
            "mood": ["放松"],
        }
    ]

    variant = choose_section_variant(section, images, understanding, section_index=0, total_sections=1)

    assert variant == "ticket_memo"


def test_choose_section_variant_uses_staggered_collage_for_two_daily_photos():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200)]
    section = content_section("section_1", ["img_1", "img_2"], body="散步路上拍了两张小照片。")

    variant = choose_section_variant(section, images, [], section_index=0, total_sections=1)

    assert variant == "staggered_collage"


def test_choose_section_variant_uses_timeline_strip_for_three_ordered_travel_photos():
    images = [image("img_1", 640, 480), image("img_2", 640, 480), image("img_3", 640, 480)]
    section = content_section("section_1", ["img_1", "img_2", "img_3"], body="从出门、坐车到抵达，刚好是一段小旅程。")
    understanding = [
        {"imageId": "img_1", "summary": "出门", "scene": "街边", "subjects": ["路"], "mood": []},
        {"imageId": "img_2", "summary": "车窗", "scene": "地铁", "subjects": ["站台"], "mood": []},
        {"imageId": "img_3", "summary": "抵达", "scene": "展览", "subjects": ["展厅"], "mood": []},
    ]

    variant = choose_section_variant(section, images, understanding, section_index=0, total_sections=1)

    assert variant == "timeline_strip"


def test_choose_section_variant_uses_timeline_strip_for_two_transport_photos():
    images = [image("img_1", 640, 480), image("img_2", 640, 480)]
    section = content_section("section_1", ["img_1", "img_2"], body="从地铁站出来，沿途慢慢走。")
    understanding = [
        {"imageId": "img_1", "summary": "地铁站台", "scene": "地铁", "subjects": ["站台"], "mood": []},
        {"imageId": "img_2", "summary": "路边指示牌", "scene": "车站", "subjects": ["路线"], "mood": []},
    ]

    variant = choose_section_variant(section, images, understanding, section_index=0, total_sections=1)

    assert variant == "timeline_strip"


def test_choose_section_variant_uses_photo_wall_for_similar_three_photo_group():
    images = [image("img_1", 640, 480), image("img_2", 640, 480), image("img_3", 640, 480)]
    section = content_section("section_1", ["img_1", "img_2", "img_3"], body="三张都是晚饭桌上的小记录。")
    understanding = [
        {"imageId": "img_1", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物", "餐盘"], "mood": []},
        {"imageId": "img_2", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物", "餐盘"], "mood": []},
        {"imageId": "img_3", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物", "餐盘"], "mood": []},
    ]

    variant = choose_section_variant(section, images, understanding, section_index=0, total_sections=1)

    assert variant == "photo_wall"


def test_choose_section_variant_uses_magazine_whitespace_for_text_forward_single_photo():
    images = [image("img_1", 1200, 900)]
    section = content_section(
        "section_1",
        ["img_1"],
        body="那一刻没有发生什么特别的事，只是光落下来，屋子安静，我突然觉得今天可以慢一点。",
        mood=["安静", "留白"],
    )

    variant = choose_section_variant(section, images, [], section_index=0, total_sections=1)

    assert variant == "magazine_whitespace"


def test_magazine_whitespace_text_stays_below_external_caption():
    images = [image("img_1", 1200, 900)]
    section_data = content_section(
        "section_1",
        ["img_1"],
        body="那一刻没有发生什么特别的事，只是光落下来，屋子安静，我突然觉得今天可以慢一点。",
        mood=["安静", "留白"],
    )

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="magazine_whitespace",
    )

    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    caption_text = next(text for text in layout["texts"] if text["role"] == "caption")
    caption_bottom = caption_text["y"] + caption_text["fontSize"] * 2.4
    assert body_text["y"] >= caption_bottom + 18


def test_build_section_layout_places_images_and_text_inside_section():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200), image("img_3", 1200, 900)]
    section_data = content_section("section_1", ["img_1", "img_2", "img_3"], body="这三张照片放在一起刚好是一段周末。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant=None,
    )

    assert layout["variant"] in ALLOWED_SECTION_VARIANTS
    assert layout["y"] == 220
    assert layout["height"] > 500
    assert [item["imageId"] for item in layout["images"]] == ["img_1", "img_2", "img_3"]
    assert layout["texts"][0]["role"] == "body"
    assert all(0 <= item["x"] <= 1080 for item in [*layout["images"], *layout["texts"]])
    assert all(layout["y"] <= item["y"] <= layout["y"] + layout["height"] for item in [*layout["images"], *layout["texts"]])


def test_build_section_layout_adds_story_section_title_above_body():
    images = [image("img_1", 640, 480)]
    section_data = content_section("section_1", ["img_1"], body="这一张照片想作为当天故事的开头。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="hero_note",
    )

    title_text = next(text for text in layout["texts"] if text["role"] == "title")
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert title_text["y"] < body_text["y"]
    assert title_text["x"] == body_text["x"]
    assert title_text["width"] <= body_text["width"]
    assert 22 <= title_text["fontSize"] <= 30


def test_build_section_layout_places_captions_below_photo_when_clear():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200)]
    section_data = content_section("section_1", ["img_1", "img_2"], body="两张照片各有一个短短的旁注。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="staggered_collage",
    )

    caption_texts = [text for text in layout["texts"] if text["role"] == "caption"]
    assert len(caption_texts) == 2
    assert [caption["y"] for caption in caption_texts] == [
        image_placement["y"] + image_placement["height"] + 10 for image_placement in layout["images"]
    ]
    assert [caption["x"] for caption in caption_texts] == [image_placement["x"] + 28 for image_placement in layout["images"]]
    assert layout["texts"][0]["role"] == "body"
    assert layout["texts"][0]["y"] > max(caption["y"] for caption in caption_texts)


def test_build_section_layout_keeps_caption_on_photo_border_when_below_would_hit_next_photo():
    images = [image("img_1", 640, 480), image("img_2", 640, 480), image("img_3", 640, 480)]
    section_data = content_section("section_1", ["img_1", "img_2", "img_3"], body="三张路上的照片错落放在一起。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="staggered_collage",
    )

    caption_texts = [text for text in layout["texts"] if text["role"] == "caption"]
    assert len(caption_texts) == 3
    first_caption_rect = (
        caption_texts[0]["x"],
        caption_texts[0]["y"],
        caption_texts[0]["width"],
        estimated_caption_height(caption_texts[0]),
    )
    assert caption_texts[0]["y"] < layout["images"][0]["y"] + layout["images"][0]["height"]
    assert not any(
        text_overlaps_image("caption", first_caption_rect, (image["x"], image["y"], image["width"], image["height"]))
        for image in layout["images"][1:]
    )
    assert caption_texts[1]["y"] == layout["images"][1]["y"] + layout["images"][1]["height"] + 10
    assert caption_texts[2]["y"] == layout["images"][2]["y"] + layout["images"][2]["height"] + 10


def test_photo_wall_layout_has_a_clear_primary_photo():
    images = [image("img_1", 640, 480), image("img_2", 640, 480), image("img_3", 640, 480)]
    section_data = content_section("section_1", ["img_1", "img_2", "img_3"], body="三张都是晚饭桌上的小记录。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[
            {"imageId": "img_1", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物"], "mood": []},
            {"imageId": "img_2", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物"], "mood": []},
            {"imageId": "img_3", "summary": "晚餐", "scene": "餐桌", "subjects": ["食物"], "mood": []},
        ],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="photo_wall",
    )

    areas = [item["width"] * item["height"] for item in layout["images"]]
    assert max(areas) / min(areas) >= 1.25


def test_ticket_memo_two_photo_layout_places_text_below_photos():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200)]
    section_data = content_section("section_1", ["img_1", "img_2"], body="坐在咖啡店里，桌上有小票和一杯咖啡。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="ticket_memo",
    )

    image_bottom = max(image["y"] + image["height"] for image in layout["images"])
    text = layout["texts"][0]
    assert text["y"] >= image_bottom + 56
    assert text["x"] == 112
    assert text["width"] == 820
    assert layout["images"][1]["x"] - (layout["images"][0]["x"] + layout["images"][0]["width"]) >= 32


def test_before_after_layout_places_two_photos_side_by_side_with_narrow_note():
    images = [image("img_1", 640, 480), image("img_2", 640, 480)]
    section_data = content_section("section_1", ["img_1", "img_2"], body="开始的时候桌面还有点乱，后来一点点收拾出来。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="before_after",
    )

    assert layout["variant"] == "before_after"
    assert [item["imageId"] for item in layout["images"]] == ["img_1", "img_2"]
    assert layout["images"][0]["x"] < layout["images"][1]["x"]
    assert abs(layout["images"][0]["y"] - layout["images"][1]["y"]) <= 24
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert body_text["y"] > max(item["y"] + item["height"] for item in layout["images"])
    assert body_text["width"] <= 760


def test_moodboard_stack_layout_overlaps_story_fragments_without_becoming_grid():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200), image("img_3", 1200, 900)]
    section_data = content_section("section_1", ["img_1", "img_2", "img_3"], body="这几张没有严格顺序，就是今天几个开心的小碎片。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="moodboard_stack",
    )

    assert layout["variant"] == "moodboard_stack"
    assert len(layout["images"]) == 3
    assert len({item["x"] for item in layout["images"]}) == 3
    assert any(abs(item["rotation"]) >= 3 for item in layout["images"])
    y_positions = [item["y"] for item in layout["images"]]
    assert max(y_positions) - min(y_positions) < 320
    assert len({round(item["y"] / 40) for item in layout["images"]}) >= 3


def test_moodboard_stack_uses_sparse_captions_for_two_overlapping_photos():
    images = [image("img_1", 640, 480), image("img_2", 900, 1200)]
    section_data = content_section("section_1", ["img_1", "img_2"], body="这两张没有严格顺序，就是今天几个开心的小碎片。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=1,
        total_sections=2,
        start_y=220,
        suggested_variant="moodboard_stack",
    )

    assert layout["variant"] == "moodboard_stack"
    assert [text for text in layout["texts"] if text["role"] == "caption"] == []


def test_recipe_memo_layout_uses_compact_photo_and_text_column():
    images = [image("img_1", 900, 1200), image("img_2", 640, 480)]
    section_data = content_section("section_1", ["img_1", "img_2"], body="咖啡、面包和一点甜味，今天的餐桌刚好可以写成小配方。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="recipe_memo",
    )

    assert layout["variant"] == "recipe_memo"
    assert all(item["width"] <= 430 for item in layout["images"])
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert body_text["x"] >= 560
    assert body_text["width"] <= 380
    assert body_text["y"] < max(item["y"] + item["height"] for item in layout["images"])


def test_recipe_memo_layout_keeps_four_photos_in_left_column_without_overlap():
    images = [
        image("img_1", 900, 1200),
        image("img_2", 640, 480),
        image("img_3", 640, 480),
        image("img_4", 640, 480),
    ]
    section_data = content_section("section_1", [item.id for item in images], body="今天的餐桌从咖啡、面包到甜点都想留下。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="recipe_memo",
    )

    assert len(layout["images"]) == 4
    assert all(item["x"] + item["width"] <= 520 for item in layout["images"])
    image_rects = [(item["x"], item["y"], item["width"], item["height"]) for item in layout["images"]]
    for index, rect in enumerate(image_rects):
        assert all(not overlaps(rect, other) for other in image_rects[index + 1 :])


def test_letter_page_layout_prioritizes_wide_writing_area():
    images = [image("img_1", 900, 1200)]
    section_data = content_section("section_1", ["img_1"], body="写给今天：有些细节不一定要很热闹，但我还是想把它们完整留下来。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="letter_page",
    )

    assert layout["variant"] == "letter_page"
    assert layout["images"][0]["width"] <= 360
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert body_text["x"] <= 120
    assert body_text["width"] >= 700
    assert body_text["y"] < layout["images"][0]["y"] + layout["images"][0]["height"]


def test_pocket_grid_layout_uses_even_slots_for_many_images():
    images = [
        image("img_1", 640, 480),
        image("img_2", 640, 480),
        image("img_3", 640, 480),
        image("img_4", 640, 480),
        image("img_5", 640, 480),
        image("img_6", 640, 480),
    ]
    section_data = content_section("section_1", [item.id for item in images], body="一天里的碎片很多，适合像口袋一样一格一格收起来。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="pocket_grid",
    )

    assert layout["variant"] == "pocket_grid"
    assert len(layout["images"]) == 6
    assert len({item["x"] for item in layout["images"]}) == 3
    assert len({item["y"] for item in layout["images"]}) == 2
    assert max(item["width"] for item in layout["images"]) - min(item["width"] for item in layout["images"]) <= 1


def test_timeline_trip_layout_wraps_many_photos_inside_canvas():
    images = [image(f"img_{index}", 640, 480) for index in range(1, 6)]
    section_data = content_section("section_1", [item.id for item in images], body="出发、路上、停留、回程，刚好是一段完整小旅行。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="timeline_trip",
    )

    assert layout["variant"] == "timeline_trip"
    assert len(layout["images"]) == 5
    assert all(0 <= item["x"] <= 1080 and item["x"] + item["width"] <= 1080 for item in layout["images"])
    assert len({item["y"] for item in layout["images"]}) >= 2


def test_chapter_scroll_layout_reads_as_vertical_story():
    images = [image(f"img_{index}", 640, 480) for index in range(1, 6)]
    section_data = content_section("section_1", [item.id for item in images], body="从早到晚有好几段，适合像章节一样往下读。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="chapter_scroll",
    )

    assert layout["variant"] == "chapter_scroll"
    assert [item["imageId"] for item in layout["images"]] == [item.id for item in images]
    assert len({item["x"] for item in layout["images"]}) >= 2
    assert layout["images"][0]["y"] < layout["images"][-1]["y"]
    assert layout["height"] > 1300


def test_field_notes_layout_places_observation_text_beside_specimen_photo():
    images = [image("img_1", 900, 1200), image("img_2", 640, 480), image("img_3", 640, 480)]
    section_data = content_section("section_1", [item.id for item in images], body="窗边的杯子、书页和一点光，都像今天的小观察。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="field_notes",
    )

    assert layout["variant"] == "field_notes"
    assert layout["images"][0]["width"] >= 400
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert body_text["x"] >= 600
    assert body_text["y"] < layout["images"][0]["y"] + layout["images"][0]["height"]


def test_split_scene_layout_separates_two_scene_columns():
    images = [image("img_1", 640, 480), image("img_2", 640, 480), image("img_3", 640, 480), image("img_4", 640, 480)]
    section_data = content_section("section_1", [item.id for item in images], body="上午在室内，下午走到外面，刚好是两个场景。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="split_scene",
    )

    assert layout["variant"] == "split_scene"
    left_column = [item for item in layout["images"] if item["x"] < 540]
    right_column = [item for item in layout["images"] if item["x"] >= 540]
    assert len(left_column) == 2
    assert len(right_column) == 2
    body_text = next(text for text in layout["texts"] if text["role"] == "body")
    assert body_text["y"] > max(item["y"] + item["height"] for item in layout["images"])


def test_detail_index_layout_uses_primary_photo_and_small_detail_strip():
    images = [
        image("img_1", 1200, 900),
        image("img_2", 640, 480),
        image("img_3", 640, 480),
        image("img_4", 640, 480),
    ]
    section_data = content_section("section_1", [item.id for item in images], body="先看整张，再把几个容易忘的细节标出来。")

    layout = build_section_layout(
        section_data,
        request_images=images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="detail_index",
    )

    assert layout["variant"] == "detail_index"
    areas = [item["width"] * item["height"] for item in layout["images"]]
    assert areas[0] == max(areas)
    assert all(item["x"] > layout["images"][0]["x"] + layout["images"][0]["width"] for item in layout["images"][1:])


def test_story_templates_use_stable_content_based_layout_variants():
    first_images = [image(f"img_{index}", 640, 480) for index in range(1, 6)]
    second_images = [image(f"trip_{index}", 640, 480) for index in range(1, 6)]
    first_section = content_section("section_1", [item.id for item in first_images], body="把这些回忆剪贴成一页。")
    second_section = content_section("section_1", [item.id for item in second_images], body="把这些回忆剪贴成一页。")

    first_layout = build_section_layout(
        first_section,
        request_images=first_images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="scrapbook_story",
    )
    repeated_layout = build_section_layout(
        first_section,
        request_images=first_images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="scrapbook_story",
    )
    second_layout = build_section_layout(
        second_section,
        request_images=second_images,
        image_understanding=[],
        section_index=0,
        total_sections=1,
        start_y=220,
        suggested_variant="scrapbook_story",
    )

    first_positions = [(item["x"], item["y"], item["width"], item["rotation"]) for item in first_layout["images"]]
    repeated_positions = [(item["x"], item["y"], item["width"], item["rotation"]) for item in repeated_layout["images"]]
    second_positions = [(item["x"], item["y"], item["width"], item["rotation"]) for item in second_layout["images"]]
    assert first_positions == repeated_positions
    assert first_positions != second_positions


def test_generator_replaces_invalid_section_variant_with_rule_choice():
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
    payload["content"]["sections"] = [content_section("section_1", ["img_1"], body="坐在咖啡店里慢慢聊天。")]
    payload["layout"]["sections"] = [{"sectionId": "section_1", "variant": "long_collage"}]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.layout.sections[0].variant == "ticket_memo"
    assert layout.layout.sections[0].images[0].image_id == "img_1"


def test_generator_expands_canvas_to_fit_section_layout():
    payload = valid_model_json()
    payload["canvas"]["height"] = 1440
    payload["content"]["sections"] = [content_section("section_1", ["img_1"], body="坐在咖啡店里慢慢聊天。")]
    payload["layout"]["sections"] = [
        {
            "sectionId": "section_1",
            "variant": "hero_note",
            "y": 1880,
            "height": 760,
            "images": [{"imageId": "img_1", "x": 150, "y": 1920, "width": 680, "height": 520, "rotation": -2}],
            "texts": [{"role": "body", "x": 112, "y": 2500, "width": 820, "fontSize": 32}],
            "decorations": [],
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    section = layout.layout.sections[0]
    text = section.texts[0]
    text_bottom = text.y + estimated_paragraph_height(payload["content"]["sections"][0]["body"], text.font_size, text.width)
    image_bottom = section.images[0].y + section.images[0].height
    assert layout.canvas.height >= max(image_bottom, text_bottom) + 80


def test_generator_places_fallback_sections_below_title_area():
    payload = valid_model_json()
    payload["content"]["sections"] = [content_section("section_1", ["img_1"], body="坐在咖啡店里慢慢聊天。")]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.layout.sections[0].y >= 250


def test_generator_adds_caption_text_placements_to_sections():
    payload = valid_model_json()
    payload["content"]["captions"] = [{"imageId": "img_1", "text": "午后的咖啡"}]
    payload["content"]["sections"] = [content_section("section_1", ["img_1"], body="坐在咖啡店里慢慢聊天。")]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    section = layout.layout.sections[0]
    caption_texts = [text for text in section.texts if text.role == "caption"]
    assert len(caption_texts) == 1
    assert caption_texts[0].y == section.images[0].y + section.images[0].height + 10


def image(image_id: str, width: int, height: int) -> JournalImageInput:
    return JournalImageInput(id=image_id, width=width, height=height)


def content_section(section_id: str, image_ids: list[str], body: str, mood: list[str] | None = None):
    return {
        "id": section_id,
        "title": "片段",
        "imageIds": image_ids,
        "body": body,
        "mood": mood or ["日常"],
    }


def estimated_paragraph_height(paragraph: str, font_size: float, width: float) -> float:
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max((len(paragraph) + characters_per_line - 1) // characters_per_line, 1)
    return line_count * font_size * 1.8


def overlaps(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def generation_request():
    return JournalGenerationRequest(
        description="周末一起散步，天气很好，喝了咖啡。",
        images=[image("img_1", 640, 480)],
        assets=[],
    )


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def generate_layout(self, request):
        return self.payload


def valid_model_json():
    return {
        "canvas": {"width": 1080, "height": 1440, "background": "#fef6e4"},
        "theme": {"style": "soft-collage", "palette": ["#fef6e4", "#f582ae"], "mood": ["温柔"]},
        "content": {
            "title": "慢下来的周末",
            "body": ["咖啡和阳光是一组，像把早晨轻轻摊开。"],
            "captions": [{"imageId": "img_1", "text": "午后的咖啡"}],
        },
        "layout": {
            "variant": "long_collage",
            "images": [{"imageId": "img_1", "x": 92, "y": 210, "width": 420, "height": 320, "rotation": -3}],
            "texts": [
                {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
                {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32},
            ],
            "decorations": [],
            "sections": [],
        },
    }
