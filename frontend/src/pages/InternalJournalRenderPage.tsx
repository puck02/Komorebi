import { useEffect, useMemo, useState } from "react";

import { getAssets } from "../api/assets";
import JournalCanvas from "../components/JournalCanvas";
import { getJournalAssetIds } from "../components/journalRenderLayers";
import type { Asset } from "../types/asset";
import type { JournalLayout } from "../types/journal";

type RenderDraft = {
  layout: JournalLayout;
  images: Array<{ id: string; src: string }>;
};

export default function InternalJournalRenderPage() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token"), []);
  const [draft, setDraft] = useState<RenderDraft | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }
    let shouldIgnore = false;

    async function loadDraft() {
      const [draftResponse, assetList] = await Promise.all([
        fetch(`/api/internal/render-drafts/${token}`).then((response) => {
          if (!response.ok) {
            throw new Error("Render draft not found");
          }
          return response.json() as Promise<RenderDraft>;
        }),
        getAssets()
      ]);
      if (shouldIgnore) {
        return;
      }
      setDraft(draftResponse);
      setAssets(assetList);
      const assetUrls = getJournalAssetIds(draftResponse.layout)
        .map((assetId) => assetList.find((asset) => asset.id === assetId)?.file_url)
        .filter((url): url is string => Boolean(url));
      await Promise.all([
        document.fonts.ready,
        ...draftResponse.images.map((image) => preloadImage(image.src)),
        ...assetUrls.map(preloadImage)
      ]);
      if (!shouldIgnore) {
        setIsReady(true);
      }
    }

    void loadDraft();
    return () => {
      shouldIgnore = true;
    };
  }, [token]);

  if (!draft) {
    return <main className="internal-render-page" />;
  }

  return (
    <main className="internal-render-page" data-render-ready={isReady ? "true" : "false"}>
      <JournalCanvas assets={assets} images={draft.images} layout={draft.layout} scale={1} />
    </main>
  );
}

function preloadImage(src: string) {
  return new Promise<void>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve();
    image.onerror = () => reject(new Error(`Failed to preload ${src}`));
    image.src = src;
  });
}
