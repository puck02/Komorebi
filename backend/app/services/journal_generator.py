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

    if approved_asset_ids:
        fallback_asset_id = approved_asset_ids[0]
        layout["layout"]["decorations"] = [
            normalize_decoration_asset(decoration, approved_asset_set, fallback_asset_id)
            for decoration in layout["layout"].get("decorations", [])
        ]
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
