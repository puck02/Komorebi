from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.admin import AdminPermissionsRead, AiConnectionTestRead, AiSettingsRead, AiSettingsUpdate
from app.services.admin import get_effective_ai_settings, get_or_create_ai_settings, is_admin_user, test_ai_service_connection

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/permissions/me", response_model=AdminPermissionsRead)
def read_admin_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminPermissionsRead:
    return AdminPermissionsRead(canManageAiSettings=is_admin_user(db, current_user))


@router.get("/ai-settings", response_model=AiSettingsRead)
def read_ai_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiSettingsRead:
    ensure_admin(db, current_user)
    effective_settings = get_effective_ai_settings(db)
    return AiSettingsRead(
        baseUrl=effective_settings.base_url,
        hasApiKey=bool(effective_settings.api_key),
        model=effective_settings.model,
        reviewModel=effective_settings.review_model,
    )


@router.patch("/ai-settings", response_model=AiSettingsRead)
def update_ai_settings(
    payload: AiSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiSettingsRead:
    ensure_admin(db, current_user)
    settings = get_or_create_ai_settings(db)
    if payload.base_url is not None:
        settings.base_url = payload.base_url
    if payload.api_key:
        settings.api_key = payload.api_key
    if payload.model is not None:
        settings.model = payload.model
    if payload.review_model is not None:
        settings.review_model = payload.review_model
    db.commit()
    effective_settings = get_effective_ai_settings(db)
    return AiSettingsRead(
        baseUrl=effective_settings.base_url,
        hasApiKey=bool(effective_settings.api_key),
        model=effective_settings.model,
        reviewModel=effective_settings.review_model,
    )


@router.post("/ai-settings/test", response_model=AiConnectionTestRead)
def test_ai_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiConnectionTestRead:
    ensure_admin(db, current_user)
    return test_ai_service_connection(db)


def ensure_admin(db: Session, current_user: User) -> None:
    if not is_admin_user(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the administrator can manage AI settings")
