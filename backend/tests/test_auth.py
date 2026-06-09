import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes.auth import login, me, register
from app.db.base import Base
from app.models import asset, generation_job, image, journal, user  # noqa: F401
from app.schemas.auth import AuthCredentials


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_register_creates_user(db_session):
    user = register(credentials("user@example.com"), db_session)

    assert user.email == "user@example.com"
    assert user.password_hash


def test_register_rejects_duplicate_email(db_session):
    payload = credentials("user@example.com")
    register(payload, db_session)

    with pytest.raises(HTTPException) as error:
        register(payload, db_session)

    assert error.value.status_code == 409


def test_login_returns_access_token(db_session):
    payload = credentials("user@example.com")
    register(payload, db_session)

    token = login(payload, db_session)

    assert token.token_type == "bearer"
    assert token.access_token


def test_login_rejects_wrong_password(db_session):
    register(credentials("user@example.com"), db_session)

    with pytest.raises(HTTPException) as error:
        login(credentials("user@example.com", "wrong-password"), db_session)

    assert error.value.status_code == 401


def test_me_requires_token_and_returns_current_user(db_session):
    payload = credentials("user@example.com")
    created_user = register(payload, db_session)
    token = login(payload, db_session)

    with pytest.raises(HTTPException) as error:
        get_current_user("invalid-token", db_session)
    current_user = get_current_user(token.access_token, db_session)

    assert error.value.status_code == 401
    assert me(current_user).id == created_user.id
    assert current_user.email == "user@example.com"


def credentials(email: str, password: str = "strong-password") -> AuthCredentials:
    return AuthCredentials(email=email, password=password)
