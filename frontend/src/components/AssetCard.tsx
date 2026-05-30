import { BadgeCheck, CircleDashed, CircleSlash } from "lucide-react";

import type { Asset } from "../types/asset";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  asset: Asset;
};

const statusMeta = {
  approved: {
    icon: BadgeCheck,
    label: "approved",
    tone: "bg-[#e5efe0] text-[#2f5632]"
  },
  draft: {
    icon: CircleDashed,
    label: "draft",
    tone: "bg-[#f4ead2] text-[#76561d]"
  },
  rejected: {
    icon: CircleSlash,
    label: "rejected",
    tone: "bg-[#f4dfdc] text-[#863d34]"
  }
};

export default function AssetCard({ asset }: Props) {
  const status = statusMeta[asset.quality_status];
  const StatusIcon = status.icon;

  return (
    <Card className="overflow-hidden">
      <div className="grid aspect-[4/3] place-items-center border-b border-[#eadccc] bg-[linear-gradient(135deg,#fffaf4,#eef4e8)] p-5">
        <img className="max-h-full max-w-full drop-shadow-[0_8px_14px_rgba(75,57,43,0.12)]" src={asset.file_url} alt={asset.name} />
      </div>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle>{asset.name}</CardTitle>
          <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${status.tone}`}>
            <StatusIcon size={13} />
            {status.label}
          </span>
        </div>
        <p className="text-xs uppercase tracking-[0.18em] text-[#7b6b5f]">{asset.category}</p>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="flex flex-wrap gap-1.5">
          {asset.tags.slice(0, 5).map((tag) => (
            <span key={tag} className="rounded-full bg-[#efe3d6] px-2 py-1 text-xs text-[#5b4d42]">
              {tag}
            </span>
          ))}
        </div>
        <dl className="grid gap-1 text-xs text-[#68594e]">
          <div className="flex justify-between gap-3">
            <dt>license</dt>
            <dd className="truncate font-semibold">{asset.license}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>source</dt>
            <dd className="truncate font-semibold">{asset.source}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
