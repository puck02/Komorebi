from app.services.assets import AssetItem
from app.services.style_recipes import choose_asset_id, recipe_tags_for_section


def test_recipe_tags_for_section_detects_coffee_memory():
    section = {"title": "窗边咖啡", "body": "坐在咖啡店里，桌上有小票和一杯咖啡。", "imageIds": ["img_1"]}
    understanding = [
        {"imageId": "img_1", "summary": "窗边咖啡和小票", "scene": "咖啡店", "subjects": ["咖啡", "小票"], "mood": ["放松"]}
    ]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["ticket", "coffee", "warm", "memory"]


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


def test_recipe_tags_for_section_detects_checklist_note():
    section = {"title": "待办清单", "body": "便签上列了今天要做的几件事，还打了两个勾。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "清单便签和勾选标记", "scene": "桌面", "subjects": ["清单"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["checklist", "note", "pen", "daily"]


def test_recipe_tags_for_section_detects_bus_ticket():
    section = {"title": "通勤车票", "body": "公交车票夹在照片旁边，记一下今天的路线。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "公交车票和路线", "scene": "公交站", "subjects": ["公交车票"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["bus", "ticket", "travel", "memory"]


def test_recipe_tags_for_section_detects_pen_note():
    section = {"title": "钢笔旁边", "body": "钢笔和笔尖压着便签，旁边有一点墨水痕迹。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "钢笔、笔尖和便签", "scene": "桌面", "subjects": ["钢笔"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["pen", "hand", "note", "daily"]


def test_recipe_tags_for_section_detects_date_stamp_memory():
    section = {"title": "六月九日", "body": "把日期章盖在这一页，旁边写了今天的日历小记。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "日期章和日历", "scene": "手账页", "subjects": ["日期章", "日历"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:3] == ["date", "stamp", "memory"]


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


def test_recipe_tags_for_section_detects_torn_photo_corner():
    section = {"title": "照片边角", "body": "撕角照片角压住了这张相片。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "照片角和相片", "scene": "手账页", "subjects": ["照片角"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["corner", "photo", "collage", "memory"]


def test_recipe_tags_for_section_detects_pressed_leaf():
    section = {"title": "压叶", "body": "干花和压叶像植物标本一样放在纸边。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "压叶和植物标本", "scene": "桌面", "subjects": ["压叶"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:3] == ["pressed", "nature", "calm"]


def test_recipe_tags_for_section_detects_movie_ticket():
    section = {"title": "电影散场", "body": "电影票和爆米花小票还夹在这一页。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "影院电影票和票根", "scene": "电影院", "subjects": ["电影票"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["movie", "ticket", "night", "memory"]


def test_recipe_tags_for_section_detects_exhibition_art_ticket():
    section = {"title": "看展这段", "body": "展览里的装置作品有点诡异，门票和导览图都夹在这一页。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "艺术展览和装置作品", "scene": "展厅", "subjects": ["作品", "门票"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["exhibition", "art", "ticket", "memory"]


def test_recipe_tags_for_section_detects_shopping_receipt():
    section = {"title": "买到喜欢的", "body": "购物小票、纸袋和收据放在照片旁边。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "购物小票和纸袋", "scene": "店里", "subjects": ["小票", "纸袋"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["shopping", "receipt", "daily", "memory"]


def test_recipe_tags_for_section_detects_rainy_umbrella():
    section = {"title": "雨天路上", "body": "雨伞上还有雨滴，回来的路有点安静。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "雨伞和雨滴", "scene": "街边", "subjects": ["雨伞"], "mood": ["安静"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["umbrella", "rainy", "weather", "calm"]


def test_recipe_tags_for_section_detects_night_lamp():
    section = {"title": "夜里写完", "body": "窗边小灯亮着，夜晚的桌面很安静。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "夜晚的台灯和窗", "scene": "房间", "subjects": ["台灯"], "mood": ["安静"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["lamp", "night", "calm", "memory"]


def test_recipe_tags_for_section_detects_cat_pet():
    section = {"title": "猫趴着", "body": "小猫趴在毯子上，爪印留在旁边。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "猫和爪印", "scene": "家里", "subjects": ["猫"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["cat", "pet", "home", "daily"]


def test_recipe_tags_for_section_detects_birthday_cake():
    section = {"title": "生日蛋糕", "body": "蛋糕、蜡烛和礼物都摆在桌上。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "生日蛋糕和蜡烛", "scene": "餐桌", "subjects": ["蛋糕", "蜡烛"], "mood": ["庆祝"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["cake", "birthday", "party", "gift"]


def test_recipe_tags_for_section_detects_book_reading():
    section = {"title": "读到这里", "body": "书页摊开，旁边夹着书签和几行笔记。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "摊开的书和书签", "scene": "书桌", "subjects": ["书", "书签"], "mood": ["安静"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["book", "quiet", "note", "home"]


def test_recipe_tags_for_section_detects_table_food():
    section = {"title": "晚饭桌上", "body": "餐桌上有盘子、面包和一张菜单卡。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "餐桌上的盘子和菜单", "scene": "餐桌", "subjects": ["盘子", "菜单"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["food", "table", "warm", "daily"]


def test_recipe_tags_for_section_detects_seaside_memory():
    section = {"title": "海边这段", "body": "海边的浪和贝壳都放进这一页。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "海边浪花和贝壳", "scene": "海边", "subjects": ["贝壳", "海浪"], "mood": ["放松"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["sea", "shell", "travel", "calm"]


def test_recipe_tags_for_section_detects_commute_bus():
    section = {"title": "早上通勤", "body": "公交车和站牌在路边，今天的路线也记一下。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "公交车和站牌", "scene": "公交站", "subjects": ["公交车", "站牌"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["commute", "bus", "travel", "daily"]


def test_recipe_tags_for_section_detects_dog_pet():
    section = {"title": "狗趴在地毯上", "body": "小狗睡着了，旁边还放着牵引绳。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "小狗和牵引绳", "scene": "家里", "subjects": ["狗"], "mood": []}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["dog", "pet", "home", "daily"]


def test_recipe_tags_for_section_detects_houseplant_home():
    section = {"title": "窗边绿植", "body": "盆栽和叶子靠在窗边，光落在桌面上。", "imageIds": ["img_1"]}
    understanding = [{"imageId": "img_1", "summary": "窗边盆栽和绿植", "scene": "房间", "subjects": ["盆栽", "绿植"], "mood": ["安静"]}]

    tags = recipe_tags_for_section(section, understanding)

    assert tags[:4] == ["plant", "home", "calm", "nature"]


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
