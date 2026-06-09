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
  metaTexts: JournalRenderText[];
  sectionTitleTexts: JournalRenderText[];
  bodyTexts: JournalRenderText[];
  captionTexts: JournalRenderText[];
  decorations: JournalDecoration[];
};

export function getJournalRenderLayers(layout: JournalLayout): JournalRenderLayers {
  const sections = layout.layout.sections ?? [];
  if (sections.length > 0) {
    const contentBySectionId = new Map((layout.content.sections ?? []).map((section) => [section.id, section]));
    const sortedSections = [...sections].sort((first, second) => first.y - second.y);
    const sectionTitleTexts = sortedSections.flatMap((section) => {
      const contentSection = contentBySectionId.get(section.sectionId);
      const paragraph = contentSection?.title?.trim();
      const placement = section.texts.find((text) => text.role === "title");
      if (!paragraph || !placement) {
        return [];
      }
      return [{ key: `${section.sectionId}-title`, paragraph, placement }];
    });
    const bodyTexts = sortedSections.flatMap((section, sectionIndex) => {
      const contentSection = contentBySectionId.get(section.sectionId);
      const paragraph = contentSection?.body ?? layout.content.body[sectionIndex] ?? "";
      const placement = section.texts.find((text) => text.role === "body");
      if (!placement) {
        return [];
      }
      return [{ key: `${section.sectionId}-body`, paragraph, placement }];
    });
    const captionTexts = sortedSections.flatMap((section) => {
      const sectionImageIds = section.images.map((image) => image.imageId);
      return buildCaptionTexts(section.texts, layout.content.captions, sectionImageIds, section.sectionId);
    });

    const sectionDecorations = sortedSections.flatMap((section) => section.decorations);

    return {
      usesSections: true,
      titlePlacement: layout.layout.texts.find((text) => text.role === "title"),
      images: sortedSections.flatMap((section) => section.images),
      metaTexts: buildMetaTexts(layout),
      sectionTitleTexts,
      bodyTexts,
      captionTexts,
      decorations: sectionDecorations.length > 0 ? sectionDecorations : layout.layout.decorations
    };
  }

  const bodyPlacements = layout.layout.texts.filter((text) => text.role === "body");
  const legacyImageIds = layout.layout.images.map((image) => image.imageId);
  return {
    usesSections: false,
    titlePlacement: layout.layout.texts.find((text) => text.role === "title"),
    images: layout.layout.images,
    metaTexts: buildMetaTexts(layout),
    sectionTitleTexts: [],
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
    captionTexts: buildCaptionTexts(layout.layout.texts, layout.content.captions, legacyImageIds, "legacy"),
    decorations: layout.layout.decorations
  };
}

export function getJournalAssetIds(layout: JournalLayout) {
  return Array.from(new Set(getJournalRenderLayers(layout).decorations.map((decoration) => decoration.assetId)));
}

function buildMetaTexts(layout: JournalLayout): JournalRenderText[] {
  const meta = layout.content.meta?.trim();
  const placement = layout.layout.texts.find((text) => text.role === "meta");
  if (!meta || !placement) {
    return [];
  }
  return [{ key: "meta", paragraph: meta, placement }];
}

function buildCaptionTexts(
  texts: JournalTextPlacement[],
  captions: JournalLayout["content"]["captions"],
  imageIds: string[],
  keyPrefix: string
): JournalRenderText[] {
  const captionPlacements = texts.filter((text) => text.role === "caption");
  return captionPlacements.flatMap((placement, index) => {
    const imageId = placement.imageId ?? imageIds[index];
    if (!imageId) {
      return [];
    }

    const caption = captions.find((item) => item.imageId === imageId)?.text.trim();
    if (!caption) {
      return [];
    }

    return [{ key: `${keyPrefix}-caption-${imageId}`, paragraph: caption, placement }];
  });
}
