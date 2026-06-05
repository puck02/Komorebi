import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getAssetPermissions, getAssets, updateAssetQualityStatus } from "../api/assets";
import AssetCard from "../components/AssetCard";
import { Button } from "../components/ui/button";
import type { AssetQualityStatus } from "../types/asset";

const allValue = "all";

export default function AssetLibraryPage() {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState(allValue);
  const [status, setStatus] = useState(allValue);
  const [tag, setTag] = useState(allValue);
  const { data: assets = [], error, isLoading } = useQuery({ queryFn: getAssets, queryKey: ["assets"] });
  const permissionsQuery = useQuery({ queryFn: getAssetPermissions, queryKey: ["asset-permissions"] });
  const updateStatusMutation = useMutation({
    mutationFn: ({ assetId, qualityStatus }: { assetId: string; qualityStatus: AssetQualityStatus }) =>
      updateAssetQualityStatus(assetId, qualityStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    }
  });

  const categories = useMemo(() => [allValue, ...unique(assets.map((asset) => asset.category))], [assets]);
  const statuses = useMemo(() => [allValue, ...unique(assets.map((asset) => asset.quality_status))], [assets]);
  const tags = useMemo(() => [allValue, ...unique(assets.flatMap((asset) => asset.tags)).slice(0, 18)], [assets]);
  const statusCounts = useMemo(
    () => ({
      approved: assets.filter((asset) => asset.quality_status === "approved").length,
      draft: assets.filter((asset) => asset.quality_status === "draft").length,
      rejected: assets.filter((asset) => asset.quality_status === "rejected").length
    }),
    [assets]
  );

  const filteredAssets = assets.filter((asset) => {
    const matchesCategory = category === allValue || asset.category === category;
    const matchesStatus = status === allValue || asset.quality_status === status;
    const matchesTag = tag === allValue || asset.tags.includes(tag);
    return matchesCategory && matchesStatus && matchesTag;
  });

  return (
    <section className="asset-library-page">
      <div className="asset-library-header">
        <div className="asset-status-strip">
          <span data-status="approved">approved {statusCounts.approved}</span>
          <span data-status="draft">draft {statusCounts.draft}</span>
          <span data-status="rejected">rejected {statusCounts.rejected}</span>
        </div>
        <div className="asset-count">
          <strong>{filteredAssets.length}</strong> / {assets.length} assets
        </div>
      </div>

      <div className="asset-filter-panel">
        <FilterRow label="分类" options={categories} value={category} onChange={setCategory} />
        <FilterRow label="状态" options={statuses} value={status} onChange={setStatus} />
        <FilterRow label="标签" options={tags} value={tag} onChange={setTag} />
      </div>

      {isLoading ? <p className="asset-state-text">正在加载素材...</p> : null}
      {error instanceof Error ? <p className="asset-state-text is-error">{error.message}</p> : null}
      {!isLoading && filteredAssets.length === 0 ? <p className="asset-state-text">没有符合筛选条件的素材。</p> : null}

      <div className="asset-grid">
        {filteredAssets.map((asset) => (
          <AssetCard
            key={asset.id}
            asset={asset}
            canManage={permissionsQuery.data?.can_manage_assets ?? false}
            isUpdating={updateStatusMutation.isPending && updateStatusMutation.variables?.assetId === asset.id}
            onStatusChange={(qualityStatus) => updateStatusMutation.mutate({ assetId: asset.id, qualityStatus })}
          />
        ))}
      </div>
    </section>
  );
}

type FilterRowProps = {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
};

function FilterRow({ label, options, value, onChange }: FilterRowProps) {
  return (
    <div className="asset-filter-row">
      <span>{label}</span>
      <div>
        {options.map((option) => (
          <Button
            aria-pressed={value === option}
            key={option}
            size="sm"
            type="button"
            variant={value === option ? "selected" : "outline"}
            onClick={() => onChange(option)}
          >
            {option === allValue ? "全部" : option}
          </Button>
        ))}
      </div>
    </div>
  );
}

function unique(values: string[]) {
  return Array.from(new Set(values)).sort((first, second) => first.localeCompare(second));
}
