import type {
  JournalDecoration,
  JournalImagePlacement,
  JournalLayout,
  JournalTextPlacement
} from "../types/journal";

export type JournalRenderText = {
  key: string;
  paragraph: string;
  placement: JournalTextPlacement;
};

export type JournalRenderLayers = {
  usesSections: boolean;
  titlePlacement?: JournalTextPlacement;
  images: JournalImagePlacement[];
  bodyTexts: JournalRenderText[];
  decorations: JournalDecoration[];
};

export function getJournalRenderLayers(layout: JournalLayout): JournalRenderLayers {
  const sections = layout.layout.sections ?? [];
  if (sections.length > 0) {
    const contentBySectionId = new Map((layout.content.sections ?? []).map((section) => [section.id, section]));
    const sortedSections = [...sections].sort((first, second) => first.y - second.y);
    const bodyTexts = sortedSections.flatMap((section, sectionIndex) => {
      const contentSection = contentBySectionId.get(section.sectionId);
      const paragraph = contentSection?.body ?? layout.content.body[sectionIndex] ?? "";
      const placement = section.texts.find((text) => text.role === "body");
      if (!placement) {
        return [];
      }
      return [{ key: `${section.sectionId}-body`, paragraph, placement }];
    });

    const sectionDecorations = sortedSections.flatMap((section) => section.decorations);

    return {
      usesSections: true,
      titlePlacement: layout.layout.texts.find((text) => text.role === "title"),
      images: sortedSections.flatMap((section) => section.images),
      bodyTexts,
      decorations: sectionDecorations.length > 0 ? sectionDecorations : layout.layout.decorations
    };
  }

  const bodyPlacements = layout.layout.texts.filter((text) => text.role === "body");
  return {
    usesSections: false,
    titlePlacement: layout.layout.texts.find((text) => text.role === "title"),
    images: layout.layout.images,
    bodyTexts: layout.content.body.map((paragraph, index) => ({
      key: `legacy-body-${index}`,
      paragraph,
      placement:
        bodyPlacements[index] ??
        ({
          role: "body",
          x: 80,
          y: (bodyPlacements[0]?.y ?? 1040) + index * 180,
          width: 760,
          fontSize: 28
        } satisfies JournalTextPlacement)
    })),
    decorations: layout.layout.decorations
  };
}

export function getJournalAssetIds(layout: JournalLayout) {
  return Array.from(new Set(getJournalRenderLayers(layout).decorations.map((decoration) => decoration.assetId)));
}
