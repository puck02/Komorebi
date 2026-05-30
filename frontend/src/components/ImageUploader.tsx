import { ChangeEvent, useState } from "react";

import { UploadedImage, uploadImage } from "../api/images";

type Props = {
  onUploaded?: (images: UploadedImage[]) => void;
};

export default function ImageUploader({ onUploaded }: Props) {
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  async function handleFilesChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    setError("");

    if (selectedFiles.length === 0) {
      return;
    }

    if (images.length + selectedFiles.length > 9) {
      setError("最多上传 9 张图片。");
      return;
    }

    setIsUploading(true);
    try {
      const uploadedImages = await Promise.all(selectedFiles.map((file) => uploadImage(file)));
      const nextImages = [...images, ...uploadedImages];
      setImages(nextImages);
      onUploaded?.(nextImages);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "图片上传失败");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  function removeImage(imageId: string) {
    const nextImages = images.filter((image) => image.id !== imageId);
    setImages(nextImages);
    onUploaded?.(nextImages);
  }

  return (
    <section className="image-uploader">
      <label className="upload-zone">
        <span>{isUploading ? "上传中..." : "选择图片"}</span>
        <input
          accept="image/jpeg,image/png,image/webp"
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
            <img alt="" src={image.thumbnail_url} />
            <button type="button" onClick={() => removeImage(image.id)}>
              删除
            </button>
          </figure>
        ))}
      </div>
    </section>
  );
}
