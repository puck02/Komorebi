import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const iconJsonPath = process.argv[2];
const assetRoot = path.join(root, "backend", "app", "assets");
const manifestPath = path.join(assetRoot, "manifest.json");
const outputRoot = path.join(assetRoot, "external", "streamline-freehand-color");
const sourceUrl = "https://icon-sets.iconify.design/streamline-freehand-color/";
const license = "CC-BY-4.0";

if (!iconJsonPath) {
  console.error("Usage: node tools/import-streamline-freehand.mjs /path/to/icons.json");
  process.exit(1);
}

const iconSet = JSON.parse(await readFile(iconJsonPath, "utf8"));

const assets = [
  externalAsset("vintage-camera-polaroid", "polaroid_camera", "Streamline Polaroid Camera", ["photo", "travel", "memory"]),
  externalAsset("photo-frame-landscape", "photo_frame", "Streamline Photo Frame", ["photo", "memory", "daily"]),
  externalAsset("picture-polaroid-four", "polaroid_stack", "Streamline Polaroid Stack", ["photo", "collage", "memory"]),
  externalAsset("party-balloon", "party_balloon", "Streamline Party Balloon", ["party", "birthday", "happy"]),
  externalAsset("party-decoration-banner-1", "party_banner", "Streamline Party Banner", ["party", "birthday", "happy"]),
  externalAsset("fireworks-2", "fireworks", "Streamline Fireworks", ["party", "night", "happy"]),
  externalAsset("movies-clapboard", "clapboard", "Streamline Clapboard", ["movie", "date", "memory"]),
  externalAsset("calendar-date", "calendar_date", "Streamline Calendar Date", ["date", "daily", "memory"]),
  externalAsset("notes-book", "notes_book", "Streamline Notes Book", ["daily", "quiet", "home"]),
  externalAsset("music-note-1", "music_note", "Streamline Music Note", ["music", "daily", "happy"]),
  externalAsset("work-from-home-user-pet-cat", "pet_cat", "Streamline Pet Cat", ["pet", "home", "daily"]),
  externalAsset("home", "home", "Streamline Home", ["home", "daily", "quiet"]),
  externalAsset("design-tool-pen-pencil-brush", "pen_pencil_brush", "Streamline Pen Pencil Brush", ["note", "daily", "hand"]),
  externalAsset("color-crayon", "crayon", "Streamline Crayon", ["note", "daily", "hand"]),
  externalAsset("edit-pen-write-paper", "write_paper", "Streamline Write Paper", ["note", "daily", "memory"]),
  externalAsset("amusement-park-ferris-wheel", "ferris_wheel", "Streamline Ferris Wheel", ["travel", "date", "happy"]),
  externalAsset("amusement-park-castle", "castle", "Streamline Castle", ["travel", "date", "happy"]),
  externalAsset("board-game-dice-pawn", "dice_pawn", "Streamline Dice Pawn", ["game", "home", "happy"]),
  externalAsset("book-flip-page", "flip_book", "Streamline Flip Book", ["book", "quiet", "daily"]),
  externalAsset("calendar-grid", "calendar_grid", "Streamline Calendar Grid", ["date", "memory", "daily"]),
  externalAsset("camera", "camera", "Streamline Camera", ["photo", "travel", "memory"]),
  externalAsset("card-game-symbols", "card_symbols", "Streamline Card Symbols", ["game", "party", "happy"]),
  externalAsset("color-brush-1", "paint_brush", "Streamline Paint Brush", ["note", "hand", "daily"]),
  externalAsset("color-palette", "color_palette", "Streamline Color Palette", ["note", "hand", "daily"]),
  externalAsset("content-brush-pen", "brush_pen", "Streamline Brush Pen", ["note", "hand", "daily"]),
  externalAsset("content-typewriter", "typewriter", "Streamline Typewriter", ["note", "memory", "quiet"]),
  externalAsset("coupon-cut", "coupon_cut", "Streamline Coupon Cut", ["shopping", "date", "daily"]),
  externalAsset("creativity-idea-bulb", "idea_bulb", "Streamline Idea Bulb", ["daily", "happy", "memory"]),
  externalAsset("design-tool-brush-ruler", "brush_ruler", "Streamline Brush Ruler", ["note", "hand", "daily"]),
  externalAsset("design-tool-liquid-glue", "liquid_glue", "Streamline Liquid Glue", ["collage", "note", "hand"]),
  externalAsset("design-tool-magic-wand", "magic_wand", "Streamline Magic Wand", ["happy", "party", "memory"]),
  externalAsset("design-tool-stamp", "stamp", "Streamline Stamp", ["travel", "memory", "collage"]),
  externalAsset("donation-charity-donate-heart-flower", "heart_flower", "Streamline Heart Flower", ["date", "gentle", "nature"]),
  externalAsset("edit-pencil", "pencil", "Streamline Pencil", ["note", "hand", "daily"]),
  externalAsset("edit-quill-feather-1", "quill_feather", "Streamline Quill Feather", ["note", "quiet", "daily"]),
  externalAsset("home-chimney-2", "home_chimney", "Streamline Home Chimney", ["home", "quiet", "daily"]),
  externalAsset("image-file-favorite-heart", "favorite_heart_photo", "Streamline Favorite Heart Photo", ["photo", "date", "memory"]),
  externalAsset("messages-bubble-smile", "smile_bubble", "Streamline Smile Bubble", ["chat", "happy", "daily"]),
  externalAsset("messages-people-woman-heart", "heart_message", "Streamline Heart Message", ["date", "love", "memory"]),
  externalAsset("mobilephone-action-navigation-map", "navigation_map", "Streamline Navigation Map", ["travel", "walk", "memory"]),
  externalAsset("movies-reel-rating", "movie_reel", "Streamline Movie Reel", ["movie", "date", "memory"]),
  externalAsset("notes-paper", "notes_paper", "Streamline Notes Paper", ["note", "daily", "memory"]),
  externalAsset("notes-quill", "notes_quill", "Streamline Notes Quill", ["note", "quiet", "daily"]),
  externalAsset("party-alchoholic-drink-1", "party_drink", "Streamline Party Drink", ["party", "date", "happy"]),
  externalAsset("picture-double-landscape", "double_landscape", "Streamline Double Landscape", ["photo", "travel", "memory"]),
  externalAsset("picture-stack-landscape", "landscape_stack", "Streamline Landscape Stack", ["photo", "collage", "travel"]),
  externalAsset("shopping-basket-favorite-star", "shopping_star", "Streamline Shopping Star", ["shopping", "daily", "happy"]),
  externalAsset("smiley-blush", "smiley_blush", "Streamline Smiley Blush", ["happy", "date", "daily"]),
  externalAsset("smiley-happy", "smiley_happy", "Streamline Smiley Happy", ["happy", "daily", "memory"]),
  externalAsset("smiley-kiss-heart", "smiley_heart", "Streamline Smiley Heart", ["date", "love", "happy"]),
  externalAsset("video-game-controller", "game_controller", "Streamline Game Controller", ["game", "home", "happy"]),
  externalAsset("walking-symbol", "walking_symbol", "Streamline Walking Symbol", ["walk", "travel", "daily"])
];

await mkdir(outputRoot, { recursive: true });

for (const asset of assets) {
  const icon = iconSet.icons[asset.icon];
  if (!icon) {
    throw new Error(`Missing icon: ${asset.icon}`);
  }
  const width = icon.width ?? iconSet.width ?? 24;
  const height = icon.height ?? iconSet.height ?? 24;
  const body = softenPalette(icon.body);
  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 ${width} ${height}" fill="none">`,
    `<rect width="${width}" height="${height}" fill="none"/>`,
    body,
    `</svg>`
  ].join("\n");
  await writeFile(path.join(outputRoot, asset.fileName), svg, "utf8");
}

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const internalAssets = manifest.filter((asset) => !asset.id.startsWith("ext_streamline_"));
const externalManifest = assets.map((asset) => ({
  id: `ext_streamline_${asset.slug}`,
  name: asset.name,
  category: "sticker",
  tags: asset.tags,
  style: ["soft-collage", "freehand", "external"],
  colors: ["#6d6875", "#f582ae"],
  file: `external/streamline-freehand-color/${asset.fileName}`,
  license,
  source: sourceUrl,
  qualityStatus: "draft"
}));
await writeFile(manifestPath, formatManifest([...internalAssets, ...externalManifest]), "utf8");

console.log(`Imported ${assets.length} Streamline Freehand assets.`);

function externalAsset(icon, slug, name, tags) {
  return {
    icon,
    slug,
    name,
    tags,
    fileName: `streamline_${slug}.svg`
  };
}

function formatManifest(items) {
  return `[\n${items.map((item) => `  ${JSON.stringify(item)}`).join(",\n")}\n]\n`;
}

function softenPalette(body) {
  return body
    .replaceAll("#020202", "#6d6875")
    .replaceAll("#0c6fff", "#f582ae");
}
