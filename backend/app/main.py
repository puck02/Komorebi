from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.admin import router as admin_router
from app.api.routes.assets import router as assets_router
from app.api.routes.auth import router as auth_router
from app.api.routes.generation_jobs import router as generation_jobs_router
from app.api.routes.images import router as images_router
from app.api.routes.internal_render import router as internal_render_router
from app.api.routes.journals import router as journals_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.generation_jobs import recover_incomplete_generation_jobs

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    recover_incomplete_generation_jobs()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(admin_router)
app.include_router(assets_router)
app.include_router(auth_router)
app.include_router(generation_jobs_router)
app.include_router(images_router)
app.include_router(internal_render_router)
app.include_router(journals_router)


@app.get(f"{settings.api_prefix}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
