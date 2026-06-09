import { CREATE_JOURNAL_MOOD_OPTIONS } from "./createJournalOptions";
import { JOURNAL_TEMPLATES, recommendJournalTemplates } from "./journalTemplates";
import type { UploadedImage } from "../api/images";

assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "治愈");
assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "珍贵");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "松快");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "满足");

assertAtLeast(JOURNAL_TEMPLATES.length, 10);
assertEqual(new Set(JOURNAL_TEMPLATES.map((template) => template.id)).size, JOURNAL_TEMPLATES.length);
assertEveryTemplateHasPreviewItems(JOURNAL_TEMPLATES);
assertEveryTemplateHasStoryMetadata(JOURNAL_TEMPLATES);

const pocketRecommendations = recommendJournalTemplates(makeImages(6), "一天里的碎片很多，像一个小合集", "");
assertEqual(pocketRecommendations.length, 3);
assertEqual(new Set(pocketRecommendations.map((template) => template.id)).size, 3);
assertIncludes(pocketRecommendations.map((template) => template.id), "pocket_grid");
assertHasRecommendationReason(pocketRecommendations);

const chapterRecommendations = recommendJournalTemplates(makeImages(7), "从早到晚的一整天，想讲成完整故事", "");
assertIncludes(chapterRecommendations.map((template) => template.id), "chapter_scroll");

const detailRecommendations = recommendJournalTemplates(makeImages(5), "有很多细节和小东西，想做成一页索引", "");
assertIncludes(detailRecommendations.map((template) => template.id), "detail_index");

const ticketRecommendations = recommendJournalTemplates(makeImages(1), "咖啡店、展览和小票都想留下", "");
assertIncludes(ticketRecommendations.map((template) => template.id), "ticket_day");

const beforeAfterRecommendations = recommendJournalTemplates(makeImages(2), "之前和之后变化很明显", "");
assertIncludes(beforeAfterRecommendations.map((template) => template.id), "before_after");

const mapRecommendations = recommendJournalTemplates(makeImages(4), "这次小旅行按地图路线和几个打卡点来记", "");
assertIncludes(mapRecommendations.map((template) => template.id), "map_journey");

const weeklyRecommendations = recommendJournalTemplates(makeImages(6), "这一周的周记和工作日复盘，连续几天都想留下", "");
assertIncludes(weeklyRecommendations.map((template) => template.id), "weekly_spread");

const dashboardRecommendations = recommendJournalTemplates(makeImages(2), "今日计划、待办清单和完成的小事项", "");
assertIncludes(dashboardRecommendations.map((template) => template.id), "day_dashboard");

const scrapbookRecommendations = recommendJournalTemplates(makeImages(5), "想做拼贴剪贴风，把这些回忆和贴纸素材放在一起", "");
assertIncludes(scrapbookRecommendations.map((template) => template.id), "scrapbook_story");

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

function assertHasRecommendationReason(values: ReturnType<typeof recommendJournalTemplates>) {
  if (values.some((template) => !template.storyArc || !template.recommendationReason)) {
    throw new Error("Expected every recommendation to explain story arc and reason");
  }
}

function assertEveryTemplateHasPreviewItems(values: typeof JOURNAL_TEMPLATES) {
  if (values.some((template) => template.previewItems.length < 3)) {
    throw new Error("Expected every template to have at least three preview items");
  }
}

function assertEveryTemplateHasStoryMetadata(values: typeof JOURNAL_TEMPLATES) {
  if (values.some((template) => !template.sourcePattern || !template.structureLabel || template.storyBeats.length !== 3)) {
    throw new Error("Expected every template to expose story metadata");
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
