import type { GenerationJob } from "../api/generationJobs";

export function generationJobErrorMessage(job: GenerationJob | null | undefined, queryError: unknown): string | null {
  if (job?.status === "failed") {
    return job.errorMessage ?? "请稍后重新生成。";
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
