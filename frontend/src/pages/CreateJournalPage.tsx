import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { CalendarDays, LayoutTemplate, MapPin, Sparkles, Tags } from "lucide-react";
import { useEffect, useMemo, useReducer, useState } from "react";
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
import {
  JOURNAL_TEMPLATES,
  limitTemplateRecommendations,
  recommendLocalJournalTemplates,
  TEMPLATE_RECOMMENDATION_COUNT,
  type JournalTemplateRecommendation
} from "./journalTemplates";
import {
  createTemplateRecommendationRequestKey,
  initialTemplateRecommendationState,
  mergeServerTemplateRecommendations,
  templateRecommendationReducer
} from "./templateRecommendationState";

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
  const [templateRecommendationState, dispatchTemplateRecommendation] = useReducer(
    templateRecommendationReducer,
    initialTemplateRecommendationState
  );
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
  const recommendedTemplates = limitTemplateRecommendations(
    templateRecommendationState.serverRecommendedTemplates ?? localRecommendedTemplates
  );
  const recommendTemplatesMutation = useMutation({
    mutationFn: ({
      requestKey,
      ...payload
    }: Parameters<typeof recommendJournalTemplatesFromServer>[0] & { requestKey: string }) =>
      recommendJournalTemplatesFromServer(payload).then((result) => ({ requestKey, result }))
  });
  const { mutate: recommendTemplates } = recommendTemplatesMutation;

  useEffect(() => {
    if (!recommendedTemplates.some((template) => template.id === selectedTemplateId)) {
      setSelectedTemplateId(recommendedTemplates[0]?.id ?? JOURNAL_TEMPLATES[0].id);
    }
  }, [recommendedTemplates, selectedTemplateId]);

  useEffect(() => {
    const imageIds = images.map((image) => image.id);
    const requestKey = createTemplateRecommendationRequestKey(imageIds, descriptionValue || "", selectedMood);
    if (images.length === 0) {
      dispatchTemplateRecommendation({ requestKey, type: "localOnly" });
      return;
    }
    dispatchTemplateRecommendation({ requestKey, type: "requestStarted" });
    const timeoutId = window.setTimeout(() => {
      recommendTemplates({
        description: descriptionValue || "",
        imageIds,
        moodTags: selectedMood ? [selectedMood] : [],
        requestKey
      }, {
        onError: (_error, variables) => {
          dispatchTemplateRecommendation({
            requestKey: variables.requestKey,
            type: "requestFailed"
          });
        },
        onSuccess: (mutationData) => {
          dispatchTemplateRecommendation({
            message: mutationData.result.message,
            recommendations: mergeServerTemplateRecommendations(mutationData.result),
            requestKey: mutationData.requestKey,
            source: mutationData.result.source,
            type: "requestSucceeded"
          });
        }
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
              选择故事模板
            </span>
            <div className="template-recommendation-status">
              {templateRecommendationState.isPending
                ? "正在结合图片内容推荐..."
                : templateRecommendationState.recommendationSource === "ai"
                  ? `已根据图片内容推荐 ${TEMPLATE_RECOMMENDATION_COUNT} 个不同讲法`
                  : templateRecommendationState.recommendationMessage ||
                    `先按照片数量和描述推荐 ${TEMPLATE_RECOMMENDATION_COUNT} 个故事模板，上传后会结合图片内容更新。`}
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
                  <TemplatePreview template={template} />
                  <span className="template-source">{template.sourcePattern}</span>
                  <span className="template-card-copy">
                    <strong>{template.name}</strong>
                    <small>{template.shortDescription}</small>
                    <span className="template-best-for">{template.bestFor}</span>
                  </span>
                  <span className="template-structure">{template.structureLabel}</span>
                  <span className="template-beats">
                    {template.storyBeats.map((beat) => (
                      <i key={beat}>{beat}</i>
                    ))}
                  </span>
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

function TemplatePreview({ template }: { template: JournalTemplateRecommendation }) {
  return (
    <span className={`template-preview ${template.previewClassName}`} aria-hidden="true">
      {template.previewItems.map((item, index) => (
        <i
          className={`is-${item.kind}`}
          key={`${item.kind}-${index}`}
          style={{
            height: item.height,
            left: item.x,
            top: item.y,
            transform: item.rotate ? `rotate(${item.rotate}deg)` : undefined,
            width: item.width
          }}
        />
      ))}
    </span>
  );
}
