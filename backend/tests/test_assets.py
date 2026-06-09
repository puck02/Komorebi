import json

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.assets import list_assets, read_asset_file, read_asset_permissions, update_asset_status
from app.api.routes.auth import login, register
from app.db.base import Base
from app.models import asset, generation_job, image, journal, user  # noqa: F401
from app.schemas.asset import AssetQualityStatusUpdate
from app.schemas.auth import AuthCredentials
from app.services import assets as asset_service
from app.services.assets import get_approved_assets, load_assets


@pytest.fixture(autouse=True)
def clear_asset_cache():
    asset_service.load_assets.cache_clear()
    yield
    asset_service.load_assets.cache_clear()


def test_manifest_loads_at_least_50_assets():
    assets = load_assets()

    assert len(assets) >= 50


def test_every_manifest_asset_has_required_metadata_and_file():
    assets = load_assets()

    for asset in assets:
        assert asset.id
        assert asset.name
        assert asset.category
        assert asset.tags
        assert asset.license
        assert asset.source
        assert asset.quality_status in {"approved", "draft", "rejected"}
        assert asset.file_path.exists()


def test_manifest_asset_ids_and_files_are_unique():
    assets = load_assets()

    assert len({asset.id for asset in assets}) == len(assets)
    assert len({asset.file for asset in assets}) == len(assets)


def test_load_assets_refreshes_when_manifest_file_changes(tmp_path, monkeypatch):
    manifest_path = copy_manifest(tmp_path, monkeypatch)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    new_asset = {**manifest[0], "id": "runtime_manifest_refresh_asset"}

    assert all(asset.id != new_asset["id"] for asset in load_assets())

    manifest.append(new_asset)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assert any(asset.id == new_asset["id"] for asset in load_assets())


def test_asset_matching_returns_only_approved_assets():
    assets = get_approved_assets(tags=["warm", "daily"])

    assert assets
    assert all(asset.quality_status == "approved" for asset in assets)


def test_internal_functional_stationery_library_is_rich_enough():
    approved_internal_assets = [
        asset for asset in load_assets() if asset.source == "internal" and asset.quality_status == "approved"
    ]
    counts_by_category = {
        category: len([asset for asset in approved_internal_assets if asset.category == category])
        for category in {"paper", "tape", "texture"}
    }

    assert counts_by_category["paper"] >= 18
    assert counts_by_category["tape"] >= 13
    assert counts_by_category["texture"] >= 11


def test_internal_handdrawn_sticker_library_is_rich_enough():
    approved_internal_stickers = [
        asset
        for asset in load_assets()
        if asset.source == "internal" and asset.category == "sticker" and asset.quality_status == "approved"
    ]

    assert len(approved_internal_stickers) >= 43


def test_approved_internal_assets_cover_human_scrapbook_materials():
    approved_internal_assets = [
        asset for asset in load_assets() if asset.source == "internal" and asset.quality_status == "approved"
    ]
    covered_tags = {tag for asset in approved_internal_assets for tag in asset.tags}

    assert {
        "pen",
        "checklist",
        "bus",
        "corner",
        "pressed",
        "movie",
        "shopping",
        "receipt",
        "book",
        "food",
        "sea",
        "commute",
        "dog",
        "plant",
    }.issubset(covered_tags)


def test_internal_scrapbook_ephemera_stickers_cover_common_journal_materials():
    approved_internal_stickers = [
        asset
        for asset in load_assets()
        if asset.source == "internal" and asset.category == "sticker" and asset.quality_status == "approved"
    ]
    covered_tags = {tag for asset in approved_internal_stickers for tag in asset.tags}

    assert {
        "photo",
        "ticket",
        "note",
        "stamp",
        "film",
        "letter",
        "tag",
        "seal",
        "clip",
        "date",
        "umbrella",
        "lamp",
        "cat",
        "cake",
        "book",
        "food",
        "sea",
        "commute",
        "dog",
        "plant",
    }.issubset(covered_tags)
    assert any({"date", "stamp"}.issubset(asset.tags) for asset in approved_internal_stickers)


def test_generic_external_icons_stay_draft_until_art_directed():
    generic_icon_ids = {
        "ext_streamline_game_controller",
        "ext_streamline_smiley_blush",
        "ext_streamline_walking_symbol",
        "ext_streamline_dice_pawn",
        "ext_streamline_card_symbols",
        "ext_streamline_idea_bulb",
        "ext_streamline_magic_wand",
        "ext_streamline_shopping_star",
        "ext_streamline_smiley_happy",
        "ext_streamline_smiley_heart",
    }
    statuses = {asset.id: asset.quality_status for asset in load_assets() if asset.id in generic_icon_ids}

    assert statuses == {asset_id: "draft" for asset_id in generic_icon_ids}


def test_fluent_emoji_assets_stay_draft_until_manually_reviewed():
    fluent_assets = [asset for asset in load_assets() if asset.id.startswith("ext_fluent_")]

    assert fluent_assets
    assert {asset.quality_status for asset in fluent_assets} == {"draft"}


def test_external_icon_assets_stay_draft_until_art_directed():
    external_icon_assets = [asset for asset in load_assets() if asset.source.startswith("https://")]

    assert external_icon_assets
    assert {asset.quality_status for asset in external_icon_assets} == {"draft"}


def test_asset_api_lists_assets_with_file_url():
    assets = list_assets(tag=[])

    assert len(assets) >= 50
    assert assets[0].file_url.startswith("/api/assets/")


def test_asset_api_serves_svg_file():
    asset = load_assets()[0]

    response = read_asset_file(asset.id)

    assert response.media_type == "image/svg+xml"
    assert response.path == asset.file_path


def test_first_registered_user_can_update_asset_quality_status(authenticated_db, tmp_path, monkeypatch):
    db, admin_user, _other_user = authenticated_db
    manifest_path = copy_manifest(tmp_path, monkeypatch)
    target = next(item for item in json.loads(manifest_path.read_text(encoding="utf-8")) if item["qualityStatus"] == "draft")

    response = update_asset_status(
        target["id"],
        AssetQualityStatusUpdate(quality_status="approved"),
        admin_user,
        db,
    )

    assert response.quality_status == "approved"
    assert next(item for item in json.loads(manifest_path.read_text(encoding="utf-8")) if item["id"] == target["id"])[
        "qualityStatus"
    ] == "approved"


def test_later_registered_user_cannot_update_asset_quality_status(authenticated_db, tmp_path, monkeypatch):
    db, _admin_user, other_user = authenticated_db
    manifest_path = copy_manifest(tmp_path, monkeypatch)
    target = json.loads(manifest_path.read_text(encoding="utf-8"))[0]

    with pytest.raises(HTTPException) as error:
        update_asset_status(target["id"], AssetQualityStatusUpdate(quality_status="draft"), other_user, db)

    assert error.value.status_code == 403


def test_asset_permissions_identify_first_registered_user(authenticated_db):
    db, admin_user, other_user = authenticated_db

    admin_response = read_asset_permissions(admin_user, db)
    other_response = read_asset_permissions(other_user, db)

    assert admin_response.can_manage_assets is True
    assert other_response.can_manage_assets is False


def test_train_sticker_is_not_rendered_as_rain_cloud():
    train = next(asset for asset in load_assets() if asset.id == "sticker_train_19")
    svg = train.file_path.read_text(encoding="utf-8")

    assert "M24 126L136 126" in svg


def test_reviewed_internal_assets_do_not_contain_rough_fill_noise():
    reviewed_asset_ids = {
        "paper_stamp_10",
        "sticker_sun_01",
        "sticker_pet_paw_17",
        "sticker_bow_20",
        "paper_exhibition_ticket_19",
        "sticker_gallery_map_50",
        "sticker_gallery_label_51",
        "sticker_installation_art_52",
    }

    for asset in load_assets():
        if asset.id in reviewed_asset_ids:
            svg = asset.file_path.read_text(encoding="utf-8")
            assert 'stroke="none" stroke-width="0"' not in svg


def test_small_sun_uses_smiling_mouth():
    sun = next(asset for asset in load_assets() if asset.id == "sticker_sun_01")
    svg = sun.file_path.read_text(encoding="utf-8")

    assert "M65 78c8 9 22 9 30 0" in svg
    assert "M65 78c8-8 22-8 30 0" not in svg


def test_bow_sticker_uses_curved_fold_lines():
    bow = next(asset for asset in load_assets() if asset.id == "sticker_bow_20")
    svg = bow.file_path.read_text(encoding="utf-8")

    assert "M57 79L36 63M103 79l21-16" not in svg
    assert "M58 77C51 72 45 67 37 64" in svg
    assert "M102 77C109 72 115 67 123 64" in svg


def test_external_assets_include_license_metadata():
    external_assets = [asset for asset in load_assets() if asset.source.startswith("https://")]

    assert len(external_assets) >= 48
    assert all(asset.license for asset in external_assets)


def test_fluent_emoji_assets_are_imported_with_mit_license():
    fluent_assets = [asset for asset in load_assets() if asset.id.startswith("ext_fluent_")]

    assert len(fluent_assets) >= 60
    assert {asset.license for asset in fluent_assets} == {"MIT"}


@pytest.fixture
def authenticated_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    try:
        admin_user = register_and_login(db, "admin@example.com")
        other_user = register_and_login(db, "other@example.com")
        yield db, admin_user, other_user
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def register_and_login(db: Session, email: str):
    payload = AuthCredentials(email=email, password="strong-password")
    register(payload, db)
    token = login(payload, db)
    return get_current_user(token.access_token, db)


def copy_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(asset_service.MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(asset_service, "MANIFEST_PATH", manifest_path)
    asset_service.load_assets.cache_clear()
    return manifest_path
