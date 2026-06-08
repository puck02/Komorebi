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
    decorations: []
  }
};

const html = renderToStaticMarkup(
  <JournalCanvas
    assets={[]}
    images={[{ id: "img_1", src: "/images/img_1/display", alt: "咖啡照片" }]}
    layout={layout}
    scale={1}
  />
);

assertIncludes(html, "journal-caption");
assertIncludes(html, "journal-meta");
assertIncludes(html, "窗边这杯咖啡");
assertIncludes(html, "2026-05-20 / 上海 / 松快");

function assertIncludes(actual: string, expected: string) {
  if (!actual.includes(expected)) {
    throw new Error(`Expected markup to include ${expected}`);
  }
}
