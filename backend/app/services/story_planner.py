from math import ceil
from typing import Any


def plan_content_sections(layout: dict[str, Any], image_ids: list[str]) -> list[dict[str, Any]]:
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
            body = section_body(raw_section, layout, index)
            title = str(raw_section.get("title") or section_title_from_body(body, index + 1)).strip()
            mood = normalize_string_list(raw_section.get("mood"))
            raw_section_id = str(raw_section.get("id") or f"section_{len(sections) + 1}")
            adjacent_groups = split_adjacent_image_ids(section_image_ids, image_ids)
            for group_index, adjacent_group in enumerate(adjacent_groups):
                section_id = raw_section_id if len(adjacent_groups) == 1 else f"{raw_section_id}_{group_index + 1}"
                sections.append(build_section(section_id, title, adjacent_group, body, mood, len(sections) + 1))
                used_image_ids.update(adjacent_group)

    if sections:
        return sections
    return build_sections_from_body(layout, image_ids)


def split_adjacent_image_ids(section_image_ids: list[str], ordered_image_ids: list[str]) -> list[list[str]]:
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
        if previous_order is None or (current_order == previous_order + 1 and len(current_group) < 3):
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


def build_sections_from_body(layout: dict[str, Any], image_ids: list[str]) -> list[dict[str, Any]]:
    paragraphs = normalized_body(layout)
    section_count = max(len(paragraphs), min(ceil(len(image_ids) / 3), 4), 1)
    image_groups = split_evenly(image_ids, section_count)
    mood = normalize_string_list(layout.get("theme", {}).get("mood") if isinstance(layout.get("theme"), dict) else [])
    sections: list[dict[str, Any]] = []

    for index, group in enumerate(image_groups):
        if not group:
            continue
        body = paragraphs[index] if index < len(paragraphs) else "这一组照片也想好好留下。"
        sections.append(
            build_section(
                f"section_{len(sections) + 1}",
                section_title_from_body(body, len(sections) + 1),
                group,
                body,
                mood,
                len(sections) + 1,
            )
        )
    return sections


def section_body(raw_section: dict[str, Any], layout: dict[str, Any], index: int) -> str:
    body = str(raw_section.get("body") or "").strip()
    if body:
        return body
    paragraphs = normalized_body(layout)
    if index < len(paragraphs):
        return paragraphs[index]
    return "这一组照片也想好好留下。"


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
) -> dict[str, Any]:
    body = str(body or "").strip() or "这一组照片也想好好留下。"
    return {
        "id": section_id,
        "title": title or section_title_from_body(body, index),
        "imageIds": image_ids,
        "body": body,
        "mood": mood,
    }


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
