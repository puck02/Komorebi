import { ChangeEvent, CSSProperties, PointerEvent, type RefObject, useEffect, useRef, useState } from "react";

import { UploadedImage, uploadImage } from "../api/images";

type Props = {
  onUploaded?: (images: UploadedImage[]) => void;
};

export default function ImageUploader({ onUploaded }: Props) {
  const [images, setImages] = useState<UploadedImagePreview[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [dragVisual, setDragVisual] = useState<DragVisual | null>(null);
  const dragGhostRef = useRef<HTMLElement | null>(null);
  const dragSession = useRef<DragSession | null>(null);
  const previewUrls = useRef(new Set<string>());

  useEffect(() => {
    return () => {
      resetDragState();
      previewUrls.current.forEach((previewUrl) => URL.revokeObjectURL(previewUrl));
      previewUrls.current.clear();
    };
  }, []);

  useEffect(() => {
    if (!dragVisual) {
      return;
    }

    const previousBodyOverflow = document.body.style.overflow;
    const previousBodyTouchAction = document.body.style.touchAction;
    const previousBodyOverscroll = document.body.style.overscrollBehavior;
    const previousHtmlOverscroll = document.documentElement.style.overscrollBehavior;

    document.body.style.overflow = "hidden";
    document.body.style.touchAction = "none";
    document.body.style.overscrollBehavior = "none";
    document.documentElement.style.overscrollBehavior = "none";

    function handleWindowPointerMove(event: globalThis.PointerEvent) {
      const session = dragSession.current;
      if (!session || session.pointerId !== event.pointerId || !session.isDragging) {
        return;
      }
      event.preventDefault();
      moveDrag(event.clientX, event.clientY);
    }

    function handleWindowPointerUp(event: globalThis.PointerEvent) {
      finishDrag(event.pointerId, true);
    }

    function handleWindowPointerCancel(event: globalThis.PointerEvent) {
      finishDrag(event.pointerId, false);
    }

    function handleWindowBlur() {
      finishDrag(undefined, false);
    }

    window.addEventListener("pointermove", handleWindowPointerMove, { passive: false });
    window.addEventListener("pointerup", handleWindowPointerUp, { passive: false });
    window.addEventListener("pointercancel", handleWindowPointerCancel, { passive: false });
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      window.removeEventListener("pointermove", handleWindowPointerMove);
      window.removeEventListener("pointerup", handleWindowPointerUp);
      window.removeEventListener("pointercancel", handleWindowPointerCancel);
      window.removeEventListener("blur", handleWindowBlur);
      document.body.style.overflow = previousBodyOverflow;
      document.body.style.touchAction = previousBodyTouchAction;
      document.body.style.overscrollBehavior = previousBodyOverscroll;
      document.documentElement.style.overscrollBehavior = previousHtmlOverscroll;
    };
  }, [dragVisual !== null]);

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

    const pressedElement = event.currentTarget;
    const initialRect = pressedElement.getBoundingClientRect();
    pressedElement.setPointerCapture(event.pointerId);
    const delay = event.pointerType === "mouse" ? 180 : 200;
    const session: DragSession = {
      activeId: imageId,
      initialRect,
      pointerId: event.pointerId,
      sourceElement: pressedElement,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      offsetX: 0,
      offsetY: 0,
      isDragging: false,
      lastTargetId: imageId,
      visualTargetId: imageId,
      frameId: null,
      timerId: window.setTimeout(() => {
        session.isDragging = true;
        setDragVisual({
          activeId: imageId,
          initialRect,
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
    moveDrag(event.clientX, event.clientY);
  }

  function moveDrag(clientX: number, clientY: number) {
    const session = dragSession.current;
    if (!session || !session.isDragging) {
      return;
    }

    session.currentX = clientX;
    session.currentY = clientY;
    session.offsetX = clientX - session.startX;
    session.offsetY = clientY - session.startY;
    scheduleDragGhostUpdate();
    const targetId = findReorderTargetIdAtPoint(clientX, clientY, session.activeId);
    const visualTargetId = targetId ?? session.lastTargetId;

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

    if (visualTargetId !== session.visualTargetId) {
      session.visualTargetId = visualTargetId;
      setDragVisual({
        activeId: session.activeId,
        initialRect: session.initialRect,
        offsetX: session.offsetX,
        offsetY: session.offsetY,
        targetId: visualTargetId
      });
    }
  }

  function endPress(event: PointerEvent<HTMLElement>) {
    if (dragSession.current?.isDragging) {
      event.preventDefault();
    }
    finishDrag(event.pointerId, true);
  }

  function cancelPress(event?: PointerEvent<HTMLElement>) {
    finishDrag(event?.pointerId, false);
  }

  function finishDrag(pointerId: number | undefined, preventNextClick: boolean) {
    const session = dragSession.current;
    if (!session || (pointerId !== undefined && session.pointerId !== pointerId)) {
      return;
    }

    if (preventNextClick) {
      session.sourceElement.dataset.dragJustEnded = "true";
      window.setTimeout(() => {
        delete session.sourceElement.dataset.dragJustEnded;
      }, 0);
    }
    if (session.sourceElement.hasPointerCapture(session.pointerId)) {
      session.sourceElement.releasePointerCapture(session.pointerId);
    }
    resetDragState();
  }

  function resetDragState() {
    clearDragTimer();
    clearDragFrame();
    dragSession.current = null;
    setDragVisual(null);
  }

  function clearDragTimer() {
    if (dragSession.current?.timerId) {
      window.clearTimeout(dragSession.current.timerId);
      dragSession.current.timerId = null;
    }
  }

  function clearDragFrame() {
    if (dragSession.current?.frameId) {
      window.cancelAnimationFrame(dragSession.current.frameId);
      dragSession.current.frameId = null;
    }
  }

  function scheduleDragGhostUpdate() {
    const session = dragSession.current;
    if (!session || session.frameId) {
      return;
    }

    session.frameId = window.requestAnimationFrame(() => {
      session.frameId = null;
      const ghost = dragGhostRef.current;
      if (!ghost) {
        return;
      }
      ghost.style.setProperty("--drag-x", `${session.offsetX}px`);
      ghost.style.setProperty("--drag-y", `${session.offsetY}px`);
    });
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

          return (
            <figure
              className={`${isDragging ? "is-drag-placeholder" : ""} ${isTarget ? "is-drag-target" : ""}`}
              data-upload-image-id={image.id}
              key={image.id}
              onContextMenu={(event) => event.preventDefault()}
              onPointerCancel={cancelPress}
              onPointerDown={(event) => startPress(event, image.id)}
              onPointerMove={movePress}
              onPointerUp={endPress}
            >
              <img alt="" draggable={false} src={image.preview_url} />
              <button type="button" onClick={() => removeImage(image.id)}>
                删除
              </button>
            </figure>
          );
        })}
      </div>
      {dragVisual ? (
        <DragGhost dragVisual={dragVisual} ghostRef={dragGhostRef} image={images.find((image) => image.id === dragVisual.activeId)} />
      ) : null}
    </section>
  );
}

type UploadedImagePreview = UploadedImage & {
  preview_url: string;
};

type DragSession = {
  activeId: string;
  initialRect: DOMRect;
  pointerId: number;
  sourceElement: HTMLElement;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  offsetX: number;
  offsetY: number;
  isDragging: boolean;
  lastTargetId: string;
  visualTargetId: string;
  frameId: number | null;
  timerId: number | null;
};

type DragVisual = {
  activeId: string;
  initialRect: DOMRect;
  offsetX: number;
  offsetY: number;
  targetId: string;
};

function DragGhost({
  dragVisual,
  ghostRef,
  image
}: {
  dragVisual: DragVisual;
  ghostRef: RefObject<HTMLElement | null>;
  image: UploadedImagePreview | undefined;
}) {
  if (!image) {
    return null;
  }

  return (
    <figure
      aria-hidden="true"
      className="upload-drag-ghost"
      ref={ghostRef}
      style={
        {
          "--drag-left": `${dragVisual.initialRect.left}px`,
          "--drag-top": `${dragVisual.initialRect.top}px`,
          "--drag-width": `${dragVisual.initialRect.width}px`,
          "--drag-x": `${dragVisual.offsetX}px`,
          "--drag-y": `${dragVisual.offsetY}px`
        } as CSSProperties
      }
    >
      <img alt="" draggable={false} src={image.preview_url} />
    </figure>
  );
}

function isSupportedImageFile(file: File) {
  return ["image/jpeg", "image/png", "image/webp"].includes(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name);
}

function findReorderTargetIdAtPoint(x: number, y: number, activeId: string) {
  const element = document.elementFromPoint(x, y);
  const directTargetId = element?.closest<HTMLElement>("[data-upload-image-id]")?.dataset.uploadImageId;
  if (directTargetId && directTargetId !== activeId) {
    return directTargetId;
  }

  let nearestTargetId: string | undefined;
  let nearestDistance = Number.POSITIVE_INFINITY;

  document.querySelectorAll<HTMLElement>("[data-upload-image-id]").forEach((item) => {
    const itemId = item.dataset.uploadImageId;
    if (!itemId || itemId === activeId) {
      return;
    }
    const rect = item.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distance = Math.hypot(x - centerX, y - centerY);
    const maxDistance = Math.max(rect.width, rect.height) * 1.2;
    if (distance <= maxDistance && distance < nearestDistance) {
      nearestDistance = distance;
      nearestTargetId = itemId;
    }
  });

  return nearestTargetId;
}
