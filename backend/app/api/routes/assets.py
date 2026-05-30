from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.schemas.asset import AssetRead
from app.services.assets import AssetItem, get_asset, get_approved_assets, load_assets

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(
    category: str | None = None,
    tag: list[str] = Query(default_factory=list),
    approved_only: bool = False,
) -> list[AssetRead]:
    assets = get_approved_assets(tags=tag, category=category) if approved_only else load_assets()
    if category is not None and not approved_only:
        assets = [asset for asset in assets if asset.category == category]
    if tag and not approved_only:
        required_tags = set(tag)
        assets = [asset for asset in assets if required_tags.intersection(asset.tags)]
    return [asset_to_read(asset) for asset in assets]


@router.get("/{asset_id}", response_model=AssetRead)
def read_asset(asset_id: str) -> AssetRead:
    asset = get_asset_or_404(asset_id)
    return asset_to_read(asset)


@router.get("/{asset_id}/file")
def read_asset_file(asset_id: str) -> FileResponse:
    asset = get_asset_or_404(asset_id)
    return FileResponse(asset.file_path, media_type="image/svg+xml")


def get_asset_or_404(asset_id: str) -> AssetItem:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


def asset_to_read(asset: AssetItem) -> AssetRead:
    return AssetRead(
        id=asset.id,
        name=asset.name,
        category=asset.category,
        tags=asset.tags,
        style=asset.style,
        colors=asset.colors,
        file=asset.file,
        file_url=f"/api/assets/{asset.id}/file",
        license=asset.license,
        source=asset.source,
        quality_status=asset.quality_status,
    )
