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
    "chapter_scroll",
    "field_notes",
    "split_scene",
    "detail_index",
    "map_journey",
    "weekly_spread",
    "day_dashboard",
    "scrapbook_story",
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
    "chapter_scroll": "chapter_scroll",
    "field_notes": "field_notes",
    "split_scene": "split_scene",
    "detail_index": "detail_index",
    "map_journey": "map_journey",
    "weekly_spread": "weekly_spread",
    "day_dashboard": "day_dashboard",
    "scrapbook_story": "scrapbook_story",
}

TEMPLATE_SECTION_VARIANT_RECIPES = {
    "quiet_story": ("quiet_story", "magazine_note", "letter_page"),
    "hero_memory": ("hero_memory", "detail_index", "letter_page"),
    "timeline_trip": ("timeline_trip", "map_journey", "ticket_day", "magazine_note"),
    "pocket_grid": ("pocket_grid", "detail_index", "letter_page"),
    "ticket_day": ("ticket_day", "recipe_memo", "letter_page"),
    "magazine_note": ("magazine_note", "quiet_story", "detail_index"),
    "before_after": ("before_after", "split_scene", "letter_page"),
    "moodboard_stack": ("moodboard_stack", "scrapbook_story", "letter_page"),
    "recipe_memo": ("recipe_memo", "ticket_day", "letter_page"),
    "letter_page": ("letter_page", "quiet_story", "hero_memory"),
    "chapter_scroll": ("chapter_scroll", "timeline_trip", "letter_page"),
    "field_notes": ("field_notes", "detail_index", "letter_page"),
    "split_scene": ("split_scene", "before_after", "magazine_note"),
    "detail_index": ("detail_index", "field_notes", "letter_page"),
    "map_journey": ("map_journey", "timeline_trip", "ticket_day", "letter_page"),
    "weekly_spread": ("weekly_spread", "day_dashboard", "pocket_grid", "letter_page"),
    "day_dashboard": ("day_dashboard", "weekly_spread", "detail_index", "letter_page"),
    "scrapbook_story": ("scrapbook_story", "moodboard_stack", "ticket_day", "letter_page"),
}

TEMPLATE_SECTION_GROUP_LIMITS = {
    "chapter_scroll": 3,
    "scrapbook_story": 3,
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
    "field_notes": 5,
    "split_scene": 4,
    "detail_index": 8,
    "map_journey": 6,
    "weekly_spread": 9,
    "day_dashboard": 6,
    "scrapbook_story": 8,
    "chapter_scroll": 9,
    "pocket_grid": 9,
}


def allowed_section_variant_text() -> str:
    return "、".join(SECTION_VARIANT_SEQUENCE)


def template_primary_section_variant(template_id: str | None) -> str | None:
    return TEMPLATE_SECTION_VARIANTS.get(str(template_id or "").strip())


def template_section_variant_recipe(template_id: str | None) -> tuple[str, ...]:
    primary = template_primary_section_variant(template_id)
    if primary is None:
        return ()
    return TEMPLATE_SECTION_VARIANT_RECIPES.get(str(template_id or "").strip(), (primary,))


def template_section_group_limit(template_id: str | None) -> int | None:
    return TEMPLATE_SECTION_GROUP_LIMITS.get(str(template_id or "").strip())
