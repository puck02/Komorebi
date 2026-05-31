import { BadgeCheck, CircleDashed, CircleSlash } from "lucide-react";
import { useState } from "react";

import type { Asset, AssetQualityStatus } from "../types/asset";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  asset: Asset;
  canManage?: boolean;
  isUpdating?: boolean;
  onStatusChange?: (qualityStatus: AssetQualityStatus) => void;
};

const statusMeta = {
  approved: {
    icon: BadgeCheck,
    label: "approved",
    tone: "bg-[#fef6e4] text-[#001858]"
  },
  draft: {
    icon: CircleDashed,
    label: "draft",
    tone: "bg-[#f3d2c1] text-[#001858]"
  },
  rejected: {
    icon: CircleSlash,
    label: "rejected",
    tone: "bg-[#8bd3dd] text-[#001858]"
  }
} satisfies Record<AssetQualityStatus, { icon: typeof BadgeCheck; label: string; tone: string }>;

const statusOptions: AssetQualityStatus[] = ["draft", "approved"];

export default function AssetCard({ asset, canManage = false, isUpdating = false, onStatusChange }: Props) {
  const [isStatusMenuOpen, setIsStatusMenuOpen] = useState(false);
  const status = statusMeta[asset.quality_status];
  const StatusIcon = status.icon;

  return (
    <Card
      className={`overflow-hidden ${canManage ? "cursor-pointer transition-transform hover:-translate-y-0.5" : ""}`}
      onClick={() => {
        if (canManage) {
          setIsStatusMenuOpen((isOpen) => !isOpen);
        }
      }}
      onKeyDown={(event) => {
        if (!canManage || (event.key !== "Enter" && event.key !== " ")) {
          return;
        }
        event.preventDefault();
        setIsStatusMenuOpen((isOpen) => !isOpen);
      }}
      role={canManage ? "button" : undefined}
      tabIndex={canManage ? 0 : undefined}
    >
      <div className="grid aspect-[4/3] place-items-center border-b border-[#f3d2c1] bg-[linear-gradient(135deg,#fef6e4,#f3d2c1)] p-5">
        <img className="max-h-full max-w-full drop-shadow-[0_8px_14px_rgba(0,24,88,0.14)]" src={asset.file_url} alt={asset.name} />
      </div>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle>{asset.name}</CardTitle>
          <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${status.tone}`}>
            <StatusIcon size={13} />
            {status.label}
          </span>
        </div>
        <p className="text-xs uppercase tracking-[0.18em] text-[#f582ae]">{asset.category}</p>
      </CardHeader>
      <CardContent className="grid gap-3">
        {canManage && isStatusMenuOpen ? (
          <div className="grid gap-2 rounded-md border border-[#f3d2c1] bg-[#fef6e4]/80 p-2">
            <span className="text-xs font-semibold text-[#172c66]">状态</span>
            <div className="flex gap-2">
              {statusOptions.map((option) => (
                <button
                  className={`min-h-8 flex-1 rounded-md border px-2 text-xs font-semibold ${
                    asset.quality_status === option
                      ? "border-[#f582ae] bg-[#f582ae] text-[#001858]"
                      : "border-[#f3d2c1] bg-[#fef6e4] text-[#001858]"
                  }`}
                  disabled={isUpdating || asset.quality_status === option}
                  key={option}
                  onClick={(event) => {
                    event.stopPropagation();
                    onStatusChange?.(option);
                  }}
                  type="button"
                >
                  {isUpdating && asset.quality_status !== option ? "更新中..." : option}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-1.5">
          {asset.tags.slice(0, 5).map((tag) => (
            <span key={tag} className="rounded-full bg-[#fef6e4]/60 px-2 py-1 text-xs text-[#001858]">
              {tag}
            </span>
          ))}
        </div>
        <dl className="grid gap-1 text-xs text-[#172c66]">
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
