from copy import deepcopy
from dataclasses import dataclass
from math import ceil, isfinite
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem
from app.services.decoration_placement import place_decorations
from app.services.diary_copy import normalize_diary_blocks, normalize_diary_text, normalize_title
from app.services.layout_variants import ALLOWED_SECTION_VARIANTS, build_section_layout
from app.services.story_planner import plan_content_sections, split_evenly

CANVAS_WIDTH = 1080
DEFAULT_CANVAS_HEIGHT = 1440
COMPACT_SECTION_CANVAS_HEIGHT = 1120
CANVAS_BOTTOM_PADDING = 80
TITLE_X = 80
TITLE_Y = 72
TITLE_WIDTH = 760
TITLE_FONT_SIZE = 58
BODY_X = 112
BODY_WIDTH = 820
BODY_FONT_SIZE = 32
BODY_BLOCK_GAP = 46
TEXT_PHOTO_GAP = 64
SECTION_GAP = 104
PHOTO_COLUMN_WIDTH = 420
PHOTO_LEFT_X = 92
PHOTO_RIGHT_X = 568
PHOTO_ROW_GAP = 56
LONG_BODY_SPLIT_TARGET = 58


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class JournalImageInput:
    id: str
    width: int
    height: int
    data_url: str | None = None


@dataclass(frozen=True)
class JournalGenerationRequest:
    description: str
    images: list[JournalImageInput]
    assets: list[AssetItem]


class JournalModelClient(Protocol):
    def generate_layout(self, request: JournalGenerationRequest) -> dict[str, Any]:
        pass


class JournalGenerator:
    def __init__(self, client: JournalModelClient):
        self.client = client

    def generate(self, request: JournalGenerationRequest) -> JournalLayout:
        approved_assets = [asset for asset in request.assets if asset.quality_status == "approved"]
        model_request = JournalGenerationRequest(
            description=request.description,
            images=request.images,
            assets=approved_assets,
        )

        try:
            raw_layout = self.client.generate_layout(model_request)
            cleaned_layout = sanitize_model_layout(raw_layout, model_request)
            return JournalLayout.model_validate(cleaned_layout)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise GenerationError("Model returned an invalid journal layout") from error


def sanitize_model_layout(raw_layout: dict[str, Any], request: JournalGenerationRequest) -> dict[str, Any]:
    layout = deepcopy(raw_layout)
    layout["canvas"]["width"] = CANVAS_WIDTH
    layout["canvas"]["background"] = normalize_background(layout["canvas"].get("background"))

    content = layout["content"]
    if "body" not in content and isinstance(content.get("notes"), list):
        content["body"] = content["notes"]
    if "body" not in content and isinstance(content.get("subtitle"), str):
        content["body"] = [content["subtitle"]]
    content["title"] = normalize_title(content.get("title"))
    content["body"] = normalize_body_content(content.get("body"), len(request.images))

    image_ids = {image.id for image in request.images}
    approved_asset_ids = [asset.id for asset in request.assets if asset.quality_status == "approved"]
    approved_asset_set = set(approved_asset_ids)

    for placement in layout["layout"].get("images", []):
        normalize_id_alias(placement, "imageId")

    layout["layout"]["images"] = [
        placement for placement in layout["layout"].get("images", []) if placement.get("imageId") in image_ids
    ]
    captions = layout["content"].get("captions")
    if not isinstance(captions, list):
        captions = [
            {"imageId": item.get("id"), "text": item.get("caption")}
            for item in layout["content"].get("images", [])
            if isinstance(item, dict)
        ]
    for caption in captions:
        normalize_id_alias(caption, "imageId")
        caption["text"] = normalize_diary_text(caption.get("text"), fallback="今天的照片")
    layout["content"]["captions"] = [
        caption for caption in captions if caption.get("imageId") in image_ids and str(caption.get("text") or "").strip()
    ]
    normalize_image_understanding(layout, request.images)

    normalize_story_layout(layout, request.images)

    asset_by_id = {asset.id: asset for asset in request.assets}

    if approved_asset_ids:
        fallback_asset_id = approved_asset_ids[0]
        category_fallbacks = build_category_fallbacks(request.assets)
        normalized_decorations = [
            normalize_decoration_asset(decoration, approved_asset_set, fallback_asset_id, category_fallbacks, asset_by_id)
            for decoration in layout["layout"].get("decorations", [])
        ]
        layout["layout"]["decorations"] = normalize_decorations(
            normalized_decorations,
            layout["layout"].get("images", []),
            layout["layout"].get("texts", []),
            asset_by_id,
        )
    else:
        layout["layout"]["decorations"] = []

    normalize_sections(layout, request.images, asset_by_id)
    layout["canvas"]["height"] = normalize_canvas_height(layout)
    return layout


def normalize_body_content(body: Any, image_count: int) -> list[str]:
    return normalize_diary_blocks(body, fallback="今天的照片先放在这里。", split_target=LONG_BODY_SPLIT_TARGET)


def normalize_story_layout(layout: dict[str, Any], request_images: list[JournalImageInput]) -> None:
    image_placements = layout["layout"].get("images", [])
    body = layout["content"].get("body", [])
    has_missing_images = {placement.get("imageId") for placement in image_placements} != {image.id for image in request_images}
    should_use_long_collage = len(request_images) > 1 or has_missing_images

    title = normalize_title_text(next((text for text in layout["layout"].get("texts", []) if text.get("role") == "title"), None))
    if should_use_long_collage:
        images, body_texts = build_long_collage_items(request_images, image_placements, body, title)
        layout["layout"]["images"] = images
        layout["layout"]["texts"] = [title, *body_texts]
        return

    layout["layout"]["texts"] = [
        title,
        *normalize_body_texts(layout["layout"].get("texts", []), body, image_placements, title),
    ]


def normalize_sections(
    layout: dict[str, Any],
    request_images: list[JournalImageInput],
    asset_by_id: dict[str, AssetItem],
) -> None:
    content_sections = normalize_content_sections(layout, request_images)
    layout["content"]["sections"] = content_sections
    layout["layout"]["sections"] = normalize_layout_sections(layout, content_sections, request_images, asset_by_id)


def normalize_image_understanding(layout: dict[str, Any], request_images: list[JournalImageInput]) -> None:
    raw_items = layout["content"].get("imageUnderstanding")
    if raw_items is None:
        raw_items = layout["content"].get("image_understanding")
    raw_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(raw_items, list):
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            normalize_id_alias(raw_item, "imageId")
            image_id = raw_item.get("imageId")
            if isinstance(image_id, str):
                raw_by_id[image_id] = raw_item

    normalized: list[dict[str, Any]] = []
    for index, image in enumerate(request_images):
        raw_item = raw_by_id.get(image.id, {})
        normalized.append(
            {
                "imageId": image.id,
                "summary": str(raw_item.get("summary") or f"第 {index + 1} 张照片的生活片段").strip(),
                "scene": str(raw_item.get("scene") or "").strip(),
                "subjects": normalize_string_list(raw_item.get("subjects")),
                "mood": normalize_string_list(raw_item.get("mood")),
            }
        )
    layout["content"]["imageUnderstanding"] = normalized


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_content_sections(layout: dict[str, Any], request_images: list[JournalImageInput]) -> list[dict[str, Any]]:
    image_ids = [image.id for image in request_images]
    sections = plan_content_sections(layout, image_ids)
    return [
        {
            **section,
            "title": normalize_title(section.get("title"), fallback=f"片段 {index + 1}"),
            "body": normalize_diary_text(section.get("body"), fallback="这一组照片也想好好留下。"),
        }
        for index, section in enumerate(sections)
    ]


def normalize_layout_sections(
    layout: dict[str, Any],
    content_sections: list[dict[str, Any]],
    request_images: list[JournalImageInput],
    asset_by_id: dict[str, AssetItem],
) -> list[dict[str, Any]]:
    raw_sections = layout["layout"].get("sections")
    raw_by_id = {
        str(section.get("sectionId") or section.get("section_id")): section
        for section in raw_sections
        if isinstance(raw_sections, list) and isinstance(section, dict)
    } if isinstance(raw_sections, list) else {}
    decorations = layout["layout"].get("decorations", [])
    layout_sections: list[dict[str, Any]] = []
    next_y = fallback_first_section_y(layout)

    for index, content_section in enumerate(content_sections):
        section_id = content_section["id"]
        source = raw_by_id.get(section_id, {})
        suggested_variant = source.get("variant") if source.get("variant") in ALLOWED_SECTION_VARIANTS else None
        generated_section = build_section_layout(
            content_section,
            request_images=request_images,
            image_understanding=layout["content"].get("imageUnderstanding", []),
            section_index=index,
            total_sections=len(content_sections),
            start_y=next_y,
            suggested_variant=suggested_variant,
        )
        section_images = generated_section["images"]
        section_texts = generated_section["texts"]
        section_decorations = normalize_section_decorations(
            source.get("decorations"),
            decorations,
            section_images,
            section_texts,
            asset_by_id,
            index,
        )
        y = positive_number(source.get("y"), generated_section["y"])
        height = max(
            min_section_height(generated_section),
            section_height(section_images, section_texts, section_decorations, y),
        )
        variant = source.get("variant") if source.get("variant") in ALLOWED_SECTION_VARIANTS else generated_section["variant"]
        layout_sections.append(
            {
                "sectionId": section_id,
                "variant": str(variant),
                "y": y,
                "height": max(height, 1),
                "images": section_images,
                "texts": section_texts,
                "decorations": section_decorations,
            }
        )
        next_y = y + max(height, 1) + SECTION_GAP
    return layout_sections


def fallback_first_section_y(layout: dict[str, Any]) -> float:
    title = next((text for text in layout["layout"].get("texts", []) if text.get("role") == "title"), None)
    if not isinstance(title, dict):
        return TITLE_Y + SECTION_GAP
    return positive_number(title.get("y"), TITLE_Y) + estimate_text_height(title, layout["content"]) + SECTION_GAP


def normalize_section_decorations(
    source_decorations: Any,
    fallback_decorations: list[dict[str, Any]],
    section_images: list[dict[str, Any]],
    section_texts: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
    section_index: int,
) -> list[dict[str, Any]]:
    if isinstance(source_decorations, list):
        decorations = [decoration for decoration in source_decorations if isinstance(decoration, dict)]
        if decorations:
            return place_decorations(
                build_template_section_decorations(
                    section_images,
                    section_texts,
                    asset_by_id,
                    section_index,
                    preferred_asset_ids=decoration_asset_ids(decorations, asset_by_id),
                ),
                section_images,
                section_texts,
                asset_by_id,
            )
    if not section_images:
        return []
    top = min(positive_number(image.get("y"), 0) for image in section_images) - 96
    bottom = max(positive_number(image.get("y"), 0) + positive_number(image.get("height"), 0) for image in section_images) + 160
    fallback_matches = [
        decoration
        for decoration in fallback_decorations
        if top <= positive_number(decoration.get("y"), 0) <= bottom
    ]
    if fallback_matches:
        return fallback_matches
    return place_decorations(
        build_template_section_decorations(section_images, section_texts, asset_by_id, section_index),
        section_images,
        section_texts,
        asset_by_id,
    )


def build_template_section_decorations(
    section_images: list[dict[str, Any]],
    section_texts: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
    section_index: int,
    preferred_asset_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not section_images and not section_texts:
        return []

    decorations: list[dict[str, Any]] = []
    paper_id = first_asset_id(asset_by_id, "paper", section_index, preferred_asset_ids)
    tape_id = first_asset_id(asset_by_id, "tape", section_index, preferred_asset_ids)
    sticker_id = first_asset_id(asset_by_id, "sticker", section_index, preferred_asset_ids)
    body_text = next((text for text in section_texts if text.get("role") == "body"), section_texts[0] if section_texts else None)
    first_image = section_images[0] if section_images else None

    if paper_id is not None and body_text is not None:
        decorations.append(
            {
                "assetId": paper_id,
                "x": positive_number(body_text.get("x"), BODY_X) - 36,
                "y": positive_number(body_text.get("y"), 0) - 30,
                "width": positive_number(body_text.get("width"), BODY_WIDTH) + 72,
                "height": 160,
                "rotation": [-1.2, 1, -0.8][section_index % 3],
            }
        )

    if tape_id is not None:
        target = body_text or first_image
        if target is not None:
            decorations.append(
                {
                    "assetId": tape_id,
                    "x": positive_number(target.get("x"), 80) + 72,
                    "y": positive_number(target.get("y"), 0) - 42,
                    "width": 220,
                    "height": 54,
                    "rotation": [-7, 6, -5][section_index % 3],
                }
            )

    if sticker_id is not None:
        target = first_image or body_text
        if target is not None:
            decorations.append(
                {
                    "assetId": sticker_id,
                    "x": positive_number(target.get("x"), 80) + positive_number(target.get("width"), 200) + 22,
                    "y": positive_number(target.get("y"), 0) + 24,
                    "width": 112,
                    "height": 112,
                    "rotation": [5, -4, 3][section_index % 3],
                }
            )
    return decorations


def decoration_asset_ids(decorations: list[dict[str, Any]], asset_by_id: dict[str, AssetItem]) -> list[str]:
    asset_ids: list[str] = []
    for decoration in decorations:
        asset_id = str(decoration.get("assetId") or decoration.get("asset_id") or decoration.get("id") or "")
        asset = asset_by_id.get(asset_id)
        if asset is not None and asset.quality_status == "approved":
            asset_ids.append(asset.id)
    return asset_ids


def first_asset_id(
    asset_by_id: dict[str, AssetItem],
    category: str,
    offset: int,
    preferred_asset_ids: list[str] | None = None,
) -> str | None:
    preferred_ids = [
        asset_id
        for asset_id in preferred_asset_ids or []
        if (asset := asset_by_id.get(asset_id)) is not None and asset.category == category and asset.quality_status == "approved"
    ]
    if preferred_ids:
        return preferred_ids[0]

    asset_ids = [asset.id for asset in asset_by_id.values() if asset.category == category and asset.quality_status == "approved"]
    if not asset_ids:
        return None
    return asset_ids[offset % len(asset_ids)]


def section_y(
    images: list[dict[str, Any]],
    texts: list[dict[str, Any]],
    decorations: list[dict[str, Any]],
    index: int,
) -> float:
    ys = [
        positive_number(item.get("y"), 0)
        for item in [*images, *texts, *decorations]
        if isinstance(item, dict)
    ]
    return min(ys, default=TITLE_Y + SECTION_GAP + index * 640)


def section_height(
    images: list[dict[str, Any]],
    texts: list[dict[str, Any]],
    decorations: list[dict[str, Any]],
    y: float,
) -> float:
    image_bottom = max_placement_bottom(images, "height")
    decoration_bottom = max_placement_bottom(decorations, "height")
    text_bottom = max(
        (
            positive_number(text.get("y"), 0) + positive_number(text.get("fontSize"), BODY_FONT_SIZE) * 2.4
            for text in texts
            if isinstance(text, dict)
        ),
        default=0,
    )
    return max(image_bottom, decoration_bottom, text_bottom, y + 320) - y


def min_section_height(generated_section: dict[str, Any]) -> float:
    generated_y = positive_number(generated_section.get("y"), 0)
    return section_height(
        generated_section.get("images", []),
        generated_section.get("texts", []),
        generated_section.get("decorations", []),
        generated_y,
    )


def normalize_title_text(title: dict[str, Any] | None) -> dict[str, Any]:
    source = title or {}
    return {
        "role": "title",
        "x": clamp_number(positive_number(source.get("x"), TITLE_X), 0, CANVAS_WIDTH - 240),
        "y": positive_number(source.get("y"), TITLE_Y),
        "width": min(positive_number(source.get("width"), TITLE_WIDTH), CANVAS_WIDTH - 120),
        "fontSize": positive_number(source.get("fontSize"), TITLE_FONT_SIZE),
    }


def normalize_body_texts(
    texts: list[dict[str, Any]],
    body: list[str],
    image_placements: list[dict[str, Any]],
    title: dict[str, Any],
) -> list[dict[str, Any]]:
    body_texts = [text for text in texts if text.get("role") == "body"]
    next_texts: list[dict[str, Any]] = []
    y = positive_number(title.get("y"), TITLE_Y) + estimate_text_height(title, {"title": "", "body": body, "captions": []}) + SECTION_GAP
    for index, paragraph in enumerate(body):
        source = body_texts[index] if index < len(body_texts) else {}
        font_size = positive_number(source.get("fontSize"), BODY_FONT_SIZE)
        width = min(positive_number(source.get("width"), BODY_WIDTH), CANVAS_WIDTH - BODY_X * 2)
        x = clamp_number(positive_number(source.get("x"), BODY_X), 40, CANVAS_WIDTH - width - 40)
        height = estimate_paragraph_height(paragraph, font_size, width)
        y = max(y, positive_number(source.get("y"), y))
        y = next_non_overlapping_y((x, y, width, height), image_placements)
        next_texts.append({"role": "body", "x": x, "y": y, "width": width, "fontSize": font_size})
        y += height + BODY_BLOCK_GAP
    return next_texts


def build_long_collage_items(
    request_images: list[JournalImageInput],
    existing_placements: list[dict[str, Any]],
    body: list[str],
    title: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_by_id = {placement.get("imageId"): placement for placement in existing_placements}
    section_count = max(len(body), min(ceil(len(request_images) / 3), 4), 1)
    image_groups = split_evenly(request_images, section_count)
    image_placements: list[dict[str, Any]] = []
    body_texts: list[dict[str, Any]] = []
    title_height = estimate_text_height(title, {"title": "", "body": body, "captions": []})
    y = positive_number(title.get("y"), TITLE_Y) + title_height + SECTION_GAP

    for section_index in range(section_count):
        group = image_groups[section_index] if section_index < len(image_groups) else []
        if group:
            group_placements, group_bottom = build_image_group(group, existing_by_id, y, section_index)
            image_placements.extend(group_placements)
            y = group_bottom + TEXT_PHOTO_GAP

        if section_index < len(body):
            paragraph = body[section_index]
            text_height = estimate_paragraph_height(paragraph, BODY_FONT_SIZE, BODY_WIDTH)
            body_texts.append({"role": "body", "x": BODY_X, "y": y, "width": BODY_WIDTH, "fontSize": BODY_FONT_SIZE})
            y += text_height + SECTION_GAP
        else:
            y += SECTION_GAP

    return image_placements, body_texts


def build_image_group(
    images: list[JournalImageInput],
    existing_by_id: dict[str, dict[str, Any]],
    start_y: float,
    section_index: int,
) -> tuple[list[dict[str, Any]], float]:
    if len(images) == 1:
        placement = build_single_image_placement(images[0], existing_by_id.get(images[0].id), start_y, section_index)
        return [placement], placement["y"] + placement["height"]

    placements: list[dict[str, Any]] = []
    column_y = [start_y, start_y + 42]
    for index, image in enumerate(images):
        column = 0 if column_y[0] <= column_y[1] else 1
        x = PHOTO_LEFT_X if column == 0 else PHOTO_RIGHT_X
        height = photo_height_for_width(image, PHOTO_COLUMN_WIDTH)
        placements.append(
            {
                "imageId": image.id,
                "x": x,
                "y": column_y[column],
                "width": PHOTO_COLUMN_WIDTH,
                "height": height,
                "rotation": normalized_photo_rotation(existing_by_id.get(image.id), index + section_index),
            }
        )
        column_y[column] += height + PHOTO_ROW_GAP
    return placements, max(column_y) - PHOTO_ROW_GAP


def build_single_image_placement(
    image: JournalImageInput,
    existing: dict[str, Any] | None,
    y: float,
    index: int,
) -> dict[str, Any]:
    aspect = image.width / max(image.height, 1)
    width = 780 if aspect >= 1 else 620
    height = photo_height_for_width(image, width)
    return {
        "imageId": image.id,
        "x": (CANVAS_WIDTH - width) / 2,
        "y": y,
        "width": width,
        "height": height,
        "rotation": normalized_photo_rotation(existing, index),
    }


def photo_height_for_width(image: JournalImageInput, width: float) -> float:
    height = width * image.height / max(image.width, 1)
    return clamp_number(height, 300, 620)


def normalized_photo_rotation(existing: dict[str, Any] | None, index: int) -> float:
    if existing is not None:
        return clamp_number(positive_number(existing.get("rotation"), 0), -6, 6)
    return [-2, 2.5, -1.5, 1.5][index % 4]


def next_non_overlapping_y(rect: tuple[float, float, float, float], image_placements: list[dict[str, Any]]) -> float:
    x, y, width, height = rect
    for _ in range(len(image_placements) + 1):
        overlapping_bottoms = [
            positive_number(image.get("y"), 0) + positive_number(image.get("height"), 0)
            for image in image_placements
            if rects_overlap((x, y, width, height), rect_from_item(image))
        ]
        if not overlapping_bottoms:
            return y
        y = max(overlapping_bottoms) + TEXT_PHOTO_GAP
    return y


def estimate_paragraph_height(paragraph: str, font_size: float, width: float) -> float:
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max(ceil(len(paragraph) / characters_per_line), 1)
    return line_count * font_size * 1.8


def normalize_canvas_height(layout: dict[str, Any]) -> int:
    if layout["layout"].get("sections"):
        title_bottom = max_text_bottom(
            [text for text in layout["layout"].get("texts", []) if isinstance(text, dict) and text.get("role") == "title"],
            layout["content"],
        ) + CANVAS_BOTTOM_PADDING
        section_decorations = [
            decoration
            for section in layout["layout"].get("sections", [])
            if isinstance(section, dict)
            for decoration in section.get("decorations", [])
            if isinstance(decoration, dict)
        ]
        fallback_decoration_bottom = (
            max_placement_bottom(layout["layout"].get("decorations", []), "height") + CANVAS_BOTTOM_PADDING
            if not section_decorations
            else 0
        )
        sections = layout["layout"].get("sections", [])
        minimum_height = COMPACT_SECTION_CANVAS_HEIGHT if len(sections) == 1 else DEFAULT_CANVAS_HEIGHT
        section_bottom = max_section_bottom(sections, layout["content"]) + CANVAS_BOTTOM_PADDING
        return ceil(max(minimum_height, title_bottom, section_bottom, fallback_decoration_bottom))

    placement_bottom = max_placement_bottom(layout["layout"].get("images", []), "height") + CANVAS_BOTTOM_PADDING
    decoration_bottom = max_placement_bottom(layout["layout"].get("decorations", []), "height") + CANVAS_BOTTOM_PADDING
    text_bottom = max_text_bottom(layout["layout"].get("texts", []), layout["content"]) + CANVAS_BOTTOM_PADDING
    section_bottom = max_section_bottom(layout["layout"].get("sections", []), layout["content"]) + CANVAS_BOTTOM_PADDING
    return ceil(max(DEFAULT_CANVAS_HEIGHT, placement_bottom, decoration_bottom, text_bottom, section_bottom))


def max_section_bottom(sections: list[dict[str, Any]], content: dict[str, Any]) -> float:
    bottoms: list[float] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        y = positive_number(section.get("y"), 0)
        bottoms.append(y + positive_number(section.get("height"), 0))
        bottoms.append(max_placement_bottom(section.get("images", []), "height"))
        bottoms.append(max_placement_bottom(section.get("decorations", []), "height"))
        bottoms.append(max_text_bottom(section.get("texts", []), content))
    return max(bottoms, default=0)


def max_placement_bottom(placements: list[dict[str, Any]], height_key: str) -> float:
    bottoms = [
        positive_number(placement.get("y"), 0) + positive_number(placement.get(height_key), 0)
        for placement in placements
        if isinstance(placement, dict)
    ]
    return max(bottoms, default=0)


def max_text_bottom(texts: list[dict[str, Any]], content: dict[str, Any]) -> float:
    bottoms = []
    for text in texts:
        if not isinstance(text, dict):
            continue
        y = positive_number(text.get("y"), 0)
        bottoms.append(y + estimate_text_height(text, content))
    return max(bottoms, default=0)


def estimate_text_height(text: dict[str, Any], content: dict[str, Any]) -> float:
    role = text.get("role")
    font_size = positive_number(text.get("fontSize"), 28)
    width = positive_number(text.get("width"), 760)
    if role == "title":
        text_value = str(content.get("title", ""))
    elif role == "body":
        text_value = "\n".join(str(paragraph) for paragraph in content.get("body", []) if paragraph)
    else:
        text_value = " ".join(str(caption.get("text", "")) for caption in content.get("captions", []) if isinstance(caption, dict))
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max(ceil(len(text_value) / characters_per_line), 1)
    return line_count * font_size * 1.8


def positive_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not isfinite(number) or number <= 0:
        return fallback
    return number


def normalize_background(background: Any) -> str:
    if isinstance(background, str):
        return background
    if isinstance(background, dict) and isinstance(background.get("color"), str):
        return background["color"]
    return "#f8f1e8"


def normalize_id_alias(item: dict[str, Any], alias: str) -> None:
    if alias not in item and isinstance(item.get("id"), str):
        item[alias] = item["id"]


def build_category_fallbacks(assets: list[AssetItem]) -> dict[str, str]:
    fallbacks: dict[str, str] = {}
    for asset in assets:
        if asset.quality_status == "approved" and asset.category not in fallbacks:
            fallbacks[asset.category] = asset.id
    return fallbacks


def normalize_decoration_asset(
    decoration: dict[str, Any],
    approved_asset_ids: set[str],
    fallback_asset_id: str,
    category_fallbacks: dict[str, str],
    asset_by_id: dict[str, AssetItem],
) -> dict[str, Any]:
    next_decoration = dict(decoration)
    normalize_id_alias(next_decoration, "assetId")
    if next_decoration.get("assetId") not in approved_asset_ids:
        asset_id = str(next_decoration.get("assetId", ""))
        asset = asset_by_id.get(asset_id)
        category = asset.category if asset is not None else asset_id.split("_", 1)[0]
        next_decoration["assetId"] = category_fallbacks.get(category, fallback_asset_id)
    return next_decoration


def normalize_decorations(
    decorations: list[dict[str, Any]],
    image_placements: list[dict[str, Any]],
    text_placements: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
) -> list[dict[str, Any]]:
    return place_decorations(decorations, image_placements, text_placements, asset_by_id)


def check_layout_rules(layout: JournalLayout, request: JournalGenerationRequest) -> list[dict[str, Any]]:
    from app.services.layout_rules import check_layout_rules as check_rules

    return check_rules(layout, request)


def rect_from_item(item: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        positive_number(item.get("x"), 0),
        positive_number(item.get("y"), 0),
        positive_number(item.get("width"), 0),
        positive_number(item.get("height"), 0),
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


def clamp_number(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)
