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
DECORATION_CATEGORY_LIMITS = {
    "paper": 4,
    "sticker": 8,
    "tape": 8,
    "texture": 2,
}


def check_layout_rules(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(check_image_order(layout, request))
    issues.extend(check_copy_quality(layout))
    issues.extend(check_readability(layout))
    issues.extend(check_decorations(layout, request))
    issues.extend(check_sections(layout))
    issues.extend(check_visual_focus(layout))
    issues.extend(check_decoration_function(layout, request))
    return issues


def check_image_order(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    expected_image_ids = [image.id for image in request.images]
    actual_image_ids = [image.image_id for image in layout.layout.images]
    if actual_image_ids != expected_image_ids:
        return [rule_issue("imageOrder", "high", actual_image_ids, "图片集合或顺序与用户确认结果不一致")]
    return []


def check_readability(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    image_rects = [(image.x, image.y, image.width, image.height) for image in layout.layout.images]
    title = layout.content.title
    body_index = 0
    for text in layout.layout.texts:
        content = title
        if text.role == "body":
            content = layout.content.body[body_index] if body_index < len(layout.content.body) else ""
            body_index += 1
        text_rect = (text.x, text.y, text.width, estimate_paragraph_height(content, text.font_size, text.width))
        if any(rects_overlap(text_rect, image_rect) for image_rect in image_rects):
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
    image_dicts = [image.model_dump(by_alias=True) for image in layout.layout.images]

    for decoration in layout.layout.decorations:
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
        if asset.category == "tape" and not overlaps_any_photo_edge(decoration_dict, image_dicts):
            issues.append(rule_issue("decorationPlacement", "high", [decoration.asset_id], "胶带没有贴近照片边缘"))

    if len(layout.layout.decorations) > MAX_DECORATIONS:
        issues.append(rule_issue("decorationDensity", "high", [], "装饰总数超过限制"))
    if len(asset_by_id) >= MIN_DECORATIONS and len(layout.layout.decorations) < MIN_DECORATIONS:
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


def check_sections(layout: JournalLayout) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    sections = sorted(layout.layout.sections, key=lambda section: section.y)
    body_by_section_id = {section.id: section.body for section in layout.content.sections}
    for index, section in enumerate(sections):
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
        if content_bottom > section_bottom:
            issues.append(rule_issue("sectionBounds", "high", [section.section_id], "章节高度没有覆盖内部内容"))
        if index > 0:
            previous = sections[index - 1]
            previous_bottom = previous.y + previous.height
            if section.y - previous_bottom < MIN_SECTION_GAP:
                issues.append(rule_issue("sectionSpacing", "medium", [previous.section_id, section.section_id], "章节之间间距不足"))
        issues.extend(check_section_image_spacing(section))
    return issues


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
            if any(rects_overlap(text_rect, image_rect) for image_rect in image_rects):
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
        *(section.body for section in layout.content.sections),
    ]
    if any(has_cliche_copy(part) for part in copy_parts):
        return [rule_issue("copyQuality", "medium", [], "正文存在明显 AI 套话，手帐记录不够具体")]
    return []


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


def check_decoration_function(layout: JournalLayout, request: Any) -> list[dict[str, Any]]:
    asset_by_id = {asset.id: asset for asset in request.assets if asset.quality_status == "approved"}
    has_functional_assets = any(asset.category in {"paper", "tape"} for asset in asset_by_id.values())
    if not has_functional_assets:
        return []

    issues: list[dict[str, Any]] = []
    for section in layout.layout.sections:
        if not section.images or not section.texts:
            continue
        decoration_categories = {
            asset.category
            for decoration in section.decorations
            if (asset := asset_by_id.get(decoration.asset_id)) is not None
        }
        if not decoration_categories.intersection({"paper", "tape"}):
            issues.append(rule_issue("decorationFunction", "medium", [section.section_id], "章节缺少承载文字或固定照片的功能性装饰"))
    return issues


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
