from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem


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
    layout["canvas"]["width"] = 1080
    layout["canvas"]["height"] = 1440

    image_ids = {image.id for image in request.images}
    approved_asset_ids = [asset.id for asset in request.assets if asset.quality_status == "approved"]
    approved_asset_set = set(approved_asset_ids)

    layout["layout"]["images"] = [
        placement for placement in layout["layout"].get("images", []) if placement.get("imageId") in image_ids
    ]
    layout["content"]["captions"] = [
        caption for caption in layout["content"].get("captions", []) if caption.get("imageId") in image_ids
    ]

    if approved_asset_ids:
        fallback_asset_id = approved_asset_ids[0]
        layout["layout"]["decorations"] = [
            normalize_decoration_asset(decoration, approved_asset_set, fallback_asset_id)
            for decoration in layout["layout"].get("decorations", [])
        ]
    else:
        layout["layout"]["decorations"] = []

    return layout


def normalize_decoration_asset(decoration: dict[str, Any], approved_asset_ids: set[str], fallback_asset_id: str) -> dict[str, Any]:
    next_decoration = dict(decoration)
    if next_decoration.get("assetId") not in approved_asset_ids:
        next_decoration["assetId"] = fallback_asset_id
    return next_decoration
