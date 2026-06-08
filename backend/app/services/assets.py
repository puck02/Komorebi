import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"
QUALITY_STATUSES = {"approved", "draft", "rejected"}


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


def load_assets() -> list[AssetItem]:
    manifest_stat = MANIFEST_PATH.stat()
    return _load_assets(str(MANIFEST_PATH), manifest_stat.st_mtime_ns, manifest_stat.st_size)


@lru_cache
def _load_assets(manifest_path: str, _mtime_ns: int, _size: int) -> list[AssetItem]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
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


load_assets.cache_clear = _load_assets.cache_clear


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


def update_asset_quality_status(asset_id: str, quality_status: str) -> AssetItem | None:
    if quality_status not in QUALITY_STATUSES:
        raise ValueError("Unsupported asset quality status")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for item in manifest:
        if item["id"] == asset_id:
            item["qualityStatus"] = quality_status
            MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            load_assets.cache_clear()
            return get_asset(asset_id)

    return None
