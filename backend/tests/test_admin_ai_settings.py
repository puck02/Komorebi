from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.admin import read_admin_permissions, read_ai_settings, update_ai_settings
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
