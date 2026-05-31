import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const iconJsonPath = process.argv[2];
const outputRoot = path.join(root, "backend", "app", "assets", "external", "streamline-freehand-color");

if (!iconJsonPath) {
  console.error("Usage: node tools/import-streamline-freehand.mjs /path/to/icons.json");
  process.exit(1);
}

const iconSet = JSON.parse(await readFile(iconJsonPath, "utf8"));

const selectedIcons = [
  ["vintage-camera-polaroid", "streamline_polaroid_camera.svg"],
  ["photo-frame-landscape", "streamline_photo_frame.svg"],
  ["picture-polaroid-four", "streamline_polaroid_stack.svg"],
  ["party-balloon", "streamline_party_balloon.svg"],
  ["party-decoration-banner-1", "streamline_party_banner.svg"],
  ["fireworks-2", "streamline_fireworks.svg"],
  ["movies-clapboard", "streamline_clapboard.svg"],
  ["calendar-date", "streamline_calendar_date.svg"],
  ["notes-book", "streamline_notes_book.svg"],
  ["music-note-1", "streamline_music_note.svg"],
  ["work-from-home-user-pet-cat", "streamline_pet_cat.svg"],
  ["home", "streamline_home.svg"],
  ["design-tool-pen-pencil-brush", "streamline_pen_pencil_brush.svg"],
  ["color-crayon", "streamline_crayon.svg"],
  ["edit-pen-write-paper", "streamline_write_paper.svg"],
  ["amusement-park-ferris-wheel", "streamline_ferris_wheel.svg"]
];

await mkdir(outputRoot, { recursive: true });

for (const [iconName, fileName] of selectedIcons) {
  const icon = iconSet.icons[iconName];
  if (!icon) {
    throw new Error(`Missing icon: ${iconName}`);
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
  await writeFile(path.join(outputRoot, fileName), svg, "utf8");
}

console.log(`Imported ${selectedIcons.length} Streamline Freehand assets.`);

function softenPalette(body) {
  return body
    .replaceAll("#020202", "#6d6875")
    .replaceAll("#0c6fff", "#f582ae");
}
