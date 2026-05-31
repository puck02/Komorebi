import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarDays, MapPin, Sparkles, Tags } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { generateJournal } from "../api/journals";
import type { UploadedImage } from "../api/images";
import ImageUploader from "../components/ImageUploader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

const createJournalSchema = z.object({
  description: z.string().trim().min(1, "请写一点今天的内容。"),
  journalDate: z.string().optional(),
  location: z.string().optional(),
  moodTags: z.string().optional()
});

type CreateJournalValues = z.infer<typeof createJournalSchema>;

export default function CreateJournalPage() {
  const navigate = useNavigate();
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [imageError, setImageError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register
  } = useForm<CreateJournalValues>({
    defaultValues: {
      description: "",
      journalDate: "",
      location: "",
      moodTags: ""
    },
    resolver: zodResolver(createJournalSchema)
  });

  async function onSubmit(values: CreateJournalValues) {
    setImageError("");
    setSubmitError("");

    if (images.length === 0) {
      setImageError("请先上传 1 张图片。");
      return;
    }

    try {
      const journal = await generateJournal({
        description: values.description,
        imageIds: images.map((image) => image.id),
        journalDate: values.journalDate || null,
        location: values.location?.trim() || null,
        moodTags: parseMoodTags(values.moodTags)
      });
      navigate(`/journals/${journal.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "生成失败，请稍后重试。");
    }
  }

  return (
    <section className="create-page">
      <div className="create-header">
        <p className="eyebrow">Create Journal</p>
        <h1>生成一页新的手帐</h1>
      </div>

      <form className="create-layout" onSubmit={handleSubmit(onSubmit)}>
        <div className="create-panel">
          <ImageUploader onUploaded={setImages} />
          {imageError ? <p className="form-error">{imageError}</p> : null}
        </div>

        <div className="create-panel create-form-panel">
          <label className="field-label">
            <span>描述</span>
            <textarea
              className="textarea-field"
              rows={8}
              placeholder="比如：周末一起去散步，喝了咖啡，傍晚的风很舒服。"
              {...register("description")}
            />
          </label>
          {errors.description?.message ? <p className="form-error">{errors.description.message}</p> : null}

          <div className="field-grid">
            <label className="field-label">
              <span>
                <CalendarDays size={15} />
                日期
              </span>
              <Input type="date" {...register("journalDate")} />
            </label>
            <label className="field-label">
              <span>
                <MapPin size={15} />
                地点
              </span>
              <Input placeholder="可选" {...register("location")} />
            </label>
          </div>

          <label className="field-label">
            <span>
              <Tags size={15} />
              心情标签
            </span>
            <Input placeholder="温柔, 开心, 慢下来" {...register("moodTags")} />
          </label>

          {submitError ? <p className="form-error">{submitError}</p> : null}
          <Button className="create-submit" disabled={isSubmitting} type="submit">
            <Sparkles size={17} />
            {isSubmitting ? "正在生成手帐..." : "生成手帐"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function parseMoodTags(value?: string) {
  return (value ?? "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}
