import { useMemo, useState } from "react";
import { Filter } from "lucide-react";
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
    <section className="mx-auto grid w-full max-w-7xl gap-6 px-5 py-8">
      <div className="flex flex-col gap-4 border-b border-[#f3d2c1] pb-5 md:flex-row md:items-end md:justify-between">
        <div className="grid gap-2">
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded-full bg-[#fef6e4] px-2.5 py-1 text-[#001858]">approved {statusCounts.approved}</span>
            <span className="rounded-full bg-[#f3d2c1] px-2.5 py-1 text-[#001858]">draft {statusCounts.draft}</span>
            <span className="rounded-full bg-[#8bd3dd] px-2.5 py-1 text-[#001858]">rejected {statusCounts.rejected}</span>
          </div>
        </div>
        <div className="rounded-md border border-[#f3d2c1] bg-[#fef6e4] px-4 py-3 text-sm text-[#172c66]">
          <strong className="text-[#f582ae]">{filteredAssets.length}</strong> / {assets.length} assets
        </div>
      </div>

      <div className="grid gap-4 rounded-md border border-[#f3d2c1] bg-[#fef6e4] p-4">
        <FilterRow label="分类" options={categories} value={category} onChange={setCategory} />
        <FilterRow label="状态" options={statuses} value={status} onChange={setStatus} />
        <FilterRow label="标签" options={tags} value={tag} onChange={setTag} />
      </div>

      {isLoading ? <p className="text-sm text-[#172c66]">正在加载素材...</p> : null}
      {error instanceof Error ? <p className="text-sm font-semibold text-[#f582ae]">{error.message}</p> : null}
      {!isLoading && filteredAssets.length === 0 ? <p className="text-sm text-[#172c66]">没有符合筛选条件的素材。</p> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
    <div className="grid gap-2 md:grid-cols-[72px_1fr] md:items-center">
      <span className="text-sm font-semibold text-[#001858]">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <Button
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
