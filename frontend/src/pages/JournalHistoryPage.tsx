import { CalendarDays, Image as ImageIcon, MapPin, NotebookPen, Tags } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { getImageThumbnailBlob } from "../api/images";
import { listJournals, type Journal } from "../api/journals";
import { Button } from "../components/ui/button";

export default function JournalHistoryPage() {
  const journalsQuery = useQuery({ queryFn: listJournals, queryKey: ["journals"] });
  const journals = journalsQuery.data ?? [];
  const thumbnailIds = journals.map((journal) => journal.imageIds[0]).filter(Boolean);
  const thumbnailsQuery = useQuery({
    enabled: thumbnailIds.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        thumbnailIds.map(async (imageId) => [imageId, URL.createObjectURL(await getImageThumbnailBlob(imageId))] as const)
      );
      return Object.fromEntries(entries) as Record<string, string>;
    },
    queryKey: ["journal-history-thumbnails", thumbnailIds]
  });

  useEffect(() => {
    const thumbnails = thumbnailsQuery.data;
    return () => {
      Object.values(thumbnails ?? {}).forEach((url) => URL.revokeObjectURL(url));
    };
  }, [thumbnailsQuery.data]);

  if (journalsQuery.isLoading) {
    return (
      <section className="history-page">
        <p className="text-sm font-semibold text-[#6d6875]">正在加载历史手帐...</p>
      </section>
    );
  }

  if (journalsQuery.error instanceof Error) {
    return (
      <section className="history-page">
        <p className="form-error">{journalsQuery.error.message}</p>
      </section>
    );
  }

  return (
    <section className="history-page">
      <header className="history-header">
        <div>
          <p className="eyebrow">Journal Archive</p>
          <h1>历史手帐</h1>
        </div>
        <Button asChild>
          <Link to="/">
            <NotebookPen size={17} />
            新建手帐
          </Link>
        </Button>
      </header>

      {journals.length === 0 ? (
        <div className="history-empty">
          <NotebookPen size={28} />
          <h2>还没有保存过手帐</h2>
          <p>上传照片并生成后，手帐会自动出现在这里。</p>
          <Button asChild>
            <Link to="/">去创建</Link>
          </Button>
        </div>
      ) : (
        <div className="history-grid">
          {journals.map((journal) => (
            <JournalHistoryCard
              key={journal.id}
              journal={journal}
              thumbnailUrl={journal.imageIds[0] ? thumbnailsQuery.data?.[journal.imageIds[0]] : undefined}
            />
          ))}
        </div>
      )}
    </section>
  );
}

type JournalHistoryCardProps = {
  journal: Journal;
  thumbnailUrl?: string;
};

function JournalHistoryCard({ journal, thumbnailUrl }: JournalHistoryCardProps) {
  const summary = journal.layout.content.body[0] ?? journal.inputText;

  return (
    <Link className="history-card" to={`/journals/${journal.id}`}>
      <div className="history-thumb" aria-hidden="true">
        {thumbnailUrl ? <img alt="" src={thumbnailUrl} /> : <ImageIcon size={26} />}
      </div>
      <div className="history-card-body">
        <div className="history-card-title-row">
          <h2>{journal.title}</h2>
          <span>{formatDate(journal.updatedAt)}</span>
        </div>
        <p>{summary}</p>
        <div className="history-card-meta">
          <MetaPill icon={<ImageIcon size={14} />} text={`${journal.imageIds.length} 张图片`} />
          {journal.journalDate ? <MetaPill icon={<CalendarDays size={14} />} text={journal.journalDate} /> : null}
          {journal.location ? <MetaPill icon={<MapPin size={14} />} text={journal.location} /> : null}
          {journal.moodTags.length > 0 ? <MetaPill icon={<Tags size={14} />} text={journal.moodTags.join(" / ")} /> : null}
        </div>
      </div>
    </Link>
  );
}

type MetaPillProps = {
  icon: ReactNode;
  text: string;
};

function MetaPill({ icon, text }: MetaPillProps) {
  return (
    <span>
      {icon}
      {text}
    </span>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit" }).format(date);
}
