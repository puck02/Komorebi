import json

import pytest
import httpx

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
    assert layout.canvas.height == 1600
    assert layout.content.title == "慢下来的周末"


def test_generator_expands_canvas_to_fit_long_placements():
    payload = valid_model_json()
    payload["canvas"]["height"] = 1500
    payload["layout"]["images"].append(
        {
            "imageId": "img_1",
            "x": 110,
            "y": 1720,
            "width": 760,
            "height": 520,
            "rotation": 2,
        }
    )
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.canvas.height >= 2320


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


def test_generator_snaps_tape_to_photo_edge():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "tape_warm_grid_01",
            "x": 760,
            "y": 980,
            "width": 320,
            "height": 120,
            "rotation": 28,
        }
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    image = layout.layout.images[0]
    tape = layout.layout.decorations[0]
    assert tape.asset_id == "tape_warm_grid_01"
    assert tape.width <= 260
    assert tape.height <= 70
    assert image.x - tape.width <= tape.x <= image.x + image.width
    assert image.y - tape.height <= tape.y <= image.y + image.height
    assert -12 <= tape.rotation <= 12


def test_generator_removes_stickers_covering_photo_center():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": "sticker_sun_01",
            "x": 220,
            "y": 300,
            "width": 180,
            "height": 180,
            "rotation": 0,
        },
        {
            "assetId": "sticker_cloud_02",
            "x": 760,
            "y": 240,
            "width": 120,
            "height": 90,
            "rotation": 0,
        },
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    assert [decoration.asset_id for decoration in layout.layout.decorations] == ["sticker_cloud_02"]


def test_generator_limits_decoration_density():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {
            "assetId": asset_id,
            "x": 720 + index * 4,
            "y": 160 + index * 18,
            "width": 140,
            "height": 80,
            "rotation": 0,
        }
        for index, asset_id in enumerate(
            [
                "paper_note_cream_01",
                "paper_note_blush_02",
                "paper_note_sage_03",
                "paper_note_sky_04",
                "texture_dots_01",
                "texture_grid_02",
                "texture_wave_03",
                "sticker_cloud_02",
                "sticker_heart_03",
                "sticker_leaf_05",
                "sticker_coffee_06",
                "tape_warm_grid_01",
                "tape_warm_stripe_02",
                "tape_sage_dash_03",
                "tape_blush_dot_04",
            ]
        )
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request(assets=load_assets()))

    assert len(layout.layout.decorations) <= 6


def test_generator_normalizes_common_model_field_variants():
    payload = valid_model_json()
    payload["canvas"]["background"] = {"type": "solid", "color": "#fff7ef"}
    payload["content"].pop("body")
    payload["content"].pop("captions")
    payload["content"]["notes"] = ["把今天的轻松小事收好。"]
    payload["content"]["images"] = [{"id": "img_1", "caption": "温柔的一刻"}]
    payload["layout"]["images"][0]["id"] = payload["layout"]["images"][0].pop("imageId")
    payload["layout"]["decorations"][0]["id"] = payload["layout"]["decorations"][0].pop("assetId")
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(generation_request())

    assert layout.canvas.background == "#fff7ef"
    assert layout.content.body == ["把今天的轻松小事收好。"]
    assert layout.content.captions[0].image_id == "img_1"
    assert layout.layout.images[0].image_id == "img_1"
    assert layout.layout.decorations[0].asset_id == "tape_warm_grid_01"


def test_invalid_model_json_is_converted_to_generation_error():
    generator = JournalGenerator(FakeClient({"canvas": {"width": 1080, "height": 1440}}))

    with pytest.raises(GenerationError):
        generator.generate(generation_request())


def test_openai_client_requires_api_key_only_when_constructed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(OpenAIConfigurationError):
        OpenAIJournalClient(api_key="")


def test_openai_client_uses_configured_base_url(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": json.dumps(valid_model_json())}}]},
        )

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")
    layout = client.generate_layout(generation_request())

    assert client.model == "gpt-5.5"
    assert layout["content"]["title"] == "慢下来的周末"
    assert captured["url"] == "https://provider.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "gpt-5.5"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["trust_env"] is True


def test_openai_client_converts_connection_errors_to_generation_error(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    with pytest.raises(GenerationError, match="AI 服务连接失败"):
        client.generate_layout(generation_request())


def test_openai_client_converts_status_errors_to_generation_error(monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(403, request=request, json={"error": {"message": "blocked"}})

    monkeypatch.setattr("app.services.openai_client.httpx.post", fake_post)
    client = OpenAIJournalClient(api_key="test-key", base_url="https://provider.example/v1")

    with pytest.raises(GenerationError, match="AI 服务返回 403"):
        client.generate_layout(generation_request())


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
