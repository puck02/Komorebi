import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import asset, image, journal, user  # noqa: F401
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


def test_asset_matching_returns_only_approved_assets():
    assets = get_approved_assets(tags=["warm", "daily"])

    assert assets
    assert all(asset.quality_status == "approved" for asset in assets)


def test_asset_api_lists_assets_with_file_url():
    client = TestClient(app)

    response = client.get("/api/assets")

    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 50
    assert assets[0]["file_url"].startswith("/api/assets/")


def test_asset_api_serves_svg_file():
    client = TestClient(app)
    asset = load_assets()[0]

    response = client.get(f"/api/assets/{asset.id}/file")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_first_registered_user_can_update_asset_quality_status(authenticated_client, tmp_path, monkeypatch):
    client, admin_token, _other_token = authenticated_client
    manifest_path = copy_manifest(tmp_path, monkeypatch)
    target = next(item for item in json.loads(manifest_path.read_text(encoding="utf-8")) if item["qualityStatus"] == "draft")

    response = client.patch(
        f"/api/assets/{target['id']}/quality-status",
        json={"quality_status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["quality_status"] == "approved"
    assert next(item for item in json.loads(manifest_path.read_text(encoding="utf-8")) if item["id"] == target["id"])[
        "qualityStatus"
    ] == "approved"


def test_later_registered_user_cannot_update_asset_quality_status(authenticated_client, tmp_path, monkeypatch):
    client, _admin_token, other_token = authenticated_client
    manifest_path = copy_manifest(tmp_path, monkeypatch)
    target = json.loads(manifest_path.read_text(encoding="utf-8"))[0]

    response = client.patch(
        f"/api/assets/{target['id']}/quality-status",
        json={"quality_status": "draft"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403


def test_asset_permissions_identify_first_registered_user(authenticated_client):
    client, admin_token, other_token = authenticated_client

    admin_response = client.get("/api/assets/permissions/me", headers={"Authorization": f"Bearer {admin_token}"})
    other_response = client.get("/api/assets/permissions/me", headers={"Authorization": f"Bearer {other_token}"})

    assert admin_response.status_code == 200
    assert admin_response.json() == {"can_manage_assets": True}
    assert other_response.status_code == 200
    assert other_response.json() == {"can_manage_assets": False}


def test_train_sticker_is_not_rendered_as_rain_cloud():
    train = next(asset for asset in load_assets() if asset.id == "sticker_train_19")
    svg = train.file_path.read_text(encoding="utf-8")

    assert "M24 126L136 126" in svg


def test_reviewed_internal_assets_do_not_contain_rough_fill_noise():
    reviewed_asset_ids = {"paper_stamp_10", "sticker_sun_01", "sticker_pet_paw_17", "sticker_bow_20"}

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
def authenticated_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        admin_token = register_and_login(client, "admin@example.com")
        other_token = register_and_login(client, "other@example.com")
        yield client, admin_token, other_token
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str) -> str:
    payload = {"email": email, "password": "strong-password"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/login", json=payload)
    return response.json()["access_token"]


def copy_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(asset_service.MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(asset_service, "MANIFEST_PATH", manifest_path)
    asset_service.load_assets.cache_clear()
    return manifest_path
