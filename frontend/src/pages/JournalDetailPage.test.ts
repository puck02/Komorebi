import { buildJournalTextUpdatePayload } from "./journalTextEditing";
import { makeJournalTextKey } from "../lib/journalTextKeys";
import type { JournalLayout } from "../types/journal";

const layout: JournalLayout = {
  canvas: { width: 1080, height: 1600, background: "#fef6e4" },
  theme: { style: "soft-collage", palette: ["#fef6e4"], mood: ["松快"] },
  content: {
    title: "旧标题",
    meta: "2026-06-09 / 上海 / 松快",
    body: ["第一段正文", "第二段正文"],
    captions: [
      { imageId: "img_1", text: "旧说明 1" },
      { imageId: "img_2", text: "旧说明 2" }
    ],
    sections: [
      { id: "section_1", title: "第一段", imageIds: ["img_1"], body: "第一段正文", mood: [] },
      { id: "section_2", title: "第二段", imageIds: ["img_2"], body: "第二段正文", mood: [] }
    ]
  },
  layout: {
    variant: "hero_note",
    images: [],
    texts: [],
    decorations: [],
    sections: []
  }
};

assertDeepEqual(buildJournalTextUpdatePayload(layout, "title", "新标题"), { title: "新标题" });
assertDeepEqual(buildJournalTextUpdatePayload(layout, makeJournalTextKey({ type: "sectionTitle", sectionId: "section_1" }), "新的章节标题"), {
  sections: [
    { id: "section_1", title: "新的章节标题", imageIds: ["img_1"], body: "第一段正文", mood: [] },
    { id: "section_2", title: "第二段", imageIds: ["img_2"], body: "第二段正文", mood: [] }
  ]
});
assertDeepEqual(buildJournalTextUpdatePayload(layout, makeJournalTextKey({ type: "sectionBody", sectionId: "section_2" }), "新的第二段"), {
  body: ["第一段正文", "新的第二段"],
  sections: [
    { id: "section_1", title: "第一段", imageIds: ["img_1"], body: "第一段正文", mood: [] },
    { id: "section_2", title: "第二段", imageIds: ["img_2"], body: "新的第二段", mood: [] }
  ]
});
assertDeepEqual(buildJournalTextUpdatePayload(layout, makeJournalTextKey({ type: "caption", imageId: "img_1" }), "新的说明"), {
  captions: [
    { imageId: "img_1", text: "新的说明" },
    { imageId: "img_2", text: "旧说明 2" }
  ]
});

const complexIdLayout: JournalLayout = {
  ...layout,
  content: {
    ...layout.content,
    captions: [{ imageId: "trip-caption-img-body-1", text: "旧复杂说明" }],
    sections: [
      {
        id: "day-caption-body-title-1",
        title: "复杂章节",
        imageIds: ["trip-caption-img-body-1"],
        body: "复杂正文",
        mood: []
      }
    ],
    body: ["复杂正文"]
  }
};

assertDeepEqual(
  buildJournalTextUpdatePayload(
    complexIdLayout,
    makeJournalTextKey({ type: "sectionBody", sectionId: "day-caption-body-title-1" }),
    "新的复杂正文"
  ),
  {
    body: ["新的复杂正文"],
    sections: [
      {
        id: "day-caption-body-title-1",
        title: "复杂章节",
        imageIds: ["trip-caption-img-body-1"],
        body: "新的复杂正文",
        mood: []
      }
    ]
  }
);

assertDeepEqual(
  buildJournalTextUpdatePayload(
    complexIdLayout,
    makeJournalTextKey({ type: "caption", imageId: "trip-caption-img-body-1" }),
    "新的复杂说明"
  ),
  {
    captions: [{ imageId: "trip-caption-img-body-1", text: "新的复杂说明" }]
  }
);

assertDeepEqual(buildJournalTextUpdatePayload(layout, "legacy-body-1", "兼容旧正文"), {
  body: ["第一段正文", "兼容旧正文"]
});
assertDeepEqual(buildJournalTextUpdatePayload(layout, "section_1-caption-img_1", "兼容旧说明"), {
  captions: [
    { imageId: "img_1", text: "兼容旧说明" },
    { imageId: "img_2", text: "旧说明 2" }
  ]
});

function assertDeepEqual(actual: unknown, expected: unknown) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`Expected ${expectedJson}, received ${actualJson}`);
  }
}
