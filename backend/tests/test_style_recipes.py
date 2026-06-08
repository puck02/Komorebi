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


def test_choose_asset_id_prefers_category_asset_with_matching_recipe_tag():
    assets = {
        "sticker_leaf_05": asset("sticker_leaf_05", "sticker", ["nature", "travel"]),
        "sticker_coffee_06": asset("sticker_coffee_06", "sticker", ["coffee", "daily"]),
    }

    result = choose_asset_id(assets, "sticker", offset=0, preferred_tags=["coffee"])

    assert result == "sticker_coffee_06"


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


def asset(asset_id: str, category: str, tags: list[str]) -> AssetItem:
    return AssetItem(
        id=asset_id,
        name=asset_id,
        category=category,
        tags=tags,
        style=["soft-collage"],
        colors=["#fef6e4"],
        file=f"{asset_id}.svg",
        license="internal",
        source="internal",
        quality_status="approved",
    )
