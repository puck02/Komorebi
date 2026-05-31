import { ChangeEvent, CSSProperties, PointerEvent, useEffect, useRef, useState } from "react";

import { UploadedImage, uploadImage } from "../api/images";

type Props = {
  onUploaded?: (images: UploadedImage[]) => void;
};

export default function ImageUploader({ onUploaded }: Props) {
  const [images, setImages] = useState<UploadedImagePreview[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [dragVisual, setDragVisual] = useState<DragVisual | null>(null);
  const dragSession = useRef<DragSession | null>(null);
  const previewUrls = useRef(new Set<string>());

  useEffect(() => {
    return () => {
      clearDragTimer();
      previewUrls.current.forEach((previewUrl) => URL.revokeObjectURL(previewUrl));
      previewUrls.current.clear();
    };
  }, []);

  async function handleFilesChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    const uploadableFiles = selectedFiles.filter(isSupportedImageFile);
    setError("");

    if (selectedFiles.length === 0) {
      return;
    }

    if (uploadableFiles.length === 0) {
      setError("暂支持 JPG、PNG、WebP 图片。");
      event.target.value = "";
      return;
    }

    if (images.length + uploadableFiles.length > 9) {
      setError("最多上传 9 张图片。");
      event.target.value = "";
      return;
    }

    if (uploadableFiles.length < selectedFiles.length) {
      setError("已跳过暂不支持的图片格式，仅上传 JPG、PNG、WebP。");
    }

    const selectedPreviews = uploadableFiles.map((file) => ({
      file,
      previewUrl: URL.createObjectURL(file)
    }));
    selectedPreviews.forEach(({ previewUrl }) => previewUrls.current.add(previewUrl));

    setIsUploading(true);
    try {
      const uploadedImages: UploadedImagePreview[] = [];
      for (const { file, previewUrl } of selectedPreviews) {
        uploadedImages.push({
          ...(await uploadImage(file)),
          preview_url: previewUrl
        });
      }
      const nextImages = [...images, ...uploadedImages];
      setImages(nextImages);
      onUploaded?.(nextImages);
    } catch (caughtError) {
      selectedPreviews.forEach(({ previewUrl }) => {
        URL.revokeObjectURL(previewUrl);
        previewUrls.current.delete(previewUrl);
      });
      setError(caughtError instanceof Error ? caughtError.message : "图片上传失败");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  function removeImage(imageId: string) {
    const removedImage = images.find((image) => image.id === imageId);
    if (removedImage) {
      URL.revokeObjectURL(removedImage.preview_url);
      previewUrls.current.delete(removedImage.preview_url);
    }
    const nextImages = images.filter((image) => image.id !== imageId);
    setImages(nextImages);
    onUploaded?.(nextImages);
  }

  function startPress(event: PointerEvent<HTMLElement>, imageId: string) {
    if (isUploading || (event.pointerType === "mouse" && event.button !== 0)) {
      return;
    }

    if ((event.target as HTMLElement).closest("button")) {
      return;
    }

    event.currentTarget.setPointerCapture(event.pointerId);
    const delay = event.pointerType === "mouse" ? 180 : 200;
    const session: DragSession = {
      activeId: imageId,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      isDragging: false,
      lastTargetId: imageId,
      timerId: window.setTimeout(() => {
        session.isDragging = true;
        setDragVisual({
          activeId: imageId,
          offsetX: 0,
          offsetY: 0,
          targetId: imageId
        });
      }, delay)
    };
    dragSession.current = session;
  }

  function movePress(event: PointerEvent<HTMLElement>) {
    const session = dragSession.current;
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }

    session.currentX = event.clientX;
    session.currentY = event.clientY;

    if (!session.isDragging) {
      const moved = Math.hypot(event.clientX - session.startX, event.clientY - session.startY);
      if (moved > 10) {
        cancelPress(event);
      }
      return;
    }

    event.preventDefault();
    const offsetX = event.clientX - session.startX;
    const offsetY = event.clientY - session.startY;
    const targetId = findImageIdAtPoint(event.clientX, event.clientY);

    if (targetId && targetId !== session.activeId && targetId !== session.lastTargetId) {
      session.lastTargetId = targetId;
      setImages((currentImages) => {
        const fromIndex = currentImages.findIndex((image) => image.id === session.activeId);
        const toIndex = currentImages.findIndex((image) => image.id === targetId);
        if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) {
          return currentImages;
        }
        const nextImages = [...currentImages];
        const [movedImage] = nextImages.splice(fromIndex, 1);
        nextImages.splice(toIndex, 0, movedImage);
        onUploaded?.(nextImages);
        return nextImages;
      });
    }

    setDragVisual({
      activeId: session.activeId,
      offsetX,
      offsetY,
      targetId: targetId ?? session.lastTargetId
    });
  }

  function endPress(event: PointerEvent<HTMLElement>) {
    const session = dragSession.current;
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }

    clearDragTimer();
    if (session.isDragging) {
      event.preventDefault();
    }
    dragSession.current = null;
    setDragVisual(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function cancelPress(event?: PointerEvent<HTMLElement>) {
    const session = dragSession.current;
    clearDragTimer();
    dragSession.current = null;
    setDragVisual(null);
    if (event && event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function clearDragTimer() {
    if (dragSession.current?.timerId) {
      window.clearTimeout(dragSession.current.timerId);
      dragSession.current.timerId = null;
    }
  }

  return (
    <section className="image-uploader">
      <label className={`upload-zone ${isUploading ? "is-disabled" : ""}`}>
        <span>{isUploading ? "上传中..." : "选择多张图片"}</span>
        <input
          accept="image/*,.jpg,.jpeg,.png,.webp"
          aria-label="选择多张图片"
          className="upload-input"
          disabled={isUploading}
          multiple
          onChange={handleFilesChange}
          type="file"
        />
      </label>
      {images.length > 1 ? <p className="upload-hint">长按图片可拖动排序</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      <div className="upload-grid">
        {images.map((image) => {
          const isDragging = dragVisual?.activeId === image.id;
          const isTarget = dragVisual?.targetId === image.id && dragVisual.activeId !== image.id;
          const dragStyle = isDragging
            ? ({
                "--drag-x": `${dragVisual.offsetX}px`,
                "--drag-y": `${dragVisual.offsetY}px`
              } as CSSProperties)
            : undefined;

          return (
            <figure
              className={`${isDragging ? "is-dragging" : ""} ${isTarget ? "is-drag-target" : ""}`}
              data-upload-image-id={image.id}
              key={image.id}
              onContextMenu={(event) => event.preventDefault()}
              onPointerCancel={cancelPress}
              onPointerDown={(event) => startPress(event, image.id)}
              onPointerMove={movePress}
              onPointerUp={endPress}
              style={dragStyle}
            >
              <img alt="" draggable={false} src={image.preview_url} />
              <button type="button" onClick={() => removeImage(image.id)}>
                删除
              </button>
            </figure>
          );
        })}
      </div>
    </section>
  );
}

type UploadedImagePreview = UploadedImage & {
  preview_url: string;
};

type DragSession = {
  activeId: string;
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  isDragging: boolean;
  lastTargetId: string;
  timerId: number | null;
};

type DragVisual = {
  activeId: string;
  offsetX: number;
  offsetY: number;
  targetId: string;
};

function isSupportedImageFile(file: File) {
  return ["image/jpeg", "image/png", "image/webp"].includes(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name);
}

function findImageIdAtPoint(x: number, y: number) {
  const element = document.elementFromPoint(x, y);
  return element?.closest<HTMLElement>("[data-upload-image-id]")?.dataset.uploadImageId;
}
