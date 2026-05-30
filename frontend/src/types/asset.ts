export type AssetQualityStatus = "approved" | "draft" | "rejected";

export type Asset = {
  id: string;
  name: string;
  category: string;
  tags: string[];
  style: string[];
  colors: string[];
  file: string;
  file_url: string;
  license: string;
  source: string;
  quality_status: AssetQualityStatus;
};
