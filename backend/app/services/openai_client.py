import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.agent_observability import log_agent_event
from app.services.assets import AssetItem
from app.services.journal_generator import GenerationError, JournalGenerationRequest
from app.services.journal_templates import allowed_section_variant_text

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_TIMEOUT_SECONDS = 300
OPENAI_MAX_ATTEMPTS = 2
TEMPLATE_STORY_GUIDES = {
    "quiet_story": "quiet_story 留白独白：只围绕一个瞬间写，照片不堆满，纸张和留白承载一段完整心情。",
    "hero_memory": "hero_memory 主照片日记：一张主图定调，其他元素围绕主图补充时间、地点或一句旁注。",
    "timeline_trip": "timeline_trip 时间线小旅行：按上传顺序写出出发、途中、停留或回程，章节从上到下推进。",
    "pocket_grid": "pocket_grid 口袋页：像 Project Life 口袋手帐，每格是一张照片、标题卡或记录卡，不要做成普通九宫格相册。",
    "ticket_day": "ticket_day 票根备忘：像票据、小票、门票和便签夹在一起，文字记录去过哪里、停在哪里、看到什么。",
    "magazine_note": "magazine_note 杂志留白：照片和文字保持编辑感留白，标题短，正文像一段清爽内页注记。",
    "before_after": "before_after 前后对照：用开始、变化、后来讲清楚对照关系，避免只把两张照片并排。",
    "moodboard_stack": "moodboard_stack 情绪堆叠：围绕一种心情组织照片、短句和贴纸，允许错落重叠但要有主次。",
    "recipe_memo": "recipe_memo 餐桌配方：像配方卡或餐桌小票，写味道、器皿、菜单和当时的小动作。",
    "letter_page": "letter_page 写给今天：像信纸或便笺，照片是旁证，正文要像写给这一天的一段话。",
    "chapter_scroll": "chapter_scroll 长卷章节：拆成开头、转场、结尾等连续章节，适合完整一天或一次出门。",
    "field_notes": "field_notes 观察手记：像野外观察本或研究笔记，用日期章、笔、便签和小标注记录具体细节。",
    "split_scene": "split_scene 双场景切换：把两个地点、时间或状态分开叙述，中间保留转场感。",
    "detail_index": "detail_index 细节索引：一张主图定调，其他图片做编号细节或索引说明，文字解释为什么这些小东西值得留下。",
    "map_journey": "map_journey 路线地图：用路线、停靠点、地点旁注讲一次移动中的经历，避免只排成时间线。",
    "weekly_spread": "weekly_spread 周记分栏：像数字周记 spread，把几天或多个片段分栏记录，每栏是一段可回看的小事。",
    "day_dashboard": "day_dashboard 日程看板：照片之外要有今日清单、完成感或小结，像手帐里的 dashboard。",
    "scrapbook_story": "scrapbook_story 剪贴故事：像 scrapbook memory keeping，用主图、边角素材、短句和贴纸讲一段回忆，不要做成照片墙。",
}


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
                if is_transient_status_error(exc) and attempt < OPENAI_MAX_ATTEMPTS:
                    log_agent_event(
                        "openai.status_retry",
                        attempt=attempt,
                        max_attempts=OPENAI_MAX_ATTEMPTS,
                        model=model,
                        status_code=exc.response.status_code,
                    )
                    continue
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

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return parse_model_json_content(content)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GenerationError("AI 服务返回格式异常，请稍后重试或检查模型服务配置") from exc


def is_transient_status_error(error: httpx.HTTPStatusError) -> bool:
    return 500 <= error.response.status_code < 600


def parse_model_json_content(content: Any) -> dict[str, Any]:
    text = str(content or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


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
    user_context = build_user_context(request)
    allowed_variants = allowed_section_variant_text()
    template_guide = build_template_story_guide(request)
    schema_example = {
        "canvas": {"width": 1080, "height": 2400, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8", "#d9a98f"], "mood": ["安静"]},
        "content": {
            "title": "窗边坐了一会儿",
            "meta": "2026-05-20 / 上海 / 松快",
            "body": ["咖啡还热着，杯沿旁边压着一张小票。", "后来走到路口，路灯已经亮了。"],
            "captions": [{"imageId": images[0]["id"] if images else "image_id", "text": "窗边咖啡和小票"}],
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
                    "body": "窗边坐了一会儿，咖啡还热着，小票被压在杯子旁边。",
                    "mood": ["安静", "日常"],
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
                {"role": "meta", "x": 84, "y": 144, "width": 720, "fontSize": 24},
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
        "用户补充信息可以用于增强准确性和日记感，例如日期可影响标题语气，地点和心情标签可辅助选素材与措辞。"
        "如果有日期、地点或心情标签，请把它们整理为 content.meta，并在标题下方生成一个 role=meta 的短文本框。"
        "如果和照片冲突，以照片和用户描述为准；不要因为地点或心情标签编造照片里不存在的内容。"
        "图片数组顺序就是用户上传或拖拽排序后的顺序，必须尊重这个顺序，不要自行重排。"
        "生成文字时要结合图片实际可见内容和用户描述；每段正文、每条 caption 都要和对应照片或照片组对得上，不能张冠李戴。"
        "必须先逐张理解图片，并在 content.imageUnderstanding 中为每张图片输出 imageId、summary、scene、subjects、mood。"
        "imageUnderstanding 必须覆盖全部图片，顺序必须和图片 order 一致，summary 只能描述对应 imageId 的真实可见内容。"
        "必须输出 content.sections 和 layout.sections。只允许把相邻图片合并成章节，禁止把不相邻的图片强行放进同一章节。"
        "content.sections 每项字段为 id、title、imageIds、body、mood；普通章节绑定 1 到 3 张图片，pocket_grid、detail_index、chapter_scroll 等模板可以按模板容量保留更多相邻图片，body 为 30 到 80 字自然日记。"
        "layout.sections 每项字段为 sectionId、variant、y、height、images、texts、decorations；sectionId 必须对应 content.sections 的 id。"
        f"layout.sections[].variant 只能从 {allowed_variants} 中选择；"
        "没有指定模板时：单张主图适合 hero_note，错落多图适合 staggered_collage，过程顺序适合 timeline_strip，相似照片组适合 photo_wall，安静留白适合 magazine_whitespace，咖啡展览票据类适合 ticket_memo。"
        "如果用户补充信息包含 templateId，请优先使用对应模板 variant：quiet_story 留白独白，hero_memory 主照片日记，timeline_trip 时间线小旅行，pocket_grid 口袋页，ticket_day 票根备忘，magazine_note 杂志留白，before_after 前后对照，moodboard_stack 情绪堆叠，recipe_memo 餐桌配方，letter_page 写给今天，chapter_scroll 长卷章节，field_notes 观察手记，split_scene 双场景切换，detail_index 细节索引。"
        "模板不是单纯照片摆法，而是叙事结构：chapter_scroll 要按开头、转场、结尾写；field_notes 要写观察到的细节；split_scene 要区分两个场景或状态；detail_index 要用一张主图带出几个小细节。"
        f"{template_guide}"
        "content.body 必须是字符串数组，不能只写一大段；请按照片主题、场景或时间分成 2 到 4 段短文字，每段 1 到 2 句。"
        "如果照片天然能分成几类，就让 content.body 的段落数量尽量对应这些类别。content.captions 必须使用 imageId 和 text。"
        "content.captions 的顺序应尽量跟图片 order 一致，caption 只能描述对应 imageId 的照片内容。"
        "layout.images 必须使用 imageId，排列顺序应尽量按照图片 order 从上到下、从左到右展开。layout.decorations 必须使用 assetId。"
        "layout.texts.role 只能是 title、meta、body 或 caption；每一段 content.body 都应该对应一个单独的 body 文本框。"
        "画布宽度必须是 1080，高度必须按内容多少生成竖向长图，不能固定为 1440。"
        "图片不要排得太密，图片组、文字块和装饰之间要留出明显呼吸感；内容多时让 canvas.height 继续向下延伸。"
        "所有图片、文字和装饰都必须落在 0 到 canvas.height 范围内，文字框不能和图片重叠。"
        "layout.decorations 请生成 12 到 22 个装饰，照片多或画布长时接近上限，照片少时也要有层次。"
        "装饰要分布在标题、照片组、正文段落和页脚附近，尽量不要重复 assetId。"
        "优先使用内部手绘素材和功能素材；外部素材只有在语义非常贴合照片内容时才少量使用。"
        "不要为了体现素材库数量强行混入外部图标，低质或泛图标感素材不要使用。"
        "电子手账素材要承担功能：胶带用于固定照片或便签，纸张用于承载文字，线条、便签和小贴纸用于分隔层次。"
        "素材使用必须符合语义：tape 只能作为胶带贴在照片边缘或四角；paper 只能作为底纸或文字背景，不能盖住照片主体；"
        "sticker 只能放在照片外侧空白区或轻微压住照片边缘，不能遮挡照片中心；texture 只能作为背景纹理。"
        "最终效果是一张可纵向滚动的完整手帐长图，而不是右侧附加正文。只能使用给定 image id 和 asset id。"
        f"\n返回 JSON 示例：{json.dumps(schema_example, ensure_ascii=False)}"
        f"\n用户描述：{request.description}"
        f"\n用户补充信息：{json.dumps(user_context, ensure_ascii=False)}"
        f"\n图片：{json.dumps(images, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )


def build_template_story_guide(request: JournalGenerationRequest) -> str:
    template_id = str(request.template_id or "").strip()
    guide = TEMPLATE_STORY_GUIDES.get(template_id)
    if not guide:
        return ""
    return f"当前用户选择的模板说明：{guide}"


def build_user_context(request: JournalGenerationRequest) -> dict[str, Any]:
    return {
        "journalDate": str(request.journal_date) if request.journal_date else None,
        "location": str(request.location).strip() if request.location else None,
        "moodTags": [str(tag).strip() for tag in request.mood_tags or [] if str(tag).strip()],
        "templateId": str(request.template_id).strip() if request.template_id else None,
    }


def order_assets_for_ai(assets: list[AssetItem]) -> list[AssetItem]:
    internal_assets = [asset for asset in assets if asset.source == "internal"]
    external_assets = [asset for asset in assets if asset.source != "internal"]
    return [*internal_assets, *external_assets]


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
        "评审素材丰富度：装饰是否过少、assetId 是否重复过多、内部手绘和功能素材是否优先、素材语义是否贴合。"
        "passed=true 必须满足 score>=85，且不存在硬失败。每轮只列出最影响体验的 3 到 6 个问题。"
        "只返回严格 JSON，字段为 score、passed、scores、issues、summary。"
        "issues 每项字段为 type、severity、targetIds、description、instruction。"
        f"\n用户描述：{request.description}"
        f"\n用户补充信息：{json.dumps(build_user_context(request), ensure_ascii=False)}"
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
        "如果 issues 指出素材过少、重复过多或素材不贴合，可新增装饰，并优先替换为更贴合的内部手绘或功能素材。"
        "只处理视觉评审 issues 中列出的 3 到 6 个主要问题，不要改变未被点名的问题区域。"
        "如果 issues 没有要求重做整体版式，不要推翻整版布局；优先做局部移动、缩放、换素材或微调文字。"
        f"这是第 {revision_round}/3 轮修订。当前最佳得分：{best_score:g}。不得扩大修改范围。"
        "输出完整严格 JSON，不要输出解释。"
        f"\n用户描述：{request.description}"
        f"\n用户补充信息：{json.dumps(build_user_context(request), ensure_ascii=False)}"
        f"\n图片顺序：{json.dumps(image_order, ensure_ascii=False)}"
        f"\n当前 JSON：{json.dumps(layout, ensure_ascii=False)}"
        f"\n视觉评审：{json.dumps(review, ensure_ascii=False)}"
        f"\n可用素材：{json.dumps(assets, ensure_ascii=False)}"
    )
