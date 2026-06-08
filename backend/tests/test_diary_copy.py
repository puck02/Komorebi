from app.services.diary_copy import (
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
    assert has_cliche_copy("咖啡还热着，窗边坐了一会儿。") is False
