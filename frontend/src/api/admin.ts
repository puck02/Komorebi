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

export type AiConnectionTest = {
  ok: boolean;
  status: string;
  message: string;
  model: string;
  statusCode: number | null;
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

export function testAiConnection() {
  return apiRequest<AiConnectionTest>("/admin/ai-settings/test", {
    auth: true,
    method: "POST"
  });
}
