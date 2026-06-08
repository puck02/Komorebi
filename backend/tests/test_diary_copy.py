from app.services.diary_copy import (
    compose_observation_note,
    has_cliche_copy,
    normalize_diary_blocks,
    normalize_diary_text,
    normalize_title,
)


def test_normalize_diary_text_removes_cliche_phrases():
    text = "今天被温柔包裹，也很治愈，充满仪式感，想把时光收藏成珍贵回忆。咖啡还热着。"

    result = normalize_diary_text(text)

    assert "被温柔包裹" not in result
    assert "治愈" not in result
    assert "仪式感" not in result
    assert "把时光收藏" not in result
    assert "珍贵回忆" not in result
    assert "咖啡还热着" in result


def test_normalize_diary_text_removes_ai_style_metaphors():
    text = "照片里是被阳光放慢的一天，咖啡和散步都刚刚好。适合把这些片段收成一页。"

    result = normalize_diary_text(text)

    assert "被阳光放慢" not in result
    assert "收成一页" not in result
    assert "是的一天" not in result
    assert "咖啡和散步" in result


def test_normalize_diary_text_removes_generic_just_right_tail():
    text = "咖啡、散步和好天气都刚刚好。"

    result = normalize_diary_text(text)

    assert "刚刚好" not in result
    assert result == "咖啡、散步和好天气。"


def test_normalize_diary_text_removes_template_journal_phrases():
    text = "今日份小确幸，照片里的氛围感很满，都是美好瞬间和生活碎片。咖啡还放在窗边。"

    result = normalize_diary_text(text)

    assert "今日份" not in result
    assert "小确幸" not in result
    assert "氛围感" not in result
    assert "美好瞬间" not in result
    assert "生活碎片" not in result
    assert "咖啡还放在窗边" in result


def test_normalize_diary_text_uses_fallback_when_cliche_cleanup_leaves_no_observation():
    result = normalize_diary_text("今日份小确幸，照片里的氛围感很满，都是美好瞬间和生活碎片。", fallback="今天先记到这里。")

    assert result == "今天先记到这里。"


def test_normalize_diary_text_drops_empty_today_stub_after_cliche_cleanup():
    result = normalize_diary_text("今天被温柔包裹，也很治愈，充满仪式感。", fallback="今天先记到这里。")

    assert result == "今天先记到这里。"


def test_normalize_diary_blocks_trims_and_splits_long_blocks():
    blocks = [
        "  ",
        "早上在窗边喝咖啡。",
        "先去车站等朋友，后来一起走到海边，风有点大。傍晚回来的时候路灯亮了，大家都没有急着回家。",
    ]

    result = normalize_diary_blocks(blocks, fallback="今日小记。", split_target=34)

    assert result[0] == "早上在窗边喝咖啡。"
    assert len(result) == 3
    assert all(len(block) <= 40 for block in result)
    assert result[-1].endswith("。")


def test_normalize_diary_blocks_uses_fallback_when_empty():
    result = normalize_diary_blocks([" ", ""], fallback="今日小记。")

    assert result == ["今日小记。"]


def test_normalize_diary_blocks_removes_duplicate_blocks_after_cleanup():
    result = normalize_diary_blocks(
        ["咖啡还热着，窗边坐了一会儿。", "咖啡还热着，窗边坐了一会儿。", "后来走到路口，云压得很低。"],
        fallback="今日小记。",
    )

    assert result == ["咖啡还热着，窗边坐了一会儿。", "后来走到路口，云压得很低。"]


def test_compose_observation_note_uses_concrete_short_phrases_without_template_tail():
    result = compose_observation_note(["窗边咖啡和小票", "回程路上的云", "窗边咖啡和小票"])

    assert result == "窗边咖啡和小票，还有回程路上的云。"
    assert "今天就记这一点" not in result


def test_normalize_title_shortens_long_ai_style_title():
    title = "把这些闪闪发光的珍贵回忆收藏在温柔又治愈的周末手帐里"

    result = normalize_title(title)

    assert result == "闪闪发光的周末"
    assert "治愈" not in result
    assert len(result) <= 12


def test_normalize_title_falls_back_when_empty():
    assert normalize_title("   ") == "今日小记"


def test_has_cliche_copy_detects_ai_like_phrases():
    assert has_cliche_copy("这是值得被记住的一天，也像被温柔包裹。") is True
    assert has_cliche_copy("照片里是被阳光放慢的一天，适合把这些片段收成一页。") is True
    assert has_cliche_copy("咖啡、散步和好天气都刚刚好。") is True
    assert has_cliche_copy("今日份小确幸，都是很有氛围感的美好瞬间。") is True
    assert has_cliche_copy("咖啡还热着，窗边坐了一会儿。") is False
