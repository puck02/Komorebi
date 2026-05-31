import pytest

from app.schemas.journal import JournalLayout
from app.services.assets import get_approved_assets, load_assets
from app.services.journal_generator import GenerationError, JournalGenerationRequest, JournalGenerator, JournalImageInput
from app.services.openai_client import OpenAIConfigurationError, OpenAIJournalClient


def test_generator_returns_valid_journal_layout():
    generator = JournalGenerator(FakeClient(valid_model_json()))
    request = generation_request()

    layout = generator.generate(request)

    assert isinstance(layout, JournalLayout)
    assert layout.canvas.width == 1080
    assert layout.canvas.height == 1440
    assert layout.content.title == "慢下来的周末"


def test_generator_keeps_only_provided_image_ids():
    payload = valid_model_json()
    payload["layout"]["images"].append(
        {
            "imageId": "unknown_image",
            "x": 20,
            "y": 20,
            "width": 200,
            "height": 160,
            "rotation": 0,
        }
    )
    payload["content"]["captions"].append({"imageId": "unknown_image", "text": "不存在的照片"})
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert {placement.image_id for placement in layout.layout.images} == {"img_1"}
    assert {caption.image_id for caption in layout.content.captions} == {"img_1"}


def test_generator_replaces_decorations_with_approved_asset_ids():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "tape_charcoal_12",
            "x": 60,
            "y": 180,
            "width": 220,
            "height": 54,
            "rotation": -8,
        },
        {
            "assetId": "missing_asset",
            "x": 720,
            "y": 120,
            "width": 120,
            "height": 120,
            "rotation": 8,
        },
    ]
    request = generation_request(assets=load_assets())
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(request)

    approved_ids = {asset.id for asset in get_approved_assets()}
    assert layout.layout.decorations
    assert all(decoration.asset_id in approved_ids for decoration in layout.layout.decorations)


def test_invalid_model_json_is_converted_to_generation_error():
    generator = JournalGenerator(FakeClient({"canvas": {"width": 1080, "height": 1440}}))

    with pytest.raises(GenerationError):
        generator.generate(generation_request())


def test_openai_client_requires_api_key_only_when_constructed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(OpenAIConfigurationError):
        OpenAIJournalClient(api_key="")


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def generate_layout(self, request):
        self.request = request
        return self.payload


def generation_request(assets=None):
    return JournalGenerationRequest(
        description="周末一起散步，天气很好，喝了咖啡。",
        images=[JournalImageInput(id="img_1", width=640, height=480)],
        assets=assets or get_approved_assets(tags=["warm", "daily"]),
    )


def valid_model_json():
    return {
        "canvas": {
            "width": 1200,
            "height": 1600,
            "background": "#f8f1e8",
        },
        "theme": {
            "style": "soft-collage",
            "palette": ["#f8f1e8", "#d9a98f", "#8f6b57", "#b9c7aa"],
            "mood": ["warm", "gentle"],
        },
        "content": {
            "title": "慢下来的周末",
            "body": ["照片里是被阳光放慢的一天，咖啡、散步和好天气都刚刚好。"],
            "captions": [{"imageId": "img_1", "text": "午后的咖啡"}],
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
                },
                {
                    "role": "body",
                    "x": 92,
                    "y": 1030,
                    "width": 760,
                    "fontSize": 30,
                },
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
