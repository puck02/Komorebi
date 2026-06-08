from app.services.story_planner import plan_content_sections, split_adjacent_image_ids


def test_plan_sections_from_body_when_model_sections_missing():
    layout = {
        "content": {
            "body": ["早餐在窗边吃。", "后来走到海边。"],
            "sections": [],
        },
        "theme": {"mood": ["日常"]},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3", "img_4"])

    assert [section["imageIds"] for section in sections] == [["img_1", "img_2"], ["img_3", "img_4"]]
    assert [section["body"] for section in sections] == ["早餐在窗边吃。", "后来走到海边。"]


def test_plan_sections_uses_image_understanding_when_body_runs_out():
    layout = {
        "content": {
            "body": ["早餐在窗边吃。"],
            "imageUnderstanding": [
                {"imageId": "img_3", "summary": "海边蓝色遮阳伞", "scene": "海边", "subjects": []},
                {"imageId": "img_4", "summary": "傍晚岸边的长椅", "scene": "岸边", "subjects": []},
            ],
            "sections": [],
        },
        "theme": {"mood": ["日常"]},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3", "img_4"])

    assert [section["imageIds"] for section in sections] == [["img_1", "img_2"], ["img_3", "img_4"]]
    assert sections[1]["body"] == "海边蓝色遮阳伞，还有傍晚岸边的长椅。"


def test_plan_sections_uses_subjects_when_understanding_summary_is_numbered_photo_label():
    layout = {
        "content": {
            "body": [],
            "imageUnderstanding": [
                {"imageId": "img_1", "summary": "第 2 张照片", "scene": "海边", "subjects": ["蓝色遮阳伞", "长椅"]},
            ],
            "sections": [],
        },
        "theme": {"mood": ["日常"]},
    }

    sections = plan_content_sections(layout, ["img_1"])

    assert sections[0]["body"] == "蓝色遮阳伞、长椅。"


def test_plan_sections_splits_non_adjacent_model_section():
    layout = {
        "content": {
            "body": ["模型把不相邻照片放到一起。"],
            "sections": [
                {
                    "id": "mixed",
                    "title": "混在一起",
                    "imageIds": ["img_1", "img_3"],
                    "body": "模型把不相邻照片放到一起。",
                    "mood": ["日常"],
                }
            ],
        },
        "theme": {"mood": []},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3"])

    assert [image_id for section in sections for image_id in section["imageIds"]] == ["img_1", "img_2", "img_3"]
    assert [section["imageIds"] for section in sections] == [["img_1"], ["img_2"], ["img_3"]]


def test_plan_sections_splits_groups_larger_than_three_images():
    layout = {
        "content": {
            "body": ["这一整段照片很多。"],
            "sections": [
                {
                    "id": "many",
                    "title": "很多照片",
                    "imageIds": ["img_1", "img_2", "img_3", "img_4", "img_5"],
                    "body": "这一整段照片很多。",
                    "mood": ["日常"],
                }
            ],
        },
        "theme": {"mood": []},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3", "img_4", "img_5"])

    assert [section["imageIds"] for section in sections] == [["img_1", "img_2", "img_3"], ["img_4", "img_5"]]


def test_plan_sections_uses_body_fallback_for_empty_model_body():
    layout = {
        "content": {
            "body": ["第一段正文。", "第二段正文。"],
            "sections": [
                {"id": "section_a", "title": "第一段", "imageIds": ["img_1"], "body": "", "mood": []},
                {"id": "section_b", "title": "第二段", "imageIds": ["img_2"], "mood": []},
            ],
        },
        "theme": {"mood": []},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2"])

    assert [section["body"] for section in sections] == ["第一段正文。", "第二段正文。"]


def test_plan_sections_keeps_each_image_once_in_order_when_model_duplicates():
    layout = {
        "content": {
            "body": ["重复图片。"],
            "sections": [
                {"id": "a", "title": "A", "imageIds": ["img_1", "img_2"], "body": "A", "mood": []},
                {"id": "b", "title": "B", "imageIds": ["img_2", "img_3"], "body": "B", "mood": []},
            ],
        },
        "theme": {"mood": []},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3"])

    assert [image_id for section in sections for image_id in section["imageIds"]] == ["img_1", "img_2", "img_3"]


def test_plan_sections_adds_images_missing_from_model_sections():
    layout = {
        "content": {
            "body": ["第一张已经写了。", "后面两张也要补上。"],
            "sections": [
                {"id": "a", "title": "A", "imageIds": ["img_1"], "body": "第一张已经写了。", "mood": []}
            ],
        },
        "theme": {"mood": []},
    }

    sections = plan_content_sections(layout, ["img_1", "img_2", "img_3"])

    assert [image_id for section in sections for image_id in section["imageIds"]] == ["img_1", "img_2", "img_3"]
    assert sections[-1]["imageIds"] == ["img_2", "img_3"]
    assert sections[-1]["body"] == "后面两张也要补上。"


def test_split_adjacent_image_ids_sorts_by_original_order():
    groups = split_adjacent_image_ids(["img_3", "img_1", "img_2", "img_5"], ["img_1", "img_2", "img_3", "img_4", "img_5"])

    assert groups == [["img_1", "img_2", "img_3"], ["img_5"]]
