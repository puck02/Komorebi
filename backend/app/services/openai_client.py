import json
from typing import Any

from openai import APIStatusError, OpenAI, OpenAIError

from app.core.config import get_settings
from app.services.journal_generator import GenerationError, JournalGenerationRequest


class OpenAIConfigurationError(RuntimeError):
    pass


class OpenAIJournalClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = base_url if base_url is not None else settings.openai_base_url
        self.model = model or settings.openai_model
        if not self.api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is required to generate journals")
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)

    def generate_layout(self, request: JournalGenerationRequest) -> dict[str, Any]:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=build_generation_prompt(request),
                text={"format": {"type": "json_object"}},
            )
        except APIStatusError as exc:
            raise GenerationError(f"AI 服务返回 {exc.status_code}，请检查模型、Key 或第三方渠道配置") from exc
        except OpenAIError as exc:
            raise GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置") from exc
        return json.loads(response.output_text)


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
    return (
        "你是一个温柔拼贴风格的日记手帐排版助手。"
        "请只返回 JSON，不要返回 Markdown。"
        "画布必须是 1080 x 1440。"
        "只能使用给定 image id 和 asset id。"
        "返回结构必须包含 canvas、theme、content、layout。"
        f"\n用户描述：{request.description}"
        f"\n图片：{json.dumps(images, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )
