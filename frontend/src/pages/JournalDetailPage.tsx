import { ArrowLeft, CalendarDays, Image as ImageIcon, MapPin, Tags } from "lucide-react";
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
        <p className="text-sm font-semibold text-[#65584d]">正在加载手帐...</p>
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
      <header className="journal-detail-header">
        <div className="grid gap-3">
          <Button asChild variant="ghost">
            <Link to="/">
              <ArrowLeft size={16} />
              继续创建
            </Link>
          </Button>
          <div>
            <p className="eyebrow">Generated Journal</p>
            <h1>{journal.title}</h1>
          </div>
        </div>
        <div className="journal-detail-meta">
          <MetaItem icon={ImageIcon} text={`${journal.imageIds.length} 张图片`} />
          {journal.journalDate ? <MetaItem icon={CalendarDays} text={journal.journalDate} /> : null}
          {journal.location ? <MetaItem icon={MapPin} text={journal.location} /> : null}
          {journal.moodTags.length > 0 ? <MetaItem icon={Tags} text={journal.moodTags.join(" / ")} /> : null}
        </div>
      </header>

      <div className="journal-detail-layout">
        <div className="journal-preview-panel">
          <JournalCanvas assets={assetsQuery.data ?? []} images={imagesQuery.data ?? []} layout={journal.layout} scale={0.54} />
        </div>
        <aside className="journal-copy-panel">
          <p className="eyebrow">Story</p>
          <div className="journal-copy-body">
            {journal.layout.content.body.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          {journal.layout.content.captions.length > 0 ? (
            <div className="journal-caption-list">
              {journal.layout.content.captions.map((caption) => (
                <p key={`${caption.imageId}-${caption.text}`}>{caption.text}</p>
              ))}
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}

type MetaItemProps = {
  icon: typeof ImageIcon;
  text: string;
};

function MetaItem({ icon: Icon, text }: MetaItemProps) {
  return (
    <span>
      <Icon size={15} />
      {text}
    </span>
  );
}
