from base64 import b64encode
from pathlib import Path
from shutil import rmtree

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.image import Image as ImageModel
from app.models.journal import Journal
from app.models.user import User
from app.schemas.journal import (
    JournalGenerateRequest,
    JournalLayout,
    JournalRead,
    JournalTemplateRecommendRead,
    JournalTemplateRecommendRequest,
    JournalUpdateRequest,
)
from app.services.admin import get_effective_ai_settings
from app.services.assets import get_approved_assets
from app.services.journal_generator import (
    GenerationError,
    JournalGenerationRequest,
    JournalGenerator,
    JournalImageInput,
    build_fallback_layout,
    sanitize_model_layout,
)
from app.services.openai_client import OpenAIConfigurationError, OpenAIJournalClient
from app.services.template_recommender import (
    OpenAITemplateVisionClient,
    TEMPLATE_PROFILES,
    TemplateRecommendationImage,
    TemplateRecommendationRequest,
    recommend_templates,
)
from app.services.thumbnails import generate_display_image

router = APIRouter(prefix="/api/journals", tags=["journals"])
KNOWN_TEMPLATE_IDS = {profile.id for profile in TEMPLATE_PROFILES}


def get_journal_generator(db: Session = Depends(get_db)) -> JournalGenerator:
    try:
        ai_settings = get_effective_ai_settings(db)
        return JournalGenerator(
            OpenAIJournalClient(
                api_key=ai_settings.api_key,
                base_url=ai_settings.base_url,
                model=ai_settings.model,
                review_model=ai_settings.review_model,
            )
        )
    except OpenAIConfigurationError as exc:
        return JournalGenerator(UnavailableJournalClient(exc))


@router.post("/generate", response_model=JournalRead, status_code=status.HTTP_201_CREATED)
def generate_journal(
    payload: JournalGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    generator: JournalGenerator = Depends(get_journal_generator),
) -> JournalRead:
    images = get_owned_images(db, current_user.id, payload.image_ids)
    generation_request = JournalGenerationRequest(
        description=payload.description,
        images=[image_to_generation_input(image) for image in images],
        assets=get_approved_assets(),
        journal_date=payload.journal_date,
        location=payload.location,
        mood_tags=payload.mood_tags,
        template_id=payload.template_id,
    )
    try:
        layout = generator.generate(generation_request)
    except (GenerationError, OpenAIConfigurationError):
        layout_json = sanitize_model_layout(build_fallback_layout(generation_request), generation_request)
        layout = JournalLayout.model_validate(layout_json)

    journal = Journal(
        user_id=current_user.id,
        title=layout.content.title,
        input_text=payload.description,
        journal_date=payload.journal_date,
        location=payload.location,
        mood_tags=payload.mood_tags,
        layout_json=layout.model_dump(by_alias=True),
        images=images,
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal_to_read(journal)


class UnavailableJournalClient:
    def __init__(self, error: OpenAIConfigurationError):
        self.error = error

    def generate_layout(self, request: JournalGenerationRequest) -> dict:
        raise self.error


@router.post("/template-recommendations", response_model=JournalTemplateRecommendRead)
def recommend_journal_templates(
    payload: JournalTemplateRecommendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalTemplateRecommendRead:
    images = get_owned_images(db, current_user.id, payload.image_ids)
    recommendation_request = TemplateRecommendationRequest(
        description=payload.description,
        images=[image_to_template_recommendation_input(image) for image in images],
        mood_tags=payload.mood_tags,
    )
    ai_settings = get_effective_ai_settings(db)
    client = None
    if ai_settings.api_key:
        client = OpenAITemplateVisionClient(
            api_key=ai_settings.api_key,
            base_url=ai_settings.base_url,
            model=ai_settings.model,
        )
    result = recommend_templates(recommendation_request, client)
    return JournalTemplateRecommendRead.model_validate(result)


@router.get("", response_model=list[JournalRead])
def list_journals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JournalRead]:
    journals = db.scalars(
        select(Journal).where(Journal.user_id == current_user.id).order_by(Journal.updated_at.desc())
    ).all()
    return [journal_to_read(journal) for journal in journals]


@router.get("/{journal_id}", response_model=JournalRead)
def get_journal(
    journal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalRead:
    journal = get_owned_journal(db, current_user.id, journal_id)
    return journal_to_read(journal)


@router.patch("/{journal_id}", response_model=JournalRead)
def update_journal(
    journal_id: str,
    payload: JournalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalRead:
    journal = get_owned_journal(db, current_user.id, journal_id)
    layout_json = dict(journal.layout_json)
    content = dict(layout_json.get("content", {}))
    layout = dict(layout_json.get("layout", {}))

    if payload.title is not None:
        journal.title = payload.title
        content["title"] = payload.title
    if payload.meta is not None:
        content["meta"] = payload.meta
    if payload.body is not None:
        content["body"] = payload.body
    if payload.captions is not None:
        content["captions"] = [caption.model_dump(by_alias=True) for caption in payload.captions]
    if payload.sections is not None:
        content["sections"] = [section.model_dump(by_alias=True) for section in payload.sections]
    if payload.layout_variant is not None:
        layout["variant"] = payload.layout_variant

    layout_json["content"] = content
    layout_json["layout"] = layout
    journal.layout_json = layout_json
    db.commit()
    db.refresh(journal)
    return journal_to_read(journal)


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(
    journal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    journal = get_owned_journal(db, current_user.id, journal_id)
    images = list(journal.images)
    journal.images.clear()
    db.delete(journal)
    for image in images:
        delete_image_files(image)
        db.delete(image)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def get_owned_images(db: Session, user_id: str, image_ids: list[str]) -> list[ImageModel]:
    images = db.scalars(select(ImageModel).where(ImageModel.id.in_(image_ids), ImageModel.user_id == user_id)).all()
    image_by_id = {image.id: image for image in images}
    if len(image_by_id) != len(set(image_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return [image_by_id[image_id] for image_id in image_ids]


def get_owned_journal(db: Session, user_id: str, journal_id: str) -> Journal:
    journal = db.scalar(select(Journal).where(Journal.id == journal_id, Journal.user_id == user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    return journal


def delete_image_files(image: ImageModel) -> None:
    rmtree(Path(image.original_path).parent, ignore_errors=True)


def image_to_generation_input(image: ImageModel) -> JournalImageInput:
    display_path = Path(image.original_path).parent / "display.webp"
    if not display_path.exists():
        generate_display_image(Path(image.original_path), display_path)
    return JournalImageInput(
        id=image.id,
        width=image.width,
        height=image.height,
        data_url=f"data:image/webp;base64,{b64encode(display_path.read_bytes()).decode('ascii')}",
    )


def image_to_template_recommendation_input(image: ImageModel) -> TemplateRecommendationImage:
    display_path = Path(image.original_path).parent / "display.webp"
    if not display_path.exists():
        generate_display_image(Path(image.original_path), display_path)
    return TemplateRecommendationImage(
        id=image.id,
        width=image.width,
        height=image.height,
        data_url=f"data:image/webp;base64,{b64encode(display_path.read_bytes()).decode('ascii')}",
    )


def journal_to_read(journal: Journal) -> JournalRead:
    layout = normalized_journal_layout(journal)
    return JournalRead(
        id=journal.id,
        title=journal.title,
        inputText=journal.input_text,
        journalDate=journal.journal_date,
        location=journal.location,
        moodTags=journal.mood_tags,
        layout=layout,
        imageIds=[image.id for image in journal.images],
        createdAt=journal.created_at,
        updatedAt=journal.updated_at,
    )


def normalized_journal_layout(journal: Journal) -> dict:
    try:
        template_id = saved_template_id(journal.layout_json)
        return sanitize_model_layout(
            journal.layout_json,
            JournalGenerationRequest(
                description=journal.input_text,
                images=[JournalImageInput(id=image.id, width=image.width, height=image.height) for image in journal.images],
                assets=get_approved_assets(),
                journal_date=journal.journal_date,
                location=journal.location,
                mood_tags=journal.mood_tags,
                template_id=template_id,
            ),
            preserve_saved_text=True,
        )
    except (KeyError, TypeError, ValueError):
        return journal.layout_json


def saved_template_id(layout_json: dict) -> str | None:
    value = str(layout_json.get("layout", {}).get("variant") or "").strip()
    return value if value in KNOWN_TEMPLATE_IDS else None
