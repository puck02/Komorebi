from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.generation_job import GenerationJob
from app.models.image import Image as ImageModel
from app.models.user import User
from app.schemas.generation_job import GenerationJobRead
from app.schemas.journal import JournalGenerateRequest

router = APIRouter(prefix="/api/journal-generation-jobs", tags=["journal-generation-jobs"])
JOB_SUBMIT_FAILURE_MESSAGE = "生成任务启动失败，请稍后重试"


def get_generation_job_submitter() -> Callable[[str], None]:
    return submit_generation_job


def submit_generation_job(job_id: str) -> None:
    from app.services.generation_jobs import submit_generation_job as submit

    submit(job_id)


@router.post("", response_model=GenerationJobRead, status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(
    payload: JournalGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    submit: Callable[[str], None] = Depends(get_generation_job_submitter),
) -> GenerationJobRead:
    get_owned_images(db, current_user.id, payload.image_ids)
    job = GenerationJob(
        user_id=current_user.id,
        payload_json=payload.model_dump(by_alias=True, mode="json"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        submit(job.id)
    except Exception:
        job.status = "failed"
        job.stage = "failed"
        job.error_message = JOB_SUBMIT_FAILURE_MESSAGE
        db.commit()
        db.refresh(job)
    return job_to_read(job)


@router.get("/{job_id}", response_model=GenerationJobRead)
def read_generation_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerationJobRead:
    job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.user_id == current_user.id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    return job_to_read(job)


def get_owned_images(db: Session, user_id: str, image_ids: list[str]) -> list[ImageModel]:
    images = db.scalars(select(ImageModel).where(ImageModel.id.in_(image_ids), ImageModel.user_id == user_id)).all()
    image_by_id = {image.id: image for image in images}
    if len(image_by_id) != len(set(image_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return [image_by_id[image_id] for image_id in image_ids]


def job_to_read(job: GenerationJob) -> GenerationJobRead:
    return GenerationJobRead(
        id=job.id,
        status=job.status,
        stage=job.stage,
        revisionRound=job.revision_round,
        maxRevisionRounds=job.max_revision_rounds,
        bestScore=job.best_score,
        journalId=job.journal_id,
        errorMessage=job.error_message,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )
