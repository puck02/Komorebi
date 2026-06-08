import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.agent_observability import log_agent_event
from app.services.assets import AssetItem
from app.services.journal_generator import GenerationError, JournalGenerationRequest

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_TIMEOUT_SECONDS = 300
OPENAI_MAX_ATTEMPTS = 2


class OpenAIConfigurationError(RuntimeError):
    pass


class OpenAIJournalClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        review_model: str | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = (base_url if base_url is not None else settings.openai_base_url) or DEFAULT_OPENAI_BASE_URL
        self.model = model or settings.openai_model
        self.review_model = review_model or settings.openai_review_model
        if not self.api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is required to generate journals")

    def generate_layout(self, request: JournalGenerationRequest) -> dict[str, Any]:
        return self._post_json(self.model, build_generation_message_content(request))

    def review_layout(
        self,
        request: JournalGenerationRequest,
        layout: dict[str, Any],
        screenshot_data_url: str,
        rule_issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        content = [
            {"type": "text", "text": build_review_prompt(request, layout, rule_issues)},
            {"type": "image_url", "image_url": {"url": screenshot_data_url}},
            *source_image_parts(request),
        ]
        return self._post_json(self.review_model, content)

    def revise_layout(
        self,
        request: JournalGenerationRequest,
        layout: dict[str, Any],
        screenshot_data_url: str,
        review: dict[str, Any],
        revision_round: int,
        best_score: float,
    ) -> dict[str, Any]:
        content = [
            {
                "type": "text",
                "text": build_revision_prompt(request, layout, review, revision_round, best_score),
            },
            {"type": "image_url", "image_url": {"url": screenshot_data_url}},
            *source_image_parts(request),
        ]
        return self._post_json(self.model, content)

    def _post_json(self, model: str, content: str | list[dict[str, Any]]) -> dict[str, Any]:
        for attempt in range(1, OPENAI_MAX_ATTEMPTS + 1):
            try:
                response = httpx.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": content}],
                        "response_format": {"type": "json_object"},
                    },
                    timeout=OPENAI_TIMEOUT_SECONDS,
                    trust_env=True,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                raise GenerationError(f"AI 服务返回 {exc.response.status_code}，请检查模型、Key 或第三方渠道配置") from exc
            except httpx.RequestError as exc:
                log_agent_event(
                    "openai.request_error",
                    attempt=attempt,
                    max_attempts=OPENAI_MAX_ATTEMPTS,
                    model=model,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc) or exc.__class__.__name__,
                )
                if attempt == OPENAI_MAX_ATTEMPTS:
                    raise GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置") from exc

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)


def build_generation_message_content(request: JournalGenerationRequest) -> str | list[dict[str, Any]]:
    prompt = build_generation_prompt(request)
    image_parts = source_image_parts(request)
    if not image_parts:
        return prompt
    return [{"type": "text", "text": prompt}, *image_parts]


def source_image_parts(request: JournalGenerationRequest) -> list[dict[str, Any]]:
    return [
        {"type": "image_url", "image_url": {"url": image.data_url}}
        for image in request.images
        if image.data_url
    ]


def build_generation_prompt(request: JournalGenerationRequest) -> str:
    images = [
        {"id": image.id, "order": index + 1, "width": image.width, "height": image.height}
        for index, image in enumerate(request.images)
    ]
    assets = [
        {
            "id": asset.id,
            "category": asset.category,
            "tags": asset.tags,
            "style": asset.style,
            "colors": asset.colors,
        }
        for asset in order_assets_for_ai(request.assets)
    ]
    schema_example = {
        "canvas": {"width": 1080, "height": 2400, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8", "#d9a98f"], "mood": ["温柔"]},
        "content": {
            "title": "慢下来的周末",
            "body": ["咖啡和阳光是一组，像把早晨轻轻摊开。", "散步的照片放在一起，留下慢下来的路。"],
            "captions": [{"imageId": images[0]["id"] if images else "image_id", "text": "照片说明"}],
            "imageUnderstanding": [
                {
                    "imageId": images[0]["id"] if images else "image_id",
                    "summary": "窗边有一杯咖啡，光线很暖。",
                    "scene": "咖啡店",
                    "subjects": ["咖啡", "窗边"],
                    "mood": ["放松", "温柔"],
                }
            ],
            "sections": [
                {
                    "id": "section_1",
                    "title": "窗边的下午",
                    "imageIds": [images[0]["id"] if images else "image_id"],
                    "body": "咖啡和阳光是一组，像把早晨轻轻摊开。",
                    "mood": ["温柔", "日常"],
                }
            ],
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
            "texts": [
                {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
                {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32},
                {"role": "body", "x": 112, "y": 1360, "width": 820, "fontSize": 32},
            ],
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
            "sections": [
                {
                    "sectionId": "section_1",
                    "variant": "hero_note",
                    "y": 180,
                    "height": 620,
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
                    "texts": [{"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}],
                    "decorations": [],
                }
            ],
        },
    }
    return (
        "你是一个温柔拼贴风格的日记手帐排版助手。"
        "请只返回一个严格 JSON 对象，不要返回 Markdown。"
        "必须完全使用下面的字段结构和 camelCase 字段名，不要增加 subtitle、notes、safe_margin、typography、content.images 等额外结构。"
        "canvas.background 必须是颜色字符串，不能是对象。"
        "文字要像真实的日记记录，像本人当天随手写下来的具体短句，可以自然、口语一点。"
        "优先写可从图片或用户描述中确认的小细节，例如咖啡还热着、路灯亮了、车站等了十分钟。"
        "不要写成 AI 总结，不要写宣传文案，不要堆砌“被温柔包裹”“治愈”“仪式感”“把时光收藏”等套话。"
        "不要替用户发明没有证据的地点、关系、天气或情绪；不确定时写成观察到的画面。"
        "图片数组顺序就是用户上传或拖拽排序后的顺序，必须尊重这个顺序，不要自行重排。"
        "生成文字时要结合图片实际可见内容和用户描述；每段正文、每条 caption 都要和对应照片或照片组对得上，不能张冠李戴。"
        "必须先逐张理解图片，并在 content.imageUnderstanding 中为每张图片输出 imageId、summary、scene、subjects、mood。"
        "imageUnderstanding 必须覆盖全部图片，顺序必须和图片 order 一致，summary 只能描述对应 imageId 的真实可见内容。"
        "必须输出 content.sections 和 layout.sections。只允许把相邻图片合并成章节，禁止把不相邻的图片强行放进同一章节。"
        "content.sections 每项字段为 id、title、imageIds、body、mood；每章绑定 1 到 3 张图片，body 为 30 到 80 字自然日记。"
        "layout.sections 每项字段为 sectionId、variant、y、height、images、texts、decorations；sectionId 必须对应 content.sections 的 id。"
        "layout.sections[].variant 只能从 hero_note、staggered_collage、timeline_strip、photo_wall、magazine_whitespace、ticket_memo 中选择；"
        "单张主图适合 hero_note，错落多图适合 staggered_collage，过程顺序适合 timeline_strip，相似照片组适合 photo_wall，安静留白适合 magazine_whitespace，咖啡展览票据类适合 ticket_memo。"
        "content.body 必须是字符串数组，不能只写一大段；请按照片主题、场景或时间分成 2 到 4 段短文字，每段 1 到 2 句。"
        "如果照片天然能分成几类，就让 content.body 的段落数量尽量对应这些类别。content.captions 必须使用 imageId 和 text。"
        "content.captions 的顺序应尽量跟图片 order 一致，caption 只能描述对应 imageId 的照片内容。"
        "layout.images 必须使用 imageId，排列顺序应尽量按照图片 order 从上到下、从左到右展开。layout.decorations 必须使用 assetId。"
        "layout.texts.role 只能是 title、body 或 caption；每一段 content.body 都应该对应一个单独的 body 文本框。"
        "画布宽度必须是 1080，高度必须按内容多少生成竖向长图，不能固定为 1440。"
        "图片不要排得太密，图片组、文字块和装饰之间要留出明显呼吸感；内容多时让 canvas.height 继续向下延伸。"
        "所有图片、文字和装饰都必须落在 0 到 canvas.height 范围内，文字框不能和图片重叠。"
        "layout.decorations 请生成 12 到 22 个装饰，照片多或画布长时接近上限，照片少时也要有层次。"
        "装饰要分布在标题、照片组、正文段落和页脚附近，尽量不要重复 assetId。"
        "如果可用素材里有外部素材，请在贴纸类装饰中自然混入外部素材，让导入素材库的丰富度体现出来。"
        "素材使用必须符合语义：tape 只能作为胶带贴在照片边缘或四角；paper 只能作为底纸或文字背景，不能盖住照片主体；"
        "sticker 只能放在照片外侧空白区或轻微压住照片边缘，不能遮挡照片中心；texture 只能作为背景纹理。"
        "最终效果是一张可纵向滚动的完整手帐长图，而不是右侧附加正文。只能使用给定 image id 和 asset id。"
        f"\n返回 JSON 示例：{json.dumps(schema_example, ensure_ascii=False)}"
        f"\n用户描述：{request.description}"
        f"\n图片：{json.dumps(images, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )


def order_assets_for_ai(assets: list[AssetItem]) -> list[AssetItem]:
    internal_assets = [asset for asset in assets if asset.source == "internal"]
    external_assets = [asset for asset in assets if asset.source != "internal"]
    ordered_assets: list[AssetItem] = []
    for index in range(max(len(internal_assets), len(external_assets))):
        if index < len(internal_assets):
            ordered_assets.append(internal_assets[index])
        if index < len(external_assets):
            ordered_assets.append(external_assets[index])
    return ordered_assets


def build_review_prompt(
    request: JournalGenerationRequest,
    layout: dict[str, Any],
    rule_issues: list[dict[str, Any]],
) -> str:
    image_order = [{"imageId": image.id, "order": index + 1} for index, image in enumerate(request.images)]
    return (
        "你是严格但克制的手帐视觉评审器。只评审当前手帐，不要修改 JSON。"
        "第一张图片是当前手帐截图，后续图片是按用户确认顺序排列的原图展示图。"
        "必须对照原图编号检查正文和 caption，不能凭空推测。"
        "不要因个人审美随意扣分；每个问题必须能从截图、原图或程序规则检查中找到证据。"
        "总分满分 100：layout 25、photoTextMatch 25、decorationPlacement 20、readability 20、coherence 10。"
        "重点检查是否有明确视觉焦点、主次关系是否清楚、留白是否有节奏，不能像普通图文列表。"
        "检查章节正文是否对应章节图片：每个 content.sections[].body 必须只描述该章节 imageIds 中的照片，不能张冠李戴。"
        "检查装饰是否有功能：胶带应像固定照片或便签，paper 应作为底纸或文字背景，贴纸应补充主题或填补留白，不能随意漂浮或遮挡主体。"
        "检查最终效果是否像电子手账：应有拼贴层次、手写日记感、照片和文字的关系，而不是普通图片加文字列表。"
        "评审素材丰富度：装饰是否过少、assetId 是否重复过多、外部素材是否几乎没有被使用。"
        "passed=true 必须满足 score>=85，且不存在硬失败。每轮只列出最影响体验的 3 到 6 个问题。"
        "只返回严格 JSON，字段为 score、passed、scores、issues、summary。"
        "issues 每项字段为 type、severity、targetIds、description、instruction。"
        f"\n用户描述：{request.description}"
        f"\n图片顺序：{json.dumps(image_order, ensure_ascii=False)}"
        f"\n程序规则问题：{json.dumps(rule_issues, ensure_ascii=False)}"
        f"\n当前 JSON：{json.dumps(layout, ensure_ascii=False)}"
    )


def build_revision_prompt(
    request: JournalGenerationRequest,
    layout: dict[str, Any],
    review: dict[str, Any],
    revision_round: int,
    best_score: float,
) -> str:
    assets = [
        {"id": asset.id, "category": asset.category, "tags": asset.tags, "style": asset.style, "colors": asset.colors}
        for asset in order_assets_for_ai(request.assets)
    ]
    image_order = [{"imageId": image.id, "order": index + 1} for index, image in enumerate(request.images)]
    return (
        "你是手帐排版修订师。第一张图片是当前最佳版截图，后续图片是按用户确认顺序排列的原图展示图。"
        "根据视觉评审问题修订当前 JSON。只修改解决 issues 所必需的字段，保留已经合理的设计。"
        "禁止修改图片集合和图片顺序。正文或 caption 只有在评审指出图文不匹配时才修改。"
        "不得新增列表之外的 assetId。若建议冲突，优先处理 high severity 问题。"
        "如果 issues 指出素材过少、重复过多或外部素材不足，可新增装饰、替换重复素材或混入合适外部素材。"
        "只处理视觉评审 issues 中列出的 3 到 6 个主要问题，不要改变未被点名的问题区域。"
        "如果 issues 没有要求重做整体版式，不要推翻整版布局；优先做局部移动、缩放、换素材或微调文字。"
        f"这是第 {revision_round}/3 轮修订。当前最佳得分：{best_score:g}。不得扩大修改范围。"
        "输出完整严格 JSON，不要输出解释。"
        f"\n用户描述：{request.description}"
        f"\n图片顺序：{json.dumps(image_order, ensure_ascii=False)}"
        f"\n当前 JSON：{json.dumps(layout, ensure_ascii=False)}"
        f"\n视觉评审：{json.dumps(review, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )
