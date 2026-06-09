from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_settings import AiSettings
from app.models.user import User
from app.schemas.admin import AiConnectionTestRead
from app.services.openai_client import (
    DEFAULT_OPENAI_BASE_URL,
    OPENAI_TIMEOUT_SECONDS,
    build_chat_completion_payload,
    is_response_format_unsupported_response,
)

DEFAULT_AI_SETTINGS_ID = "default"
AI_CONNECTION_TEST_MAX_TIMEOUT = min(OPENAI_TIMEOUT_SECONDS, 30)


@dataclass(frozen=True)
class EffectiveAiSettings:
    base_url: str
    api_key: str
    model: str
    review_model: str


def is_admin_user(db: Session, current_user: User) -> bool:
    first_user = db.scalar(select(User).order_by(User.created_at, User.id).limit(1))
    return first_user is not None and first_user.id == current_user.id


def get_saved_ai_settings(db: Session) -> AiSettings | None:
    return db.get(AiSettings, DEFAULT_AI_SETTINGS_ID)


def get_or_create_ai_settings(db: Session) -> AiSettings:
    saved = get_saved_ai_settings(db)
    if saved is not None:
        return saved

    settings = get_settings()
    saved = AiSettings(
        id=DEFAULT_AI_SETTINGS_ID,
        base_url=settings.openai_base_url,
        api_key="",
        model=settings.openai_model,
        review_model=settings.openai_review_model,
    )
    db.add(saved)
    db.flush()
    return saved


def get_effective_ai_settings(db: Session) -> EffectiveAiSettings:
    settings = get_settings()
    saved = get_saved_ai_settings(db)
    if saved is None:
        return EffectiveAiSettings(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            review_model=settings.openai_review_model,
        )

    return EffectiveAiSettings(
        base_url=saved.base_url or settings.openai_base_url,
        api_key=saved.api_key or settings.openai_api_key,
        model=saved.model or settings.openai_model,
        review_model=saved.review_model or settings.openai_review_model,
    )


def test_ai_service_connection(db: Session) -> AiConnectionTestRead:
    settings = get_effective_ai_settings(db)
    if not settings.api_key:
        return AiConnectionTestRead(
            ok=False,
            status="missing_key",
            message="API Key 未配置，请先保存 Key",
            model=settings.model,
        )

    base_url = settings.base_url or DEFAULT_OPENAI_BASE_URL
    try:
        response = post_ai_connection_test(
            base_url=base_url,
            api_key=settings.api_key,
            model=settings.model,
            use_response_format=True,
        )
    except httpx.RequestError:
        return AiConnectionTestRead(
            ok=False,
            status="connection_failed",
            message="AI 服务连接失败，请检查 Base URL 或网络",
            model=settings.model,
        )

    if response.status_code in {401, 403}:
        return AiConnectionTestRead(
            ok=False,
            status="auth_failed",
            message="AI 服务认证失败，请检查 Key 或渠道权限",
            model=settings.model,
            statusCode=response.status_code,
        )
    if 400 <= response.status_code < 500:
        return AiConnectionTestRead(
            ok=False,
            status="request_failed",
            message=f"AI 服务返回 {response.status_code}，请检查模型名或渠道参数",
            model=settings.model,
            statusCode=response.status_code,
        )
    if response.status_code >= 500:
        return AiConnectionTestRead(
            ok=False,
            status="provider_unavailable",
            message=f"AI 服务返回 {response.status_code}，第三方渠道暂时不可用",
            model=settings.model,
            statusCode=response.status_code,
        )
    if not is_chat_completion_json_response(response):
        return AiConnectionTestRead(
            ok=False,
            status="invalid_response",
            message="AI 服务返回格式异常，请检查渠道是否兼容 OpenAI Chat Completions",
            model=settings.model,
            statusCode=response.status_code,
        )

    return AiConnectionTestRead(
        ok=True,
        status="ok",
        message="AI 服务连接正常",
        model=settings.model,
        statusCode=response.status_code,
    )


def post_ai_connection_test(
    *,
    base_url: str,
    api_key: str,
    model: str,
    use_response_format: bool,
) -> httpx.Response:
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=build_chat_completion_payload(
            model,
            "Return only this JSON object: {\"ok\": true}",
            use_response_format=use_response_format,
        ),
        timeout=AI_CONNECTION_TEST_MAX_TIMEOUT,
        trust_env=True,
    )
    if use_response_format and is_response_format_unsupported_response(response):
        return post_ai_connection_test(
            base_url=base_url,
            api_key=api_key,
            model=model,
            use_response_format=False,
        )
    return response


def is_chat_completion_json_response(response: httpx.Response) -> bool:
    try:
        payload: dict[str, Any] = response.json()
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, TypeError, ValueError):
        return False
    return isinstance(content, str) and bool(content.strip())
