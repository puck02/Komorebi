from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JournalCanvas(BaseModel):
    width: int
    height: int
    background: str

    @model_validator(mode="after")
    def validate_canvas_size(self) -> "JournalCanvas":
        if self.width != 1080 or self.height != 1440:
            raise ValueError("Journal canvas must be 1080 x 1440")
        return self


class JournalTheme(BaseModel):
    style: str = Field(min_length=1)
    palette: list[str] = Field(min_length=1)
    mood: list[str] = Field(default_factory=list)


class JournalCaption(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_id: str = Field(alias="imageId", min_length=1)
    text: str = Field(min_length=1)


class JournalContent(BaseModel):
    title: str = Field(min_length=1)
    body: list[str] = Field(min_length=1)
    captions: list[JournalCaption] = Field(default_factory=list)


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


class JournalLayoutLayer(BaseModel):
    variant: str = Field(min_length=1)
    images: list[JournalImagePlacement] = Field(default_factory=list)
    texts: list[JournalTextPlacement] = Field(default_factory=list)
    decorations: list[JournalDecoration] = Field(default_factory=list)


class JournalLayout(BaseModel):
    canvas: JournalCanvas
    theme: JournalTheme
    content: JournalContent
    layout: JournalLayoutLayer
