import { apiRequest } from "./client";
import type { JournalLayout } from "../types/journal";

export type Journal = {
  id: string;
  title: string;
  inputText: string;
  journalDate: string | null;
  location: string | null;
  moodTags: string[];
  layout: JournalLayout;
  imageIds: string[];
  createdAt: string;
  updatedAt: string;
};

export type GenerateJournalPayload = {
  imageIds: string[];
  description: string;
  journalDate?: string | null;
  location?: string | null;
  moodTags?: string[];
  templateId?: string | null;
};

export type UpdateJournalPayload = {
  title?: string;
  meta?: string | null;
  body?: string[];
  captions?: JournalLayout["content"]["captions"];
  sections?: NonNullable<JournalLayout["content"]["sections"]>;
  layoutVariant?: string;
};

export function generateJournal(payload: GenerateJournalPayload) {
  return apiRequest<Journal>("/journals/generate", {
    auth: true,
    body: JSON.stringify(payload),
    method: "POST"
  });
}

export function listJournals() {
  return apiRequest<Journal[]>("/journals", { auth: true });
}

export function getJournal(journalId: string) {
  return apiRequest<Journal>(`/journals/${journalId}`, { auth: true });
}

export function updateJournal(journalId: string, payload: UpdateJournalPayload) {
  return apiRequest<Journal>(`/journals/${journalId}`, {
    auth: true,
    body: JSON.stringify(payload),
    method: "PATCH"
  });
}

export function deleteJournal(journalId: string) {
  return apiRequest<void>(`/journals/${journalId}`, {
    auth: true,
    method: "DELETE"
  });
}
