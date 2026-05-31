import { apiRequest, getAccessToken } from "./client";

export type UploadedImage = {
  id: string;
  content_type: string;
  width: number;
  height: number;
  file_url: string;
  thumbnail_url: string;
  created_at: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function uploadImage(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const token = getAccessToken();
  if (!token) {
    throw new Error("请先登录后再上传图片。");
  }

  const response = await fetch(`${API_BASE_URL}/images`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData
  });

  if (!response.ok) {
    throw new Error(await readUploadError(response));
  }

  return (await response.json()) as UploadedImage;
}

export async function getImage(imageId: string) {
  return apiRequest<UploadedImage>(`/images/${imageId}`, { auth: true });
}

async function readUploadError(response: Response) {
  if (response.status === 401) {
    return "请先登录后再上传图片。";
  }

  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? "图片上传失败";
  } catch {
    return "图片上传失败";
  }
}
