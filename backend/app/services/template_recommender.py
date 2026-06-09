from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.services.openai_client import OPENAI_TIMEOUT_SECONDS, parse_model_json_content, source_image_parts


@dataclass(frozen=True)
class TemplateRecommendationImage:
    id: str
    width: int
    height: int
    data_url: str | None = None


@dataclass(frozen=True)
class TemplateRecommendationRequest:
    description: str
    images: list[TemplateRecommendationImage]
    mood_tags: list[str]


class TemplateVisionClient(Protocol):
    def understand_images(self, request: TemplateRecommendationRequest) -> list[dict[str, Any]]:
        pass


class TemplateRecommendationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TemplateProfile:
    id: str
    name: str
    story_arc: str
    min_images: int
    max_images: int
    keywords: tuple[str, ...]
    family: str


TEMPLATE_PROFILES: tuple[TemplateProfile, ...] = (
    TemplateProfile("quiet_story", "留白独白", "先看见一个瞬间，再把当时的感受写完整。", 1, 2, ("安静", "慢", "窗边", "独处", "光", "平静"), "reflective"),
    TemplateProfile("hero_memory", "主照片日记", "把最重要的一张照片当成开场，其他内容都围着它讲。", 1, 2, ("重要", "纪念", "今天", "周末", "散步"), "focus"),
    TemplateProfile("timeline_trip", "时间线小旅行", "从开始到后来，照片顺序就是页面阅读顺序。", 2, 6, ("旅行", "路上", "出发", "抵达", "车站", "路线", "沿途"), "sequence"),
    TemplateProfile("pocket_grid", "口袋页", "把一天拆成几个小口袋，每格是一件被留下的小事。", 4, 9, ("很多", "合集", "一天", "碎片", "相册", "photo dump"), "collection"),
    TemplateProfile("ticket_day", "票根备忘", "用票据和便签感记录去过哪里、停在哪里、看见什么。", 1, 4, ("咖啡", "展览", "博物馆", "电影", "票", "小票", "餐厅"), "ephemera"),
    TemplateProfile("magazine_note", "杂志留白", "像杂志内页一样保留留白，让照片和文字都有呼吸。", 1, 3, ("留白", "杂志", "简洁", "光线", "下午"), "editorial"),
    TemplateProfile("before_after", "前后对照", "对比两个时刻，让变化本身成为故事。", 2, 3, ("之前", "之后", "变化", "开始", "后来", "完成"), "contrast"),
    TemplateProfile("moodboard_stack", "情绪堆叠", "不强调时间顺序，而是把同一种心情贴在一页上。", 2, 5, ("开心", "松快", "热闹", "日常", "朋友"), "mood"),
    TemplateProfile("recipe_memo", "餐桌配方", "像写一张配方卡一样记录今天吃到的味道。", 1, 4, ("吃", "餐", "咖啡", "甜品", "饭", "茶", "面包"), "food"),
    TemplateProfile("letter_page", "写给今天", "照片只做旁证，主角是一段写给今天的话。", 1, 3, ("想说", "记录", "心情", "纪念", "给"), "letter"),
    TemplateProfile("chapter_scroll", "长卷章节", "开头、转场、结尾依次出现，适合完整一天或一次出门。", 3, 9, ("一整天", "完整", "连续", "过程", "故事", "章节", "从早到晚"), "sequence"),
    TemplateProfile("field_notes", "观察手记", "从一个细节开始，写成观察、补充、想到的事。", 1, 5, ("细节", "观察", "发现", "植物", "书", "物件", "角落"), "observation"),
    TemplateProfile("split_scene", "双场景切换", "先讲一个场景，再切到另一个场景，中间留下转场感。", 2, 4, ("上午", "下午", "室内", "室外", "转场", "两个地方", "换了"), "contrast"),
    TemplateProfile("detail_index", "细节索引", "主图定调，细节图负责补充那些容易忘的小东西。", 3, 8, ("细节", "索引", "清单", "编号", "几样", "小东西", "主题"), "observation"),
)

FOOD_TERMS = {"咖啡", "茶", "甜品", "餐厅", "餐桌", "饭", "面包", "蛋糕", "饮料", "食物"}
EPHEMERA_TERMS = {"票", "票根", "小票", "展览", "展厅", "博物馆", "电影", "标签", "收据", "车票"}
JOURNEY_TERMS = {"旅行", "旅程", "出门", "路上", "出发", "抵达", "车站", "地铁", "公交", "路线", "沿途", "散步"}
CHRONOLOGY_TERMS = {"早上", "上午", "中午", "下午", "傍晚", "晚上", "后来", "最后", "从早到晚", "过程", "连续"}
CONTRAST_TERMS = {"之前", "之后", "前后", "变化", "完成", "开始", "后来", "对比", "两个地方", "室内", "室外", "转场"}
DETAIL_TERMS = {"细节", "观察", "发现", "植物", "书", "物件", "角落", "编号", "索引", "清单", "小东西"}
REFLECTIVE_TERMS = {"想说", "心情", "写给", "独处", "平静", "安静", "慢", "纪念", "记下来"}
SOCIAL_TERMS = {"朋友", "一起", "家人", "聚会", "热闹", "约会", "同事", "陪"}
FRAGMENT_TERMS = {"很多", "合集", "碎片", "相册", "photo dump", "几张", "几样", "一天"}


class OpenAITemplateVisionClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def understand_images(self, request: TemplateRecommendationRequest) -> list[dict[str, Any]]:
        if not self.api_key:
            raise TemplateRecommendationError("API Key missing")
        content = [
            {"type": "text", "text": build_template_understanding_prompt(request)},
            *source_image_parts(request),
        ]
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": content}],
                    "response_format": {"type": "json_object"},
                },
                timeout=min(OPENAI_TIMEOUT_SECONDS, 45),
                trust_env=True,
            )
            response.raise_for_status()
            payload = response.json()
            model_content = payload["choices"][0]["message"]["content"]
            parsed = parse_model_json_content(model_content)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise TemplateRecommendationError("Template image understanding failed") from exc

        raw_items = parsed.get("imageUnderstanding")
        if not isinstance(raw_items, list):
            raise TemplateRecommendationError("Template image understanding missing")
        return [item for item in raw_items if isinstance(item, dict)]


def recommend_templates(
    request: TemplateRecommendationRequest,
    client: TemplateVisionClient | None = None,
) -> dict[str, Any]:
    try:
        understanding = client.understand_images(request) if client is not None else []
        if understanding:
            return {
                "recommendations": score_templates(request, understanding),
                "source": "ai",
                "imageUnderstanding": understanding,
                "message": None,
            }
    except TemplateRecommendationError:
        pass

    return {
        "recommendations": score_templates(request, []),
        "source": "local",
        "imageUnderstanding": [],
        "message": "AI 图片理解暂不可用，已按照片数量、横竖比例和描述推荐模板。",
    }


def score_templates(request: TemplateRecommendationRequest, understanding: list[dict[str, Any]]) -> list[dict[str, str]]:
    text = searchable_text(request, understanding)
    image_profile = describe_images(request.images)
    story_signals = detect_story_signals(request, understanding, text, image_profile)
    scored: list[tuple[int, int, TemplateProfile, list[str]]] = []
    for index, profile in enumerate(TEMPLATE_PROFILES):
        keyword_hits = [keyword for keyword in profile.keywords if keyword.lower() in text]
        score = 0
        if profile.min_images <= len(request.images) <= profile.max_images:
            score += 8
        if len(request.images) > profile.max_images:
            score -= min(len(request.images) - profile.max_images, 4)
        if len(request.images) < profile.min_images:
            score -= 3
        score += len(keyword_hits) * 5
        score += bonus_score(profile, request, image_profile, story_signals)
        scored.append((score, -index, profile, keyword_hits))

    scored.sort(reverse=True)
    selected = select_diverse_templates(scored)
    return [
        recommendation_item(profile, request, keyword_hits, image_profile, story_signals)
        for _, _, profile, keyword_hits in selected
    ]


def bonus_score(
    profile: TemplateProfile,
    request: TemplateRecommendationRequest,
    image_profile: dict[str, bool],
    story_signals: dict[str, bool],
) -> int:
    score = 0
    if profile.id == "pocket_grid":
        score += 6 if len(request.images) >= 5 else 0
        score += 4 if story_signals["fragments"] else 0
    if profile.id == "chapter_scroll":
        score += 5 if len(request.images) >= 5 else 0
        score += 5 if story_signals["chronology"] else 0
        score += 3 if story_signals["journey"] else 0
    if profile.id == "detail_index":
        score += 4 if len(request.images) >= 4 and image_profile["has_mixed_orientation"] else 0
        score += 5 if story_signals["detail"] else 0
    if profile.id == "timeline_trip":
        score += 3 if len(request.images) >= 3 else 0
        score += 6 if story_signals["journey"] else 0
        score += 3 if story_signals["chronology"] else 0
    if profile.id == "quiet_story":
        score += 2 if image_profile["has_portrait_dominance"] else 0
        score += 4 if story_signals["reflective"] else 0
    if profile.id == "split_scene":
        score += 6 if 2 <= len(request.images) <= 4 and story_signals["two_scene"] else 0
    if profile.id == "before_after":
        score += 7 if story_signals["contrast"] else 0
    if profile.id == "ticket_day":
        score += 7 if story_signals["ephemera"] else 0
        score += 2 if story_signals["food"] else 0
    if profile.id == "recipe_memo":
        score += 7 if story_signals["food"] else 0
    if profile.id == "letter_page":
        score += 6 if story_signals["reflective"] else 0
    if profile.id == "field_notes":
        score += 6 if story_signals["detail"] else 0
    if profile.id == "moodboard_stack":
        score += 5 if story_signals["social"] else 0
        score += 3 if story_signals["fragments"] and len(request.images) <= 5 else 0
    if profile.id == "hero_memory":
        score += 4 if len(request.images) == 1 else 0
    if profile.id == "magazine_note":
        score += 3 if story_signals["reflective"] and len(request.images) <= 3 else 0
    return score


def select_diverse_templates(scored: list[tuple[int, int, TemplateProfile, list[str]]]) -> list[tuple[int, int, TemplateProfile, list[str]]]:
    selected: list[tuple[int, int, TemplateProfile, list[str]]] = []
    used_families: set[str] = set()
    for item in scored:
        profile = item[2]
        if profile.family in used_families and has_unused_family_candidate(scored, selected, used_families):
            continue
        selected.append(item)
        used_families.add(profile.family)
        if len(selected) == 3:
            return selected
    return selected[:3]


def has_unused_family_candidate(
    scored: list[tuple[int, int, TemplateProfile, list[str]]],
    selected: list[tuple[int, int, TemplateProfile, list[str]]],
    used_families: set[str],
) -> bool:
    selected_ids = {item[2].id for item in selected}
    return any(item[2].id not in selected_ids and item[2].family not in used_families for item in scored)


def recommendation_item(
    profile: TemplateProfile,
    request: TemplateRecommendationRequest,
    keyword_hits: list[str],
    image_profile: dict[str, bool],
    story_signals: dict[str, bool],
) -> dict[str, str]:
    return {
        "templateId": profile.id,
        "name": profile.name,
        "storyArc": profile.story_arc,
        "reason": recommendation_reason(profile, request, keyword_hits, image_profile, story_signals),
    }


def recommendation_reason(
    profile: TemplateProfile,
    request: TemplateRecommendationRequest,
    keyword_hits: list[str],
    image_profile: dict[str, bool],
    story_signals: dict[str, bool],
) -> str:
    signal_reason = story_signal_reason(profile, story_signals, len(request.images))
    if signal_reason is not None:
        return signal_reason
    if keyword_hits:
        return f"匹配到「{'、'.join(keyword_hits[:2])}」，适合用这个结构讲。"
    if profile.min_images <= len(request.images) <= profile.max_images:
        return f"{len(request.images)} 张照片落在它的舒适范围里。"
    if profile.id == "quiet_story" and image_profile["has_portrait_dominance"]:
        return "竖图偏多，适合留白和长段文字。"
    if profile.id == "detail_index" and image_profile["has_mixed_orientation"]:
        return "横竖图混合，适合主图加细节索引。"
    return "作为不同叙事节奏的备选。"


def story_signal_reason(profile: TemplateProfile, story_signals: dict[str, bool], image_count: int) -> str | None:
    if profile.id == "chapter_scroll" and image_count >= 5:
        return "照片数量多，适合拆成开头、转场和结尾来读。"
    if profile.id == "timeline_trip" and (story_signals["journey"] or story_signals["chronology"]):
        return "有路上或时间顺序线索，适合按经历推进。"
    if profile.id == "ticket_day" and story_signals["ephemera"]:
        return "有票据、展览或地点凭证线索，适合做票根备忘。"
    if profile.id == "recipe_memo" and story_signals["food"]:
        return "食物或咖啡线索明显，适合写成餐桌小记。"
    if profile.id == "field_notes" and story_signals["detail"]:
        return "细节主体比较明确，适合写成观察手记。"
    if profile.id == "detail_index" and story_signals["detail"]:
        return "有可编号的小细节，适合用主图带出索引。"
    if profile.id == "split_scene" and story_signals["two_scene"]:
        return "出现两个场景或状态，适合分成两段讲。"
    if profile.id == "before_after" and story_signals["contrast"]:
        return "有前后变化线索，适合把变化本身讲清楚。"
    if profile.id == "pocket_grid" and story_signals["fragments"]:
        return "片段感强，适合用口袋卡片收纳照片和短句。"
    if profile.id == "letter_page" and story_signals["reflective"]:
        return "描述更像一段想说的话，适合让文字成为主角。"
    if profile.id == "moodboard_stack" and story_signals["social"]:
        return "有人物或相处线索，适合把同一种心情贴成一页。"
    return None


def searchable_text(request: TemplateRecommendationRequest, understanding: list[dict[str, Any]]) -> str:
    parts = [request.description, *request.mood_tags]
    for item in understanding:
        parts.extend([str(item.get("summary") or ""), str(item.get("scene") or "")])
        parts.extend(str(subject) for subject in item.get("subjects") or [])
        parts.extend(str(mood) for mood in item.get("mood") or [])
    return " ".join(parts).lower()


def describe_images(images: list[TemplateRecommendationImage]) -> dict[str, bool]:
    portrait_count = sum(1 for image in images if image.height > image.width)
    landscape_count = sum(1 for image in images if image.width >= image.height)
    return {
        "has_mixed_orientation": portrait_count > 0 and landscape_count > 0,
        "has_portrait_dominance": bool(images) and portrait_count >= (len(images) + 1) // 2,
    }


def detect_story_signals(
    request: TemplateRecommendationRequest,
    understanding: list[dict[str, Any]],
    text: str,
    image_profile: dict[str, bool],
) -> dict[str, bool]:
    scenes = {str(item.get("scene") or "").strip() for item in understanding if str(item.get("scene") or "").strip()}
    subjects = {
        str(subject).strip()
        for item in understanding
        for subject in item.get("subjects") or []
        if str(subject).strip()
    }
    return {
        "food": contains_any(text, FOOD_TERMS),
        "ephemera": contains_any(text, EPHEMERA_TERMS),
        "journey": contains_any(text, JOURNEY_TERMS),
        "chronology": contains_any(text, CHRONOLOGY_TERMS),
        "contrast": contains_any(text, CONTRAST_TERMS),
        "detail": contains_any(text, DETAIL_TERMS) or len(subjects) >= max(3, len(request.images)),
        "reflective": contains_any(text, REFLECTIVE_TERMS),
        "social": contains_any(text, SOCIAL_TERMS),
        "fragments": contains_any(text, FRAGMENT_TERMS) or len(request.images) >= 5,
        "two_scene": contains_any(text, CONTRAST_TERMS) or (2 <= len(request.images) <= 4 and len(scenes) >= 2),
        "mixed_orientation": image_profile["has_mixed_orientation"],
    }


def contains_any(text: str, terms: set[str]) -> bool:
    return any(term.lower() in text for term in terms)


def build_template_understanding_prompt(request: TemplateRecommendationRequest) -> str:
    images = [{"id": image.id, "order": index + 1, "width": image.width, "height": image.height} for index, image in enumerate(request.images)]
    return (
        "请先逐张理解用户上传的图片，用于推荐电子手帐模板。"
        "只返回严格 JSON，不要返回 Markdown。字段为 imageUnderstanding。"
        "imageUnderstanding 每项字段必须是 imageId、summary、scene、subjects、mood。"
        "summary 只描述对应图片真实可见内容，不要发明地点、关系、天气或情绪。"
        "subjects 用 1 到 4 个短词记录可见主体。mood 只写可从画面推断的氛围词。"
        f"\n用户描述：{request.description}"
        f"\n心情标签：{request.mood_tags}"
        f"\n图片：{images}"
    )
