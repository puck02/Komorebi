import { ArrowLeft, Download, NotebookPen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getAssets } from "../api/assets";
import { getImageDisplayBlob, getImageFileBlob } from "../api/images";
import { getJournal } from "../api/journals";
import JournalCanvas from "../components/JournalCanvas";
import { Button } from "../components/ui/button";

type CanvasImage = {
  id: string;
  src: string;
  alt: string;
};

const TRANSPARENT_IMAGE_PLACEHOLDER = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";

export default function JournalDetailPage() {
  const { journalId } = useParams<{ journalId: string }>();
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const previewPanelRef = useRef<HTMLDivElement | null>(null);
  const [displayImages, setDisplayImages] = useState<CanvasImage[]>([]);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isDisplayImagesLoading, setIsDisplayImagesLoading] = useState(false);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [isOriginalImageLoading, setIsOriginalImageLoading] = useState(false);
  const [previewWidth, setPreviewWidth] = useState(getInitialPreviewWidth);
  const journalQuery = useQuery({
    enabled: Boolean(journalId),
    queryFn: () => getJournal(journalId as string),
    queryKey: ["journal", journalId]
  });
  const assetsQuery = useQuery({ queryFn: getAssets, queryKey: ["assets"] });

  useEffect(() => {
    const journal = journalQuery.data;
    if (!journal) {
      setDisplayImages([]);
      setIsDisplayImagesLoading(false);
      return;
    }

    let shouldIgnore = false;
    const imageIds = journal.imageIds;
    const title = journal.title;
    setDisplayImages([]);
    setIsDisplayImagesLoading(true);

    async function loadDisplayImages() {
      for (const imageId of imageIds) {
        try {
          const blob = await getImageDisplayBlob(imageId);
          if (shouldIgnore) {
            return;
          }
          const src = await blobToDataUrl(blob);
          if (shouldIgnore) {
            return;
          }
          setDisplayImages((currentImages) => [
            ...currentImages,
            {
              alt: title,
              id: imageId,
              src
            }
          ]);
        } catch {
          if (shouldIgnore) {
            return;
          }
        }
      }

      if (!shouldIgnore) {
        setIsDisplayImagesLoading(false);
      }
    }

    void loadDisplayImages();

    return () => {
      shouldIgnore = true;
    };
  }, [journalQuery.data]);

  const selectedDisplayImage = useMemo(
    () => displayImages.find((image) => image.id === selectedImageId),
    [displayImages, selectedImageId]
  );

  useLayoutEffect(() => {
    const panel = previewPanelRef.current;
    if (!panel) {
      return;
    }
    const observedPanel = panel;

    function updatePreviewWidth() {
      setPreviewWidth(getElementContentWidth(observedPanel));
    }

    updatePreviewWidth();
    const resizeObserver = new ResizeObserver(updatePreviewWidth);
    resizeObserver.observe(observedPanel);
    return () => resizeObserver.disconnect();
  }, [journalQuery.data?.id]);

  useEffect(() => {
    if (!selectedImageId) {
      setOriginalImageUrl(null);
      setIsOriginalImageLoading(false);
      return;
    }

    let shouldIgnore = false;
    let objectUrl: string | null = null;
    setOriginalImageUrl(null);
    setIsOriginalImageLoading(true);

    getImageFileBlob(selectedImageId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (!shouldIgnore) {
          setOriginalImageUrl(objectUrl);
        }
      })
      .catch(() => {
        if (!shouldIgnore) {
          setOriginalImageUrl(null);
        }
      })
      .finally(() => {
        if (!shouldIgnore) {
          setIsOriginalImageLoading(false);
        }
      });

    return () => {
      shouldIgnore = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [selectedImageId]);

  const journal = journalQuery.data;
  const isLoading = journalQuery.isLoading || assetsQuery.isLoading;
  const error = journalQuery.error ?? assetsQuery.error;
  const canvasScale = useMemo(() => {
    if (!journal) {
      return 0.64;
    }

    const fitScale = previewWidth / journal.layout.canvas.width;
    return Math.min(0.64, Math.max(0.1, fitScale));
  }, [journal, previewWidth]);

  const handleExportImage = useCallback(async () => {
    if (!journal || !canvasRef.current) {
      return;
    }

    setExportError(null);
    setIsExporting(true);
    try {
      const dataUrl = await toPng(canvasRef.current, {
        cacheBust: true,
        height: journal.layout.canvas.height,
        imagePlaceholder: TRANSPARENT_IMAGE_PLACEHOLDER,
        pixelRatio: 1,
        skipFonts: true,
        style: {
          transform: "none"
        },
        width: journal.layout.canvas.width
      });
      const link = document.createElement("a");
      link.download = `${sanitizeFileName(journal.title)}.png`;
      link.href = dataUrl;
      link.click();
    } catch {
      setExportError("导出失败，请稍后重试");
    } finally {
      setIsExporting(false);
    }
  }, [journal]);

  if (isLoading) {
    return (
      <section className="journal-detail-page">
        <p className="text-sm font-semibold text-[#001858]">正在加载手帐...</p>
      </section>
    );
  }

  if (error instanceof Error || !journal) {
    return (
      <section className="journal-detail-page">
        <Button asChild variant="ghost">
          <Link to="/">
            <ArrowLeft size={16} />
            返回创建
          </Link>
        </Button>
        <p className="form-error">{error instanceof Error ? error.message : "手帐不存在"}</p>
      </section>
    );
  }

  return (
    <section className="journal-detail-page">
      <header className="journal-detail-toolbar">
        <Button asChild variant="ghost">
          <Link to="/history">
            <ArrowLeft size={16} />
            返回历史
          </Link>
        </Button>
        <div className="journal-detail-actions">
          <Button
            disabled={isExporting || isDisplayImagesLoading}
            onClick={handleExportImage}
            type="button"
            variant="outline"
          >
            <Download size={16} />
            {isExporting ? "导出中" : "导出图片"}
          </Button>
          <Button asChild variant="ghost">
            <Link to="/">
              <NotebookPen size={16} />
              继续创建
            </Link>
          </Button>
        </div>
      </header>

      <div className="journal-detail-single">
        <div className="journal-preview-panel" ref={previewPanelRef}>
          <div className="journal-canvas-fit-shell">
            <JournalCanvas
              assets={assetsQuery.data ?? []}
              canvasRef={canvasRef}
              images={displayImages}
              layout={journal.layout}
              onImageClick={setSelectedImageId}
              scale={canvasScale}
            />
          </div>
        </div>
      </div>

      {isDisplayImagesLoading ? <p className="journal-image-loading">图片正在逐张加载...</p> : null}
      {exportError ? <p className="form-error journal-export-error">{exportError}</p> : null}

      {selectedImageId ? (
        <button className="image-lightbox" type="button" onClick={() => setSelectedImageId(null)}>
          {isOriginalImageLoading ? <span>正在加载原图...</span> : null}
          <img
            alt={selectedDisplayImage?.alt ?? journal.title}
            src={originalImageUrl ?? selectedDisplayImage?.src}
          />
        </button>
      ) : null}
    </section>
  );
}

function sanitizeFileName(fileName: string) {
  return fileName.trim().replace(/[\\/:*?"<>|]/g, "_") || "komorebi-journal";
}

function getInitialPreviewWidth() {
  if (typeof window === "undefined") {
    return 0;
  }
  return Math.max(window.innerWidth - 40, 0);
}

function getElementContentWidth(element: HTMLElement) {
  const style = window.getComputedStyle(element);
  const paddingLeft = Number.parseFloat(style.paddingLeft) || 0;
  const paddingRight = Number.parseFloat(style.paddingRight) || 0;
  return Math.max(element.clientWidth - paddingLeft - paddingRight, 0);
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("图片读取失败"));
      }
    });
    reader.addEventListener("error", () => reject(reader.error ?? new Error("图片读取失败")));
    reader.readAsDataURL(blob);
  });
}
