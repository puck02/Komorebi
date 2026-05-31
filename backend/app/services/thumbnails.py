from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image as PillowImage, ImageOps

DISPLAY_MAX_BYTES = 1024 * 1024
DISPLAY_MAX_EDGE = 1600


def generate_thumbnail(original_path: Path, thumbnail_path: Path) -> tuple[int, int]:
    with PillowImage.open(original_path) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        image.thumbnail((512, 512))
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(thumbnail_path, format="WEBP", quality=85)
    return width, height


def generate_display_image(original_path: Path, display_path: Path, max_bytes: int = DISPLAY_MAX_BYTES) -> None:
    with PillowImage.open(original_path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((DISPLAY_MAX_EDGE, DISPLAY_MAX_EDGE))
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        display_path.parent.mkdir(parents=True, exist_ok=True)
        save_webp_under_limit(image, display_path, max_bytes)


def save_webp_under_limit(image: PillowImage.Image, destination: Path, max_bytes: int) -> None:
    candidate = image.copy()
    while True:
        for quality in (86, 80, 74, 68, 62, 56, 50):
            with NamedTemporaryFile(dir=destination.parent, suffix=".webp", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                candidate.save(temp_path, format="WEBP", quality=quality, method=6)
                if temp_path.stat().st_size <= max_bytes:
                    temp_path.replace(destination)
                    return
            finally:
                temp_path.unlink(missing_ok=True)

        next_width = int(candidate.width * 0.85)
        next_height = int(candidate.height * 0.85)
        if next_width < 640 or next_height < 640:
            candidate.save(destination, format="WEBP", quality=45, method=6)
            return
        candidate = candidate.resize((next_width, next_height), PillowImage.Resampling.LANCZOS)
