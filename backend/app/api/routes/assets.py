from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.asset import AssetPermissionsRead, AssetQualityStatusUpdate, AssetRead
from app.services.admin import is_admin_user
from app.services.assets import AssetItem, get_asset, get_approved_assets, load_assets, update_asset_quality_status

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


@router.get("/permissions/me", response_model=AssetPermissionsRead)
def read_asset_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetPermissionsRead:
    return AssetPermissionsRead(can_manage_assets=is_admin_user(db, current_user))


@router.patch("/{asset_id}/quality-status", response_model=AssetRead)
def update_asset_status(
    asset_id: str,
    payload: AssetQualityStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetRead:
    if not is_admin_user(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the asset administrator can update assets")

    try:
        asset = update_asset_quality_status(asset_id, payload.quality_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported asset quality status") from exc

    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset_to_read(asset)


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
