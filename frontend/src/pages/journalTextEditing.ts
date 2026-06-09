import type { UpdateJournalPayload } from "../api/journals";
import type { JournalLayout } from "../types/journal";

export function buildJournalTextUpdatePayload(
  layout: JournalLayout,
  key: string,
  value: string
): UpdateJournalPayload {
  if (key === "title") {
    return { title: value };
  }
  if (key === "meta") {
    return { meta: value };
  }
  if (key.startsWith("legacy-body-")) {
    const index = Number(key.replace("legacy-body-", ""));
    const body = [...layout.content.body];
    if (Number.isInteger(index) && index >= 0 && index < body.length) {
      body[index] = value;
    }
    return { body };
  }
  if (key.includes("-title")) {
    const sectionId = key.replace(/-title$/, "");
    const sections = (layout.content.sections ?? []).map((section) =>
      section.id === sectionId ? { ...section, title: value } : section
    );
    return { sections };
  }
  if (key.includes("-body")) {
    const sectionId = key.replace(/-body$/, "");
    const sections = (layout.content.sections ?? []).map((section) =>
      section.id === sectionId ? { ...section, body: value } : section
    );
    const body = layout.content.body.map((paragraph, index) => {
      const section = sections[index];
      return section?.id === sectionId ? value : paragraph;
    });
    return { body, sections };
  }
  if (key.includes("-caption-")) {
    const imageId = key.split("-caption-")[1];
    const captions = layout.content.captions.map((caption) =>
      caption.imageId === imageId ? { ...caption, text: value } : caption
    );
    return { captions };
  }
  return { body: layout.content.body };
}
