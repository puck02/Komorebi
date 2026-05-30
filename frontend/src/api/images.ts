import { apiRequest } from "./client";

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

  const token = localStorage.getItem("komorebi_access_token");
  const response = await fetch(`${API_BASE_URL}/images`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData
  });

  if (!response.ok) {
    throw new Error("图片上传失败");
  }

  return (await response.json()) as UploadedImage;
}

export async function getImage(imageId: string) {
  return apiRequest<UploadedImage>(`/images/${imageId}`, { auth: true });
}
