from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_settings import AiSettings
from app.models.user import User

DEFAULT_AI_SETTINGS_ID = "default"


@dataclass(frozen=True)
class EffectiveAiSettings:
    base_url: str
    api_key: str
    model: str
    review_model: str


def is_admin_user(db: Session, current_user: User) -> bool:
    first_user = db.scalar(select(User).order_by(User.created_at, User.id).limit(1))
    return first_user is not None and first_user.id == current_user.id


def get_saved_ai_settings(db: Session) -> AiSettings | None:
    return db.get(AiSettings, DEFAULT_AI_SETTINGS_ID)


def get_or_create_ai_settings(db: Session) -> AiSettings:
    saved = get_saved_ai_settings(db)
    if saved is not None:
        return saved

    settings = get_settings()
    saved = AiSettings(
        id=DEFAULT_AI_SETTINGS_ID,
        base_url=settings.openai_base_url,
        api_key="",
        model=settings.openai_model,
        review_model=settings.openai_review_model,
    )
    db.add(saved)
    db.flush()
    return saved


def get_effective_ai_settings(db: Session) -> EffectiveAiSettings:
    settings = get_settings()
    saved = get_saved_ai_settings(db)
    if saved is None:
        return EffectiveAiSettings(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            review_model=settings.openai_review_model,
        )

    return EffectiveAiSettings(
        base_url=saved.base_url or settings.openai_base_url,
        api_key=saved.api_key or settings.openai_api_key,
        model=saved.model or settings.openai_model,
        review_model=saved.review_model or settings.openai_review_model,
    )
