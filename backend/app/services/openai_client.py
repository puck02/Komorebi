import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.journal_generator import GenerationError, JournalGenerationRequest

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_TIMEOUT_SECONDS = 120


class OpenAIConfigurationError(RuntimeError):
    pass


class OpenAIJournalClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = (base_url if base_url is not None else settings.openai_base_url) or DEFAULT_OPENAI_BASE_URL
        self.model = model or settings.openai_model
        if not self.api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is required to generate journals")

    def generate_layout(self, request: JournalGenerationRequest) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": build_generation_prompt(request)}],
                    "response_format": {"type": "json_object"},
                },
                timeout=OPENAI_TIMEOUT_SECONDS,
                trust_env=True,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GenerationError(f"AI 服务返回 {exc.response.status_code}，请检查模型、Key 或第三方渠道配置") from exc
        except httpx.RequestError as exc:
            raise GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置") from exc

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)


def build_generation_prompt(request: JournalGenerationRequest) -> str:
    images = [{"id": image.id, "width": image.width, "height": image.height} for image in request.images]
    assets = [
        {
            "id": asset.id,
            "category": asset.category,
            "tags": asset.tags,
            "style": asset.style,
            "colors": asset.colors,
        }
        for asset in request.assets
    ]
    schema_example = {
        "canvas": {"width": 1080, "height": 2400, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8", "#d9a98f"], "mood": ["温柔"]},
        "content": {
            "title": "慢下来的周末",
            "body": ["一段温柔的正文。"],
            "captions": [{"imageId": images[0]["id"] if images else "image_id", "text": "照片说明"}],
        },
        "layout": {
            "variant": "long_collage",
            "images": [
                {
                    "imageId": images[0]["id"] if images else "image_id",
                    "x": 92,
                    "y": 210,
                    "width": 420,
                    "height": 320,
                    "rotation": -3,
                }
            ],
            "texts": [{"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56}],
            "decorations": [
                {
                    "assetId": assets[0]["id"] if assets else "asset_id",
                    "x": 60,
                    "y": 180,
                    "width": 220,
                    "height": 54,
                    "rotation": -8,
                }
            ],
        },
    }
    return (
        "你是一个温柔拼贴风格的日记手帐排版助手。"
        "请只返回一个严格 JSON 对象，不要返回 Markdown。"
        "必须完全使用下面的字段结构和 camelCase 字段名，不要增加 subtitle、notes、safe_margin、typography、content.images 等额外结构。"
        "canvas.background 必须是颜色字符串，不能是对象。"
        "content.body 必须是字符串数组。content.captions 必须使用 imageId 和 text。"
        "layout.images 必须使用 imageId。layout.decorations 必须使用 assetId。"
        "layout.texts.role 只能是 title、body 或 caption。"
        "画布宽度必须是 1080，高度必须按内容多少生成竖向长图，不能固定为 1440。"
        "所有图片、文字和装饰都必须落在 0 到 canvas.height 范围内，内容多时让 canvas.height 继续向下延伸。"
        "素材使用必须符合语义：tape 只能作为胶带贴在照片边缘或四角；paper 只能作为底纸或文字背景，不能盖住照片主体；"
        "sticker 只能放在照片外侧空白区或轻微压住照片边缘，不能遮挡照片中心；texture 只能作为背景纹理。"
        "最终效果是一张可纵向滚动的完整手帐长图，而不是右侧附加正文。只能使用给定 image id 和 asset id。"
        f"\n返回 JSON 示例：{json.dumps(schema_example, ensure_ascii=False)}"
        f"\n用户描述：{request.description}"
        f"\n图片：{json.dumps(images, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )
