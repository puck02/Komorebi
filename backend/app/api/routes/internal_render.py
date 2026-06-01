from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response

from app.services.render_drafts import RenderDraft, RenderDraftRegistry, render_draft_registry

router = APIRouter(prefix="/api/internal/render-drafts", tags=["internal-render"])


@router.get("/{token}")
def read_render_draft(token: str, request: Request) -> dict:
    draft = get_draft_or_404(token, request)
    return {
        "layout": draft.layout,
        "images": [{"id": image_id, "src": f"/api/internal/render-drafts/{token}/images/{image_id}"} for image_id in draft.images],
    }


@router.get("/{token}/images/{image_id}")
def read_render_draft_image(token: str, image_id: str, request: Request) -> Response:
    draft = get_draft_or_404(token, request)
    image = draft.images.get(image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Render draft image not found")
    return Response(content=image.content, media_type=image.media_type)


def get_draft_or_404(token: str, request: Request) -> RenderDraft:
    draft = get_registry(request).get(token)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Render draft not found")
    return draft


def get_registry(request: Request) -> RenderDraftRegistry:
    return getattr(request.app.state, "render_draft_registry", render_draft_registry)
