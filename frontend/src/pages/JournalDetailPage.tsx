import { ArrowLeft, NotebookPen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getAssets } from "../api/assets";
import { getImageDisplayBlob, getImageFileBlob } from "../api/images";
import { getJournal } from "../api/journals";
import JournalCanvas from "../components/JournalCanvas";
import { Button } from "../components/ui/button";

export default function JournalDetailPage() {
  const { journalId } = useParams<{ journalId: string }>();
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [isOriginalImageLoading, setIsOriginalImageLoading] = useState(false);
  const journalQuery = useQuery({
    enabled: Boolean(journalId),
    queryFn: () => getJournal(journalId as string),
    queryKey: ["journal", journalId]
  });
  const assetsQuery = useQuery({ queryFn: getAssets, queryKey: ["assets"] });
  const imagesQuery = useQuery({
    enabled: Boolean(journalQuery.data),
    queryFn: () =>
      Promise.all(
        (journalQuery.data?.imageIds ?? []).map(async (imageId) => {
          const blob = await getImageDisplayBlob(imageId);
          return {
            alt: journalQuery.data?.title ?? "",
            id: imageId,
            src: URL.createObjectURL(blob)
          };
        })
      ),
    gcTime: 0,
    queryKey: ["journal-images", journalQuery.data?.imageIds]
  });

  useEffect(() => {
    const images = imagesQuery.data ?? [];
    return () => {
      images.forEach((image) => URL.revokeObjectURL(image.src));
    };
  }, [imagesQuery.data]);

  const selectedDisplayImage = useMemo(
    () => imagesQuery.data?.find((image) => image.id === selectedImageId),
    [imagesQuery.data, selectedImageId]
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
  const isLoading = journalQuery.isLoading || assetsQuery.isLoading || imagesQuery.isLoading;
  const error = journalQuery.error ?? assetsQuery.error ?? imagesQuery.error;

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
            images={imagesQuery.data ?? []}
            layout={journal.layout}
            onImageClick={setSelectedImageId}
            scale={0.64}
          />
        </div>
      </div>

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
