import { CREATE_JOURNAL_MOOD_OPTIONS } from "./createJournalOptions";
import { JOURNAL_TEMPLATES, recommendJournalTemplates } from "./journalTemplates";
import type { UploadedImage } from "../api/images";

assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "治愈");
assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "珍贵");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "松快");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "满足");

assertAtLeast(JOURNAL_TEMPLATES.length, 10);
assertEqual(new Set(JOURNAL_TEMPLATES.map((template) => template.id)).size, JOURNAL_TEMPLATES.length);

const pocketRecommendations = recommendJournalTemplates(makeImages(6), "一天里的碎片很多，像一个小合集", "");
assertEqual(pocketRecommendations.length, 3);
assertEqual(new Set(pocketRecommendations.map((template) => template.id)).size, 3);
assertIncludes(pocketRecommendations.map((template) => template.id), "pocket_grid");

const ticketRecommendations = recommendJournalTemplates(makeImages(1), "咖啡店、展览和小票都想留下", "");
assertIncludes(ticketRecommendations.map((template) => template.id), "ticket_day");

const beforeAfterRecommendations = recommendJournalTemplates(makeImages(2), "之前和之后变化很明显", "");
assertIncludes(beforeAfterRecommendations.map((template) => template.id), "before_after");

function assertIncludes(values: string[], expected: string) {
  if (!values.includes(expected)) {
    throw new Error(`Expected options to include ${expected}`);
  }
}

function assertDoesNotInclude(values: string[], expected: string) {
  if (values.includes(expected)) {
    throw new Error(`Expected options not to include ${expected}`);
  }
}

function assertEqual(actual: unknown, expected: unknown) {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, received ${String(actual)}`);
  }
}

function assertAtLeast(actual: number, expected: number) {
  if (actual < expected) {
    throw new Error(`Expected at least ${expected}, received ${actual}`);
  }
}

function makeImages(count: number): UploadedImage[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `img_${index + 1}`,
    content_type: "image/png",
    width: index % 2 === 0 ? 900 : 640,
    height: index % 2 === 0 ? 1200 : 480,
    file_url: `/images/img_${index + 1}/file`,
    display_url: `/images/img_${index + 1}/display`,
    thumbnail_url: `/images/img_${index + 1}/thumbnail`,
    created_at: "2026-06-09T00:00:00Z"
  }));
}
