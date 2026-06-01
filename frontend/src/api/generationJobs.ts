import { apiRequest } from "./client";
import type { GenerateJournalPayload } from "./journals";

export type GenerationJob = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  revisionRound: number;
  maxRevisionRounds: number;
  bestScore: number | null;
  journalId: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
};

export function createGenerationJob(payload: GenerateJournalPayload) {
  return apiRequest<GenerationJob>("/journal-generation-jobs", {
    auth: true,
    body: JSON.stringify(payload),
    method: "POST"
  });
}

export function getGenerationJob(jobId: string) {
  return apiRequest<GenerationJob>(`/journal-generation-jobs/${jobId}`, { auth: true });
}
