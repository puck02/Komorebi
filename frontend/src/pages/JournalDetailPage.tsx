import { ArrowLeft, NotebookPen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import { getAssets } from "../api/assets";
import { getImage, getImageFileBlob } from "../api/images";
import { getJournal } from "../api/journals";
import JournalCanvas from "../components/JournalCanvas";
import { Button } from "../components/ui/button";

export default function JournalDetailPage() {
  const { journalId } = useParams<{ journalId: string }>();
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
          const [image, blob] = await Promise.all([getImage(imageId), getImageFileBlob(imageId)]);
          return {
            alt: journalQuery.data?.title ?? "",
            id: image.id,
            src: URL.createObjectURL(blob)
          };
        })
      ),
    queryKey: ["journal-images", journalQuery.data?.imageIds]
  });

  useEffect(() => {
    const images = imagesQuery.data ?? [];
    return () => {
      images.forEach((image) => URL.revokeObjectURL(image.src));
    };
  }, [imagesQuery.data]);

  const journal = journalQuery.data;
  const isLoading = journalQuery.isLoading || assetsQuery.isLoading || imagesQuery.isLoading;
  const error = journalQuery.error ?? assetsQuery.error ?? imagesQuery.error;

  if (isLoading) {
    return (
      <section className="journal-detail-page">
        <p className="text-sm font-semibold text-[#6d6875]">正在加载手帐...</p>
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
            scale={0.64}
          />
        </div>
      </div>
    </section>
  );
}
