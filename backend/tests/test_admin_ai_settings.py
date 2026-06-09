from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.admin import read_admin_permissions, read_ai_settings, test_ai_connection as call_test_ai_connection, update_ai_settings
from app.core.config import get_settings
from app.db.base import Base
from app.models import ai_settings, asset, generation_job, image, journal, user  # noqa: F401
from app.models.user import User
from app.schemas.admin import AiSettingsUpdate


def test_admin_permissions_identify_first_registered_user(session_factory):
    with session_factory() as db:
        admin, other = seed_users(db)

        admin_response = read_admin_permissions(current_user=admin, db=db)
        other_response = read_admin_permissions(current_user=other, db=db)

    assert admin_response.model_dump(by_alias=True) == {"canManageAiSettings": True}
    assert other_response.model_dump(by_alias=True) == {"canManageAiSettings": False}


def test_admin_can_update_ai_settings_without_exposing_api_key(session_factory):
    with session_factory() as db:
        admin, _other = seed_users(db)

        update_response = update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )
        read_response = read_ai_settings(current_user=admin, db=db)

    expected = {
        "baseUrl": "https://example.test/v1",
        "hasApiKey": True,
        "model": "gpt-5.5",
        "reviewModel": "gpt-5.4-mini",
    }
    assert update_response.model_dump(by_alias=True) == expected
    assert "apiKey" not in update_response.model_dump(by_alias=True)
    assert read_response.model_dump(by_alias=True) == expected


def test_ai_settings_default_to_gpt_55_for_admin(session_factory):
    with session_factory() as db:
        admin, _other = seed_users(db)

        response = read_ai_settings(current_user=admin, db=db)

    assert response.model == "gpt-5.5"


def test_later_registered_user_cannot_manage_ai_settings(session_factory):
    with session_factory() as db:
        _admin, other = seed_users(db)

        with pytest.raises(HTTPException) as read_error:
            read_ai_settings(current_user=other, db=db)
        with pytest.raises(HTTPException) as update_error:
            update_ai_settings(
                AiSettingsUpdate(
                    baseUrl="https://example.test/v1",
                    apiKey="dummy-admin-api-key",
                    model="gpt-5.5",
                    reviewModel="gpt-5.4-mini",
                ),
                current_user=other,
                db=db,
            )

    assert read_error.value.status_code == 403
    assert update_error.value.status_code == 403


def test_empty_api_key_preserves_existing_secret(session_factory):
    with session_factory() as db:
        admin, _other = seed_users(db)

        first_response = update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )
        second_response = update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )

    assert first_response.has_api_key is True
    assert second_response.has_api_key is True


def test_admin_can_test_ai_connection_success(session_factory, monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    monkeypatch.setattr("app.services.admin.httpx.post", fake_post)
    with session_factory() as db:
        admin, _other = seed_users(db)
        update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )

        response = call_test_ai_connection(current_user=admin, db=db)

    assert response.model_dump(by_alias=True) == {
        "ok": True,
        "status": "ok",
        "message": "AI 服务连接正常",
        "model": "gpt-5.5",
        "statusCode": 200,
    }
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer dummy-admin-api-key"
    assert captured["json"]["model"] == "gpt-5.5"


def test_ai_connection_test_retries_without_response_format_for_compatible_provider(session_factory, monkeypatch):
    captured_payloads = []

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        captured_payloads.append(kwargs["json"])
        if len(captured_payloads) == 1:
            return httpx.Response(
                400,
                request=request,
                json={"error": {"message": "response_format is not supported"}},
            )
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    monkeypatch.setattr("app.services.admin.httpx.post", fake_post)
    with session_factory() as db:
        admin, _other = seed_users(db)
        update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )

        response = call_test_ai_connection(current_user=admin, db=db)

    assert response.ok is True
    assert response.status == "ok"
    assert captured_payloads[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in captured_payloads[1]


def test_ai_connection_test_reports_missing_key_without_requesting_provider(session_factory, monkeypatch):
    requested = False

    def fake_post(_url, **_kwargs):
        nonlocal requested
        requested = True
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("app.services.admin.httpx.post", fake_post)
    with session_factory() as db:
        admin, _other = seed_users(db)

        response = call_test_ai_connection(current_user=admin, db=db)

    assert response.model_dump(by_alias=True) == {
        "ok": False,
        "status": "missing_key",
        "message": "API Key 未配置，请先保存 Key",
        "model": "gpt-5.5",
        "statusCode": None,
    }
    assert requested is False


def test_ai_connection_test_reports_provider_status_error(session_factory, monkeypatch):
    def fake_post(url, **_kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(403, request=request, json={"error": {"message": "forbidden"}})

    monkeypatch.setattr("app.services.admin.httpx.post", fake_post)
    with session_factory() as db:
        admin, _other = seed_users(db)
        update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )

        response = call_test_ai_connection(current_user=admin, db=db)

    assert response.ok is False
    assert response.status == "auth_failed"
    assert response.status_code == 403
    assert response.message == "AI 服务认证失败，请检查 Key 或渠道权限"


def test_ai_connection_test_reports_network_error(session_factory, monkeypatch):
    def fake_post(url, **_kwargs):
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr("app.services.admin.httpx.post", fake_post)
    with session_factory() as db:
        admin, _other = seed_users(db)
        update_ai_settings(
            AiSettingsUpdate(
                baseUrl="https://example.test/v1",
                apiKey="dummy-admin-api-key",
                model="gpt-5.5",
                reviewModel="gpt-5.4-mini",
            ),
            current_user=admin,
            db=db,
        )

        response = call_test_ai_connection(current_user=admin, db=db)

    assert response.ok is False
    assert response.status == "connection_failed"
    assert response.status_code is None
    assert response.message == "AI 服务连接失败，请检查 Base URL 或网络"


def test_later_registered_user_cannot_test_ai_connection(session_factory):
    with session_factory() as db:
        _admin, other = seed_users(db)

        with pytest.raises(HTTPException) as error:
            call_test_ai_connection(current_user=other, db=db)

    assert error.value.status_code == 403


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    finally:
        Base.metadata.drop_all(bind=engine)


def seed_users(db):
    created_at = datetime.now(timezone.utc)
    admin = User(email="admin@example.com", password_hash="hash", created_at=created_at)
    other = User(email="other@example.com", password_hash="hash", created_at=created_at + timedelta(seconds=1))
    db.add_all([admin, other])
    db.commit()
    return admin, other
