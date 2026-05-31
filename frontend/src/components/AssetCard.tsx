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
    tone: "bg-[#ffcdb2] text-[#6d6875]"
  },
  draft: {
    icon: CircleDashed,
    label: "draft",
    tone: "bg-[#ffb4a2] text-[#6d6875]"
  },
  rejected: {
    icon: CircleSlash,
    label: "rejected",
    tone: "bg-[#e5989b] text-[#fff8f4]"
  }
};

export default function AssetCard({ asset }: Props) {
  const status = statusMeta[asset.quality_status];
  const StatusIcon = status.icon;

  return (
    <Card className="overflow-hidden">
      <div className="grid aspect-[4/3] place-items-center border-b border-[#ffb4a2] bg-[linear-gradient(135deg,#fff3ed,#ffcdb2)] p-5">
        <img className="max-h-full max-w-full drop-shadow-[0_8px_14px_rgba(109,104,117,0.14)]" src={asset.file_url} alt={asset.name} />
      </div>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle>{asset.name}</CardTitle>
          <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${status.tone}`}>
            <StatusIcon size={13} />
            {status.label}
          </span>
        </div>
        <p className="text-xs uppercase tracking-[0.18em] text-[#b5838d]">{asset.category}</p>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="flex flex-wrap gap-1.5">
          {asset.tags.slice(0, 5).map((tag) => (
            <span key={tag} className="rounded-full bg-[#ffcdb2]/60 px-2 py-1 text-xs text-[#6d6875]">
              {tag}
            </span>
          ))}
        </div>
        <dl className="grid gap-1 text-xs text-[#6d6875]">
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
