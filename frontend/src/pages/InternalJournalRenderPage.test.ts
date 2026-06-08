import { waitForRenderAssets } from "./internalRenderAssets";

const originalDocument = globalThis.document;
const originalImage = globalThis.Image;

async function run() {
  mockDocumentFontsReady();

  installMockImage((src) => src.includes("broken-photo") || src.includes("broken-sticker"));
  await waitForRenderAssets(["/images/good-photo.webp"], ["/assets/broken-sticker.svg"]);

  installMockImage((src) => src.includes("broken-photo"));
  await assertRejects(
    () => waitForRenderAssets(["/images/broken-photo.webp"], ["/assets/good-sticker.svg"]),
    "Failed to preload /images/broken-photo.webp"
  );
}

void run().finally(() => {
  globalThis.document = originalDocument;
  globalThis.Image = originalImage;
});

function mockDocumentFontsReady() {
  globalThis.document = {
    fonts: {
      ready: Promise.resolve()
    }
  } as unknown as Document;
}

function installMockImage(shouldFail: (src: string) => boolean) {
  globalThis.Image = class {
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;

    set src(value: string) {
      queueMicrotask(() => {
        if (shouldFail(value)) {
          this.onerror?.();
          return;
        }
        this.onload?.();
      });
    }
  } as unknown as typeof Image;
}

async function assertRejects(action: () => Promise<void>, expectedMessage: string) {
  try {
    await action();
  } catch (error) {
    if (error instanceof Error && error.message === expectedMessage) {
      return;
    }
    throw error;
  }
  throw new Error(`Expected promise to reject with ${expectedMessage}`);
}
