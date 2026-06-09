from math import ceil
from typing import Any

from app.services.journal_templates import ALLOWED_SECTION_VARIANTS

CANVAS_WIDTH = 1080
SECTION_SIDE_PADDING = 92
SECTION_TEXT_WIDTH = 820
SECTION_TEXT_FONT_SIZE = 32
SECTION_TITLE_FONT_SIZE = 26
SECTION_CAPTION_FONT_SIZE = 22
SECTION_CAPTION_SIDE_PADDING = 28
SECTION_CAPTION_BOTTOM_OFFSET = 38
SECTION_CAPTION_BELOW_OFFSET = 10
SECTION_CAPTION_TEXT_GAP = 18
SECTION_CAPTION_BORDER_OFFSET = 64
SECTION_GAP = 104
TEXT_PHOTO_GAP = 56
IMAGE_GAP = 38

TICKET_KEYWORDS = {
    "咖啡",
    "咖啡店",
    "餐厅",
    "餐桌",
    "饭",
    "甜品",
    "展览",
    "展厅",
    "博物馆",
    "票",
    "小票",
    "电影",
    "地铁",
    "车站",
}
TIMELINE_KEYWORDS = {"旅行", "旅程", "出门", "抵达", "路上", "地铁", "车站", "散步", "路线", "沿途"}
STRONG_TIMELINE_KEYWORDS = {"旅行", "旅程", "出门", "抵达", "地铁", "车站", "站台", "路线", "沿途"}
WHITESPACE_KEYWORDS = {"安静", "留白", "慢", "光", "窗边", "独处", "平静"}
MAP_KEYWORDS = {"地图", "坐标", "打卡", "打卡点", "景点", "目的地", "导航"}
WEEKLY_KEYWORDS = {"一周", "周记", "周末", "工作日", "复盘", "习惯", "连续几天"}
DASHBOARD_KEYWORDS = {"日程", "待办", "清单", "计划", "安排", "今日", "事项"}
SCRAPBOOK_KEYWORDS = {"拼贴", "剪贴", "手作", "回忆", "纪念", "相册", "贴纸"}


def choose_section_variant(
    section: dict[str, Any],
    request_images: list[Any],
    image_understanding: list[dict[str, Any]],
    section_index: int,
    total_sections: int,
) -> str:
    section_image_ids = list(section.get("imageIds") or section.get("image_ids") or [])
    section_images = [image for image in request_images if image_id(image) in section_image_ids]
    keyword_text = section_keywords(section, image_understanding)
    image_count = len(section_images)

    if image_count >= 2 and any(keyword in keyword_text for keyword in STRONG_TIMELINE_KEYWORDS):
        if any(keyword in keyword_text for keyword in MAP_KEYWORDS):
            return "map_journey"
        return "timeline_strip"

    if image_count >= 4 and any(keyword in keyword_text for keyword in WEEKLY_KEYWORDS):
        return "weekly_spread"

    if image_count <= 6 and any(keyword in keyword_text for keyword in DASHBOARD_KEYWORDS):
        return "day_dashboard"

    if image_count >= 3 and any(keyword in keyword_text for keyword in SCRAPBOOK_KEYWORDS):
        return "scrapbook_story"

    if image_count <= 2 and any(keyword in keyword_text for keyword in TICKET_KEYWORDS):
        return "ticket_memo"

    if image_count >= 3:
        if has_similar_scenes(section_image_ids, image_understanding):
            return "photo_wall"
        if any(keyword in keyword_text for keyword in TIMELINE_KEYWORDS) or total_sections > 1:
            return "timeline_strip"
        return "staggered_collage"

    if image_count == 2:
        return "staggered_collage"

    if len(str(section.get("body") or "")) >= 44 or any(keyword in keyword_text for keyword in WHITESPACE_KEYWORDS):
        return "magazine_whitespace"
    return "hero_note"


def build_section_layout(
    section: dict[str, Any],
    request_images: list[Any],
    image_understanding: list[dict[str, Any]],
    section_index: int,
    total_sections: int,
    start_y: float,
    suggested_variant: str | None,
) -> dict[str, Any]:
    variant = suggested_variant if suggested_variant in ALLOWED_SECTION_VARIANTS else choose_section_variant(
        section,
        request_images,
        image_understanding,
        section_index,
        total_sections,
    )
    section_image_ids = list(section.get("imageIds") or section.get("image_ids") or [])
    section_images = [image for image in request_images if image_id(image) in section_image_ids]
    image_placements = build_image_placements(variant, section_images, start_y, section_index)
    image_bottom = max((item["y"] + item["height"] for item in image_placements), default=start_y)
    caption_texts = build_caption_placements(variant, image_placements)
    caption_bottom = max(
        (caption["y"] + estimated_caption_height(caption) for caption in caption_texts),
        default=image_bottom,
    )
    text_y = image_bottom + TEXT_PHOTO_GAP
    if caption_texts:
        text_y = max(text_y, caption_bottom + SECTION_CAPTION_TEXT_GAP)
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"} and image_placements:
        caption_floor = caption_bottom + SECTION_CAPTION_TEXT_GAP if caption_texts else start_y
        text_y = max(min(text_y, start_y + 420), caption_floor)
    if variant == "letter_page" and image_placements:
        text_y = start_y + 68
    if variant == "recipe_memo" and image_placements:
        text_y = start_y + 44
    if variant == "field_notes" and image_placements:
        text_y = start_y + 64
    if variant in {"ticket_memo", "ticket_day"} and len(image_placements) >= 2:
        text_y = max(image_bottom + TEXT_PHOTO_GAP, caption_bottom + SECTION_CAPTION_TEXT_GAP)
    if variant in {"moodboard_stack", "chapter_scroll", "detail_index"} and caption_texts:
        text_y = max(text_y, caption_bottom + SECTION_CAPTION_TEXT_GAP + SECTION_TITLE_FONT_SIZE * 2.4)
    text = {
        "role": "body",
        "x": text_x_for_variant(variant, len(image_placements)),
        "y": text_y,
        "width": text_width_for_variant(variant, len(image_placements)),
        "fontSize": SECTION_TEXT_FONT_SIZE,
    }
    title = {
        "role": "title",
        "x": text["x"],
        "y": max(start_y, text["y"] - 44),
        "width": min(text["width"], 680),
        "fontSize": SECTION_TITLE_FONT_SIZE,
    }
    if caption_texts and any(rects_overlap(text_rect(title), text_rect(caption)) for caption in caption_texts):
        title["y"] = caption_bottom + SECTION_CAPTION_TEXT_GAP
        text["y"] = title["y"] + SECTION_TITLE_FONT_SIZE * 2.4 + 12
    body = str(section.get("body") or "")
    text_bottom = text["y"] + estimate_paragraph_height(body, text["fontSize"], text["width"])
    section_bottom = max(image_bottom, caption_bottom, text_bottom) + SECTION_GAP

    return {
        "sectionId": str(section["id"]),
        "variant": variant,
        "y": start_y,
        "height": max(section_bottom - start_y, 1),
        "images": image_placements,
        "texts": [text, title, *caption_texts],
        "decorations": [],
    }


def build_image_placements(variant: str, images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if variant == "quiet_story":
        return build_quiet_story_images(images, start_y, section_index)
    if variant == "hero_memory":
        return build_hero_memory_images(images, start_y, section_index)
    if variant == "timeline_trip":
        return build_timeline_trip_images(images, start_y, section_index)
    if variant == "pocket_grid":
        return build_pocket_grid_images(images, start_y, section_index)
    if variant == "ticket_day":
        return build_ticket_day_images(images, start_y, section_index)
    if variant == "magazine_note":
        return build_magazine_note_images(images, start_y, section_index)
    if variant == "before_after":
        return build_before_after_images(images, start_y, section_index)
    if variant == "moodboard_stack":
        return build_moodboard_stack_images(images, start_y, section_index)
    if variant == "recipe_memo":
        return build_recipe_memo_images(images, start_y, section_index)
    if variant == "letter_page":
        return build_letter_page_images(images, start_y, section_index)
    if variant == "chapter_scroll":
        return build_chapter_scroll_images(images, start_y, section_index)
    if variant == "field_notes":
        return build_field_notes_images(images, start_y, section_index)
    if variant == "split_scene":
        return build_split_scene_images(images, start_y, section_index)
    if variant == "detail_index":
        return build_detail_index_images(images, start_y, section_index)
    if variant == "map_journey":
        return build_map_journey_images(images, start_y, section_index)
    if variant == "weekly_spread":
        return build_weekly_spread_images(images, start_y, section_index)
    if variant == "day_dashboard":
        return build_day_dashboard_images(images, start_y, section_index)
    if variant == "scrapbook_story":
        return build_scrapbook_story_images(images, start_y, section_index)
    if variant == "hero_note":
        return build_hero_note_images(images, start_y, section_index)
    if variant == "magazine_whitespace":
        return build_magazine_whitespace_images(images, start_y, section_index)
    if variant == "timeline_strip":
        return build_timeline_strip_images(images, start_y, section_index)
    if variant == "photo_wall":
        return build_photo_wall_images(images, start_y, section_index)
    if variant == "ticket_memo":
        return build_ticket_memo_images(images, start_y, section_index)
    return build_staggered_collage_images(images, start_y, section_index)


def build_quiet_story_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = [placement(images[0], SECTION_SIDE_PADDING, start_y + 28, 420, section_index, rotation=-1.2)]
    for index, image in enumerate(images[1:3], start=1):
        placements.append(
            placement(
                image,
                330 + (index - 1) * 110,
                start_y + 430 + (index - 1) * 160,
                210,
                section_index + index,
                rotation=[2.5, -2][(index - 1) % 2],
            )
        )
    return placements


def build_hero_memory_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    pattern = layout_pattern_index("hero_memory", images, section_index)
    primary_width = 760 if aspect_ratio(images[0]) >= 1 else 620
    primary_x = (CANVAS_WIDTH - primary_width) / 2
    if pattern == 1:
        primary_x = SECTION_SIDE_PADDING
    elif pattern == 2:
        primary_x = CANVAS_WIDTH - SECTION_SIDE_PADDING - primary_width
    placements = [placement(images[0], primary_x, start_y, primary_width, section_index, rotation=[0, -1.1, 1.1][pattern])]
    primary = placements[0]
    for index, image in enumerate(images[1:3], start=1):
        width = 250
        placements.append(
            placement(
                image,
                SECTION_SIDE_PADDING + (index - 1) * 630,
                primary["y"] + primary["height"] - 130 + (index - 1) * 52,
                width,
                section_index + index,
                rotation=[-4, 3.5][(index - 1) % 2],
            )
        )
    return placements


def build_timeline_trip_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if len(images) <= 3:
        placements = build_timeline_strip_images(images, start_y, section_index)
        if layout_pattern_index("timeline_trip", images, section_index, count=2) == 1:
            return mirror_placements(placements)
        return placements

    placements = []
    pattern = layout_pattern_index("timeline_trip", images, section_index)
    width = [260, 286, 242][pattern]
    columns = 3
    for index, image in enumerate(images):
        column = index % columns
        row = index // columns
        y_offset = column * [26, 12, 38][pattern] + (24 if pattern == 2 and row % 2 else 0)
        placements.append(
            placement(
                image,
                SECTION_SIDE_PADDING + column * (width + IMAGE_GAP),
                start_y + row * 430 + y_offset,
                width,
                section_index + index,
                rotation=[-1.5, 1.2, -0.8, 1.4, -1.1, 0.8][index % 6],
            )
        )
    return mirror_placements(placements) if pattern == 1 else placements


def build_pocket_grid_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    columns = min(3, max(len(images), 1))
    width = (CANVAS_WIDTH - SECTION_SIDE_PADDING * 2 - IMAGE_GAP * (columns - 1)) / columns
    placements = []
    for index, image in enumerate(images):
        column = index % columns
        row = index // columns
        placements.append(
            placement(
                image,
                SECTION_SIDE_PADDING + column * (width + IMAGE_GAP),
                start_y + row * 420,
                width,
                section_index + index,
                rotation=0,
            )
        )
    return placements


def build_ticket_day_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = build_ticket_memo_images(images[:2], start_y, section_index)
    pattern = layout_pattern_index("ticket_day", images, section_index)
    for index, image in enumerate(images[2:4], start=2):
        placements.append(
            placement(
                image,
                628 + [0, -44, 36][pattern],
                start_y + 330 + (index - 2) * [190, 214, 176][pattern],
                [240, 220, 252][pattern],
                section_index + index,
                rotation=[2.5, -2][(index - 2) % 2],
            )
        )
    return placements


def build_magazine_note_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = build_magazine_whitespace_images(images[:1], start_y, section_index)
    for index, image in enumerate(images[1:3], start=1):
        placements.append(
            placement(
                image,
                180 + (index - 1) * 280,
                start_y + 680,
                250,
                section_index + index,
                rotation=[2.2, -1.8][(index - 1) % 2],
            )
        )
    return placements


def build_before_after_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = []
    for index, image in enumerate(images[:2]):
        placements.append(
            placement(
                image,
                SECTION_SIDE_PADDING + index * 476,
                start_y + (0 if index == 0 else 18),
                420,
                section_index + index,
                rotation=[-1.5, 1.5][index],
            )
        )
    if len(images) >= 3:
        placements.append(placement(images[2], 386, start_y + 286, 260, section_index + 2, rotation=0.8))
    return placements


def build_moodboard_stack_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    pattern = layout_pattern_index("moodboard_stack", images, section_index)
    specs_by_pattern = [
        [
            (92, 86, 420, -4.5),
            (424, 0, 360, 3.8),
            (694, 124, 300, -3.2),
            (120, 604, 250, 2.6),
            (610, 454, 230, -2.4),
        ],
        [
            (118, 0, 330, 4.2),
            (438, 90, 430, -4.6),
            (232, 258, 284, 2.8),
            (664, 462, 238, 3.2),
            (96, 524, 280, -2.6),
        ],
        [
            (116, 126, 360, -3.2),
            (520, 18, 336, 4.8),
            (360, 288, 420, -5.2),
            (112, 560, 250, 2.4),
            (690, 602, 230, -3.4),
        ],
    ]
    specs = specs_by_pattern[pattern]
    for index, image in enumerate(images[: len(specs)]):
        x, y_offset, width, rotation = specs[index]
        placements.append(placement(image, x, start_y + y_offset, width, section_index + index, rotation=rotation))
    return placements


def build_recipe_memo_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    column_y = start_y
    for index, image in enumerate(images[:4]):
        width = 360 if index == 0 else 170
        x = SECTION_SIDE_PADDING if index < 2 else 342
        if index == 2:
            column_y = placements[0]["y"] + placements[0]["height"] + 34
        elif index == 3:
            column_y = placements[2]["y"] + placements[2]["height"] + IMAGE_GAP
        placements.append(placement(image, x, column_y, width, section_index + index, rotation=[-2, 1.6, -1.2, 2][index]))
        if index == 0:
            column_y += placements[-1]["height"] + 34
    return placements


def build_letter_page_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = [placement(images[0], 820, start_y + 36, 222, section_index, rotation=2.5)]
    for index, image in enumerate(images[1:3], start=1):
        placements.append(
            placement(
                image,
                798 + (index - 1) * 44,
                start_y + 300 + (index - 1) * 172,
                168,
                section_index + index,
                rotation=[-2.5, 1.8][(index - 1) % 2],
            )
        )
    return placements


def build_chapter_scroll_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    pattern = layout_pattern_index("chapter_scroll", images, section_index)
    y = start_y
    for index, image in enumerate(images[:9]):
        x_sets = ([92, 462, 168], [292, 92, 538], [118, 398, 214])
        width_sets = ([500, 430, 470], [470, 430, 382], [430, 500, 454])
        x = x_sets[pattern][index % 3]
        width = width_sets[pattern][index % 3]
        image_placement = placement(
            image,
            x,
            y,
            width,
            section_index + index,
            rotation=[-1.8, 1.4, -0.8, 1.8][index % 4],
        )
        placements.append(image_placement)
        y += image_placement["height"] + 136
    return placements


def build_field_notes_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = [placement(images[0], SECTION_SIDE_PADDING, start_y + 18, 430, section_index, rotation=-1.2)]
    for index, image in enumerate(images[1:5], start=1):
        row = index - 1
        placements.append(
            placement(
                image,
                120 + (row % 2) * 216,
                start_y + 516 + (row // 2) * 188,
                180,
                section_index + index,
                rotation=[2, -1.6, 1.2, -2.2][row % 4],
            )
        )
    return placements


def build_split_scene_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if len(images) == 3:
        return [
            placement(images[0], 92, start_y + 12, 420, section_index, rotation=-1.4),
            placement(images[1], 596, start_y, 330, section_index + 1, rotation=1.2),
            placement(images[2], 596, start_y + 406, 330, section_index + 2, rotation=-1.2),
        ]
    placements = []
    for index, image in enumerate(images[:4]):
        if len(images) <= 2:
            x = 92 + index * 476
            y = start_y + index * 22
        else:
            side_index = index // 2
            row_index = index % 2
            x = 92 if side_index == 0 else 568
            y = start_y + row_index * 318 + side_index * 26
        placements.append(
            placement(
                image,
                x,
                y,
                390,
                section_index + index,
                rotation=[-1.4, 1.2, 1.6, -1.2][index],
            )
        )
    return placements


def build_detail_index_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = [placement(images[0], SECTION_SIDE_PADDING, start_y + 12, 520, section_index, rotation=-0.8)]
    for index, image in enumerate(images[1:8], start=1):
        placements.append(
            placement(
                image,
                718,
                start_y + 18 + (index - 1) * 148,
                180,
                section_index + index,
                rotation=[1.2, -1.4, 1.6, -1][(index - 1) % 4],
            )
        )
    return placements


def build_map_journey_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    pattern = layout_pattern_index("map_journey", images, section_index)
    specs_by_pattern = [
        [
            (112, 40, 330, -2.2),
            (586, 214, 300, 2),
            (156, 568, 340, 1.2),
            (610, 868, 286, -1.6),
            (132, 1184, 310, -2.4),
            (558, 1448, 318, 1.8),
        ],
        [
            (568, 20, 334, 2.2),
            (148, 252, 306, -2),
            (614, 548, 324, -1.4),
            (186, 858, 288, 1.8),
            (552, 1192, 310, 2.4),
            (154, 1450, 318, -1.8),
        ],
        [
            (166, 42, 292, -1.6),
            (596, 178, 348, 2.4),
            (120, 512, 320, 2),
            (522, 802, 328, -1.4),
            (224, 1124, 286, -2.2),
            (618, 1426, 302, 1.6),
        ],
    ]
    specs = specs_by_pattern[pattern]
    for index, image in enumerate(images[: len(specs)]):
        x, y_offset, width, rotation = specs[index]
        placements.append(placement(image, x, start_y + y_offset, width, section_index + index, rotation=rotation))
    return placements


def build_weekly_spread_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    pattern = layout_pattern_index("weekly_spread", images, section_index)
    primary_width = [322, 312, 336][pattern]
    placements = [
        placement(
            images[0],
            [92, 108, 88][pattern],
            start_y + [42, 44, 38][pattern],
            primary_width,
            section_index,
            rotation=[-1.2, 1, -0.8][pattern],
        )
    ]
    side_specs_by_pattern = [
        [
            (486, 48, 218),
            (752, 48, 190),
            (96, 540, 210),
            (384, 540, 218),
            (678, 540, 206),
            (116, 996, 220),
            (430, 996, 200),
            (704, 996, 210),
        ],
        [
            (500, 44, 206),
            (750, 44, 198),
            (124, 512, 216),
            (410, 512, 204),
            (690, 512, 214),
            (108, 970, 206),
            (396, 970, 218),
            (690, 970, 196),
        ],
        [
            (510, 58, 220),
            (766, 58, 188),
            (92, 548, 214),
            (388, 548, 222),
            (704, 548, 198),
            (140, 1008, 208),
            (432, 1008, 214),
            (708, 1008, 204),
        ],
    ]
    for index, image in enumerate(images[1:9], start=1):
        x, y_offset, width = side_specs_by_pattern[pattern][index - 1]
        placements.append(
            placement(
                image,
                x,
                start_y + y_offset,
                width,
                section_index + index,
                rotation=[1, -0.8, 1.4, -1, 0.8, -1.2, 1.2, -0.6][(index - 1) % 8],
            )
        )
    return placements


def build_day_dashboard_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    pattern = layout_pattern_index("day_dashboard", images, section_index)
    placements = [placement(images[0], SECTION_SIDE_PADDING, start_y + 28, [420, 390, 440][pattern], section_index, rotation=[-1, 1, -1.4][pattern])]
    for index, image in enumerate(images[1:6], start=1):
        column = (index - 1) % 2
        row = (index - 1) // 2
        width = [178, 190, 166][pattern]
        placements.append(
            placement(
                image,
                590 + column * (width + 32),
                start_y + 42 + row * [322, 306, 336][pattern] + column * [0, 12, -8][pattern],
                width,
                section_index + index,
                rotation=[1.5, -1.2, 1, -1.5, 0.8][(index - 1) % 5],
            )
        )
    return placements


def build_scrapbook_story_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    pattern = layout_pattern_index("scrapbook_story", images, section_index)
    specs_by_pattern = [
        [
            (92, 24, 390, -3.2),
            (560, 88, 310, 3.5),
            (150, 612, 270, 2.2),
            (520, 640, 342, -2.1),
            (112, 1008, 320, 1.4),
            (584, 1088, 260, -3),
            (214, 1418, 340, 2),
            (640, 1514, 230, -2.2),
        ],
        [
            (520, 28, 380, 3.2),
            (126, 108, 328, -3.6),
            (614, 572, 282, -2.4),
            (132, 684, 342, 2.2),
            (566, 980, 318, -1.8),
            (184, 1114, 264, 3),
            (490, 1408, 344, -2),
            (122, 1540, 232, 2.2),
        ],
        [
            (118, 38, 346, -2.6),
            (510, 62, 354, 4),
            (284, 512, 286, 2.4),
            (626, 664, 300, -3),
            (104, 928, 340, 1.8),
            (540, 1086, 306, -2.8),
            (210, 1390, 310, 2.2),
            (620, 1500, 248, -2),
        ],
    ]
    specs = specs_by_pattern[pattern]
    for index, image in enumerate(images[: len(specs)]):
        x, y_offset, width, rotation = specs[index]
        placements.append(placement(image, x, start_y + y_offset, width, section_index + index, rotation=rotation))
    return placements


def build_hero_note_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    image = images[0]
    width = 780 if aspect_ratio(image) >= 1 else 620
    return [placement(image, (CANVAS_WIDTH - width) / 2, start_y, width, section_index)]


def build_magazine_whitespace_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    image = images[0]
    width = 520 if aspect_ratio(image) < 1 else 660
    return [placement(image, 92, start_y + 18, width, section_index, rotation=-1)]


def build_ticket_memo_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    for index, image in enumerate(images[:2]):
        width = 520 if index == 0 else 340
        x = 92 if index == 0 else 648
        y = start_y + (0 if index == 0 else 72)
        placements.append(placement(image, x, y, width, section_index + index, rotation=[-2.5, 3][index]))
    return placements


def build_staggered_collage_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    placements = []
    column_y = [start_y, start_y + 54]
    for index, image in enumerate(images):
        column = 0 if column_y[0] <= column_y[1] else 1
        width = 420
        x = 92 if column == 0 else 568
        placements.append(placement(image, x, column_y[column], width, section_index + index))
        column_y[column] += placements[-1]["height"] + IMAGE_GAP
    return placements


def build_timeline_strip_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    count = max(len(images), 1)
    width = 292 if count >= 3 else 420
    x = SECTION_SIDE_PADDING
    placements = []
    for index, image in enumerate(images):
        row = index // 3
        column = index % 3
        y = start_y + column * 64 + row * 430
        placements.append(placement(image, x, y, width, section_index + index, rotation=[-1.5, 1.5, -1][index % 3]))
        x += width + IMAGE_GAP
        if column == 2:
            x = SECTION_SIDE_PADDING
    return placements


def build_photo_wall_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    if len(images) < 3:
        return build_staggered_collage_images(images, start_y, section_index)

    placements = [placement(images[0], SECTION_SIDE_PADDING, start_y, 430, section_index, rotation=-1)]
    side_width = 276
    side_x = 622
    side_y = start_y + 18
    for index, image in enumerate(images[1:3], start=1):
        placements.append(
            placement(
                image,
                side_x,
                side_y,
                side_width,
                section_index + index,
                rotation=[1.2, -0.8][(index - 1) % 2],
            )
        )
        side_y += placements[-1]["height"] + IMAGE_GAP
    return placements


def placement(image: Any, x: float, y: float, width: float, index: int, rotation: float | None = None) -> dict[str, Any]:
    return {
        "imageId": image_id(image),
        "x": x,
        "y": y,
        "width": width,
        "height": photo_height_for_width(image, width),
        "rotation": rotation if rotation is not None else [-2, 2.5, -1.5, 1.5][index % 4],
    }


def layout_pattern_index(variant: str, images: list[Any], section_index: int, count: int = 3) -> int:
    signal_parts = [variant, str(section_index)]
    signal_parts.extend(image_id(image) for image in images)
    signal = "|".join(signal_parts)
    return stable_text_hash(signal) % max(count, 1)


def stable_text_hash(value: str) -> int:
    hash_value = 0
    for character in value:
        hash_value = (hash_value * 131 + ord(character)) % 1_000_003
    return hash_value


def mirror_placements(placements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mirrored = []
    for item in placements:
        next_item = dict(item)
        next_item["x"] = CANVAS_WIDTH - float(item["x"]) - float(item["width"])
        next_item["rotation"] = -float(item.get("rotation") or 0)
        mirrored.append(next_item)
    return mirrored


def build_caption_placements(variant: str, image_placements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    caption_placements = []
    for image in caption_images_for_variant(variant, image_placements):
        caption = {
            "role": "caption",
            "imageId": image["imageId"],
            "x": image["x"] + SECTION_CAPTION_SIDE_PADDING,
            "y": caption_y_for_image(image, image_placements),
            "width": max(image["width"] - SECTION_CAPTION_SIDE_PADDING * 2, 120),
            "fontSize": SECTION_CAPTION_FONT_SIZE,
        }
        caption_placements.append(caption)
    return caption_placements


def caption_images_for_variant(variant: str, image_placements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if variant == "moodboard_stack" and len(image_placements) >= 2:
        return []
    if variant in {"detail_index", "field_notes", "letter_page", "moodboard_stack", "quiet_story", "ticket_day"} and len(image_placements) >= 3:
        return []
    return [image for image in image_placements if caption_y_for_image(image, image_placements) >= image["y"] + image["height"] - 72]


def caption_y_for_image(image: dict[str, Any], image_placements: list[dict[str, Any]]) -> float:
    below_y = image["y"] + image["height"] + SECTION_CAPTION_BELOW_OFFSET
    caption_height = SECTION_CAPTION_FONT_SIZE * 2.4
    caption_rect = (
        image["x"] + SECTION_CAPTION_SIDE_PADDING,
        below_y,
        max(image["width"] - SECTION_CAPTION_SIDE_PADDING * 2, 120),
        caption_height,
    )
    other_image_rects = [
        (candidate["x"], candidate["y"], candidate["width"], candidate["height"])
        for candidate in image_placements
        if candidate is not image
    ]
    if not any(caption_conflicts_with_image(caption_rect, rect) for rect in other_image_rects):
        return below_y
    inside_y = image["y"] + image["height"] - caption_height - SECTION_CAPTION_BELOW_OFFSET
    inside_rect = (caption_rect[0], inside_y, caption_rect[2], caption_height)
    if not any(caption_conflicts_with_image(inside_rect, rect) for rect in other_image_rects):
        return inside_y
    above_y = max(image["y"] - caption_height - SECTION_CAPTION_BELOW_OFFSET, 0)
    above_rect = (caption_rect[0], above_y, caption_rect[2], caption_height)
    if not any(caption_conflicts_with_image(above_rect, rect) for rect in other_image_rects):
        return above_y
    return image["y"] + image["height"] - min(SECTION_CAPTION_BORDER_OFFSET - 8, caption_height)


def caption_conflicts_with_image(
    caption_rect: tuple[float, float, float, float],
    image_rect: tuple[float, float, float, float],
) -> bool:
    if not rects_overlap(caption_rect, image_rect):
        return False
    _, caption_y, _, caption_height = caption_rect
    _, image_y, _, image_height = image_rect
    image_bottom = image_y + image_height
    overlap_top = max(caption_y, image_y)
    overlap_bottom = min(caption_y + caption_height, image_bottom)
    return overlap_top < image_bottom - SECTION_CAPTION_BORDER_OFFSET or overlap_bottom > image_bottom + 1


def estimated_caption_height(caption: dict[str, Any]) -> float:
    return float(caption.get("fontSize") or SECTION_CAPTION_FONT_SIZE) * 2.4


def text_rect(text: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(text.get("x") or 0),
        float(text.get("y") or 0),
        float(text.get("width") or 0),
        float(text.get("fontSize") or SECTION_TEXT_FONT_SIZE) * 2.4,
    )


def rects_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def section_keywords(section: dict[str, Any], image_understanding: list[dict[str, Any]]) -> str:
    section_image_ids = set(section.get("imageIds") or section.get("image_ids") or [])
    parts = [str(section.get("title") or ""), str(section.get("body") or "")]
    parts.extend(str(item) for item in section.get("mood") or [])
    for item in image_understanding:
        if item.get("imageId") not in section_image_ids:
            continue
        parts.extend([str(item.get("summary") or ""), str(item.get("scene") or "")])
        parts.extend(str(subject) for subject in item.get("subjects") or [])
        parts.extend(str(mood) for mood in item.get("mood") or [])
    return " ".join(parts)


def has_similar_scenes(section_image_ids: list[str], image_understanding: list[dict[str, Any]]) -> bool:
    scenes: list[str] = []
    subject_sets: list[set[str]] = []
    for item in image_understanding:
        if item.get("imageId") not in section_image_ids:
            continue
        scene = str(item.get("scene") or "").strip()
        if scene:
            scenes.append(scene)
        subject_sets.append({str(subject) for subject in item.get("subjects") or [] if str(subject)})
    if len(scenes) >= 2 and len(set(scenes)) == 1:
        return True
    if len(subject_sets) >= 2:
        common_subjects = set.intersection(*subject_sets)
        return bool(common_subjects)
    return False


def image_id(image: Any) -> str:
    return str(getattr(image, "id", "") or image.get("id"))


def image_width(image: Any) -> float:
    return float(getattr(image, "width", 1) or image.get("width") or 1)


def image_height(image: Any) -> float:
    return float(getattr(image, "height", 1) or image.get("height") or 1)


def aspect_ratio(image: Any) -> float:
    return image_width(image) / max(image_height(image), 1)


def photo_height_for_width(image: Any, width: float) -> float:
    height = width * image_height(image) / max(image_width(image), 1)
    return max(min(height, 620), 260)


def text_x_for_variant(variant: str, image_count: int = 0) -> float:
    if variant == "quiet_story":
        return 690
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"}:
        return 642
    if variant == "recipe_memo":
        return 590
    if variant == "field_notes":
        return 610
    if variant == "letter_page":
        return 112
    if variant == "detail_index":
        return 112
    if variant == "map_journey":
        return 602
    if variant == "weekly_spread":
        return 112
    if variant == "day_dashboard":
        return 112
    if variant == "scrapbook_story":
        return 150
    if variant == "before_after":
        return 150
    if variant in {"ticket_memo", "ticket_day"} and image_count >= 2:
        return 112
    if variant in {"ticket_memo", "ticket_day"}:
        return 612
    return 112


def text_width_for_variant(variant: str, image_count: int = 0) -> float:
    if variant == "quiet_story":
        return 300
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"}:
        return 350
    if variant == "recipe_memo":
        return 360
    if variant == "field_notes":
        return 330
    if variant == "letter_page":
        return 700
    if variant == "detail_index":
        return 560
    if variant == "map_journey":
        return 300
    if variant == "weekly_spread":
        return 820
    if variant == "day_dashboard":
        return 430
    if variant == "scrapbook_story":
        return 720
    if variant == "before_after":
        return 720
    if variant in {"ticket_memo", "ticket_day"} and image_count >= 2:
        return SECTION_TEXT_WIDTH
    if variant in {"ticket_memo", "ticket_day"}:
        return 360
    return SECTION_TEXT_WIDTH


def estimate_paragraph_height(paragraph: str, font_size: float, width: float) -> float:
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max(ceil(len(paragraph) / characters_per_line), 1)
    return line_count * font_size * 1.8
