from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.generation_job import GenerationJob
from app.models.image import Image as ImageModel
from app.models.journal import Journal
from app.schemas.journal import JournalGenerateRequest
from app.services.agent_observability import log_agent_event
from app.services.assets import get_approved_assets
from app.services.journal_agent import JournalAgent, JournalAgentResult
from app.services.journal_generator import JournalGenerationRequest, JournalImageInput
from app.services.journal_renderer import PlaywrightJournalRenderer
from app.services.openai_client import OpenAIJournalClient
from app.services.thumbnails import generate_display_image

GENERATION_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="journal-generation")


def submit_generation_job(job_id: str) -> None:
    GENERATION_EXECUTOR.submit(run_generation_job, job_id)


def build_journal_agent() -> JournalAgent:
    return JournalAgent(OpenAIJournalClient(), PlaywrightJournalRenderer())


def run_generation_job(
    job_id: str,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    agent_factory: Callable[[], JournalAgent] = build_journal_agent,
) -> None:
    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        try:
            payload = JournalGenerateRequest.model_validate(job.payload_json)
            images = get_job_images(db, job.user_id, payload.image_ids)
            assets = get_approved_assets()
            request = JournalGenerationRequest(
                description=payload.description,
                images=[image_to_generation_input(image) for image in images],
                assets=assets,
            )
            job.status = "running"
            job.stage = "understanding_photos"
            db.commit()
            log_agent_event(
                "agent.job_started",
                job_id=job.id,
                user_id=job.user_id,
                image_count=len(images),
                asset_count=len(assets),
                description_length=len(payload.description),
                mood_tag_count=len(payload.mood_tags),
            )
            result = agent_factory().generate(
                request,
                on_progress=lambda stage, revision_round, score: update_job_progress(db, job, stage, revision_round, score),
                log_context={"job_id": job.id, "user_id": job.user_id},
            )
            journal = save_generated_journal(db, job, payload, images, result)
            job.status = "completed"
            job.stage = "completed"
            job.journal_id = journal.id
            job.revision_round = result.revision_round
            job.best_score = result.score
            job.error_message = None
            db.commit()
            log_agent_event(
                "agent.job_completed",
                job_id=job.id,
                user_id=job.user_id,
                journal_id=journal.id,
                revision_round=result.revision_round,
                score=result.score,
                passed=result.passed,
            )
        except Exception as exc:
            db.rollback()
            failed_job = db.get(GenerationJob, job_id)
            if failed_job is not None:
                failed_job.status = "failed"
                failed_job.stage = "failed"
                failed_job.error_message = str(exc) or exc.__class__.__name__
                db.commit()
                log_agent_event(
                    "agent.job_failed",
                    job_id=failed_job.id,
                    user_id=failed_job.user_id,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc) or exc.__class__.__name__,
                )


def update_job_progress(
    db: Session,
    job: GenerationJob,
    stage: str,
    revision_round: int,
    score: float | None,
) -> None:
    job.stage = stage
    job.revision_round = revision_round
    if score is not None and (job.best_score is None or score > job.best_score):
        job.best_score = score
    db.commit()
    log_agent_event(
        "agent.progress",
        job_id=job.id,
        user_id=job.user_id,
        stage=stage,
        revision_round=revision_round,
        score=score,
        best_score=job.best_score,
    )


def save_generated_journal(
    db: Session,
    job: GenerationJob,
    payload: JournalGenerateRequest,
    images: list[ImageModel],
    result: JournalAgentResult,
) -> Journal:
    journal = Journal(
        user_id=job.user_id,
        title=result.layout.content.title,
        input_text=payload.description,
        journal_date=payload.journal_date,
        location=payload.location,
        mood_tags=payload.mood_tags,
        layout_json=result.layout.model_dump(by_alias=True),
        images=images,
    )
    db.add(journal)
    db.flush()
    return journal


def get_job_images(db: Session, user_id: str, image_ids: list[str]) -> list[ImageModel]:
    images = db.scalars(select(ImageModel).where(ImageModel.id.in_(image_ids), ImageModel.user_id == user_id)).all()
    image_by_id = {image.id: image for image in images}
    if len(image_by_id) != len(set(image_ids)):
        raise ValueError("Image not found")
    return [image_by_id[image_id] for image_id in image_ids]


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


def recover_incomplete_generation_jobs(*, session_factory: sessionmaker[Session] = SessionLocal) -> None:
    with session_factory() as db:
        jobs = db.scalars(select(GenerationJob).where(GenerationJob.status.in_(["queued", "running"]))).all()
        for job in jobs:
            job.status = "failed"
            job.stage = "failed"
            job.error_message = "服务已重启，请重新生成手帐"
        db.commit()
