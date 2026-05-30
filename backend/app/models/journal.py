from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, Date, DateTime, ForeignKey, JSON, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


journal_images = Table(
    "journal_images",
    Base.metadata,
    Column("journal_id", ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True),
    Column("image_id", ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
)


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    journal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mood_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    layout_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user = relationship("User", back_populates="journals")
    images = relationship("Image", secondary=journal_images, back_populates="journals")
