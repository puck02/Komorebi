import { useMemo, useState } from "react";
import { Filter, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { getAssets } from "../api/assets";
import AssetCard from "../components/AssetCard";
import { Button } from "../components/ui/button";

const allValue = "all";

export default function AssetLibraryPage() {
  const [category, setCategory] = useState(allValue);
  const [status, setStatus] = useState(allValue);
  const [tag, setTag] = useState(allValue);
  const { data: assets = [], error, isLoading } = useQuery({ queryFn: getAssets, queryKey: ["assets"] });

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
      <div className="flex flex-col gap-4 border-b border-[#d8cab8] pb-5 md:flex-row md:items-end md:justify-between">
        <div className="grid gap-2">
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#7b4e3d]">
            <Search size={16} />
            Asset Library
          </p>
          <h1 className="text-3xl font-semibold text-[#2f2924] md:text-4xl">素材库预览</h1>
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded-full bg-[#e5efe0] px-2.5 py-1 text-[#2f5632]">approved {statusCounts.approved}</span>
            <span className="rounded-full bg-[#f4ead2] px-2.5 py-1 text-[#76561d]">draft {statusCounts.draft}</span>
            <span className="rounded-full bg-[#f4dfdc] px-2.5 py-1 text-[#863d34]">rejected {statusCounts.rejected}</span>
          </div>
        </div>
        <div className="rounded-md border border-[#d8cab8] bg-[#fffaf5] px-4 py-3 text-sm text-[#51463e]">
          <strong className="text-[#263c3d]">{filteredAssets.length}</strong> / {assets.length} assets
        </div>
      </div>

      <div className="grid gap-4 rounded-md border border-[#d8cab8] bg-[#f8f1e8] p-4">
        <FilterRow label="分类" options={categories} value={category} onChange={setCategory} />
        <FilterRow label="状态" options={statuses} value={status} onChange={setStatus} />
        <FilterRow label="标签" options={tags} value={tag} onChange={setTag} />
      </div>

      {isLoading ? <p className="text-sm text-[#65584d]">正在加载素材...</p> : null}
      {error instanceof Error ? <p className="text-sm font-semibold text-[#9b332b]">{error.message}</p> : null}
      {!isLoading && filteredAssets.length === 0 ? <p className="text-sm text-[#65584d]">没有符合筛选条件的素材。</p> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filteredAssets.map((asset) => (
          <AssetCard key={asset.id} asset={asset} />
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
      <span className="text-sm font-semibold text-[#4d4239]">{label}</span>
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
