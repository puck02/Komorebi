from typing import Any

from app.services.assets import AssetItem

COFFEE_KEYWORDS = {"咖啡", "咖啡店", "甜品", "茶", "饮料"}
TRAVEL_KEYWORDS = {"旅行", "路上", "车站", "站台", "地铁", "路线", "沿途", "散步", "海边"}
CALM_KEYWORDS = {"安静", "窗边", "平静", "慢", "独处", "雨", "夜色"}
BIRTHDAY_KEYWORDS = {"生日", "礼物", "蛋糕", "庆祝", "派对"}
PET_KEYWORDS = {"猫", "狗", "宠物", "小猫", "小狗", "爪"}
MOVIE_KEYWORDS = {"电影", "电影票", "影院", "电影院", "观影", "散场", "爆米花"}
SHOPPING_KEYWORDS = {"购物", "纸袋", "购物袋", "买到", "逛店", "商场"}
RECEIPT_KEYWORDS = {"小票", "收据", "发票", "receipt"}
RAINY_KEYWORDS = {"雨天", "雨伞", "雨滴", "下雨", "淋雨", "雨衣", "伞"}
NIGHT_LAMP_KEYWORDS = {"夜晚", "夜里", "台灯", "小灯", "窗灯", "灯光", "卧室"}
CAT_KEYWORDS = {"猫", "小猫", "猫咪", "喵"}
CAKE_KEYWORDS = {"蛋糕", "蜡烛", "生日蛋糕", "许愿"}
BOOK_KEYWORDS = {"读书", "阅读", "书", "书页", "书签", "书桌", "翻书", "摘抄"}
FOOD_TABLE_KEYWORDS = {"餐桌", "饭", "晚饭", "午饭", "早餐", "盘子", "菜单", "面包", "餐厅", "料理", "便当"}
SEASIDE_KEYWORDS = {"海边", "海浪", "浪花", "贝壳", "沙滩", "海岸"}
COMMUTE_KEYWORDS = {"通勤", "公交车", "公交站", "站牌", "巴士", "早高峰", "地铁口"}
DOG_KEYWORDS = {"狗", "小狗", "狗狗", "牵引绳"}
HOUSEPLANT_KEYWORDS = {"盆栽", "绿植", "植物", "叶子", "花盆"}
PHOTO_KEYWORDS = {"照片", "相片", "相册", "拍立得", "照片角", "冲印", "合影"}
TICKET_KEYWORDS = {"票根", "门票", "车票", "入场券", "展览", "电影票", "小票", "收据", "小卡片"}
EXHIBITION_KEYWORDS = {"看展", "展厅", "美术馆", "博物馆", "艺术馆", "画展", "装置", "导览图", "展签"}
NOTE_KEYWORDS = {"便签", "纸条", "手写", "记录", "笔记", "备忘", "小事"}
CHECKLIST_KEYWORDS = {"清单", "待办", "勾选", "打勾", "事项", "todo", "checklist"}
BUS_TICKET_KEYWORDS = {"公交", "公交车票", "巴士", "车票", "通勤", "路线"}
PEN_KEYWORDS = {"钢笔", "笔尖", "笔", "墨水", "手写笔", "签字笔"}
PHOTO_CORNER_KEYWORDS = {"撕角", "相册角", "护角"}
PRESSED_NATURE_KEYWORDS = {"压叶", "压花", "干花", "植物标本", "叶片标本"}
DATE_STAMP_KEYWORDS = {"日期章", "日期", "日历", "盖章", "手帐章", "手账章"}
STAMP_FILM_KEYWORDS = {"邮票", "胶片", "底片", "冲印", "相纸", "旧照片"}
LETTER_TAG_KEYWORDS = {"信封", "信纸", "封蜡", "标签", "吊牌", "牛皮纸"}


def recipe_tags_for_section(
    section: dict[str, Any],
    image_understanding: list[dict[str, Any]],
) -> list[str]:
    text = section_keyword_text(section, image_understanding)
    if any(keyword in text for keyword in EXHIBITION_KEYWORDS):
        return ["exhibition", "art", "ticket", "memory"]
    if any(keyword in text for keyword in MOVIE_KEYWORDS) and any(keyword in text for keyword in TICKET_KEYWORDS):
        return ["movie", "ticket", "night", "memory"]
    if any(keyword in text for keyword in SHOPPING_KEYWORDS) and any(keyword in text for keyword in RECEIPT_KEYWORDS):
        return ["shopping", "receipt", "daily", "memory"]
    if any(keyword in text for keyword in RAINY_KEYWORDS):
        return ["umbrella", "rainy", "weather", "calm"]
    if any(keyword in text for keyword in NIGHT_LAMP_KEYWORDS):
        return ["lamp", "night", "calm", "memory"]
    if any(keyword in text for keyword in CAKE_KEYWORDS) and any(keyword in text for keyword in BIRTHDAY_KEYWORDS):
        return ["cake", "birthday", "party", "gift"]
    if any(keyword in text for keyword in CAT_KEYWORDS):
        return ["cat", "pet", "home", "daily"]
    if any(keyword in text for keyword in DOG_KEYWORDS):
        return ["dog", "pet", "home", "daily"]
    if any(keyword in text for keyword in BUS_TICKET_KEYWORDS) and any(keyword in text for keyword in TICKET_KEYWORDS):
        return ["bus", "ticket", "travel", "memory"]
    if any(keyword in text for keyword in PRESSED_NATURE_KEYWORDS):
        return ["pressed", "nature", "calm"]
    if any(keyword in text for keyword in BOOK_KEYWORDS):
        return ["book", "quiet", "note", "home"]
    if any(keyword in text for keyword in FOOD_TABLE_KEYWORDS):
        return ["food", "table", "warm", "daily"]
    if any(keyword in text for keyword in SEASIDE_KEYWORDS):
        return ["sea", "shell", "travel", "calm"]
    if any(keyword in text for keyword in COMMUTE_KEYWORDS):
        return ["commute", "bus", "travel", "daily"]
    if any(keyword in text for keyword in HOUSEPLANT_KEYWORDS):
        return ["plant", "home", "calm", "nature"]
    if any(keyword in text for keyword in COFFEE_KEYWORDS) and any(keyword in text for keyword in TICKET_KEYWORDS):
        return ["ticket", "coffee", "warm", "memory"]
    if any(keyword in text for keyword in COFFEE_KEYWORDS):
        return ["coffee", "warm", "daily"]
    if any(keyword in text for keyword in BIRTHDAY_KEYWORDS):
        return ["birthday", "warm", "party", "gift"]
    if any(keyword in text for keyword in PET_KEYWORDS):
        return ["pet", "home", "daily"]
    if any(keyword in text for keyword in CHECKLIST_KEYWORDS):
        return ["checklist", "note", "pen", "daily"]
    if any(keyword in text for keyword in PEN_KEYWORDS):
        return ["pen", "hand", "note", "daily"]
    if any(keyword in text for keyword in DATE_STAMP_KEYWORDS):
        return ["date", "stamp", "memory"]
    if any(keyword in text for keyword in PHOTO_CORNER_KEYWORDS):
        return ["corner", "photo", "collage", "memory"]
    if any(keyword in text for keyword in STAMP_FILM_KEYWORDS):
        return ["film", "stamp", "photo", "memory"]
    if any(keyword in text for keyword in LETTER_TAG_KEYWORDS):
        return ["letter", "seal", "tag", "note"]
    if any(keyword in text for keyword in TICKET_KEYWORDS):
        return ["ticket", "travel", "memory"]
    if any(keyword in text for keyword in PHOTO_KEYWORDS):
        return ["photo", "memory", "collage"]
    if any(keyword in text for keyword in NOTE_KEYWORDS):
        return ["note", "daily", "collage"]
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

    def score(asset: AssetItem) -> tuple[int, int, int, int, str]:
        matching_tag_indexes = [tag_rank[tag] for tag in asset.tags if tag in tag_rank]
        best_tag_index = min(matching_tag_indexes) if matching_tag_indexes else len(tag_rank) + 1
        source_rank = 0 if asset.source == "internal" else 1
        return (0 if matching_tag_indexes else 1, best_tag_index, -len(matching_tag_indexes), source_rank, asset.id)

    ranked_assets = sorted(assets, key=score)
    if ranked_assets and score(ranked_assets[0])[0] == 0:
        best_score = score(ranked_assets[0])
        equally_matched_assets = [asset for asset in ranked_assets if score(asset)[:4] == best_score[:4]]
        return equally_matched_assets[offset % len(equally_matched_assets)].id
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
