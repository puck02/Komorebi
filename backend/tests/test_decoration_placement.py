from app.services.assets import AssetItem
from app.services.decoration_placement import (
    infer_asset_function,
    overlaps_any_text,
    overlaps_photo_safe_area,
    place_decorations,
)
from app.services.journal_generator import JournalGenerationRequest, JournalGenerator, JournalImageInput


def test_infer_asset_function_from_category_tags_and_id():
    assert infer_asset_function(asset_item("tape_warm_grid_01", "tape")) == "tape"
    assert infer_asset_function(asset_item("paper_note_cream_01", "paper", tags=["note"])) == "note"
    assert infer_asset_function(asset_item("paper_ticket_07", "paper", tags=["ticket"])) == "ticket"
    assert infer_asset_function(asset_item("paper_label_ochre_05", "paper", tags=["label"])) == "label"
    assert infer_asset_function(asset_item("sticker_flower_04", "sticker", tags=["flower"])) == "flower"
    assert infer_asset_function(asset_item("sticker_star_08", "sticker", tags=["daily"])) == "star"
    assert infer_asset_function(asset_item("texture_dots_01", "texture")) == "texture"
    assert infer_asset_function(asset_item("sticker_film_strip_30", "sticker", tags=["film", "photo"])) == "film"
    assert infer_asset_function(asset_item("sticker_wax_seal_31", "sticker", tags=["seal", "letter"])) == "seal"
    assert infer_asset_function(asset_item("sticker_tiny_envelope_33", "sticker", tags=["letter", "note"])) == "envelope"
    assert infer_asset_function(asset_item("sticker_kraft_tag_32", "sticker", tags=["tag", "label"])) == "tag"


def test_infer_asset_function_keeps_ticket_sticker_as_sticker():
    assert infer_asset_function(asset_item("sticker_ticket_stub_24", "sticker", tags=["ticket", "travel"])) == "sticker"


def test_place_decorations_uses_note_paper_as_text_backing():
    decorations = [{"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0}]
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}

    placed = place_decorations(
        decorations,
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={"paper_note": asset_item("paper_note", "paper", tags=["note"])},
    )

    paper = placed[0]
    assert paper["x"] <= text["x"] <= paper["x"] + paper["width"]
    assert paper["y"] <= text["y"] <= paper["y"] + paper["height"]
    assert paper["width"] >= text["width"]
    assert not overlaps_photo_safe_area(paper, [image_placement()])


def test_place_decorations_expands_note_paper_to_text_height():
    decorations = [{"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0}]
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32, "height": 230}

    placed = place_decorations(
        decorations,
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={"paper_note": asset_item("paper_note", "paper", tags=["note"])},
    )

    paper = placed[0]
    assert paper["y"] <= text["y"]
    assert paper["y"] + paper["height"] >= text["y"] + text["height"] + 28


def test_place_decorations_snaps_tape_to_nearest_paper_or_photo_edge():
    decorations = [
        {"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0},
        {"assetId": "tape_note", "x": 140, "y": 720, "width": 300, "height": 120, "rotation": 0},
    ]
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}

    placed = place_decorations(
        decorations,
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={
            "paper_note": asset_item("paper_note", "paper", tags=["note"]),
            "tape_note": asset_item("tape_note", "tape"),
        },
    )

    paper = placed[0]
    tape = placed[1]
    assert paper["x"] - tape["width"] <= tape["x"] <= paper["x"] + paper["width"]
    assert paper["y"] - tape["height"] <= tape["y"] <= paper["y"] + paper["height"]
    assert tape["width"] <= 260
    assert tape["height"] <= 70


def test_place_decorations_moves_sticker_out_of_text_and_photo_safe_area():
    sticker = {"assetId": "sticker_leaf", "x": 122, "y": 770, "width": 180, "height": 180, "rotation": 0}
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}

    placed = place_decorations(
        [sticker],
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={"sticker_leaf": asset_item("sticker_leaf", "sticker")},
    )

    assert placed
    assert not overlaps_any_text(placed[0], [text])
    assert not overlaps_photo_safe_area(placed[0], [image_placement()])


def test_place_decorations_snaps_photo_corner_sticker_to_photo_corner():
    photo_corner = {"assetId": "sticker_photo_corner_21", "x": 534, "y": 234, "width": 112, "height": 112, "rotation": 0}
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}
    image = image_placement()

    placed = place_decorations(
        [photo_corner],
        image_placements=[image],
        text_placements=[text],
        asset_by_id={"sticker_photo_corner_21": asset_item("sticker_photo_corner_21", "sticker", tags=["photo", "memory"])},
    )

    corner = placed[0]
    assert corner["x"] < image["x"]
    assert corner["y"] < image["y"]
    assert corner["x"] + corner["width"] > image["x"]
    assert corner["y"] + corner["height"] > image["y"]
    assert not overlaps_photo_safe_area(corner, [image])


def test_place_decorations_snaps_clip_sticker_to_paper_edge():
    decorations = [
        {"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0},
        {"assetId": "sticker_binder_clip_34", "x": 122, "y": 770, "width": 160, "height": 160, "rotation": 0},
    ]
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}

    placed = place_decorations(
        decorations,
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={
            "paper_note": asset_item("paper_note", "paper", tags=["note"]),
            "sticker_binder_clip_34": asset_item("sticker_binder_clip_34", "sticker", tags=["clip", "note", "collage"]),
        },
    )

    paper = placed[0]
    clip = placed[1]
    assert paper["x"] < clip["x"] < paper["x"] + paper["width"]
    assert clip["y"] < paper["y"] + 20
    assert clip["y"] + clip["height"] > paper["y"]
    assert not overlaps_photo_safe_area(clip, [image_placement()])


def test_place_decorations_snaps_film_sticker_to_photo_edge():
    film = {"assetId": "sticker_film_strip_30", "x": 760, "y": 760, "width": 190, "height": 150, "rotation": 0}
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}
    image = image_placement()

    placed = place_decorations(
        [film],
        image_placements=[image],
        text_placements=[text],
        asset_by_id={"sticker_film_strip_30": asset_item("sticker_film_strip_30", "sticker", tags=["film", "photo"])},
    )

    placed_film = placed[0]
    image_right = image["x"] + image["width"]
    assert placed_film["x"] < image_right < placed_film["x"] + placed_film["width"]
    assert image["y"] <= placed_film["y"] <= image["y"] + image["height"]
    assert not overlaps_photo_safe_area(placed_film, [image])
    assert not overlaps_any_text(placed_film, [text])


def test_place_decorations_attaches_wax_seal_to_paper_edge_without_covering_text():
    decorations = [
        {"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0},
        {"assetId": "sticker_wax_seal_31", "x": 122, "y": 770, "width": 160, "height": 160, "rotation": 0},
    ]
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}

    placed = place_decorations(
        decorations,
        image_placements=[image_placement()],
        text_placements=[text],
        asset_by_id={
            "paper_note": asset_item("paper_note", "paper", tags=["note"]),
            "sticker_wax_seal_31": asset_item("sticker_wax_seal_31", "sticker", tags=["seal", "letter"]),
        },
    )

    paper = placed[0]
    seal = placed[1]
    assert paper["x"] + paper["width"] - seal["width"] <= seal["x"] <= paper["x"] + paper["width"]
    assert paper["y"] + paper["height"] - seal["height"] <= seal["y"] <= paper["y"] + paper["height"]
    assert not overlaps_any_text(seal, [text])
    assert not overlaps_photo_safe_area(seal, [image_placement()])


def test_place_decorations_tucks_letter_tag_stickers_near_paper_edge():
    text = {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32}
    for asset_id, tags in [
        ("sticker_tiny_envelope_33", ["letter", "note"]),
        ("sticker_kraft_tag_32", ["tag", "label"]),
    ]:
        placed = place_decorations(
            [
                {"assetId": "paper_note", "x": 0, "y": 0, "width": 120, "height": 80, "rotation": 0},
                {"assetId": asset_id, "x": 122, "y": 770, "width": 160, "height": 160, "rotation": 0},
            ],
            image_placements=[image_placement()],
            text_placements=[text],
            asset_by_id={
                "paper_note": asset_item("paper_note", "paper", tags=["note"]),
                asset_id: asset_item(asset_id, "sticker", tags=tags),
            },
        )

        paper = placed[0]
        ephemera = placed[1]
        assert ephemera["x"] < paper["x"] + paper["width"]
        assert ephemera["x"] + ephemera["width"] > paper["x"]
        assert ephemera["y"] < paper["y"] + paper["height"]
        assert ephemera["y"] + ephemera["height"] > paper["y"]
        assert not overlaps_any_text(ephemera, [text])
        assert not overlaps_photo_safe_area(ephemera, [image_placement()])


def test_generator_places_paper_near_body_text():
    payload = valid_model_json()
    payload["layout"]["decorations"] = [
        {"assetId": "paper_note", "x": 12, "y": 12, "width": 120, "height": 80, "rotation": 0}
    ]
    generator = JournalGenerator(FakeClient(payload))

    layout = generator.generate(
        JournalGenerationRequest(
            description="周末一起散步，天气很好。",
            images=[JournalImageInput(id="img_1", width=640, height=480)],
            assets=[asset_item("paper_note", "paper", tags=["note"])],
        )
    )

    paper = layout.layout.decorations[0]
    body = next(text for text in layout.layout.texts if text.role == "body")
    assert paper.x <= body.x <= paper.x + paper.width
    assert paper.y <= body.y <= paper.y + paper.height


def image_placement():
    return {"imageId": "img_1", "x": 92, "y": 210, "width": 420, "height": 320, "rotation": -3}


def asset_item(asset_id, category, tags=None, source="internal"):
    return AssetItem(
        id=asset_id,
        name=asset_id,
        category=category,
        tags=tags or ["daily"],
        style=["soft-collage"],
        colors=["#fef6e4"],
        file=f"{asset_id}.svg",
        license="internal",
        source=source,
        quality_status="approved",
    )


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def generate_layout(self, request):
        return self.payload


def valid_model_json():
    return {
        "canvas": {"width": 1080, "height": 1440, "background": "#fef6e4"},
        "theme": {"style": "soft-collage", "palette": ["#fef6e4", "#f582ae"], "mood": ["温柔"]},
        "content": {
            "title": "慢下来的周末",
            "body": ["照片里是被阳光放慢的一天，咖啡、散步和好天气都刚刚好。"],
            "captions": [{"imageId": "img_1", "text": "午后的咖啡"}],
        },
        "layout": {
            "variant": "long_collage",
            "images": [image_placement()],
            "texts": [
                {"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56},
                {"role": "body", "x": 112, "y": 760, "width": 820, "fontSize": 32},
            ],
            "decorations": [],
            "sections": [],
        },
    }
