import { apiRequest } from "./client";
import type { Asset } from "../types/asset";

export function getAssets() {
  return apiRequest<Asset[]>("/assets");
}
