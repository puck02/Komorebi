from fastapi import FastAPI

from app.api.routes.assets import router as assets_router
from app.api.routes.auth import router as auth_router
from app.api.routes.generation_jobs import router as generation_jobs_router
from app.api.routes.images import router as images_router
from app.api.routes.internal_render import router as internal_render_router
from app.api.routes.journals import router as journals_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(assets_router)
app.include_router(auth_router)
app.include_router(generation_jobs_router)
app.include_router(images_router)
app.include_router(internal_render_router)
app.include_router(journals_router)


@app.get(f"{settings.api_prefix}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
