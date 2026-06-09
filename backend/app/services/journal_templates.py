SECTION_VARIANT_SEQUENCE = (
    "hero_note",
    "staggered_collage",
    "timeline_strip",
    "photo_wall",
    "magazine_whitespace",
    "ticket_memo",
    "quiet_story",
    "hero_memory",
    "timeline_trip",
    "pocket_grid",
    "ticket_day",
    "magazine_note",
    "before_after",
    "moodboard_stack",
    "recipe_memo",
    "letter_page",
)

ALLOWED_SECTION_VARIANTS = set(SECTION_VARIANT_SEQUENCE)

TEMPLATE_SECTION_VARIANTS = {
    "quiet_story": "quiet_story",
    "hero_memory": "hero_memory",
    "timeline_trip": "timeline_trip",
    "pocket_grid": "pocket_grid",
    "ticket_day": "ticket_day",
    "magazine_note": "magazine_note",
    "before_after": "before_after",
    "moodboard_stack": "moodboard_stack",
    "recipe_memo": "recipe_memo",
    "letter_page": "letter_page",
}

SECTION_VARIANT_IMAGE_LIMITS = {
    "hero_note": 1,
    "magazine_whitespace": 1,
    "ticket_memo": 2,
    "before_after": 3,
    "hero_memory": 3,
    "letter_page": 3,
    "magazine_note": 3,
    "quiet_story": 3,
    "timeline_trip": 6,
    "ticket_day": 4,
    "recipe_memo": 4,
    "moodboard_stack": 5,
    "pocket_grid": 9,
}


def allowed_section_variant_text() -> str:
    return "、".join(SECTION_VARIANT_SEQUENCE)
