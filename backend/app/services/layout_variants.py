from math import ceil
from typing import Any

CANVAS_WIDTH = 1080
SECTION_SIDE_PADDING = 92
SECTION_TEXT_WIDTH = 820
SECTION_TEXT_FONT_SIZE = 32
SECTION_CAPTION_FONT_SIZE = 22
SECTION_CAPTION_SIDE_PADDING = 28
SECTION_CAPTION_BOTTOM_OFFSET = 38
SECTION_GAP = 104
TEXT_PHOTO_GAP = 56
IMAGE_GAP = 38
ALLOWED_SECTION_VARIANTS = {
    "hero_note",
    "staggered_collage",
    "timeline_strip",
    "photo_wall",
    "magazine_whitespace",
    "ticket_memo",
}

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
    text_y = image_bottom + TEXT_PHOTO_GAP
    if variant in {"magazine_whitespace", "ticket_memo"} and image_placements:
        text_y = min(text_y, start_y + 420)
    if variant == "ticket_memo" and len(image_placements) >= 2:
        text_y = image_bottom + TEXT_PHOTO_GAP
    text = {
        "role": "body",
        "x": text_x_for_variant(variant, len(image_placements)),
        "y": text_y,
        "width": text_width_for_variant(variant, len(image_placements)),
        "fontSize": SECTION_TEXT_FONT_SIZE,
    }
    body = str(section.get("body") or "")
    text_bottom = text["y"] + estimate_paragraph_height(body, text["fontSize"], text["width"])
    section_bottom = max(image_bottom, text_bottom) + SECTION_GAP
    caption_texts = build_caption_placements(image_placements)

    return {
        "sectionId": str(section["id"]),
        "variant": variant,
        "y": start_y,
        "height": max(section_bottom - start_y, 1),
        "images": image_placements,
        "texts": [text, *caption_texts],
        "decorations": [],
    }


def build_image_placements(variant: str, images: list[Any], start_y: float, section_index: int) -> list[dict[str, Any]]:
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
    return [
        {
            "role": "caption",
            "x": image["x"] + SECTION_CAPTION_SIDE_PADDING,
            "y": image["y"] + image["height"] - SECTION_CAPTION_BOTTOM_OFFSET,
            "width": max(image["width"] - SECTION_CAPTION_SIDE_PADDING * 2, 120),
            "fontSize": SECTION_CAPTION_FONT_SIZE,
        }
        for image in image_placements
    ]


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
    if variant == "magazine_whitespace":
        return 642
    if variant == "ticket_memo" and image_count >= 2:
        return 112
    if variant == "ticket_memo":
        return 612
    return 112


def text_width_for_variant(variant: str, image_count: int = 0) -> float:
    if variant == "magazine_whitespace":
        return 350
    if variant == "ticket_memo" and image_count >= 2:
        return SECTION_TEXT_WIDTH
    if variant == "ticket_memo":
        return 360
    return SECTION_TEXT_WIDTH


def estimate_paragraph_height(paragraph: str, font_size: float, width: float) -> float:
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max(ceil(len(paragraph) / characters_per_line), 1)
    return line_count * font_size * 1.8
