from datetime import datetime

from pydantic import BaseModel


class ImageRead(BaseModel):
    id: str
    content_type: str
    width: int
    height: int
    file_url: str
    display_url: str
    thumbnail_url: str
    created_at: datetime
