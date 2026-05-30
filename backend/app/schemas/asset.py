from pydantic import BaseModel


class AssetRead(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    style: list[str]
    colors: list[str]
    file: str
    file_url: str
    license: str
    source: str
    quality_status: str
