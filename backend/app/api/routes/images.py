from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.image import Image as ImageModel
from app.models.user import User
from app.schemas.image import ImageRead
from app.services.storage import build_image_paths, extension_for_content_type, save_upload_file
from app.services.thumbnails import generate_thumbnail

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageRead:
    extension = extension_for_content_type(file.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    image_id = str(uuid4())
    paths = build_image_paths(get_settings().storage_root, current_user.id, image_id, extension)
    save_upload_file(file, paths.original)

    try:
        width, height = generate_thumbnail(paths.original, paths.thumbnail)
    except UnidentifiedImageError as exc:
        rmtree(paths.directory, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file") from exc

    image = ImageModel(
        id=image_id,
        user_id=current_user.id,
        original_path=str(paths.original),
        thumbnail_path=str(paths.thumbnail),
        content_type=file.content_type or "application/octet-stream",
        width=width,
        height=height,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image_to_read(image)


@router.get("/{image_id}", response_model=ImageRead)
def get_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageRead:
    image = get_owned_image(db, current_user.id, image_id)
    return image_to_read(image)


@router.get("/{image_id}/file")
def get_image_file(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    image = get_owned_image(db, current_user.id, image_id)
    return FileResponse(Path(image.original_path), media_type=image.content_type)


@router.get("/{image_id}/thumbnail")
def get_image_thumbnail(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    image = get_owned_image(db, current_user.id, image_id)
    return FileResponse(Path(image.thumbnail_path), media_type="image/webp")


def get_owned_image(db: Session, user_id: str, image_id: str) -> ImageModel:
    image = db.scalar(select(ImageModel).where(ImageModel.id == image_id, ImageModel.user_id == user_id))
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


def image_to_read(image: ImageModel) -> ImageRead:
    return ImageRead(
        id=image.id,
        content_type=image.content_type,
        width=image.width,
        height=image.height,
        file_url=f"/api/images/{image.id}/file",
        thumbnail_url=f"/api/images/{image.id}/thumbnail",
        created_at=image.created_at,
    )
