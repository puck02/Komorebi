from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj

from fastapi import UploadFile

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@dataclass(frozen=True)
class ImagePaths:
    directory: Path
    original: Path
    thumbnail: Path


def extension_for_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    return SUPPORTED_IMAGE_TYPES.get(content_type)


def build_image_paths(storage_root: str, user_id: str, image_id: str, extension: str) -> ImagePaths:
    directory = Path(storage_root) / "users" / user_id / "images" / image_id
    return ImagePaths(
        directory=directory,
        original=directory / f"original.{extension}",
        thumbnail=directory / "thumb.webp",
    )


def save_upload_file(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    upload.file.seek(0)
    with destination.open("wb") as output:
        copyfileobj(upload.file, output)
