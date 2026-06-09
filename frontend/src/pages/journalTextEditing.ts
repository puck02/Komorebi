import type { UpdateJournalPayload } from "../api/journals";
import { parseJournalTextKey } from "../lib/journalTextKeys";
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
  const target = parseJournalTextKey(key);
  if (target?.type === "legacyBody") {
    const index = target.index;
    const body = [...layout.content.body];
    if (Number.isInteger(index) && index >= 0 && index < body.length) {
      body[index] = value;
    }
    return { body };
  }
  if (target?.type === "sectionTitle") {
    const sectionId = target.sectionId;
    const sections = (layout.content.sections ?? []).map((section) =>
      section.id === sectionId ? { ...section, title: value } : section
    );
    return { sections };
  }
  if (target?.type === "sectionBody") {
    const sectionId = target.sectionId;
    const sections = (layout.content.sections ?? []).map((section) =>
      section.id === sectionId ? { ...section, body: value } : section
    );
    const body = layout.content.body.map((paragraph, index) => {
      const section = sections[index];
      return section?.id === sectionId ? value : paragraph;
    });
    return { body, sections };
  }
  if (target?.type === "caption") {
    const imageId = target.imageId;
    const captions = layout.content.captions.map((caption) =>
      caption.imageId === imageId ? { ...caption, text: value } : caption
    );
    return { captions };
  }
  return { body: layout.content.body };
}
