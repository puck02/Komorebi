from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from math import ceil, isfinite
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem
from app.services.decoration_placement import place_decorations
from app.services.diary_copy import normalize_diary_blocks, normalize_diary_text, normalize_title
from app.services.layout_variants import ALLOWED_SECTION_VARIANTS, build_section_layout
from app.services.style_recipes import choose_asset_id, recipe_tags_for_section
from app.services.story_planner import plan_content_sections, split_evenly

CANVAS_WIDTH = 1080
DEFAULT_CANVAS_HEIGHT = 1440
COMPACT_SECTION_CANVAS_HEIGHT = 1120
CANVAS_BOTTOM_PADDING = 80
TITLE_X = 80
TITLE_Y = 72
TITLE_WIDTH = 760
TITLE_FONT_SIZE = 58
TITLE_FONT_SIZE_MIN = 44
TITLE_FONT_SIZE_MAX = 72
BODY_X = 112
BODY_WIDTH = 820
BODY_FONT_SIZE = 32
BODY_FONT_SIZE_MIN = 24
BODY_FONT_SIZE_MAX = 38
BODY_BLOCK_GAP = 46
TEXT_PHOTO_GAP = 64
SECTION_GAP = 104
CAPTION_FONT_SIZE_MIN = 18
CAPTION_FONT_SIZE_MAX = 28
PHOTO_COLUMN_WIDTH = 420
PHOTO_LEFT_X = 92
PHOTO_RIGHT_X = 568
PHOTO_ROW_GAP = 56
LONG_BODY_SPLIT_TARGET = 58
GENERIC_CAPTIONS = {"今天的照片", "照片说明", "这张照片", "生活片段"}
GENERIC_SECTION_BODIES = {"这一组照片也想好好留下", "今天的照片先放在这里", "今天的照片"}
GENERIC_SECTION_TITLES = {"第一段", "第二段", "第三段", "第四段", "照片小组", "模型乱分组", "A", "B"}


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
    journal_date: date | str | None = None
    location: str | None = None
    mood_tags: list[str] | None = None


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
            journal_date=request.journal_date,
            location=request.location,
            mood_tags=request.mood_tags,
        )

        try:
            raw_layout = self.client.generate_layout(model_request)
        except GenerationError:
            raw_layout = build_fallback_layout(model_request)
            cleaned_layout = sanitize_model_layout(raw_layout, model_request)
            return JournalLayout.model_validate(cleaned_layout)
        try:
            cleaned_layout = sanitize_model_layout(raw_layout, model_request)
            return JournalLayout.model_validate(cleaned_layout)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise GenerationError("Model returned an invalid journal layout") from error


def build_fallback_layout(request: JournalGenerationRequest) -> dict[str, Any]:
    body = request.description.strip() or "今天的照片先放在这里。"
    caption = body.strip(" 。！？!?；;，,")[:14] or "今日小记"
    image_id = request.images[0].id if request.images else "img_1"
    mood_tags = normalized_mood_tags(request)
    captions_by_image = [
        {"imageId": image.id, "text": caption if index == 0 else f"第 {index + 1} 张照片"}
        for index, image in enumerate(request.images)
    ]
    return {
        "canvas": {"width": CANVAS_WIDTH, "height": DEFAULT_CANVAS_HEIGHT, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8", "#d9a98f"], "mood": mood_tags or ["日常"]},
        "content": {
            "title": fallback_title(request),
            "body": [body],
            "captions": captions_by_image or [{"imageId": image_id, "text": caption}],
            "imageUnderstanding": [
                {
                    "imageId": image.id,
                    "summary": caption if index == 0 else f"第 {index + 1} 张照片",
                    "scene": "",
                    "subjects": [],
                    "mood": mood_tags or ["日常"],
                }
                for index, image in enumerate(request.images)
            ],
            "sections": fallback_sections(request, body),
        },
        "layout": {
            "variant": "long_collage",
            "images": [
                {
                    "imageId": image.id,
                    "x": 92,
                    "y": 210,
                    "width": 420,
                    "height": 320,
                    "rotation": 0,
                }
                for image in request.images
            ],
            "texts": [
                {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
                {"role": "body", "x": 112, "y": 620, "width": 820, "fontSize": 32},
            ],
            "decorations": [],
            "sections": [
                {
                    "sectionId": "section_1",
                    "variant": "hero_note",
                    "y": 220,
                    "height": 720,
                    "images": [],
                    "texts": [],
                    "decorations": [
                        {"assetId": "paper_note_cream_01"},
                        {"assetId": "tape_warm_grid_01"},
                        {"assetId": "sticker_leaf_05"},
                    ],
                }
            ],
        },
    }


def fallback_title(request: JournalGenerationRequest) -> str:
    location = str(request.location or "").strip()
    if location:
        return normalize_title(f"{location}小记")
    return "今日小记"


def fallback_sections(request: JournalGenerationRequest, body: str) -> list[dict[str, Any]]:
    mood_tags = normalized_mood_tags(request) or ["日常"]
    if not request.images:
        return [{"id": "section_1", "title": fallback_title(request), "imageIds": ["img_1"], "body": body, "mood": mood_tags}]

    sections: list[dict[str, Any]] = []
    for start in range(0, len(request.images), 3):
        group = request.images[start : start + 3]
        sections.append(
            {
                "id": f"section_{len(sections) + 1}",
                "title": fallback_title(request) if start == 0 else f"第 {start + 1} 张照片",
                "imageIds": [image.id for image in group],
                "body": body if start == 0 else f"第 {start + 1} 张照片也放在这里。",
                "mood": mood_tags,
            }
        )
    return sections


def normalized_mood_tags(request: JournalGenerationRequest) -> list[str]:
    return [str(tag).strip() for tag in request.mood_tags or [] if str(tag).strip()]


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
    content["body"] = normalize_body_content(content.get("body"), request.description)

    image_ids = {image.id for image in request.images}
    approved_asset_ids = [asset.id for asset in request.assets if asset.quality_status == "approved"]
    approved_asset_set = set(approved_asset_ids)

    for placement in layout["layout"].get("images", []):
        normalize_id_alias(placement, "imageId")

    layout["layout"]["images"] = [
        placement for placement in layout["layout"].get("images", []) if placement.get("imageId") in image_ids
    ]
    normalize_image_understanding(layout, request.images)

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
    layout["content"]["captions"] = fill_missing_captions(layout["content"]["captions"], layout["content"]["imageUnderstanding"])

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


def normalize_body_content(body: Any, fallback: str) -> list[str]:
    return normalize_diary_blocks(body, fallback=normalize_diary_text(fallback, fallback="今天的照片先放在这里。"), split_target=LONG_BODY_SPLIT_TARGET)


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


def fill_missing_captions(
    captions: list[dict[str, Any]],
    image_understanding: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    captions_by_id = {caption.get("imageId"): caption for caption in captions}
    next_captions: list[dict[str, Any]] = []
    for item in image_understanding:
        image_id = item.get("imageId")
        if not isinstance(image_id, str):
            continue
        caption = captions_by_id.get(image_id)
        if caption is not None:
            if is_generic_caption(caption.get("text")):
                next_captions.append({"imageId": image_id, "text": caption_from_understanding(item)})
            else:
                next_captions.append(caption)
            continue
        next_captions.append({"imageId": image_id, "text": caption_from_understanding(item)})
    return next_captions


def is_generic_caption(value: Any) -> bool:
    text = str(value or "").strip(" 。！？!?；;，,")
    return text in GENERIC_CAPTIONS


def caption_from_understanding(item: dict[str, Any]) -> str:
    summary = normalize_diary_text(item.get("summary"))
    if summary.startswith("第 ") and "张照片" in summary:
        return summary.split("的", 1)[0][:18]
    if summary and not summary.startswith("第 "):
        return summary[:18]
    subjects = [str(subject).strip() for subject in item.get("subjects") or [] if str(subject).strip()]
    if subjects:
        return "、".join(subjects[:2])[:18]
    scene = normalize_diary_text(item.get("scene"))
    if scene:
        return scene[:18]
    return "今天的照片"


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_content_sections(layout: dict[str, Any], request_images: list[JournalImageInput]) -> list[dict[str, Any]]:
    image_ids = [image.id for image in request_images]
    sections = plan_content_sections(layout, image_ids)
    understanding_by_id = {item.get("imageId"): item for item in layout["content"].get("imageUnderstanding", [])}
    return [
        {
            **section,
            "title": normalize_section_title(section, understanding_by_id, index + 1),
            "body": normalize_section_body(section, understanding_by_id),
        }
        for index, section in enumerate(sections)
    ]


def normalize_section_title(section: dict[str, Any], understanding_by_id: dict[Any, dict[str, Any]], index: int) -> str:
    title = normalize_title(section.get("title"), fallback=f"片段 {index}")
    if not is_generic_section_title(title):
        return title
    for image_id in section.get("imageIds", []):
        if image_id not in understanding_by_id:
            continue
        caption = caption_from_understanding(understanding_by_id[image_id])
        if not is_generic_caption(caption):
            return normalize_title(caption, fallback=title)
    return title


def is_generic_section_title(value: Any) -> bool:
    text = str(value or "").strip(" 。！？!?；;，,")
    return text.startswith("片段 ") or text in GENERIC_SECTION_TITLES


def normalize_section_body(section: dict[str, Any], understanding_by_id: dict[Any, dict[str, Any]]) -> str:
    body = normalize_diary_text(section.get("body"), fallback="这一组照片也想好好留下。")
    section_image_ids = section.get("imageIds", [])
    if not is_generic_section_body(body) and not body_mentions_outside_section(body, section_image_ids, understanding_by_id):
        return body

    summaries = [
        caption_from_understanding(understanding_by_id[image_id])
        for image_id in section_image_ids
        if image_id in understanding_by_id
    ]
    concrete_parts = [summary for summary in summaries if not is_generic_caption(summary)]
    if not concrete_parts:
        return body
    return f"{'、'.join(concrete_parts[:2])}，今天就记这一点。"


def is_generic_section_body(value: Any) -> bool:
    text = str(value or "").strip(" 。！？!?；;，,")
    return text in GENERIC_SECTION_BODIES


def body_mentions_outside_section(
    body: str,
    section_image_ids: list[str],
    understanding_by_id: dict[Any, dict[str, Any]],
) -> bool:
    section_image_id_set = set(section_image_ids)
    for image_id, understanding in understanding_by_id.items():
        if image_id in section_image_id_set:
            continue
        keywords = [caption_from_understanding(understanding)]
        keywords.extend(str(subject).strip() for subject in understanding.get("subjects") or [] if str(subject).strip())
        if any(keyword and keyword in body for keyword in keywords):
            return True
    return False


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
        source_y = positive_number(source.get("y"), next_y)
        y = max(source_y, next_y)
        generated_section = build_section_layout(
            content_section,
            request_images=request_images,
            image_understanding=layout["content"].get("imageUnderstanding", []),
            section_index=index,
            total_sections=len(content_sections),
            start_y=y,
            suggested_variant=suggested_variant,
        )
        section_images = generated_section["images"]
        section_texts = generated_section["texts"]
        for text in section_texts:
            if text.get("role") == "body":
                text["height"] = estimate_paragraph_height(
                    content_section.get("body", ""),
                    positive_number(text.get("fontSize"), BODY_FONT_SIZE),
                    positive_number(text.get("width"), BODY_WIDTH),
                )
        section_decorations = normalize_section_decorations(
            content_section,
            layout["content"].get("imageUnderstanding", []),
            source.get("decorations"),
            decorations,
            section_images,
            section_texts,
            asset_by_id,
            index,
        )
        height = max(
            min_section_height(generated_section, content_section.get("body", "")),
            section_height(section_images, section_texts, section_decorations, y, content_section.get("body", "")),
        )
        variant = source.get("variant") if source.get("variant") in ALLOWED_SECTION_VARIANTS else generated_section["variant"]
        layout_sections.append(
            {
                "sectionId": section_id,
                "variant": str(variant),
                "y": y,
                "height": max(ceil(height), 1),
                "images": section_images,
                "texts": section_texts,
                "decorations": section_decorations,
            }
        )
        next_y = y + max(ceil(height), 1) + SECTION_GAP
    return layout_sections


def fallback_first_section_y(layout: dict[str, Any]) -> float:
    title = next((text for text in layout["layout"].get("texts", []) if text.get("role") == "title"), None)
    if not isinstance(title, dict):
        return TITLE_Y + SECTION_GAP
    return positive_number(title.get("y"), TITLE_Y) + estimate_text_height(title, layout["content"]) + SECTION_GAP


def normalize_section_decorations(
    content_section: dict[str, Any],
    image_understanding: list[dict[str, Any]],
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
                    preferred_tags=recipe_tags_for_section(content_section, image_understanding),
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
        build_template_section_decorations(
            section_images,
            section_texts,
            asset_by_id,
            section_index,
            preferred_tags=recipe_tags_for_section(content_section, image_understanding),
        ),
        section_images,
        section_texts,
        asset_by_id,
    )


def build_template_section_decorations(
    section_images: list[dict[str, Any]],
    section_texts: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
    section_index: int,
    preferred_tags: list[str] | None = None,
    preferred_asset_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not section_images and not section_texts:
        return []

    decorations: list[dict[str, Any]] = []
    recipe_tags = preferred_tags or ["daily", "warm", "collage"]
    paper_id = first_asset_id(asset_by_id, "paper", section_index, recipe_tags, preferred_asset_ids)
    tape_id = first_asset_id(asset_by_id, "tape", section_index, recipe_tags, preferred_asset_ids)
    sticker_id = first_asset_id(asset_by_id, "sticker", section_index, recipe_tags, preferred_asset_ids)
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
    preferred_tags: list[str] | None = None,
    preferred_asset_ids: list[str] | None = None,
) -> str | None:
    return choose_asset_id(asset_by_id, category, offset, preferred_tags or ["daily"], preferred_asset_ids)


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
    body: str = "",
) -> float:
    image_bottom = max_placement_bottom(images, "height")
    decoration_bottom = max_placement_bottom(decorations, "height")
    text_bottom = max(
        (
            positive_number(text.get("y"), 0) + placement_text_height(text, body)
            for text in texts
            if isinstance(text, dict)
        ),
        default=0,
    )
    return max(image_bottom, decoration_bottom, text_bottom, y + 320) - y


def min_section_height(generated_section: dict[str, Any], body: str = "") -> float:
    generated_y = positive_number(generated_section.get("y"), 0)
    return section_height(
        generated_section.get("images", []),
        generated_section.get("texts", []),
        generated_section.get("decorations", []),
        generated_y,
        body,
    )


def placement_text_height(text: dict[str, Any], body: str) -> float:
    font_size = clamp_font_size(text, str(text.get("role") or "body"))
    width = positive_number(text.get("width"), BODY_WIDTH)
    if text.get("role") == "body":
        return estimate_paragraph_height(body, font_size, width)
    return font_size * 2.4


def clamp_font_size(text: dict[str, Any], role: str) -> float:
    font_size = positive_number(text.get("fontSize"), BODY_FONT_SIZE)
    if role == "title":
        return clamp_number(font_size, TITLE_FONT_SIZE_MIN, TITLE_FONT_SIZE_MAX)
    if role == "caption":
        return clamp_number(font_size, CAPTION_FONT_SIZE_MIN, CAPTION_FONT_SIZE_MAX)
    return clamp_number(font_size, BODY_FONT_SIZE_MIN, BODY_FONT_SIZE_MAX)


def normalize_title_text(title: dict[str, Any] | None) -> dict[str, Any]:
    source = title or {}
    return {
        "role": "title",
        "x": clamp_number(positive_number(source.get("x"), TITLE_X), 0, CANVAS_WIDTH - 240),
        "y": positive_number(source.get("y"), TITLE_Y),
        "width": min(positive_number(source.get("width"), TITLE_WIDTH), CANVAS_WIDTH - 120),
        "fontSize": clamp_number(
            positive_number(source.get("fontSize"), TITLE_FONT_SIZE),
            TITLE_FONT_SIZE_MIN,
            TITLE_FONT_SIZE_MAX,
        ),
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
        font_size = clamp_font_size(source, "body")
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
