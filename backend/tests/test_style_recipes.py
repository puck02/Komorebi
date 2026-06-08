from app.services.assets import AssetItem
from app.services.style_recipes import choose_asset_id, recipe_tags_for_section


def test_recipe_tags_for_section_detects_coffee_memory():
    section = {"title": "窗边咖啡", "body": "坐在咖啡店里，桌上有小票和一杯咖啡。", "imageIds": ["img_1"]}
    understanding = [
        {"imageId": "img_1", "summary": "窗边咖啡和小票", "scene": "咖啡店", "subjects": ["咖啡", "小票"], "mood": ["放松"]}
    ]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:2] == ["coffee", "warm"]


def test_recipe_tags_for_section_detects_travel_route():
    section = {"title": "路上", "body": "从车站出来，沿途慢慢走。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "站台和路线牌", "scene": "车站", "subjects": ["站台"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert "travel" in tags
    assert "walk" in tags


def test_recipe_tags_for_section_detects_photo_memory():
    section = {"title": "照片拼贴", "body": "把几张拍立得和相册小角贴在一起。", "imageIds": ["img_1"]}
    understanding = [
        {"imageId": "img_1", "summary": "桌面上的相片和照片角", "scene": "手账页", "subjects": ["照片", "相册"], "mood": []}
    ]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:3] == ["photo", "memory", "collage"]


def test_recipe_tags_for_section_detects_ticket_memory():
    section = {"title": "展览票根", "body": "票根和小卡片都夹在这一页。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "展览门票和票根", "scene": "展览", "subjects": ["票根"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:3] == ["ticket", "travel", "memory"]


def test_recipe_tags_for_section_detects_note_memory():
    section = {"title": "今日便签", "body": "纸条上写了今天的几件小事。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "便签纸和手写记录", "scene": "桌面", "subjects": ["便签"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:3] == ["note", "daily", "collage"]


def test_recipe_tags_for_section_detects_stamp_and_film_ephemera():
    section = {"title": "冲印相片", "body": "胶片边和旧邮票放在照片旁边。", "imageIds": ["img_1"]}
    understanding = [
        {"imageId": "img_1", "summary": "照片旁边有邮票和胶片", "scene": "手账桌面", "subjects": ["胶片", "邮票"], "mood": []}
    ]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["film", "stamp", "photo", "memory"]


def test_recipe_tags_for_section_detects_letter_and_tag_ephemera():
    section = {"title": "写给今天", "body": "信封、封蜡和牛皮纸标签压在便签下面。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "信封和标签", "scene": "桌面", "subjects": ["信封", "封蜡", "标签"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["letter", "seal", "tag", "note"]


def test_choose_asset_id_prefers_category_asset_with_matching_recipe_tag():
    assets = {
        "sticker_leaf_05": asset("sticker_leaf_05", "sticker", ["nature", "travel"]),
        "sticker_coffee_06": asset("sticker_coffee_06", "sticker", ["coffee", "daily"]),
    }

    result = choose_asset_id(assets, "sticker", offset=0, preferred_tags=["coffee"])

    assert result == "sticker_coffee_06"


def test_choose_asset_id_keeps_best_recipe_match_across_section_offsets():
    assets = {
        "sticker_coffee_06": asset("sticker_coffee_06", "sticker", ["coffee", "daily"]),
        "sticker_daily_02": asset("sticker_daily_02", "sticker", ["daily"]),
        "sticker_leaf_05": asset("sticker_leaf_05", "sticker", ["nature", "travel"]),
    }

    result = choose_asset_id(assets, "sticker", offset=1, preferred_tags=["coffee", "daily"])

    assert result == "sticker_coffee_06"


def test_choose_asset_id_rotates_between_equally_matching_assets():
    assets = {
        "paper_note_cream_01": asset("paper_note_cream_01", "paper", ["daily", "warm", "note"]),
        "paper_note_linen_11": asset("paper_note_linen_11", "paper", ["daily", "warm", "note"]),
        "paper_label_sage_12": asset("paper_label_sage_12", "paper", ["nature", "calm", "label"]),
    }

    result = choose_asset_id(assets, "paper", offset=1, preferred_tags=["daily", "warm"])

    assert result == "paper_note_linen_11"


def test_choose_asset_id_prefers_more_matching_recipe_tags():
    assets = {
        "paper_daily_01": asset("paper_daily_01", "paper", ["daily", "note"]),
        "paper_warm_daily_02": asset("paper_warm_daily_02", "paper", ["daily", "warm", "note"]),
    }

    result = choose_asset_id(assets, "paper", offset=0, preferred_tags=["daily", "warm", "collage"])

    assert result == "paper_warm_daily_02"


def test_choose_asset_id_prefers_internal_asset_when_recipe_match_is_equal():
    assets = {
        "ext_streamline_camera": asset(
            "ext_streamline_camera",
            "sticker",
            ["photo", "memory"],
            source="https://icon-sets.iconify.design/streamline-freehand-color/",
        ),
        "sticker_photo_corner_21": asset("sticker_photo_corner_21", "sticker", ["photo", "memory"]),
    }

    result = choose_asset_id(assets, "sticker", offset=0, preferred_tags=["photo", "memory"])

    assert result == "sticker_photo_corner_21"


def test_choose_asset_id_rotates_only_within_same_source_priority_group():
    assets = {
        "ext_streamline_camera": asset(
            "ext_streamline_camera",
            "sticker",
            ["photo", "memory"],
            source="https://icon-sets.iconify.design/streamline-freehand-color/",
        ),
        "sticker_photo_corner_21": asset("sticker_photo_corner_21", "sticker", ["photo", "memory"]),
        "sticker_camera_07": asset("sticker_camera_07", "sticker", ["photo", "memory"]),
    }

    result = choose_asset_id(assets, "sticker", offset=2, preferred_tags=["photo", "memory"])

    assert result == "sticker_camera_07"


def test_choose_asset_id_keeps_preferred_asset_when_category_matches():
    assets = {
        "sticker_leaf_05": asset("sticker_leaf_05", "sticker", ["nature", "travel"]),
        "sticker_coffee_06": asset("sticker_coffee_06", "sticker", ["coffee", "daily"]),
    }

    result = choose_asset_id(
        assets,
        "sticker",
        offset=0,
        preferred_tags=["coffee"],
        preferred_asset_ids=["sticker_leaf_05"],
    )

    assert result == "sticker_leaf_05"


def asset(asset_id: str, category: str, tags: list[str], source: str = "internal") -> AssetItem:
    return AssetItem(
        id=asset_id,
        name=asset_id,
        category=category,
        tags=tags,
        style=["soft-collage"],
        colors=["#fef6e4"],
        file=f"{asset_id}.svg",
        license="internal",
        source=source,
        quality_status="approved",
    )
