from math import ceil
from typing import Any

CLICHE_PHRASES = (
    "被温柔包裹",
    "被阳光放慢",
    "把时光收藏",
    "把这些片段收成一页",
    "收成一页",
    "都刚刚好",
    "珍贵回忆",
    "值得被记住",
    "今日份",
    "小确幸",
    "氛围感",
    "美好瞬间",
    "生活碎片",
    "治愈",
    "仪式感",
)
TITLE_NOISE_PHRASES = (
    "把这些",
    "收藏在",
    "温柔又",
    "温柔",
    "手帐里",
    "手帐",
    "日记里",
)
PUNCTUATION = "。！？!?；;，,"
SENTENCE_ENDINGS = "。！？!?；;"


def normalize_diary_text(value: Any, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    for phrase in CLICHE_PHRASES:
        text = text.replace(phrase, "")
    text = tidy_text(text)
    return fallback if is_empty_observation(text) else text


def normalize_diary_blocks(
    values: Any,
    *,
    fallback: str,
    split_target: int = 58,
) -> list[str]:
    if isinstance(values, str):
        raw_blocks = [values]
    elif isinstance(values, list):
        raw_blocks = values
    else:
        raw_blocks = []

    blocks: list[str] = []
    seen_blocks: set[str] = set()
    for raw_block in raw_blocks:
        block = normalize_diary_text(raw_block)
        for next_block in split_long_block(block, split_target) if len(block) > split_target else [block]:
            if not next_block or next_block in seen_blocks:
                continue
            blocks.append(next_block)
            seen_blocks.add(next_block)
    return blocks or [fallback]


def compose_observation_note(parts: list[str], *, fallback: str = "") -> str:
    observations: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = normalize_diary_text(part).strip(PUNCTUATION + "、 ")
        if not text or text in seen:
            continue
        observations.append(text[:18])
        seen.add(text)
        if len(observations) >= 2:
            break
    if not observations:
        return fallback
    if len(observations) == 1:
        return f"{observations[0]}。"
    return f"{observations[0]}，还有{observations[1]}。"


def normalize_title(value: Any, *, fallback: str = "今日小记", max_length: int = 12) -> str:
    title = normalize_diary_text(value)
    for phrase in TITLE_NOISE_PHRASES:
        title = title.replace(phrase, "")
    title = tidy_text(title)
    if not title:
        return fallback
    title = title.replace("的的", "的")
    for delimiter in ("，", "。", "；", "、"):
        if delimiter in title:
            title = title.split(delimiter, 1)[0].strip()
    title = trim_wrapping_particles(title)
    return title[:max_length] or fallback


def has_cliche_copy(value: Any) -> bool:
    text = str(value or "")
    return any(phrase in text for phrase in CLICHE_PHRASES)


def split_long_block(block: str, split_target: int) -> list[str]:
    sentences = split_sentences(block)
    if len(sentences) <= 1:
        chunk_size = max(split_target, 1)
        return [
            block[index : index + chunk_size].strip()
            for index in range(0, len(block), chunk_size)
            if block[index : index + chunk_size].strip()
        ]

    group_count = max(ceil(len(block) / max(split_target, 1)), 1)
    group_count = min(group_count, len(sentences))
    groups: list[list[str]] = [[] for _ in range(group_count)]
    for index, sentence in enumerate(sentences):
        groups[index * group_count // len(sentences)].append(sentence)
    return [tidy_text("".join(group)) for group in groups if tidy_text("".join(group))]


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    for index, character in enumerate(text):
        if character in SENTENCE_ENDINGS:
            sentences.append(text[start : index + 1].strip())
            start = index + 1
    if start < len(text):
        sentences.append(text[start:].strip())
    return [sentence for sentence in sentences if sentence]


def tidy_text(text: str) -> str:
    text = text.strip()
    while any(double in text for double in ("，，", "。。", "；；", "！！", "？？")):
        for double in ("，，", "。。", "；；", "！！", "？？"):
            text = text.replace(double, double[0])
    text = text.replace("，。", "。").replace("。,", "。").replace("，,", "，")
    text = text.replace("，也很，", "，").replace("，也很。", "。").replace("，充满，", "，")
    text = text.replace("也很，", "").replace("充满，", "").replace("充满。", "")
    text = text.replace("照片里是的一天，", "").replace("照片里是的一天。", "")
    text = text.replace("是的一天，", "").replace("是的一天。", "")
    text = text.replace("很满", "").replace("都是和。", "").replace("都是和，", "")
    text = text.replace("照片里的很满，", "").replace("照片里的，", "")
    text = text.replace("刚刚好", "")
    return text.strip(" ")


def is_empty_observation(text: str) -> bool:
    return text.strip(" 的和又在把成里。！？!?；;，,、") in {"", "今天", "照片", "这一页"}


def trim_wrapping_particles(text: str) -> str:
    return text.strip(" 的和又在把成里。！？!?；;，,")
