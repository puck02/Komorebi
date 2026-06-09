import { getJournalAssetIds, getJournalRenderLayers } from "./journalRenderLayers";
import type { JournalLayout } from "../types/journal";

const sectionLayout = makeLayout({
  sections: [
    {
      sectionId: "section_1",
      variant: "hero_note",
      y: 180,
      height: 560,
      images: [{ imageId: "img_1", x: 92, y: 220, width: 420, height: 320, rotation: 0 }],
      texts: [
        { role: "title", x: 112, y: 548, width: 620, fontSize: 26 },
        { role: "caption", x: 112, y: 550, width: 360, fontSize: 24 },
        { role: "body", x: 112, y: 590, width: 820, fontSize: 32 }
      ],
      decorations: [{ assetId: "paper_note", x: 80, y: 550, width: 880, height: 180, rotation: -1 }]
    },
    {
      sectionId: "section_2",
      variant: "photo_wall",
      y: 820,
      height: 620,
      images: [{ imageId: "img_2", x: 120, y: 860, width: 320, height: 260, rotation: 0 }],
      texts: [{ role: "body", x: 112, y: 1180, width: 820, fontSize: 32 }],
      decorations: [{ assetId: "sticker_star", x: 760, y: 900, width: 120, height: 120, rotation: 5 }]
    }
  ]
});

const sectionLayers = getJournalRenderLayers(sectionLayout);
assertEqual(sectionLayers.usesSections, true);
assertDeepEqual(sectionLayers.images.map((image) => image.imageId), ["img_1", "img_2"]);
assertDeepEqual(sectionLayers.sectionTitleTexts.map((text) => text.paragraph), ["第一段"]);
assertDeepEqual(sectionLayers.sectionTitleTexts.map((text) => text.key), ["section_1-title"]);
assertDeepEqual(sectionLayers.bodyTexts.map((text) => text.placement.y), [590, 1180]);
assertDeepEqual(sectionLayers.captionTexts.map((text) => text.paragraph), ["窗边这杯咖啡"]);
assertDeepEqual(sectionLayers.captionTexts.map((text) => text.placement.y), [550]);
assertDeepEqual(sectionLayers.decorations.map((decoration) => decoration.assetId), ["paper_note", "sticker_star"]);
assertDeepEqual(getJournalAssetIds(sectionLayout), ["paper_note", "sticker_star"]);

const repeatedSectionLayout = makeLayout({
  sections: [
    {
      sectionId: "section_1",
      variant: "hero_note",
      y: 180,
      height: 760,
      images: [{ imageId: "img_1", x: 92, y: 220, width: 420, height: 320, rotation: 0 }],
      texts: [
        { role: "body", x: 112, y: 590, width: 820, fontSize: 32 },
        { role: "caption", x: 112, y: 720, width: 820, fontSize: 28 },
        { role: "body", x: 112, y: 860, width: 820, fontSize: 32 }
      ],
      decorations: [{ assetId: "paper_note", x: 80, y: 550, width: 880, height: 180, rotation: -1 }]
    }
  ]
});
const repeatedSectionLayers = getJournalRenderLayers(repeatedSectionLayout);
assertDeepEqual(repeatedSectionLayers.bodyTexts.map((text) => text.paragraph), ["第一段正文。"]);
assertDeepEqual(repeatedSectionLayers.decorations.map((decoration) => decoration.assetId), ["paper_note"]);

const visualOrderCaptionLayout = makeLayout({
  sections: [
    {
      sectionId: "section_1",
      variant: "staggered_collage",
      y: 180,
      height: 760,
      images: [
        { imageId: "img_2", x: 92, y: 220, width: 420, height: 320, rotation: 0 },
        { imageId: "img_1", x: 568, y: 260, width: 420, height: 320, rotation: 0 }
      ],
      texts: [
        { role: "caption", x: 112, y: 550, width: 360, fontSize: 24 },
        { role: "caption", x: 588, y: 590, width: 360, fontSize: 24 },
        { role: "body", x: 112, y: 700, width: 820, fontSize: 32 }
      ],
      decorations: []
    }
  ]
});
const visualOrderCaptionLayers = getJournalRenderLayers(visualOrderCaptionLayout);
assertDeepEqual(visualOrderCaptionLayers.images.map((image) => image.imageId), ["img_2", "img_1"]);
assertDeepEqual(visualOrderCaptionLayers.captionTexts.map((text) => text.paragraph), [
  "回程路上的云",
  "窗边这杯咖啡"
]);

const explicitCaptionImageLayout = makeLayout({
  sections: [
    {
      sectionId: "section_1",
      variant: "staggered_collage",
      y: 180,
      height: 760,
      images: [
        { imageId: "img_1", x: 92, y: 220, width: 420, height: 320, rotation: 0 },
        { imageId: "img_2", x: 568, y: 260, width: 420, height: 320, rotation: 0 }
      ],
      texts: [
        { role: "caption", imageId: "img_2", x: 588, y: 590, width: 360, fontSize: 24 },
        { role: "body", x: 112, y: 700, width: 820, fontSize: 32 }
      ],
      decorations: []
    }
  ]
});
const explicitCaptionImageLayers = getJournalRenderLayers(explicitCaptionImageLayout);
assertDeepEqual(explicitCaptionImageLayers.captionTexts.map((text) => text.paragraph), ["回程路上的云"]);
assertDeepEqual(explicitCaptionImageLayers.captionTexts.map((text) => text.key), ["section_1-caption-img_2"]);

const legacyLayout = makeLayout({ sections: [] });
const legacyLayers = getJournalRenderLayers(legacyLayout);
assertEqual(legacyLayers.usesSections, false);
assertDeepEqual(legacyLayers.images.map((image) => image.imageId), ["img_1"]);
assertDeepEqual(legacyLayers.metaTexts.map((text) => text.paragraph), ["2026-05-20 / 上海 / 松快"]);
assertDeepEqual(legacyLayers.bodyTexts.map((text) => text.paragraph), ["第一段正文。", "第二段正文。"]);
assertDeepEqual(legacyLayers.captionTexts.map((text) => text.paragraph), ["窗边这杯咖啡"]);
assertDeepEqual(getJournalAssetIds(legacyLayout), ["tape_legacy", "sticker_global"]);

function makeLayout({ sections }: Required<Pick<JournalLayout["layout"], "sections">>): JournalLayout {
  const usesSections = sections.length > 0;
  return {
    canvas: { width: 1080, height: 1600, background: "#fef6e4" },
    theme: { style: "soft-collage", palette: ["#fef6e4"], mood: ["温柔"] },
    content: {
      title: "慢下来的周末",
      meta: "2026-05-20 / 上海 / 松快",
      body: ["第一段正文。", "第二段正文。"],
      captions: [
        { imageId: "img_1", text: "窗边这杯咖啡" },
        { imageId: "img_2", text: "回程路上的云" }
      ],
      sections: [
        { id: "section_1", title: "第一段", imageIds: ["img_1"], body: "第一段正文。", mood: [] },
        { id: "section_2", title: "第二段", imageIds: ["img_2"], body: "第二段正文。", mood: [] }
      ]
    },
    layout: {
      variant: "long_collage",
      images: [{ imageId: "img_1", x: 92, y: 220, width: 420, height: 320, rotation: 0 }],
      texts: [
        { role: "title", x: 80, y: 72, width: 680, fontSize: 56 },
        { role: "meta", x: 84, y: 144, width: 720, fontSize: 24 },
        { role: "caption", x: 130, y: 560, width: 320, fontSize: 24 },
        { role: "body", x: 112, y: 760, width: 820, fontSize: 32 }
      ],
      decorations: [
        { assetId: usesSections ? "paper_note" : "tape_legacy", x: 80, y: usesSections ? 550 : 210, width: 220, height: 54, rotation: -8 },
        { assetId: "sticker_global", x: 840, y: 120, width: 110, height: 110, rotation: 4 }
      ],
      sections
    }
  };
}

function assertEqual(actual: unknown, expected: unknown) {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, received ${String(actual)}`);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`Expected ${expectedJson}, received ${actualJson}`);
  }
}
