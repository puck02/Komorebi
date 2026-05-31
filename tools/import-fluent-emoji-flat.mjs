import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const iconJsonPath = process.argv[2];
const assetRoot = path.join(root, "backend", "app", "assets");
const manifestPath = path.join(assetRoot, "manifest.json");
const outputRoot = path.join(assetRoot, "external", "fluent-emoji-flat");
const sourceUrl = "https://icon-sets.iconify.design/fluent-emoji-flat/";

if (!iconJsonPath) {
  console.error("Usage: node tools/import-fluent-emoji-flat.mjs /path/to/icons.json");
  process.exit(1);
}

const iconSet = JSON.parse(await readFile(iconJsonPath, "utf8"));
const assets = [
  asset("camera", ["photo", "memory", "daily"]),
  asset("camera-with-flash", ["photo", "night", "memory"]),
  asset("movie-camera", ["movie", "date", "memory"]),
  asset("red-heart", ["date", "love", "happy"]),
  asset("pink-heart", ["date", "gentle", "love"]),
  asset("two-hearts", ["date", "love", "happy"]),
  asset("sparkling-heart", ["date", "love", "happy"]),
  asset("heart-with-ribbon", ["gift", "date", "love"]),
  asset("sparkles", ["happy", "party", "daily"]),
  asset("star", ["night", "happy", "daily"]),
  asset("glowing-star", ["night", "happy", "daily"]),
  asset("shooting-star", ["night", "travel", "memory"]),
  asset("sun", ["sunny", "warm", "daily"]),
  asset("sun-with-face", ["sunny", "warm", "happy"]),
  asset("sunrise", ["sunny", "travel", "memory"]),
  asset("sunset", ["travel", "date", "memory"]),
  asset("crescent-moon", ["night", "calm", "memory"]),
  asset("full-moon", ["night", "calm", "memory"]),
  asset("cloud", ["weather", "calm", "daily"]),
  asset("cloud-with-rain", ["rainy", "weather", "calm"]),
  asset("rainbow", ["happy", "weather", "daily"]),
  asset("umbrella-with-rain-drops", ["rainy", "travel", "daily"]),
  asset("teacup-without-handle", ["tea", "daily", "warm"]),
  asset("teapot", ["tea", "home", "warm"]),
  asset("bubble-tea", ["drink", "date", "happy"]),
  asset("birthday-cake", ["birthday", "party", "happy"]),
  asset("cupcake", ["birthday", "food", "happy"]),
  asset("shortcake", ["date", "food", "happy"]),
  asset("balloon", ["birthday", "party", "happy"]),
  asset("wrapped-gift", ["gift", "birthday", "happy"]),
  asset("party-popper", ["party", "birthday", "happy"]),
  asset("fireworks", ["party", "night", "happy"]),
  asset("sunflower", ["nature", "sunny", "gentle"]),
  asset("white-flower", ["nature", "gentle", "daily"]),
  asset("fallen-leaf", ["nature", "calm", "travel"]),
  asset("maple-leaf", ["nature", "travel", "calm"]),
  asset("four-leaf-clover", ["nature", "happy", "daily"]),
  asset("cat", ["pet", "home", "daily"]),
  asset("dog", ["pet", "home", "daily"]),
  asset("paw-prints", ["pet", "home", "daily"]),
  asset("musical-note", ["music", "daily", "happy"]),
  asset("musical-notes", ["music", "party", "happy"]),
  asset("open-book", ["book", "quiet", "daily"]),
  asset("notebook", ["note", "daily", "memory"]),
  asset("pencil", ["note", "hand", "daily"]),
  asset("fountain-pen", ["note", "hand", "quiet"]),
  asset("spiral-calendar", ["date", "daily", "memory"]),
  asset("tear-off-calendar", ["date", "daily", "memory"]),
  asset("world-map", ["travel", "walk", "memory"]),
  asset("train", ["travel", "daily", "memory"]),
  asset("high-speed-train", ["travel", "daily", "memory"]),
  asset("bicycle", ["walk", "travel", "daily"]),
  asset("airplane", ["travel", "memory", "happy"]),
  asset("beach-with-umbrella", ["travel", "sea", "sunny"]),
  asset("mountain", ["travel", "nature", "calm"]),
  asset("house", ["home", "quiet", "daily"]),
  asset("house-with-garden", ["home", "nature", "daily"]),
  asset("game-die", ["game", "home", "happy"]),
  asset("video-game", ["game", "home", "happy"]),
  asset("admission-tickets", ["ticket", "date", "memory"]),
  asset("ticket", ["ticket", "travel", "memory"]),
  asset("shopping-bags", ["shopping", "daily", "happy"]),
  asset("handbag", ["shopping", "daily", "date"]),
  asset("tropical-drink", ["drink", "travel", "happy"]),
  asset("bread", ["food", "daily", "warm"]),
  asset("cookie", ["food", "daily", "happy"]),
  asset("soft-ice-cream", ["food", "date", "happy"]),
  asset("face-blowing-a-kiss", ["date", "love", "happy"]),
  asset("smiling-face-with-hearts", ["date", "love", "happy"]),
  asset("smiling-face-with-heart-eyes", ["date", "love", "happy"]),
  asset("face-savoring-food", ["food", "happy", "daily"])
];

await mkdir(outputRoot, { recursive: true });

for (const item of assets) {
  const icon = iconSet.icons[item.icon];
  if (!icon) {
    throw new Error(`Missing icon: ${item.icon}`);
  }
  const width = icon.width ?? iconSet.width ?? 32;
  const height = icon.height ?? iconSet.height ?? 32;
  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 ${width} ${height}" fill="none">`,
    `<rect width="${width}" height="${height}" fill="none"/>`,
    icon.body,
    `</svg>`
  ].join("\n");
  await writeFile(path.join(outputRoot, item.fileName), svg, "utf8");
}

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const remainingAssets = manifest.filter((item) => !item.id.startsWith("ext_fluent_"));
const externalAssets = assets.map((item) => ({
  id: `ext_fluent_${item.slug}`,
  name: item.name,
  category: "sticker",
  tags: item.tags,
  style: ["soft-collage", "emoji-flat", "external"],
  colors: [],
  file: `external/fluent-emoji-flat/${item.fileName}`,
  license: "MIT",
  source: sourceUrl,
  qualityStatus: "draft"
}));

await writeFile(manifestPath, formatManifest([...remainingAssets, ...externalAssets]), "utf8");
console.log(`Imported ${assets.length} Fluent Emoji Flat assets.`);

function asset(icon, tags) {
  const slug = icon.replaceAll("-", "_");
  return {
    icon,
    slug,
    tags,
    name: `Fluent ${titleCase(icon)}`,
    fileName: `fluent_${slug}.svg`
  };
}

function titleCase(value) {
  return value
    .split("-")
    .map((word) => `${word.slice(0, 1).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

function formatManifest(items) {
  return `[\n${items.map((item) => `  ${JSON.stringify(item)}`).join(",\n")}\n]\n`;
}
