import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"


@dataclass(frozen=True)
class AssetItem:
    id: str
    name: str
    category: str
    tags: list[str]
    style: list[str]
    colors: list[str]
    file: str
    license: str
    source: str
    quality_status: str

    @property
    def file_path(self) -> Path:
        return ASSET_ROOT / self.file


@lru_cache
def load_assets() -> list[AssetItem]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [
        AssetItem(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            tags=item["tags"],
            style=item["style"],
            colors=item["colors"],
            file=item["file"],
            license=item["license"],
            source=item["source"],
            quality_status=item["qualityStatus"],
        )
        for item in manifest
    ]


def get_asset(asset_id: str) -> AssetItem | None:
    return next((asset for asset in load_assets() if asset.id == asset_id), None)


def get_approved_assets(tags: list[str] | None = None, category: str | None = None) -> list[AssetItem]:
    required_tags = set(tags or [])
    assets = [asset for asset in load_assets() if asset.quality_status == "approved"]
    if category is not None:
        assets = [asset for asset in assets if asset.category == category]
    if required_tags:
        assets = [asset for asset in assets if required_tags.intersection(asset.tags)]
    return assets
