import { renderToStaticMarkup } from "react-dom/server";

import JournalCanvas from "./JournalCanvas";
import type { JournalLayout } from "../types/journal";

const layout: JournalLayout = {
  canvas: { width: 1080, height: 1600, background: "#fef6e4" },
  theme: { style: "soft-collage", palette: ["#fef6e4"], mood: ["安静"] },
  content: {
    title: "慢下来的周末",
    meta: "2026-05-20 / 上海 / 松快",
    body: ["第一段正文。"],
    captions: [{ imageId: "img_1", text: "窗边这杯咖啡" }]
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
      { assetId: "paper_note", x: 70, y: 720, width: 904, height: 220, rotation: -1 },
      { assetId: "sticker_star", x: 860, y: 250, width: 120, height: 120, rotation: 4 }
    ]
  }
};

const html = renderToStaticMarkup(
  <JournalCanvas
    assets={[
      {
        id: "paper_note",
        name: "Paper note",
        category: "paper",
        tags: ["note"],
        style: ["soft-collage"],
        colors: ["#fef6e4"],
        file: "paper_note.svg",
        file_url: "/assets/paper-note.svg",
        license: "internal",
        source: "internal",
        quality_status: "approved"
      },
      {
        id: "sticker_star",
        name: "Sticker star",
        category: "sticker",
        tags: ["star"],
        style: ["soft-collage"],
        colors: ["#fef6e4"],
        file: "sticker_star.svg",
        file_url: "/assets/sticker-star.svg",
        license: "internal",
        source: "internal",
        quality_status: "approved"
      }
    ]}
    images={[{ id: "img_1", src: "/images/img_1/display", alt: "咖啡照片" }]}
    layout={layout}
    scale={1}
  />
);

const editableHtml = renderToStaticMarkup(
  <JournalCanvas
    assets={[]}
    editableTextKey="legacy-body-0"
    editableTextValue="正在编辑正文。"
    images={[{ id: "img_1", src: "/images/img_1/display", alt: "咖啡照片" }]}
    layout={layout}
    onEditableTextCancel={() => undefined}
    onEditableTextChange={() => undefined}
    onEditableTextSave={() => undefined}
    onTextDoubleClick={() => undefined}
    scale={1}
  />
);

assertIncludes(html, "journal-caption");
assertIncludes(html, "journal-meta");
assertIncludes(html, "窗边这杯咖啡");
assertIncludes(html, "2026-05-20 / 上海 / 松快");
assertIncludes(html, "journal-decoration-paper-surface");
assertIncludes(html, "journal-decoration-paper-note-surface");
assertIncludes(html, "background-image:url(&quot;/assets/paper-note.svg&quot;)");
assertIncludes(html, "background-color:#fff7ed");
assertIncludes(html, "border-radius:18px");
assertIncludes(html, "background-size:126% 138%");
assertIncludes(html, "journal-decoration-sticker");
assertIncludes(html, 'src="/assets/sticker-star.svg"');
assertIncludes(editableHtml, "journal-editable-text");
assertIncludes(editableHtml, "journal-text-edit-shell");
assertIncludes(editableHtml, "正在编辑正文。");
assertIncludes(editableHtml, "保存");

function assertIncludes(actual: string, expected: string) {
  if (!actual.includes(expected)) {
    throw new Error(`Expected markup to include ${expected}`);
  }
}
