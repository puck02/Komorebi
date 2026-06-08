import type { GenerationJob } from "../api/generationJobs";

export function generationJobRouteAfterCreate(job: GenerationJob): string | null {
  if (job.status === "failed") {
    return null;
  }
  return `/generation/${job.id}`;
}

export function generationJobErrorMessage(job: GenerationJob | null | undefined, queryError: unknown): string | null {
  if (job?.status === "failed") {
    return normalizeGenerationFailureMessage(job.errorMessage);
  }
  if (job?.status === "completed" && !job.journalId) {
    return "手帐已生成，但没有拿到保存后的入口。请返回后重新生成。";
  }
  if (queryError instanceof Error) {
    return queryError.message;
  }
  if (queryError) {
    return "请稍后重新生成。";
  }
  return null;
}

function normalizeGenerationFailureMessage(message: string | null): string {
  if (!message) {
    return "请稍后重新生成。";
  }
  if (message.includes("AI服务") || message.includes("AI 服务") || message.includes("OPENAI_API_KEY")) {
    return "AI 暂时不可用，请返回后重新生成。";
  }
  return message;
}
