import { ArrowLeft, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getGenerationJob } from "../api/generationJobs";
import { Button } from "../components/ui/button";

const STAGE_LABELS: Record<string, string> = {
  queued: "正在准备照片",
  understanding_photos: "正在理解照片",
  generating_draft: "正在生成初稿",
  reviewing: "正在检查排版",
  reviewed: "正在检查排版",
  revising: "正在调整细节",
  completed: "正在保存手帐",
  failed: "生成失败"
};

export default function GenerationJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const jobQuery = useQuery({
    enabled: Boolean(jobId),
    queryFn: () => getGenerationJob(jobId as string),
    queryKey: ["generation-job", jobId],
    refetchInterval: (query) => (query.state.data?.status === "completed" || query.state.data?.status === "failed" ? false : 2000)
  });

  useEffect(() => {
    const job = jobQuery.data;
    if (job?.status === "completed" && job.journalId) {
      navigate(`/journals/${job.journalId}`, { replace: true });
    }
  }, [jobQuery.data, navigate]);

  const job = jobQuery.data;
  const stage = job?.stage ?? "queued";
  const stageLabel = STAGE_LABELS[stage] ?? "正在精修手帐";
  const revisionLabel = stage === "revising" && job ? ` · 第 ${job.revisionRound}/${job.maxRevisionRounds} 轮` : "";

  return (
    <section className="generation-page">
      <div className="generation-panel">
        <div className="generation-paper-preview" aria-hidden="true">
          <span className="generation-paper-tape" />
          <span className="generation-paper-photo" />
          <span className="generation-paper-line" />
          <span className="generation-paper-line is-short" />
        </div>
        <div className="generation-mark" aria-hidden="true">
          <Sparkles size={26} />
        </div>
        {jobQuery.isError || job?.status === "failed" ? (
          <>
            <h1>这次没有生成成功</h1>
            <p>{job?.errorMessage ?? (jobQuery.error instanceof Error ? jobQuery.error.message : "请稍后重新生成。")}</p>
            <Button asChild variant="ghost">
              <Link to="/">
                <ArrowLeft size={16} />
                返回创建
              </Link>
            </Button>
          </>
        ) : (
          <>
            <p className="generation-eyebrow">Binding journal</p>
            <h1>{stageLabel}{revisionLabel}</h1>
            <p>照片、文字和小元素正在逐步调整，完成后会自动打开手帐。</p>
            <div className="generation-progress" aria-label="正在生成">
              <span />
            </div>
          </>
        )}
      </div>
    </section>
  );
}
