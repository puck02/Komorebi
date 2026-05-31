from copy import deepcopy
from dataclasses import dataclass
from math import ceil, isfinite
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem

CANVAS_WIDTH = 1080
DEFAULT_CANVAS_HEIGHT = 1440
CANVAS_BOTTOM_PADDING = 80
PHOTO_SAFE_INSET_RATIO = 0.18
TAPE_MAX_WIDTH = 260
TAPE_MAX_HEIGHT = 70
TAPE_MIN_WIDTH = 150
TAPE_MIN_HEIGHT = 38
MAX_DECORATIONS = 6
DECORATION_CATEGORY_LIMITS = {
    "paper": 1,
    "sticker": 2,
    "tape": 3,
    "texture": 1,
}


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class JournalImageInput:
    id: str
    width: int
    height: int


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
    layout["content"]["captions"] = [caption for caption in captions if caption.get("imageId") in image_ids]

    asset_by_id = {asset.id: asset for asset in request.assets}

    if approved_asset_ids:
        fallback_asset_id = approved_asset_ids[0]
        normalized_decorations = [
            normalize_decoration_asset(decoration, approved_asset_set, fallback_asset_id)
            for decoration in layout["layout"].get("decorations", [])
        ]
        layout["layout"]["decorations"] = normalize_decorations(
            normalized_decorations,
            layout["layout"].get("images", []),
            asset_by_id,
        )
    else:
        layout["layout"]["decorations"] = []

    layout["canvas"]["height"] = normalize_canvas_height(layout)
    return layout


def normalize_canvas_height(layout: dict[str, Any]) -> int:
    canvas_height = positive_number(layout["canvas"].get("height"), DEFAULT_CANVAS_HEIGHT)
    placement_bottom = max_placement_bottom(layout["layout"].get("images", []), "height") + CANVAS_BOTTOM_PADDING
    decoration_bottom = max_placement_bottom(layout["layout"].get("decorations", []), "height") + CANVAS_BOTTOM_PADDING
    text_bottom = max_text_bottom(layout["layout"].get("texts", []), layout["content"]) + CANVAS_BOTTOM_PADDING
    return ceil(max(DEFAULT_CANVAS_HEIGHT, canvas_height, placement_bottom, decoration_bottom, text_bottom))


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


def normalize_decoration_asset(decoration: dict[str, Any], approved_asset_ids: set[str], fallback_asset_id: str) -> dict[str, Any]:
    next_decoration = dict(decoration)
    normalize_id_alias(next_decoration, "assetId")
    if next_decoration.get("assetId") not in approved_asset_ids:
        next_decoration["assetId"] = fallback_asset_id
    return next_decoration


def normalize_decorations(
    decorations: list[dict[str, Any]],
    image_placements: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for decoration in decorations:
        asset = asset_by_id.get(str(decoration.get("assetId")))
        category = asset.category if asset is not None else ""
        if category == "tape":
            normalized.append(snap_tape_to_photo_edge(decoration, image_placements))
            continue
        if category == "sticker" and overlaps_any_photo_safe_area(decoration, image_placements):
            continue
        normalized.append(clamp_decoration_to_canvas(decoration))
    return limit_decoration_density(normalized, asset_by_id)


def limit_decoration_density(decorations: list[dict[str, Any]], asset_by_id: dict[str, AssetItem]) -> list[dict[str, Any]]:
    limited: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for decoration in decorations:
        asset = asset_by_id.get(str(decoration.get("assetId")))
        category = asset.category if asset is not None else "unknown"
        category_limit = DECORATION_CATEGORY_LIMITS.get(category, 1)
        if category_counts.get(category, 0) >= category_limit:
            continue
        if len(limited) >= MAX_DECORATIONS:
            break
        category_counts[category] = category_counts.get(category, 0) + 1
        limited.append(decoration)
    return limited


def snap_tape_to_photo_edge(decoration: dict[str, Any], image_placements: list[dict[str, Any]]) -> dict[str, Any]:
    if not image_placements:
        return clamp_decoration_to_canvas(decoration)

    target = nearest_image_placement(decoration, image_placements)
    tape_width = min(max(positive_number(decoration.get("width"), 210), TAPE_MIN_WIDTH), TAPE_MAX_WIDTH)
    tape_height = min(max(positive_number(decoration.get("height"), 52), TAPE_MIN_HEIGHT), TAPE_MAX_HEIGHT)
    image_x = positive_number(target.get("x"), 0)
    image_y = positive_number(target.get("y"), 0)
    image_width = positive_number(target.get("width"), 1)
    image_height = positive_number(target.get("height"), 1)
    decoration_center_x = positive_number(decoration.get("x"), image_x) + tape_width / 2
    decoration_center_y = positive_number(decoration.get("y"), image_y) + tape_height / 2
    image_center_x = image_x + image_width / 2
    image_center_y = image_y + image_height / 2
    use_left_anchor = decoration_center_x <= image_center_x
    use_top_anchor = decoration_center_y <= image_center_y

    next_decoration = dict(decoration)
    next_decoration["width"] = tape_width
    next_decoration["height"] = tape_height
    next_decoration["x"] = image_x + (image_width * 0.12 if use_left_anchor else image_width * 0.68 - tape_width)
    next_decoration["y"] = image_y - tape_height * 0.45 if use_top_anchor else image_y + image_height - tape_height * 0.55
    fallback_rotation = -8 if use_left_anchor else 8
    next_decoration["rotation"] = clamp_number(positive_number(decoration.get("rotation"), fallback_rotation), -12, 12)
    return clamp_decoration_to_canvas(next_decoration)


def nearest_image_placement(decoration: dict[str, Any], image_placements: list[dict[str, Any]]) -> dict[str, Any]:
    decoration_center_x = positive_number(decoration.get("x"), 0) + positive_number(decoration.get("width"), 0) / 2
    decoration_center_y = positive_number(decoration.get("y"), 0) + positive_number(decoration.get("height"), 0) / 2

    def distance_squared(image: dict[str, Any]) -> float:
        image_center_x = positive_number(image.get("x"), 0) + positive_number(image.get("width"), 0) / 2
        image_center_y = positive_number(image.get("y"), 0) + positive_number(image.get("height"), 0) / 2
        return (decoration_center_x - image_center_x) ** 2 + (decoration_center_y - image_center_y) ** 2

    return min(image_placements, key=distance_squared)


def overlaps_any_photo_safe_area(decoration: dict[str, Any], image_placements: list[dict[str, Any]]) -> bool:
    decoration_rect = rect_from_item(decoration)
    return any(rects_overlap(decoration_rect, photo_safe_rect(image)) for image in image_placements)


def photo_safe_rect(image: dict[str, Any]) -> tuple[float, float, float, float]:
    x = positive_number(image.get("x"), 0)
    y = positive_number(image.get("y"), 0)
    width = positive_number(image.get("width"), 0)
    height = positive_number(image.get("height"), 0)
    inset_x = width * PHOTO_SAFE_INSET_RATIO
    inset_y = height * PHOTO_SAFE_INSET_RATIO
    return (x + inset_x, y + inset_y, width - inset_x * 2, height - inset_y * 2)


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


def clamp_decoration_to_canvas(decoration: dict[str, Any]) -> dict[str, Any]:
    next_decoration = dict(decoration)
    width = positive_number(next_decoration.get("width"), 1)
    next_decoration["x"] = clamp_number(positive_number(next_decoration.get("x"), 0), 0, max(CANVAS_WIDTH - width, 0))
    next_decoration["y"] = max(positive_number(next_decoration.get("y"), 0), 0)
    return next_decoration


def clamp_number(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)
