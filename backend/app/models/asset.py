from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    style: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    colors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    file: Mapped[str] = mapped_column(String(512), nullable=False)
    license: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
