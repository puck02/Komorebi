import { apiRequest } from "./client";

export type AdminPermissions = {
  canManageAiSettings: boolean;
};

export type AiSettings = {
  baseUrl: string;
  hasApiKey: boolean;
  model: string;
  reviewModel: string;
};

export type AiSettingsUpdate = {
  baseUrl: string;
  apiKey?: string;
  model: string;
  reviewModel: string;
};

export function getAdminPermissions() {
  return apiRequest<AdminPermissions>("/admin/permissions/me", { auth: true });
}

export function getAiSettings() {
  return apiRequest<AiSettings>("/admin/ai-settings", { auth: true });
}

export function updateAiSettings(payload: AiSettingsUpdate) {
  return apiRequest<AiSettings>("/admin/ai-settings", {
    auth: true,
    body: JSON.stringify(payload),
    method: "PATCH"
  });
}
