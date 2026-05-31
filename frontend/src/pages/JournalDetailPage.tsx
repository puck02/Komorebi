import { ArrowLeft, NotebookPen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
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

export default function JournalDetailPage() {
  const { journalId } = useParams<{ journalId: string }>();
  const [displayImages, setDisplayImages] = useState<CanvasImage[]>([]);
  const [isDisplayImagesLoading, setIsDisplayImagesLoading] = useState(false);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [isOriginalImageLoading, setIsOriginalImageLoading] = useState(false);
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
    const objectUrls: string[] = [];
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
          const src = URL.createObjectURL(blob);
          objectUrls.push(src);
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
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [journalQuery.data]);

  const selectedDisplayImage = useMemo(
    () => displayImages.find((image) => image.id === selectedImageId),
    [displayImages, selectedImageId]
  );

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
        <Button asChild variant="ghost">
          <Link to="/">
            <NotebookPen size={16} />
            继续创建
          </Link>
        </Button>
      </header>

      <div className="journal-detail-single">
        <div className="journal-preview-panel">
          <JournalCanvas
            assets={assetsQuery.data ?? []}
            images={displayImages}
            layout={journal.layout}
            onImageClick={setSelectedImageId}
            scale={0.64}
          />
        </div>
      </div>

      {isDisplayImagesLoading ? <p className="journal-image-loading">图片正在逐张加载...</p> : null}

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
