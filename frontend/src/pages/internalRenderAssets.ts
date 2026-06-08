export async function waitForRenderAssets(imageUrls: string[], assetUrls: string[]) {
  await Promise.all([
    document.fonts.ready,
    ...imageUrls.map((url) => preloadImage(url)),
    ...assetUrls.map((url) => preloadImage(url).catch(() => undefined))
  ]);
}

function preloadImage(src: string) {
  return new Promise<void>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve();
    image.onerror = () => reject(new Error(`Failed to preload ${src}`));
    image.src = src;
  });
}
