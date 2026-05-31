import { apiRequest } from "./client";
import type { Asset, AssetQualityStatus } from "../types/asset";

export function getAssets() {
  return apiRequest<Asset[]>("/assets");
}

export function getAssetPermissions() {
  return apiRequest<{ can_manage_assets: boolean }>("/assets/permissions/me", { auth: true });
}

export function updateAssetQualityStatus(assetId: string, qualityStatus: AssetQualityStatus) {
  return apiRequest<Asset>(`/assets/${assetId}/quality-status`, {
    auth: true,
    body: JSON.stringify({ quality_status: qualityStatus }),
    method: "PATCH"
  });
}
