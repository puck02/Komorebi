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
        return "timeline_strip"

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
    caption_texts = build_caption_placements(image_placements)
    caption_bottom = max(
        (caption["y"] + estimated_caption_height(caption) for caption in caption_texts),
        default=image_bottom,
    )
    text_y = image_bottom + TEXT_PHOTO_GAP
    if caption_texts:
        text_y = max(text_y, caption_bottom + SECTION_CAPTION_TEXT_GAP)
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"} and image_placements:
        text_y = max(min(text_y, start_y + 420), caption_bottom + SECTION_CAPTION_TEXT_GAP)
    if variant == "letter_page" and image_placements:
        text_y = start_y + 68
    if variant == "recipe_memo" and image_placements:
        text_y = start_y + 44
    if variant in {"ticket_memo", "ticket_day"} and len(image_placements) >= 2:
        text_y = max(image_bottom + TEXT_PHOTO_GAP, caption_bottom + SECTION_CAPTION_TEXT_GAP)
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
                320 + (index - 1) * 86,
                start_y + 300 + (index - 1) * 92,
                230,
                section_index + index,
                rotation=[2.5, -2][(index - 1) % 2],
            )
        )
    return placements


def build_hero_memory_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    primary_width = 760 if aspect_ratio(images[0]) >= 1 else 620
    placements = [placement(images[0], (CANVAS_WIDTH - primary_width) / 2, start_y, primary_width, section_index, rotation=0)]
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
        return build_timeline_strip_images(images, start_y, section_index)

    placements = []
    width = 260
    columns = 3
    for index, image in enumerate(images):
        column = index % columns
        row = index // columns
        placements.append(
            placement(
                image,
                SECTION_SIDE_PADDING + column * (width + IMAGE_GAP),
                start_y + row * 314 + column * 26,
                width,
                section_index + index,
                rotation=[-1.5, 1.2, -0.8, 1.4, -1.1, 0.8][index % 6],
            )
        )
    return placements


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
    for index, image in enumerate(images[2:4], start=2):
        placements.append(
            placement(
                image,
                628,
                start_y + 330 + (index - 2) * 190,
                240,
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
                start_y + 430,
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
    specs = [
        (92, 86, 420, -4.5),
        (424, 0, 360, 3.8),
        (694, 124, 300, -3.2),
        (168, 268, 270, 2.6),
        (574, 298, 250, -2.4),
    ]
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
            column_y = placements[2]["y"] + placements[2]["height"] + 28
        placements.append(placement(image, x, column_y, width, section_index + index, rotation=[-2, 1.6, -1.2, 2][index]))
        if index == 0:
            column_y += placements[-1]["height"] + 34
    return placements


def build_letter_page_images(images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
    if not images:
        return []
    placements = [placement(images[0], 812, start_y + 36, 230, section_index, rotation=2.5)]
    for index, image in enumerate(images[1:3], start=1):
        placements.append(
            placement(
                image,
                754 + (index - 1) * 42,
                start_y + 300 + (index - 1) * 172,
                190,
                section_index + index,
                rotation=[-2.5, 1.8][(index - 1) % 2],
            )
        )
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
        placements.append(placement(image, x, start_y + index * 64, width, section_index + index, rotation=[-1.5, 1.5, -1][index % 3]))
        x += width + IMAGE_GAP
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


def build_caption_placements(image_placements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    caption_placements = []
    for image in image_placements:
        caption = {
            "role": "caption",
            "x": image["x"] + SECTION_CAPTION_SIDE_PADDING,
            "y": caption_y_for_image(image, image_placements),
            "width": max(image["width"] - SECTION_CAPTION_SIDE_PADDING * 2, 120),
            "fontSize": SECTION_CAPTION_FONT_SIZE,
        }
        caption_placements.append(caption)
    return caption_placements


def caption_y_for_image(image: dict[str, Any], image_placements: list[dict[str, Any]]) -> float:
    below_y = image["y"] + image["height"] + SECTION_CAPTION_BELOW_OFFSET
    caption_rect = (
        image["x"] + SECTION_CAPTION_SIDE_PADDING,
        below_y,
        max(image["width"] - SECTION_CAPTION_SIDE_PADDING * 2, 120),
        SECTION_CAPTION_FONT_SIZE * 2.4,
    )
    other_image_rects = [
        (candidate["x"], candidate["y"], candidate["width"], candidate["height"])
        for candidate in image_placements
        if candidate is not image
    ]
    if any(rects_overlap(caption_rect, rect) for rect in other_image_rects):
        return image["y"] + image["height"] - SECTION_CAPTION_BOTTOM_OFFSET
    return below_y


def estimated_caption_height(caption: dict[str, Any]) -> float:
    return float(caption.get("fontSize") or SECTION_CAPTION_FONT_SIZE) * 2.4


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
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"}:
        return 642
    if variant == "recipe_memo":
        return 590
    if variant == "letter_page":
        return 112
    if variant == "before_after":
        return 150
    if variant in {"ticket_memo", "ticket_day"} and image_count >= 2:
        return 112
    if variant in {"ticket_memo", "ticket_day"}:
        return 612
    return 112


def text_width_for_variant(variant: str, image_count: int = 0) -> float:
    if variant in {"magazine_whitespace", "magazine_note", "quiet_story"}:
        return 350
    if variant == "recipe_memo":
        return 360
    if variant == "letter_page":
        return 700
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
