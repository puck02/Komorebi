import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { CalendarDays, LayoutTemplate, MapPin, Sparkles, Tags } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { createGenerationJob } from "../api/generationJobs";
import type { UploadedImage } from "../api/images";
import { recommendJournalTemplates as recommendJournalTemplatesFromServer } from "../api/journals";
import ImageUploader from "../components/ImageUploader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { CREATE_JOURNAL_MOOD_OPTIONS } from "./createJournalOptions";
import { generationJobErrorMessage, generationJobRouteAfterCreate } from "./generationJobStatus";
import { JOURNAL_TEMPLATES, recommendLocalJournalTemplates, type JournalTemplateRecommendation } from "./journalTemplates";

const createJournalSchema = z.object({
  description: z.string().trim().min(1, "请写一点今天的内容。"),
  journalDate: z.string().optional(),
  location: z.string().optional()
});

type CreateJournalValues = z.infer<typeof createJournalSchema>;

export default function CreateJournalPage() {
  const navigate = useNavigate();
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [imageError, setImageError] = useState("");
  const [isMoodPickerOpen, setIsMoodPickerOpen] = useState(false);
  const [selectedMood, setSelectedMood] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState(JOURNAL_TEMPLATES[0].id);
  const [serverRecommendedTemplates, setServerRecommendedTemplates] = useState<JournalTemplateRecommendation[] | null>(null);
  const [recommendationSource, setRecommendationSource] = useState<"ai" | "local" | null>(null);
  const [recommendationMessage, setRecommendationMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState("");
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    watch
  } = useForm<CreateJournalValues>({
    defaultValues: {
      description: "",
      journalDate: "",
      location: ""
    },
    resolver: zodResolver(createJournalSchema)
  });
  const descriptionValue = watch("description");
  const localRecommendedTemplates = useMemo(
    () => recommendLocalJournalTemplates(images, descriptionValue, selectedMood),
    [descriptionValue, images, selectedMood]
  );
  const recommendedTemplates = serverRecommendedTemplates ?? localRecommendedTemplates;
  const recommendTemplatesMutation = useMutation({
    mutationFn: recommendJournalTemplatesFromServer,
    onSuccess: (result) => {
      const mergedRecommendations = result.recommendations
        .map((recommendation) => {
          const template = JOURNAL_TEMPLATES.find((item) => item.id === recommendation.templateId);
          if (!template) {
            return null;
          }
          return {
            ...template,
            recommendationReason: recommendation.reason,
            storyArc: recommendation.storyArc
          };
        })
        .filter((template): template is JournalTemplateRecommendation => template !== null);
      setServerRecommendedTemplates(mergedRecommendations.length ? mergedRecommendations : null);
      setRecommendationSource(result.source);
      setRecommendationMessage(result.message);
    },
    onError: () => {
      setServerRecommendedTemplates(null);
      setRecommendationSource("local");
      setRecommendationMessage("模板推荐服务暂不可用，已按本地规则推荐。");
    }
  });
  const { mutate: recommendTemplates } = recommendTemplatesMutation;

  useEffect(() => {
    if (!recommendedTemplates.some((template) => template.id === selectedTemplateId)) {
      setSelectedTemplateId(recommendedTemplates[0]?.id ?? JOURNAL_TEMPLATES[0].id);
    }
  }, [recommendedTemplates, selectedTemplateId]);

  useEffect(() => {
    setServerRecommendedTemplates(null);
    setRecommendationSource(null);
    setRecommendationMessage(null);
    if (images.length === 0) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      recommendTemplates({
        description: descriptionValue || "",
        imageIds: images.map((image) => image.id),
        moodTags: selectedMood ? [selectedMood] : []
      });
    }, 420);
    return () => window.clearTimeout(timeoutId);
  }, [descriptionValue, images, recommendTemplates, selectedMood]);

  async function onSubmit(values: CreateJournalValues) {
    setImageError("");
    setSubmitError("");

    if (images.length === 0) {
      setImageError("请先上传 1 张图片。");
      return;
    }

    try {
      const job = await createGenerationJob({
        description: values.description,
        imageIds: images.map((image) => image.id),
        journalDate: values.journalDate || null,
        location: values.location?.trim() || null,
        moodTags: selectedMood ? [selectedMood] : [],
        templateId: selectedTemplateId
      });
      const route = generationJobRouteAfterCreate(job);
      if (route) {
        navigate(route);
        return;
      }
      setSubmitError(generationJobErrorMessage(job, null) ?? "生成任务启动失败，请稍后重试。");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "生成失败，请稍后重试。");
    }
  }

  return (
    <section className="create-page">
      <header className="create-studio-hero">
        <div className="create-studio-copy">
          <p className="eyebrow">Komorebi studio</p>
          <h1>
            把今天摊开，<span>整理成一页手帐</span>
          </h1>
          <p>先放入几张照片，再写下当天的片段。Komorebi 会把这些素材整理成温柔的拼贴页面。</p>
        </div>
        <div className="create-preview-paper" aria-hidden="true">
          <div className="preview-tape preview-tape-top" />
          <div className="preview-paper-title" />
          <div className="preview-photo-stack">
            <span className="preview-photo is-main" />
            <span className="preview-photo is-side" />
          </div>
          <div className="preview-note-lines">
            <span />
            <span />
            <span />
          </div>
          <div className="preview-sticker" />
        </div>
      </header>

      <form className="create-layout" onSubmit={handleSubmit(onSubmit)}>
        <div className="create-panel create-photo-panel">
          <div className="create-panel-heading">
            <p>照片投放区</p>
            <span>{images.length}/9</span>
          </div>
          <ImageUploader onUploaded={setImages} />
          {imageError ? <p className="form-error">{imageError}</p> : null}
        </div>

        <div className="create-panel create-form-panel create-note-panel">
          <div className="create-panel-heading">
            <p>记录纸</p>
            <span>{selectedMood || "未选择心情"}</span>
          </div>
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

          <div className="field-label mood-field">
            <span>
              <Tags size={15} />
              心情
            </span>
            <button
              aria-expanded={isMoodPickerOpen}
              className="mood-picker-trigger"
              onClick={() => setIsMoodPickerOpen((isOpen) => !isOpen)}
              type="button"
            >
              <span>{selectedMood || "选择一个心情"}</span>
            </button>
            {isMoodPickerOpen ? (
              <div className="mood-picker" role="listbox" aria-label="选择心情">
                {CREATE_JOURNAL_MOOD_OPTIONS.map((mood) => (
                  <button
                    aria-selected={selectedMood === mood}
                    className={selectedMood === mood ? "is-selected" : ""}
                    key={mood}
                    onClick={() => {
                      setSelectedMood(mood);
                      setIsMoodPickerOpen(false);
                    }}
                    role="option"
                    type="button"
                  >
                    {mood}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <div className="field-label template-field">
            <span>
              <LayoutTemplate size={15} />
              推荐模板
            </span>
            <div className="template-recommendation-status">
              {recommendTemplatesMutation.isPending
                ? "正在结合图片内容推荐..."
                : recommendationSource === "ai"
                  ? "已根据图片内容推荐"
                  : recommendationMessage || "先按照片数量和描述推荐，上传后会结合图片内容更新。"}
            </div>
            <div className="template-picker" role="radiogroup" aria-label="选择手帐模板">
              {recommendedTemplates.map((template) => (
                <button
                  aria-checked={selectedTemplateId === template.id}
                  className={selectedTemplateId === template.id ? "is-selected" : ""}
                  key={template.id}
                  onClick={() => setSelectedTemplateId(template.id)}
                  role="radio"
                  type="button"
                >
                  <span className={`template-preview ${template.previewClassName}`} aria-hidden="true">
                    <i />
                    <i />
                    <i />
                    <i />
                  </span>
                  <strong>{template.name}</strong>
                  <small>{template.shortDescription}</small>
                  <em>{template.bestFor}</em>
                  <span className="template-story">{template.storyArc}</span>
                  <span className="template-reason">{template.recommendationReason}</span>
                </button>
              ))}
            </div>
          </div>

          {submitError ? <p className="form-error">{submitError}</p> : null}
          <Button className="create-submit" disabled={isSubmitting} type="submit">
            <Sparkles size={17} />
            {isSubmitting ? "正在准备..." : "生成手帐"}
          </Button>
        </div>
      </form>
    </section>
  );
}
