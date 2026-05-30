from pathlib import Path

from PIL import Image as PillowImage


def generate_thumbnail(original_path: Path, thumbnail_path: Path) -> tuple[int, int]:
    with PillowImage.open(original_path) as image:
        width, height = image.size
        image.thumbnail((512, 512))
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(thumbnail_path, format="WEBP", quality=85)
    return width, height
