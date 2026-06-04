from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JournalCanvas(BaseModel):
    width: int
    height: int = Field(gt=0)
    background: str

    @model_validator(mode="after")
    def validate_canvas_size(self) -> "JournalCanvas":
        if self.width != 1080:
            raise ValueError("Journal canvas width must be 1080")
        return self


class JournalTheme(BaseModel):
    style: str = Field(min_length=1)
    palette: list[str] = Field(min_length=1)
    mood: list[str] = Field(default_factory=list)


class JournalCaption(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_id: str = Field(alias="imageId", min_length=1)
    text: str = Field(min_length=1)


class JournalImageUnderstanding(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_id: str = Field(alias="imageId", min_length=1)
    summary: str = Field(min_length=1)
    scene: str = ""
    subjects: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)


class JournalContentSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    image_ids: list[str] = Field(alias="imageIds", min_length=1)
    body: str = Field(min_length=1)
    mood: list[str] = Field(default_factory=list)


class JournalContent(BaseModel):
    title: str = Field(min_length=1)
    body: list[str] = Field(min_length=1)
    captions: list[JournalCaption] = Field(default_factory=list)
    image_understanding: list[JournalImageUnderstanding] = Field(default_factory=list, alias="imageUnderstanding")
    sections: list[JournalContentSection] = Field(default_factory=list)


class JournalImagePlacement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_id: str = Field(alias="imageId", min_length=1)
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0


class JournalTextPlacement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: Literal["title", "body", "caption"]
    x: float
    y: float
    width: float = Field(gt=0)
    font_size: float = Field(alias="fontSize", gt=0)


class JournalDecoration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(alias="assetId", min_length=1)
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0


class JournalLayoutSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    section_id: str = Field(alias="sectionId", min_length=1)
    variant: str = Field(min_length=1)
    y: float
    height: float = Field(gt=0)
    images: list[JournalImagePlacement] = Field(default_factory=list)
    texts: list[JournalTextPlacement] = Field(default_factory=list)
    decorations: list[JournalDecoration] = Field(default_factory=list)


class JournalLayoutLayer(BaseModel):
    variant: str = Field(min_length=1)
    images: list[JournalImagePlacement] = Field(default_factory=list)
    texts: list[JournalTextPlacement] = Field(default_factory=list)
    decorations: list[JournalDecoration] = Field(default_factory=list)
    sections: list[JournalLayoutSection] = Field(default_factory=list)


class JournalLayout(BaseModel):
    canvas: JournalCanvas
    theme: JournalTheme
    content: JournalContent
    layout: JournalLayoutLayer


class JournalGenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_ids: list[str] = Field(alias="imageIds", min_length=1, max_length=9)
    description: str = Field(min_length=1)
    journal_date: date | None = Field(default=None, alias="journalDate")
    location: str | None = None
    mood_tags: list[str] = Field(default_factory=list, alias="moodTags")


class JournalUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, min_length=1)
    body: list[str] | None = Field(default=None, min_length=1)
    layout_variant: str | None = Field(default=None, alias="layoutVariant", min_length=1)


class JournalRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    input_text: str = Field(alias="inputText")
    journal_date: date | None = Field(alias="journalDate")
    location: str | None
    mood_tags: list[str] = Field(alias="moodTags")
    layout: dict
    image_ids: list[str] = Field(alias="imageIds")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
