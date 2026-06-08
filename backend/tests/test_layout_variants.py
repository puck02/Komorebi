from app.services.journal_generator import (
    JournalGenerationRequest,
    JournalGenerator,
    JournalImageInput,
)
from app.services.layout_variants import (
    ALLOWED_SECTION_VARIANTS,
    build_section_layout,
    choose_section_variant,
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
