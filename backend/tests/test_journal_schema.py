import pytest
from pydantic import ValidationError

from app.schemas.journal import JournalLayout


def test_valid_journal_layout_accepts_fixed_canvas_size():
    layout = JournalLayout.model_validate(valid_layout())

    assert layout.canvas.width == 1080
    assert layout.canvas.height == 1440
    assert layout.content.title == "周末小记"
    assert layout.layout.images[0].image_id == "img_1"
    assert layout.layout.decorations[0].asset_id == "tape_warm_grid_01"


def test_journal_layout_rejects_unsupported_canvas_size():
    payload = valid_layout()
    payload["canvas"]["width"] = 1200

    with pytest.raises(ValidationError):
        JournalLayout.model_validate(payload)


def test_journal_layout_requires_title():
    payload = valid_layout()
    del payload["content"]["title"]

    with pytest.raises(ValidationError):
        JournalLayout.model_validate(payload)


def valid_layout():
    return {
        "canvas": {
            "width": 1080,
            "height": 1440,
            "background": "#f8f1e8",
        },
        "theme": {
            "style": "soft-collage",
            "palette": ["#f8f1e8", "#d9a98f", "#8f6b57", "#b9c7aa"],
            "mood": ["warm", "gentle"],
        },
        "content": {
            "title": "周末小记",
            "body": ["今天的风很轻，照片里都是慢下来的瞬间。"],
            "captions": [{"imageId": "img_1", "text": "海边的傍晚"}],
        },
        "layout": {
            "variant": "collage_a",
            "images": [
                {
                    "imageId": "img_1",
                    "x": 92,
                    "y": 210,
                    "width": 420,
                    "height": 320,
                    "rotation": -3,
                }
            ],
            "texts": [
                {
                    "role": "title",
                    "x": 80,
                    "y": 72,
                    "width": 680,
                    "fontSize": 56,
                }
            ],
            "decorations": [
                {
                    "assetId": "tape_warm_grid_01",
                    "x": 60,
                    "y": 180,
                    "width": 220,
                    "height": 54,
                    "rotation": -8,
                }
            ],
        },
    }
