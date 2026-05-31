import { ChangeEvent, useEffect, useRef, useState } from "react";

import { UploadedImage, uploadImage } from "../api/images";

type Props = {
  onUploaded?: (images: UploadedImage[]) => void;
};

export default function ImageUploader({ onUploaded }: Props) {
  const [images, setImages] = useState<UploadedImagePreview[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const previewUrls = useRef(new Set<string>());

  useEffect(() => {
    return () => {
      previewUrls.current.forEach((previewUrl) => URL.revokeObjectURL(previewUrl));
      previewUrls.current.clear();
    };
  }, []);

  async function handleFilesChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    const uploadableFiles = selectedFiles.filter(isSupportedImageFile);
    setError("");

    if (selectedFiles.length === 0) {
      return;
    }

    if (uploadableFiles.length === 0) {
      setError("暂支持 JPG、PNG、WebP 图片。");
      event.target.value = "";
      return;
    }

    if (images.length + uploadableFiles.length > 9) {
      setError("最多上传 9 张图片。");
      event.target.value = "";
      return;
    }

    if (uploadableFiles.length < selectedFiles.length) {
      setError("已跳过暂不支持的图片格式，仅上传 JPG、PNG、WebP。");
    }

    const selectedPreviews = uploadableFiles.map((file) => ({
      file,
      previewUrl: URL.createObjectURL(file)
    }));
    selectedPreviews.forEach(({ previewUrl }) => previewUrls.current.add(previewUrl));

    setIsUploading(true);
    try {
      const uploadedImages = await Promise.all(
        selectedPreviews.map(async ({ file, previewUrl }) => ({
          ...(await uploadImage(file)),
          preview_url: previewUrl
        }))
      );
      const nextImages = [...images, ...uploadedImages];
      setImages(nextImages);
      onUploaded?.(nextImages);
    } catch (caughtError) {
      selectedPreviews.forEach(({ previewUrl }) => {
        URL.revokeObjectURL(previewUrl);
        previewUrls.current.delete(previewUrl);
      });
      setError(caughtError instanceof Error ? caughtError.message : "图片上传失败");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  function removeImage(imageId: string) {
    const removedImage = images.find((image) => image.id === imageId);
    if (removedImage) {
      URL.revokeObjectURL(removedImage.preview_url);
      previewUrls.current.delete(removedImage.preview_url);
    }
    const nextImages = images.filter((image) => image.id !== imageId);
    setImages(nextImages);
    onUploaded?.(nextImages);
  }

  return (
    <section className="image-uploader">
      <label className={`upload-zone ${isUploading ? "is-disabled" : ""}`}>
        <span>{isUploading ? "上传中..." : "选择多张图片"}</span>
        <input
          accept="image/*,.jpg,.jpeg,.png,.webp"
          aria-label="选择多张图片"
          className="upload-input"
          disabled={isUploading}
          multiple
          onChange={handleFilesChange}
          type="file"
        />
      </label>
      {error ? <p className="form-error">{error}</p> : null}
      <div className="upload-grid">
        {images.map((image) => (
          <figure key={image.id}>
            <img alt="" src={image.preview_url} />
            <button type="button" onClick={() => removeImage(image.id)}>
              删除
            </button>
          </figure>
        ))}
      </div>
    </section>
  );
}

type UploadedImagePreview = UploadedImage & {
  preview_url: string;
};

function isSupportedImageFile(file: File) {
  return ["image/jpeg", "image/png", "image/webp"].includes(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name);
}
