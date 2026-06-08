from math import ceil, isfinite
from typing import Any

from app.services.assets import AssetItem

CANVAS_WIDTH = 1080
PHOTO_SAFE_INSET_RATIO = 0.18
TAPE_MAX_WIDTH = 260
TAPE_MAX_HEIGHT = 70
TAPE_MIN_WIDTH = 150
TAPE_MIN_HEIGHT = 38
PHOTO_CORNER_MAX_SIZE = 128
PHOTO_CORNER_MIN_SIZE = 40
MAX_DECORATIONS = 22
DECORATION_CATEGORY_LIMITS = {
    "paper": 4,
    "sticker": 8,
    "tape": 8,
    "texture": 2,
}
PAPER_FUNCTIONS = {"note", "ticket", "label"}
STICKER_FUNCTIONS = {"flower", "star", "line"}


def place_decorations(
    decorations: list[dict[str, Any]],
    image_placements: list[dict[str, Any]],
    text_placements: list[dict[str, Any]],
    asset_by_id: dict[str, AssetItem],
) -> list[dict[str, Any]]:
    placed: list[dict[str, Any]] = []
    paper_backings: list[dict[str, Any]] = []

    for decoration in decorations:
        asset = asset_by_id.get(str(decoration.get("assetId")))
        function = infer_asset_function(asset) if asset is not None else "sticker"
        if function in PAPER_FUNCTIONS:
            paper = place_paper_backing(decoration, text_placements, image_placements, len(paper_backings))
            paper_backings.append(paper)
            placed.append(paper)
            continue
        if function == "tape":
            placed.append(snap_tape_to_target(decoration, [*paper_backings, *image_placements]))
            continue
        if function == "texture":
            placed.append(clamp_decoration_to_canvas(decoration))
            continue
        if function == "photo_corner":
            photo_corner = place_photo_corner_sticker(decoration, image_placements, text_placements)
            if photo_corner is not None:
                placed.append(photo_corner)
            continue
        sticker = place_sticker(decoration, image_placements, text_placements)
        if sticker is not None:
            placed.append(sticker)

    return limit_decoration_density(placed, asset_by_id)


def infer_asset_function(asset: AssetItem) -> str:
    text = " ".join([asset.id, asset.name, asset.category, *asset.tags]).lower()
    if asset.category == "tape":
        return "tape"
    if asset.category == "texture":
        return "texture"
    if asset.category == "paper":
        if "ticket" in text:
            return "ticket"
        if "label" in text:
            return "label"
        return "note"
    if "photo_corner" in text or "photo corner" in text:
        return "photo_corner"
    if "flower" in text:
        return "flower"
    if "star" in text:
        return "star"
    if "line" in text:
        return "line"
    return "sticker"


def place_paper_backing(
    decoration: dict[str, Any],
    text_placements: list[dict[str, Any]],
    image_placements: list[dict[str, Any]],
    index: int,
) -> dict[str, Any]:
    backing_targets = [text for text in text_placements if text.get("role") == "body"] or text_placements
    text = backing_targets[index % len(backing_targets)] if backing_targets else None
    next_decoration = dict(decoration)
    if text is None:
        return clamp_decoration_to_canvas(next_decoration)

    text_width = positive_number(text.get("width"), 760)
    font_size = positive_number(text.get("fontSize"), 30)
    text_height = max(font_size * 2.4, positive_number(text.get("height"), 0))
    width = min(max(positive_number(decoration.get("width"), 0), text_width + 84), CANVAS_WIDTH - 80)
    height = max(positive_number(decoration.get("height"), 0), text_height + 78, 138)
    x = positive_number(text.get("x"), 80) - 42
    y = positive_number(text.get("y"), 0) - 34

    next_decoration["width"] = width
    next_decoration["height"] = height
    next_decoration["x"] = clamp_number(x, 40, max(CANVAS_WIDTH - width - 40, 40))
    next_decoration["y"] = max(y, 0)
    next_decoration["rotation"] = clamp_number(positive_number(decoration.get("rotation"), -1.5), -4, 4)

    if overlaps_photo_safe_area(next_decoration, image_placements):
        image_bottom = max((rect_from_item(image)[1] + rect_from_item(image)[3] for image in image_placements), default=0)
        next_decoration["y"] = max(next_decoration["y"], image_bottom + 40)
    return clamp_decoration_to_canvas(next_decoration)


def snap_tape_to_target(decoration: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    if not targets:
        return clamp_decoration_to_canvas(decoration)

    target = nearest_rect(decoration, targets)
    tape_width = min(max(positive_number(decoration.get("width"), 210), TAPE_MIN_WIDTH), TAPE_MAX_WIDTH)
    tape_height = min(max(positive_number(decoration.get("height"), 52), TAPE_MIN_HEIGHT), TAPE_MAX_HEIGHT)
    target_x, target_y, target_width, target_height = rect_from_item(target)
    decoration_center_x = positive_number(decoration.get("x"), target_x) + tape_width / 2
    decoration_center_y = positive_number(decoration.get("y"), target_y) + tape_height / 2
    target_center_x = target_x + target_width / 2
    target_center_y = target_y + target_height / 2
    use_left_anchor = decoration_center_x <= target_center_x
    use_top_anchor = decoration_center_y <= target_center_y

    next_decoration = dict(decoration)
    next_decoration["width"] = tape_width
    next_decoration["height"] = tape_height
    next_decoration["x"] = target_x + (target_width * 0.12 if use_left_anchor else target_width * 0.68 - tape_width)
    next_decoration["y"] = target_y - tape_height * 0.45 if use_top_anchor else target_y + target_height - tape_height * 0.55
    next_decoration["rotation"] = clamp_number(positive_number(decoration.get("rotation"), -8 if use_left_anchor else 8), -12, 12)
    return clamp_decoration_to_canvas(next_decoration)


def place_sticker(
    decoration: dict[str, Any],
    image_placements: list[dict[str, Any]],
    text_placements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidate = clamp_decoration_to_canvas(decoration)
    if not overlaps_photo_safe_area(candidate, image_placements) and not overlaps_any_text(candidate, text_placements):
        return candidate

    width = positive_number(candidate.get("width"), 120)
    height = positive_number(candidate.get("height"), 120)
    anchors = sticker_anchors(image_placements, text_placements, width, height)
    for x, y in anchors:
        next_candidate = dict(candidate)
        next_candidate["x"] = clamp_number(x, 0, max(CANVAS_WIDTH - width, 0))
        next_candidate["y"] = max(y, 0)
        if not overlaps_photo_safe_area(next_candidate, image_placements) and not overlaps_any_text(next_candidate, text_placements):
            return next_candidate
    return None


def place_photo_corner_sticker(
    decoration: dict[str, Any],
    image_placements: list[dict[str, Any]],
    text_placements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not image_placements:
        return place_sticker(decoration, image_placements, text_placements)

    target = nearest_rect(decoration, image_placements)
    target_x, target_y, target_width, target_height = rect_from_item(target)
    size_limit = max(min(target_width, target_height) * 0.28, PHOTO_CORNER_MIN_SIZE)
    width = min(max(positive_number(decoration.get("width"), 96), PHOTO_CORNER_MIN_SIZE), PHOTO_CORNER_MAX_SIZE, size_limit)
    height = min(max(positive_number(decoration.get("height"), 96), PHOTO_CORNER_MIN_SIZE), PHOTO_CORNER_MAX_SIZE, size_limit)
    candidate = dict(decoration)
    candidate["width"] = width
    candidate["height"] = height
    candidate["x"] = target_x - width * 0.42
    candidate["y"] = target_y - height * 0.42
    candidate["rotation"] = clamp_number(positive_number(decoration.get("rotation"), -2), -6, 6)
    candidate = clamp_decoration_to_canvas(candidate)
    if overlaps_any_text(candidate, text_placements):
        return place_sticker(decoration, image_placements, text_placements)
    return candidate


def sticker_anchors(
    image_placements: list[dict[str, Any]],
    text_placements: list[dict[str, Any]],
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    anchors: list[tuple[float, float]] = []
    for image in image_placements:
        x, y, image_width, image_height = rect_from_item(image)
        anchors.extend(
            [
                (x - width * 0.55, y - height * 0.25),
                (x + image_width - width * 0.45, y - height * 0.25),
                (x - width * 0.55, y + image_height - height * 0.55),
                (x + image_width - width * 0.45, y + image_height - height * 0.55),
            ]
        )
    for text in text_placements:
        x, y, text_width, text_height = text_rect(text)
        anchors.extend([(x + text_width + 28, y), (x - width - 28, y), (x + text_width - width, y + text_height + 24)])
    anchors.extend([(80, 160), (CANVAS_WIDTH - width - 80, 160)])
    return anchors


def limit_decoration_density(decorations: list[dict[str, Any]], asset_by_id: dict[str, AssetItem]) -> list[dict[str, Any]]:
    limited: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for decoration in decorations:
        asset = asset_by_id.get(str(decoration.get("assetId")))
        category = asset.category if asset is not None else "unknown"
        category_limit = DECORATION_CATEGORY_LIMITS.get(category, 1)
        if category_counts.get(category, 0) >= category_limit:
            continue
        if len(limited) >= MAX_DECORATIONS:
            break
        category_counts[category] = category_counts.get(category, 0) + 1
        limited.append(decoration)
    return limited


def overlaps_photo_safe_area(decoration: dict[str, Any], image_placements: list[dict[str, Any]]) -> bool:
    decoration_rect = rect_from_item(decoration)
    return any(rects_overlap(decoration_rect, photo_safe_rect(image)) for image in image_placements)


def overlaps_any_text(decoration: dict[str, Any], text_placements: list[dict[str, Any]]) -> bool:
    decoration_rect = rect_from_item(decoration)
    return any(rects_overlap(decoration_rect, text_rect(text)) for text in text_placements)


def photo_safe_rect(image: dict[str, Any]) -> tuple[float, float, float, float]:
    x, y, width, height = rect_from_item(image)
    inset_x = width * PHOTO_SAFE_INSET_RATIO
    inset_y = height * PHOTO_SAFE_INSET_RATIO
    return (x + inset_x, y + inset_y, width - inset_x * 2, height - inset_y * 2)


def text_rect(text: dict[str, Any]) -> tuple[float, float, float, float]:
    x = positive_number(text.get("x"), 0)
    y = positive_number(text.get("y"), 0)
    width = positive_number(text.get("width"), 0)
    font_size = positive_number(text.get("fontSize"), 28)
    height = positive_number(text.get("height"), 0) or font_size * 2.4
    return (x, y, width, height)


def nearest_rect(decoration: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    decoration_center_x = positive_number(decoration.get("x"), 0) + positive_number(decoration.get("width"), 0) / 2
    decoration_center_y = positive_number(decoration.get("y"), 0) + positive_number(decoration.get("height"), 0) / 2

    def distance_squared(target: dict[str, Any]) -> float:
        target_x, target_y, target_width, target_height = rect_from_item(target)
        target_center_x = target_x + target_width / 2
        target_center_y = target_y + target_height / 2
        return (decoration_center_x - target_center_x) ** 2 + (decoration_center_y - target_center_y) ** 2

    return min(targets, key=distance_squared)


def rect_from_item(item: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        positive_number(item.get("x"), 0),
        positive_number(item.get("y"), 0),
        positive_number(item.get("width"), 0),
        positive_number(item.get("height"), 0),
    )


def rects_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def clamp_decoration_to_canvas(decoration: dict[str, Any]) -> dict[str, Any]:
    next_decoration = dict(decoration)
    width = positive_number(next_decoration.get("width"), 1)
    next_decoration["x"] = clamp_number(positive_number(next_decoration.get("x"), 0), 0, max(CANVAS_WIDTH - width, 0))
    next_decoration["y"] = max(positive_number(next_decoration.get("y"), 0), 0)
    return next_decoration


def positive_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not isfinite(number) or number <= 0:
        return fallback
    return number


def clamp_number(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)
