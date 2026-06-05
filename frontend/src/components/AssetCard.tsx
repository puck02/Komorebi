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
    tone: "is-approved"
  },
  draft: {
    icon: CircleDashed,
    label: "draft",
    tone: "is-draft"
  },
  rejected: {
    icon: CircleSlash,
    label: "rejected",
    tone: "is-rejected"
  }
} satisfies Record<AssetQualityStatus, { icon: typeof BadgeCheck; label: string; tone: string }>;

const statusOptions: AssetQualityStatus[] = ["draft", "approved"];

export default function AssetCard({ asset, canManage = false, isUpdating = false, onStatusChange }: Props) {
  const [isStatusMenuOpen, setIsStatusMenuOpen] = useState(false);
  const status = statusMeta[asset.quality_status];
  const StatusIcon = status.icon;

  return (
    <Card className={`asset-card ${canManage ? "is-manageable" : ""}`}>
      <div className="asset-card-preview">
        <img src={asset.file_url} alt={asset.name} />
      </div>
      <CardHeader>
        <div className="asset-card-title-row">
          <div className="asset-card-title-group">
            <CardTitle>{asset.name}</CardTitle>
            <span className={`asset-status-pill ${status.tone}`}>
              <StatusIcon size={13} />
              {status.label}
            </span>
          </div>
          {canManage ? (
            <button
              aria-expanded={isStatusMenuOpen}
              className="asset-manage-trigger"
              disabled={isUpdating}
              onClick={() => setIsStatusMenuOpen((isOpen) => !isOpen)}
              type="button"
            >
              更改状态
            </button>
          ) : null}
        </div>
        <p className="asset-category">{asset.category}</p>
      </CardHeader>
      <CardContent className="asset-card-content">
        {canManage && isStatusMenuOpen ? (
          <div className="asset-status-menu">
            <span>状态</span>
            <div>
              {statusOptions.map((option) => (
                <button
                  aria-pressed={asset.quality_status === option}
                  className={asset.quality_status === option ? "is-selected" : ""}
                  disabled={isUpdating || asset.quality_status === option}
                  key={option}
                  onClick={() => onStatusChange?.(option)}
                  type="button"
                >
                  {isUpdating && asset.quality_status !== option ? "更新中..." : option}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="asset-tags">
          {asset.tags.slice(0, 5).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
        <dl className="asset-meta-list">
          <div>
            <dt>license</dt>
            <dd>{asset.license}</dd>
          </div>
          <div>
            <dt>source</dt>
            <dd>{asset.source}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
