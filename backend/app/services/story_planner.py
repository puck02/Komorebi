from math import ceil
from typing import Any

from app.services.diary_copy import compose_observation_note
from app.services.journal_templates import ALLOWED_SECTION_VARIANTS, SECTION_VARIANT_IMAGE_LIMITS

DEFAULT_SECTION_IMAGE_LIMIT = 3


def plan_content_sections(
    layout: dict[str, Any],
    image_ids: list[str],
    suggested_variant: str | None = None,
    suggested_group_limit: int | None = None,
) -> list[dict[str, Any]]:
    image_id_set = set(image_ids)
    raw_sections = layout.get("content", {}).get("sections")
    sections: list[dict[str, Any]] = []
    used_image_ids: set[str] = set()

    if isinstance(raw_sections, list):
        for index, raw_section in enumerate(raw_sections):
            if not isinstance(raw_section, dict):
                continue
            section_image_ids = normalized_section_image_ids(raw_section, image_id_set, used_image_ids)
            if not section_image_ids:
                continue
            body = section_body(raw_section, layout, index, section_image_ids)
            title = str(raw_section.get("title") or section_title_from_body(body, index + 1)).strip()
            mood = normalize_string_list(raw_section.get("mood"))
            variant = section_variant(raw_section) or suggested_variant
            raw_section_id = str(raw_section.get("id") or f"section_{len(sections) + 1}")
            adjacent_groups = split_adjacent_image_ids(
                section_image_ids,
                image_ids,
                max_group_size=section_image_limit(variant, suggested_group_limit),
            )
            for group_index, adjacent_group in enumerate(adjacent_groups):
                section_id = raw_section_id if len(adjacent_groups) == 1 else f"{raw_section_id}_{group_index + 1}"
                section_id = unique_section_id(section_id, sections)
                sections.append(build_section(section_id, title, adjacent_group, body, mood, len(sections) + 1, variant))
                used_image_ids.update(adjacent_group)

    if sections:
        sections.extend(
            build_missing_image_sections(
                layout,
                image_ids,
                used_image_ids,
                len(sections),
                suggested_variant,
                suggested_group_limit,
            )
        )
        return sort_sections_by_image_order(sections, image_ids)
    return build_sections_from_body(layout, image_ids, suggested_variant, suggested_group_limit)


def split_adjacent_image_ids(
    section_image_ids: list[str],
    ordered_image_ids: list[str],
    max_group_size: int = DEFAULT_SECTION_IMAGE_LIMIT,
) -> list[list[str]]:
    order_by_id = {image_id: index for index, image_id in enumerate(ordered_image_ids)}
    ordered_ids = sorted(
        [image_id for image_id in section_image_ids if image_id in order_by_id],
        key=lambda image_id: order_by_id[image_id],
    )
    groups: list[list[str]] = []
    current_group: list[str] = []
    previous_order: int | None = None
    for image_id in ordered_ids:
        current_order = order_by_id[image_id]
        if previous_order is None or (
            current_order == previous_order + 1 and len(current_group) < max(max_group_size, 1)
        ):
            current_group.append(image_id)
        else:
            groups.append(current_group)
            current_group = [image_id]
        previous_order = current_order
    if current_group:
        groups.append(current_group)
    return groups


def normalized_section_image_ids(
    raw_section: dict[str, Any],
    image_id_set: set[str],
    used_image_ids: set[str],
) -> list[str]:
    raw_image_ids = raw_section.get("imageIds")
    if raw_image_ids is None:
        raw_image_ids = raw_section.get("image_ids")
    section_image_ids: list[str] = []
    for raw_image_id in raw_image_ids or []:
        image_id = str(raw_image_id)
        if image_id not in image_id_set or image_id in used_image_ids:
            continue
        section_image_ids.append(image_id)
    return section_image_ids


def build_sections_from_body(
    layout: dict[str, Any],
    image_ids: list[str],
    suggested_variant: str | None = None,
    suggested_group_limit: int | None = None,
) -> list[dict[str, Any]]:
    paragraphs = normalized_body(layout)
    section_count = section_count_from_body(len(image_ids), len(paragraphs), suggested_variant, suggested_group_limit)
    image_groups = split_evenly(image_ids, section_count)
    mood = normalize_string_list(layout.get("theme", {}).get("mood") if isinstance(layout.get("theme"), dict) else [])
    sections: list[dict[str, Any]] = []

    for index, group in enumerate(image_groups):
        if not group:
            continue
        body = paragraphs[index] if index < len(paragraphs) else section_body_from_understanding(layout, group)
        sections.append(
            build_section(
                f"section_{len(sections) + 1}",
                section_title_from_body(body, len(sections) + 1),
                group,
                body,
                mood,
                len(sections) + 1,
                suggested_variant,
            )
        )
    return sections


def section_count_from_body(
    image_count: int,
    paragraph_count: int,
    suggested_variant: str | None,
    suggested_group_limit: int | None = None,
) -> int:
    if image_count <= 0:
        return 1
    if suggested_group_limit is not None and suggested_group_limit > 0:
        return max(paragraph_count, ceil(image_count / suggested_group_limit), 1)
    if suggested_variant in {"pocket_grid", "detail_index", "moodboard_stack"}:
        max_images = SECTION_VARIANT_IMAGE_LIMITS.get(suggested_variant, image_count)
        if image_count <= max_images:
            return max(paragraph_count, 1)
    if suggested_variant == "split_scene":
        return max(paragraph_count, min(2, image_count), 1)
    if suggested_variant == "chapter_scroll":
        return max(paragraph_count, ceil(image_count / 3), 1)
    return max(paragraph_count, min(ceil(image_count / DEFAULT_SECTION_IMAGE_LIMIT), 4), 1)


def build_missing_image_sections(
    layout: dict[str, Any],
    image_ids: list[str],
    used_image_ids: set[str],
    existing_section_count: int,
    suggested_variant: str | None = None,
    suggested_group_limit: int | None = None,
) -> list[dict[str, Any]]:
    missing_image_ids = [image_id for image_id in image_ids if image_id not in used_image_ids]
    if not missing_image_ids:
        return []

    paragraphs = normalized_body(layout)
    mood = normalize_string_list(layout.get("theme", {}).get("mood") if isinstance(layout.get("theme"), dict) else [])
    sections: list[dict[str, Any]] = []
    for group in split_adjacent_image_ids(
        missing_image_ids,
        image_ids,
        max_group_size=section_image_limit(suggested_variant, suggested_group_limit),
    ):
        body_index = existing_section_count + len(sections)
        body = paragraphs[body_index] if body_index < len(paragraphs) else section_body_from_understanding(layout, group)
        sections.append(
            build_section(
                f"section_{existing_section_count + len(sections) + 1}",
                section_title_from_body(body, existing_section_count + len(sections) + 1),
                group,
                body,
                mood,
                existing_section_count + len(sections) + 1,
                suggested_variant,
            )
        )
    return sections


def section_variant(raw_section: dict[str, Any]) -> str | None:
    variant = raw_section.get("variant")
    if variant in ALLOWED_SECTION_VARIANTS:
        return str(variant)
    return None


def section_image_limit(variant: str | None, suggested_group_limit: int | None = None) -> int:
    if suggested_group_limit is not None and suggested_group_limit > 0:
        return suggested_group_limit
    if variant is None:
        return DEFAULT_SECTION_IMAGE_LIMIT
    return SECTION_VARIANT_IMAGE_LIMITS.get(variant, DEFAULT_SECTION_IMAGE_LIMIT)


def sort_sections_by_image_order(sections: list[dict[str, Any]], image_ids: list[str]) -> list[dict[str, Any]]:
    order_by_id = {image_id: index for index, image_id in enumerate(image_ids)}

    def first_image_order(section: dict[str, Any]) -> int:
        section_image_ids = section.get("imageIds") or []
        return min((order_by_id.get(image_id, len(image_ids)) for image_id in section_image_ids), default=len(image_ids))

    return sorted(sections, key=first_image_order)


def unique_section_id(section_id: str, sections: list[dict[str, Any]]) -> str:
    used_ids = {section.get("id") for section in sections}
    if section_id not in used_ids:
        return section_id
    suffix = 2
    while f"{section_id}_{suffix}" in used_ids:
        suffix += 1
    return f"{section_id}_{suffix}"


def section_body(raw_section: dict[str, Any], layout: dict[str, Any], index: int, section_image_ids: list[str]) -> str:
    body = str(raw_section.get("body") or "").strip()
    if body:
        return body
    paragraphs = normalized_body(layout)
    if index < len(paragraphs):
        return paragraphs[index]
    return section_body_from_understanding(layout, section_image_ids)


def section_body_from_understanding(layout: dict[str, Any], image_ids: list[str]) -> str:
    understanding_by_id = {
        item.get("imageId"): item
        for item in layout.get("content", {}).get("imageUnderstanding", [])
        if isinstance(item, dict)
    }
    parts = [
        concrete_understanding_text(understanding_by_id[image_id])
        for image_id in image_ids
        if image_id in understanding_by_id
    ]
    parts = [part for part in parts if part]
    if not parts:
        return "这一组照片也想好好留下。"
    return compose_observation_note(parts, fallback="这一组照片也想好好留下。")


def concrete_understanding_text(item: dict[str, Any]) -> str:
    summary = str(item.get("summary") or "").strip()
    if summary and not numbered_photo_label(summary):
        return summary[:18]
    subjects = normalize_string_list(item.get("subjects"))
    if subjects:
        return "、".join(subjects[:2])[:18]
    scene = str(item.get("scene") or "").strip()
    if scene:
        return scene[:18]
    return ""


def numbered_photo_label(text: str) -> bool:
    return text.startswith("第 ") and "张照片" in text


def normalized_body(layout: dict[str, Any]) -> list[str]:
    body = layout.get("content", {}).get("body", [])
    if isinstance(body, str):
        return [body.strip()] if body.strip() else []
    if isinstance(body, list):
        return [str(paragraph).strip() for paragraph in body if str(paragraph).strip()]
    return []


def build_section(
    section_id: str,
    title: str,
    image_ids: list[str],
    body: str,
    mood: list[str],
    index: int,
    variant: str | None = None,
) -> dict[str, Any]:
    body = str(body or "").strip() or "这一组照片也想好好留下。"
    section = {
        "id": section_id,
        "title": title or section_title_from_body(body, index),
        "imageIds": image_ids,
        "body": body,
        "mood": mood,
    }
    if variant is not None:
        section["variant"] = variant
    return section


def section_title_from_body(body: str, index: int) -> str:
    text = body.strip()
    if not text:
        return f"片段 {index}"
    title = text.split("，", 1)[0].split("。", 1)[0].strip()
    return title[:12] or f"片段 {index}"


def split_evenly(items: list[Any], group_count: int) -> list[list[Any]]:
    if group_count <= 0:
        return []
    base_size, remainder = divmod(len(items), group_count)
    groups: list[list[Any]] = []
    cursor = 0
    for index in range(group_count):
        size = base_size + (1 if index < remainder else 0)
        groups.append(items[cursor : cursor + size])
        cursor += size
    return groups


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
