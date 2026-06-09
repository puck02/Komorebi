export type JournalTextKeyTarget =
  | { type: "title" }
  | { type: "meta" }
  | { type: "legacyBody"; index: number }
  | { type: "sectionTitle"; sectionId: string }
  | { type: "sectionBody"; sectionId: string }
  | { type: "caption"; imageId: string };

export function makeJournalTextKey(target: JournalTextKeyTarget) {
  if (target.type === "title" || target.type === "meta") {
    return target.type;
  }
  if (target.type === "legacyBody") {
    return `body:legacy:${target.index}`;
  }
  if (target.type === "sectionTitle") {
    return `title:section:${encodeTextKeyPart(target.sectionId)}`;
  }
  if (target.type === "sectionBody") {
    return `body:section:${encodeTextKeyPart(target.sectionId)}`;
  }
  return `caption:image:${encodeTextKeyPart(target.imageId)}`;
}

export function parseJournalTextKey(key: string): JournalTextKeyTarget | null {
  if (key === "title" || key === "meta") {
    return { type: key };
  }

  const [role, scope, encodedValue] = key.split(":");
  if (role === "body" && scope === "legacy") {
    const index = Number(encodedValue);
    return Number.isInteger(index) && index >= 0 ? { type: "legacyBody", index } : null;
  }
  if (role === "title" && scope === "section") {
    const sectionId = decodeTextKeyPart(encodedValue);
    return sectionId ? { type: "sectionTitle", sectionId } : null;
  }
  if (role === "body" && scope === "section") {
    const sectionId = decodeTextKeyPart(encodedValue);
    return sectionId ? { type: "sectionBody", sectionId } : null;
  }
  if (role === "caption" && scope === "image") {
    const imageId = decodeTextKeyPart(encodedValue);
    return imageId ? { type: "caption", imageId } : null;
  }

  return parseLegacyJournalTextKey(key);
}

function encodeTextKeyPart(value: string) {
  return encodeURIComponent(value);
}

function decodeTextKeyPart(value: string | undefined) {
  if (!value) {
    return null;
  }
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

function parseLegacyJournalTextKey(key: string): JournalTextKeyTarget | null {
  if (key.startsWith("legacy-body-")) {
    const index = Number(key.replace("legacy-body-", ""));
    return Number.isInteger(index) && index >= 0 ? { type: "legacyBody", index } : null;
  }

  const titleMatch = /^(.*)-title$/.exec(key);
  if (titleMatch?.[1]) {
    return { type: "sectionTitle", sectionId: titleMatch[1] };
  }

  const bodyMatch = /^(.*)-body$/.exec(key);
  if (bodyMatch?.[1]) {
    return { type: "sectionBody", sectionId: bodyMatch[1] };
  }

  const captionMatch = /^(.*)-caption-(.*)$/.exec(key);
  if (captionMatch?.[2]) {
    return { type: "caption", imageId: captionMatch[2] };
  }

  return null;
}
