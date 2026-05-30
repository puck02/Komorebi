from fastapi.testclient import TestClient

from app.main import app
from app.services.assets import get_approved_assets, load_assets


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
