from typing import Any

from app.services.assets import AssetItem

COFFEE_KEYWORDS = {"咖啡", "咖啡店", "小票", "甜品", "茶", "饮料", "餐桌"}
TRAVEL_KEYWORDS = {"旅行", "路上", "车站", "站台", "地铁", "路线", "沿途", "散步", "海边"}
CALM_KEYWORDS = {"安静", "窗边", "平静", "慢", "独处", "雨", "夜色"}
BIRTHDAY_KEYWORDS = {"生日", "礼物", "蛋糕", "庆祝", "派对"}
PET_KEYWORDS = {"猫", "狗", "宠物", "小猫", "小狗", "爪"}


def recipe_tags_for_section(
    section: dict[str, Any],
    image_understanding: list[dict[str, Any]],
) -> list[str]:
    text = section_keyword_text(section, image_understanding)
    if any(keyword in text for keyword in COFFEE_KEYWORDS):
        return ["coffee", "warm", "daily"]
    if any(keyword in text for keyword in BIRTHDAY_KEYWORDS):
        return ["birthday", "warm", "party", "gift"]
    if any(keyword in text for keyword in PET_KEYWORDS):
        return ["pet", "home", "daily"]
    if any(keyword in text for keyword in TRAVEL_KEYWORDS):
        return ["travel", "walk", "memory", "daily"]
    if any(keyword in text for keyword in CALM_KEYWORDS):
        return ["calm", "daily", "warm"]
    return ["daily", "warm", "collage"]


def choose_asset_id(
    asset_by_id: dict[str, AssetItem],
    category: str,
    offset: int,
    preferred_tags: list[str],
    preferred_asset_ids: list[str] | None = None,
) -> str | None:
    preferred_ids = [
        asset_id
        for asset_id in preferred_asset_ids or []
        if (asset := asset_by_id.get(asset_id)) is not None and asset.category == category and asset.quality_status == "approved"
    ]
    if preferred_ids:
        return preferred_ids[0]

    assets = [
        asset
        for asset in asset_by_id.values()
        if asset.category == category and asset.quality_status == "approved"
    ]
    if not assets:
        return None

    tag_rank = {tag: index for index, tag in enumerate(preferred_tags)}

    def score(asset: AssetItem) -> tuple[int, int, str]:
        matching_tag_indexes = [tag_rank[tag] for tag in asset.tags if tag in tag_rank]
        best_tag_index = min(matching_tag_indexes) if matching_tag_indexes else len(tag_rank) + 1
        return (0 if matching_tag_indexes else 1, best_tag_index, asset.id)

    ranked_assets = sorted(assets, key=score)
    if ranked_assets and score(ranked_assets[0])[0] == 0:
        return ranked_assets[offset % len(ranked_assets)].id if offset and len(ranked_assets) > 1 else ranked_assets[0].id
    return assets[offset % len(assets)].id


def section_keyword_text(section: dict[str, Any], image_understanding: list[dict[str, Any]]) -> str:
    section_image_ids = set(section.get("imageIds") or section.get("image_ids") or [])
    parts = [str(section.get("title") or ""), str(section.get("body") or "")]
    parts.extend(str(item) for item in section.get("mood") or [])
    for item in image_understanding:
        if item.get("imageId") not in section_image_ids:
            continue
        parts.extend([str(item.get("summary") or ""), str(item.get("scene") or "")])
        parts.extend(str(subject) for subject in item.get("subjects") or [])
        parts.extend(str(mood) for mood in item.get("mood") or [])
    return " ".join(parts)
