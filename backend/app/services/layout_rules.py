from typing import Any

from app.schemas.journal import JournalLayout
from app.services.decoration_placement import overlaps_photo_safe_area
from app.services.diary_copy import has_cliche_copy

CANVAS_WIDTH = 1080
MAX_DECORATIONS = 22
MIN_DECORATIONS = 12
MIN_EXTERNAL_STICKERS = 2
MIN_SECTION_GAP = 80
MIN_IMAGE_GAP = 32
MIN_SECTION_BODY_CHARS = 6
MAX_SECTION_BODY_CHARS = 100
SECTION_RHYTHM_HEIGHT_EPSILON = 24
SECTION_BOUNDS_EPSILON = 1
CAPTION_BORDER_OFFSET = 64
DECORATION_CATEGORY_LIMITS = {
    "paper": 4,
    "sticker": 8,
    "tape": 8,
    "texture": 2,
}
PLACEHOLDER_COPY = {
    "今天的照片",
    "照片说明",
    "这张照片",
    "生活片段",
    "第一段",
    "第二段",
    "第三段",
    "第四段",
    "这一组照片也想好好留下",
    "今天的照片先放在这里",
}


def check_layout_rules(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(check_image_order(layout, request))
    issues.extend(check_copy_quality(layout))
    issues.extend(check_meta_coverage(layout))
    issues.extend(check_readability(layout))
    issues.extend(check_decorations(layout, request))
    issues.extend(check_sections(layout))
    issues.extend(check_visual_focus(layout))
    issues.extend(check_layout_rhythm(layout))
    issues.extend(check_decoration_function(layout, request))
    return issues


def check_image_order(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    expected_image_ids = [image.id for image in request.images]
    actual_image_ids = rendered_image_ids(layout)
    if actual_image_ids != expected_image_ids:
        return [rule_issue("imageOrder", "high", actual_image_ids, "图片集合或顺序与用户确认结果不一致")]
    return []


def rendered_image_ids(layout: JournalLayout) -> list[str]:
    if layout.layout.sections:
        return [
            image.image_id
            for section in sorted(layout.layout.sections, key=lambda item: item.y)
            for image in sorted(section.images, key=lambda item: (item.y, item.x))
        ]
    return [image.image_id for image in layout.layout.images]


def check_meta_coverage(layout: JournalLayout) -> list[dict[str, Any]]:
    if not str(layout.content.meta or "").strip():
        return []
    if any(text.role == "meta" for text in layout.layout.texts):
        return []
    return [rule_issue("metaCoverage", "medium", [], "手帐元信息没有渲染位置")]


def check_readability(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    image_rects = [rect_from_item(image) for image in all_image_dicts(layout)]
    texts = [
        text
        for text in layout.layout.texts
        if not layout.layout.sections or text.role in {"title", "meta"}
    ]
    body_index = 0
    for text in texts:
        content = layout.content.title
        if text.role == "meta":
            content = layout.content.meta or ""
        elif text.role == "body":
            content = layout.content.body[body_index] if body_index < len(layout.content.body) else ""
            body_index += 1
        text_rect = (text.x, text.y, text.width, estimate_paragraph_height(content, text.font_size, text.width))
        if any(text_overlaps_image(text.role, text_rect, image_rect) for image_rect in image_rects):
            issues.append(rule_issue("readability", "high", [text.role], "文字与照片发生重叠"))
    issues.extend(check_section_readability(layout))
    return issues


def check_decorations(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    asset_by_id = {asset.id: asset for asset in request.assets if asset.quality_status == "approved"}
    category_counts: dict[str, int] = {}
    asset_counts: dict[str, int] = {}
    sticker_count = 0
    external_sticker_count = 0
    image_dicts = all_image_dicts(layout)
    rendered_decorations = all_rendered_decorations(layout)
    paper_dicts = [
        decoration.model_dump(by_alias=True)
        for decoration in rendered_decorations
        if (asset := asset_by_id.get(decoration.asset_id)) is not None and asset.category == "paper"
    ]

    for decoration in rendered_decorations:
        asset = asset_by_id.get(decoration.asset_id)
        if asset is None:
            issues.append(rule_issue("asset", "high", [decoration.asset_id], "使用了未审核或不存在的素材"))
            continue
        asset_counts[asset.id] = asset_counts.get(asset.id, 0) + 1
        category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
        if asset.category == "sticker":
            sticker_count += 1
            if asset.source != "internal":
                external_sticker_count += 1
        if not rect_inside_canvas((decoration.x, decoration.y, decoration.width, decoration.height), layout.canvas.height):
            issues.append(rule_issue("decorationPlacement", "high", [decoration.asset_id], "素材超出画布范围"))
        decoration_dict = decoration.model_dump(by_alias=True)
        if asset.category == "sticker" and overlaps_photo_safe_area(decoration_dict, image_dicts):
            issues.append(rule_issue("decorationPlacement", "high", [decoration.asset_id], "贴纸覆盖照片主体安全区"))
        if asset.category == "tape" and not tape_attached_to_target(decoration_dict, image_dicts, paper_dicts):
            issues.append(rule_issue("decorationPlacement", "high", [decoration.asset_id], "胶带没有贴近照片边缘"))

    if len(rendered_decorations) > MAX_DECORATIONS:
        issues.append(rule_issue("decorationDensity", "high", [], "装饰总数超过限制"))
    min_decorations = minimum_decoration_count(layout)
    if len(asset_by_id) >= min_decorations and len(rendered_decorations) < min_decorations:
        issues.append(rule_issue("decorationDensity", "medium", [], "装饰数量偏少，画面丰富度不足"))
    repeated_asset_ids = [asset_id for asset_id, count in asset_counts.items() if count > 1]
    if repeated_asset_ids and len(asset_by_id) > len(asset_counts):
        issues.append(rule_issue("decorationVariety", "medium", repeated_asset_ids, "素材重复使用过多，画面变化不足"))
    external_sticker_candidates = [
        asset for asset in asset_by_id.values() if asset.category == "sticker" and asset.source != "internal"
    ]
    if len(external_sticker_candidates) >= MIN_EXTERNAL_STICKERS and sticker_count >= 4 and external_sticker_count < MIN_EXTERNAL_STICKERS:
        issues.append(rule_issue("decorationVariety", "medium", [], "外部素材使用偏少，素材库丰富度没有体现出来"))
    for category, count in category_counts.items():
        if count > DECORATION_CATEGORY_LIMITS.get(category, 1):
            issues.append(rule_issue("decorationDensity", "high", [category], f"{category} 类素材数量超过限制"))
    return issues


def tape_attached_to_target(
    decoration: dict[str, Any],
    image_dicts: list[dict[str, Any]],
    paper_dicts: list[dict[str, Any]],
) -> bool:
    if overlaps_any_photo_edge(decoration, image_dicts):
        return True
    return overlaps_any_photo_edge(decoration, paper_dicts)


def all_image_dicts(layout: JournalLayout) -> list[dict[str, Any]]:
    section_images = [image for section in layout.layout.sections for image in section.images]
    images = section_images or layout.layout.images
    return [image.model_dump(by_alias=True) for image in images]


def section_decorations(layout: JournalLayout) -> list[Any]:
    return [decoration for section in layout.layout.sections for decoration in section.decorations]


def all_rendered_decorations(layout: JournalLayout) -> list[Any]:
    decorations = section_decorations(layout)
    return decorations if decorations else list(layout.layout.decorations)


def minimum_decoration_count(layout: JournalLayout) -> int:
    if layout.layout.sections:
        return min(MIN_DECORATIONS, max(len(layout.layout.sections) * 3, 3))
    return MIN_DECORATIONS


def check_sections(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    sections = sorted(layout.layout.sections, key=lambda section: section.y)
    body_by_section_id = {section.id: section.body for section in layout.content.sections}
    image_ids_by_section_id = {section.id: section.image_ids for section in layout.content.sections}
    caption_image_ids = {caption.image_id for caption in layout.content.captions}
    content_section_ids = set(body_by_section_id)
    for index, section in enumerate(sections):
        if section.section_id not in content_section_ids:
            issues.append(rule_issue("sectionReference", "high", [section.section_id], "版式章节没有对应的内容章节"))
        elif rendered_section_image_ids(section) != image_ids_by_section_id[section.section_id]:
            issues.append(rule_issue("sectionImageMatch", "high", [section.section_id], "版式章节图片与内容章节不一致"))
        elif (section_copy_issue := check_section_copy_alignment(section.section_id, body_by_section_id[section.section_id])) is not None:
            issues.append(section_copy_issue)
        issues.extend(check_section_caption_coverage(section, caption_image_ids))
        section_bottom = section.y + section.height
        content_bottom = max(
            [
                section.y,
                *[image.y + image.height for image in section.images],
                *[
                    text.y + section_text_height(text, body_by_section_id.get(section.section_id, ""))
                    for text in section.texts
                ],
                *[decoration.y + decoration.height for decoration in section.decorations],
            ]
        )
        if content_bottom - section_bottom > SECTION_BOUNDS_EPSILON:
            issues.append(rule_issue("sectionBounds", "high", [section.section_id], "章节高度没有覆盖内部内容"))
        if index > 0:
            previous = sections[index - 1]
            previous_bottom = previous.y + previous.height
            if section.y - previous_bottom < MIN_SECTION_GAP:
                issues.append(rule_issue("sectionSpacing", "medium", [previous.section_id, section.section_id], "章节之间间距不足"))
        issues.extend(check_section_image_spacing(section))
    return issues


def rendered_section_image_ids(section: Any) -> list[str]:
    return [image.image_id for image in sorted(section.images, key=lambda item: (item.y, item.x))]


def check_section_caption_coverage(section: Any, caption_image_ids: set[str]) -> list[dict[str, Any]]:
    caption_placements = [text for text in section.texts if text.role == "caption"]
    if not caption_placements:
        return []
    expected_caption_images = [
        image
        for image in sorted(section.images, key=lambda item: (item.y, item.x))
        if image.image_id in caption_image_ids
    ]
    if len(caption_placements) < len(expected_caption_images):
        return [rule_issue("captionCoverage", "medium", [section.section_id], "章节照片说明没有完整渲染")]
    for image, caption in zip(expected_caption_images, caption_placements):
        if not caption_attached_to_image(caption, image):
            return [rule_issue("captionPlacement", "medium", [section.section_id], "照片说明没有贴近对应照片")]
    return []


def caption_attached_to_image(caption: Any, image: Any) -> bool:
    caption_rect = (caption.x, caption.y, caption.width, section_text_height(caption, ""))
    image_rect = (image.x, image.y, image.width, image.height)
    if rect_intersection_area(caption_rect, expand_rect(image_rect, 18)) <= 0:
        return False
    caption_center_x = caption.x + caption.width / 2
    image_bottom = image.y + image.height
    return image.x <= caption_center_x <= image.x + image.width and image_bottom - 72 <= caption.y <= image_bottom + 28


def check_section_readability(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    body_by_section_id = {section.id: section.body for section in layout.content.sections}
    for section in layout.layout.sections:
        image_rects = [(image.x, image.y, image.width, image.height) for image in section.images]
        for text in section.texts:
            text_rect = (
                text.x,
                text.y,
                text.width,
                section_text_height(text, body_by_section_id.get(section.section_id, "")),
            )
            if any(text_overlaps_image(text.role, text_rect, image_rect) for image_rect in image_rects):
                issues.append(rule_issue("readability", "high", [section.section_id], "章节文字与照片发生重叠"))
    return issues


def section_text_height(text: Any, body: str) -> float:
    if text.role == "body":
        return estimate_paragraph_height(body, text.font_size, text.width)
    return text.font_size * 2.4


def check_copy_quality(layout: JournalLayout) -> list[dict[str, Any]]:
    copy_parts = [
        layout.content.title,
        *layout.content.body,
        *(caption.text for caption in layout.content.captions),
        *(section.title for section in layout.content.sections),
        *(section.body for section in layout.content.sections),
    ]
    if any(has_cliche_copy(part) for part in copy_parts):
        return [rule_issue("copyQuality", "medium", [], "正文存在明显 AI 套话，手帐记录不够具体")]
    if any(is_placeholder_copy(part) for part in copy_parts):
        return [rule_issue("copyQuality", "medium", [], "正文存在占位式描述，手帐记录不够具体")]
    return []


def is_placeholder_copy(value: Any) -> bool:
    text = str(value or "").strip(" 。！？!?；;，,")
    return text.startswith("片段 ") or numbered_photo_label(text) or text in PLACEHOLDER_COPY


def numbered_photo_label(text: str) -> bool:
    return text.startswith("第 ") and "张照片" in text


def copy_signal_text(value: Any) -> str:
    return str(value or "").strip(" \n\t。！？!?；;，,、")


def check_section_copy_alignment(section_id: str, body: Any) -> dict[str, Any] | None:
    text = copy_signal_text(body)
    if len(text) < MIN_SECTION_BODY_CHARS:
        return rule_issue("sectionCopyAlignment", "medium", [section_id], "章节正文过短，手帐记录不够具体")
    if len(text) > MAX_SECTION_BODY_CHARS:
        return rule_issue("sectionCopyAlignment", "medium", [section_id], "章节正文过长，手帐记录应拆成短句")
    return None


def check_visual_focus(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for section in layout.layout.sections:
        if len(section.images) < 3:
            continue
        areas = [image.width * image.height for image in section.images]
        smallest_area = min(areas)
        largest_area = max(areas)
        if smallest_area <= 0:
            continue
        if largest_area / smallest_area < 1.25:
            issues.append(rule_issue("visualFocus", "medium", [section.section_id], "多图章节缺少明确主图或视觉焦点"))
    return issues


def check_layout_rhythm(layout: JournalLayout) -> list[dict[str, Any]]:
    sections = layout.layout.sections
    if len(sections) < 3:
        return []
    variants = {section.variant for section in sections}
    heights = [section.height for section in sections]
    if len(variants) == 1 and max(heights) - min(heights) <= SECTION_RHYTHM_HEIGHT_EPSILON:
        return [rule_issue("layoutRhythm", "medium", [section.section_id for section in sections], "章节版式节奏过于重复")]
    return []


def check_decoration_function(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    asset_by_id = {asset.id: asset for asset in request.assets if asset.quality_status == "approved"}
    has_functional_assets = any(asset.category in {"paper", "tape"} for asset in asset_by_id.values())
    if not has_functional_assets:
        return []

    issues: list[dict[str, Any]] = []
    body_by_section_id = {section.id: section.body for section in layout.content.sections}
    for section in layout.layout.sections:
        if not section.images or not section.texts:
            continue
        paper_decorations = []
        decoration_categories = set()
        for decoration in section.decorations:
            asset = asset_by_id.get(decoration.asset_id)
            if asset is None:
                continue
            decoration_categories.add(asset.category)
            if asset.category == "paper":
                paper_decorations.append(decoration)
        if not decoration_categories.intersection({"paper", "tape"}):
            issues.append(rule_issue("decorationFunction", "medium", [section.section_id], "章节缺少承载文字或固定照片的功能性装饰"))
        body_texts = [text for text in section.texts if text.role == "body"]
        if paper_decorations and body_texts and not any(
            paper_backs_text(paper, text, body_by_section_id.get(section.section_id, ""))
            for paper in paper_decorations
            for text in body_texts
        ):
            issues.append(rule_issue("decorationFunction", "medium", [section.section_id], "纸张素材没有承载章节文字"))
    return issues


def paper_backs_text(paper: Any, text: Any, body: str) -> bool:
    paper_rect = rect_from_item(paper.model_dump(by_alias=True))
    text_rect = (text.x, text.y, text.width, section_text_height(text, body))
    text_area = text_rect[2] * text_rect[3]
    if text_area <= 0:
        return False
    return rect_intersection_area(paper_rect, text_rect) / text_area >= 0.55


def rect_intersection_area(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    overlap_width = min(first_x + first_width, second_x + second_width) - max(first_x, second_x)
    overlap_height = min(first_y + first_height, second_y + second_height) - max(first_y, second_y)
    return max(overlap_width, 0) * max(overlap_height, 0)


def check_section_image_spacing(section: Any) -> list[dict[str, Any]]:
    images = section.images
    for index, first in enumerate(images):
        first_rect = (first.x, first.y, first.width, first.height)
        for second in images[index + 1 :]:
            second_rect = (second.x, second.y, second.width, second.height)
            if rects_overlap(expand_rect(first_rect, MIN_IMAGE_GAP / 2), expand_rect(second_rect, MIN_IMAGE_GAP / 2)):
                return [rule_issue("imageSpacing", "medium", [section.section_id], "章节内图片间距不足")]
    return []


def rule_issue(issue_type: str, severity: str, target_ids: list[str], description: str) -> dict[str, Any]:
    return {"type": issue_type, "severity": severity, "targetIds": target_ids, "description": description}


def rect_inside_canvas(rect: tuple[float, float, float, float], canvas_height: float) -> bool:
    x, y, width, height = rect
    return x >= 0 and y >= 0 and x + width <= CANVAS_WIDTH and y + height <= canvas_height


def overlaps_any_photo_edge(decoration: dict[str, Any], image_placements: list[dict[str, Any]]) -> bool:
    decoration_rect = rect_from_item(decoration)
    for image in image_placements:
        image_x, image_y, image_width, image_height = rect_from_item(image)
        expanded_image = (image_x - 48, image_y - 48, image_width + 96, image_height + 96)
        if rects_overlap(decoration_rect, expanded_image):
            return True
    return False


def rect_from_item(item: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        positive_number(item.get("x"), 0),
        positive_number(item.get("y"), 0),
        positive_number(item.get("width"), 0),
        positive_number(item.get("height"), 0),
    )


def expand_rect(rect: tuple[float, float, float, float], amount: float) -> tuple[float, float, float, float]:
    x, y, width, height = rect
    return (x - amount, y - amount, width + amount * 2, height + amount * 2)


def rects_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def text_overlaps_image(
    role: str,
    text_rect: tuple[float, float, float, float],
    image_rect: tuple[float, float, float, float],
) -> bool:
    if not rects_overlap(text_rect, image_rect):
        return False
    if role != "caption":
        return True

    _, text_y, _, text_height = text_rect
    _, image_y, _, image_height = image_rect
    image_bottom = image_y + image_height
    overlap_top = max(text_y, image_y)
    overlap_bottom = min(text_y + text_height, image_bottom)
    return overlap_top < image_bottom - CAPTION_BORDER_OFFSET or overlap_bottom > image_bottom + SECTION_BOUNDS_EPSILON


def estimate_paragraph_height(paragraph: str, font_size: float, width: float) -> float:
    characters_per_line = max(int(width / max(font_size, 1)), 1)
    line_count = max((len(paragraph) + characters_per_line - 1) // characters_per_line, 1)
    return line_count * font_size * 1.8


def positive_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number <= 0:
        return fallback
    return number
