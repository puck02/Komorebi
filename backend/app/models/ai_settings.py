from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AiSettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    base_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    api_key: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="gpt-5.5", nullable=False)
    review_model: Mapped[str] = mapped_column(String(120), default="gpt-5.4-mini", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
