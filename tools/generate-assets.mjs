import { createRequire } from "node:module";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "frontend", "package.json"));
const rough = require("roughjs");

const assetRoot = path.join(root, "backend", "app", "assets");
const manifestPath = path.join(assetRoot, "manifest.json");
const force = process.argv.includes("--force");
const generator = rough.generator({
  options: {
    bowing: 1.1,
    disableMultiStrokeFill: true,
    fixedDecimalPlaceDigits: 2,
    roughness: 1.25,
    strokeWidth: 2
  }
});

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

await mkdir(path.join(assetRoot, "stickers"), { recursive: true });

let generatedCount = 0;
for (const [index, asset] of manifest.filter((item) => item.source === "internal").entries()) {
  const filePath = path.join(assetRoot, asset.file);
  if (!force && await fileExists(filePath)) {
    continue;
  }
  const svg = renderAsset(asset, index + 1);
  await writeFile(filePath, svg, "utf8");
  generatedCount += 1;
}

const mode = force ? "regenerated" : "generated missing";
console.log(`${mode} ${generatedCount} internal assets.`);

async function fileExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function renderAsset(asset, seed) {
  const reviewedAsset = reviewedInternalAsset(asset);
  if (reviewedAsset) {
    return reviewedAsset;
  }

  if (asset.category === "tape") {
    return svg(240, 72, [
      roughShape("rectangle", [10, 16, 220, 40], asset, seed, { fillStyle: "hachure" }),
      ...tapePattern(asset, seed)
    ]);
  }

  if (asset.category === "paper") {
    return svg(220, 170, paperShape(asset, seed));
  }

  if (asset.category === "texture") {
    return svg(220, 160, textureShape(asset, seed));
  }

  return svg(160, 160, stickerShape(asset, seed));
}

function reviewedInternalAsset(asset) {
  if (asset.id === "paper_stamp_10") {
    return cleanSvg(220, 170, [
      roundedRect(38, 34, 144, 102, 8, "#fff3df", "#9f6b5e", 2),
      `<path d="M54 54h44M54 74h68M54 94h52" stroke="#9f6b5e" stroke-width="2" stroke-linecap="round" opacity="0.28"/>`,
      `<path d="M136 50c18 0 30 11 30 26s-12 26-30 26s-30-11-30-26s12-26 30-26Z" fill="none" stroke="#9f6b5e" stroke-width="2" opacity="0.7"/>`,
      `<path d="M116 78c10-12 27-16 42-8" stroke="#9f6b5e" stroke-width="2" stroke-linecap="round" opacity="0.42"/>`,
      `<path d="M42 36l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8l6 8l6-8" stroke="#9f6b5e" stroke-width="1.6" stroke-linecap="round" opacity="0.46"/>`
    ]);
  }
  if (asset.id === "sticker_sun_01") {
    return cleanSvg(160, 160, [
      ...Array.from({ length: 12 }, (_, index) => {
        const angle = (Math.PI * 2 * index) / 12;
        const x1 = Math.round(80 + Math.cos(angle) * 44);
        const y1 = Math.round(80 + Math.sin(angle) * 44);
        const x2 = Math.round(80 + Math.cos(angle) * 62);
        const y2 = Math.round(80 + Math.sin(angle) * 62);
        return `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="#9e813f" stroke-width="3" stroke-linecap="round" opacity="0.56"/>`;
      }),
      `<circle cx="80" cy="80" r="35" fill="#fff1cb" stroke="#9e813f" stroke-width="3"/>`,
      `<path d="M65 78c8 9 22 9 30 0" stroke="#9e813f" stroke-width="2.4" stroke-linecap="round" opacity="0.55"/>`,
      `<circle cx="69" cy="70" r="3" fill="#9e813f" opacity="0.55"/>`,
      `<circle cx="91" cy="70" r="3" fill="#9e813f" opacity="0.55"/>`
    ]);
  }
  if (asset.id === "sticker_pet_paw_17") {
    return cleanSvg(160, 160, [
      `<ellipse cx="80" cy="98" rx="30" ry="25" fill="#fff0e3" stroke="#785b49" stroke-width="3"/>`,
      `<ellipse cx="47" cy="68" rx="12" ry="16" fill="#fff0e3" stroke="#785b49" stroke-width="3"/>`,
      `<ellipse cx="68" cy="50" rx="13" ry="17" fill="#fff0e3" stroke="#785b49" stroke-width="3"/>`,
      `<ellipse cx="94" cy="50" rx="13" ry="17" fill="#fff0e3" stroke="#785b49" stroke-width="3"/>`,
      `<ellipse cx="115" cy="70" rx="12" ry="16" fill="#fff0e3" stroke="#785b49" stroke-width="3"/>`,
      `<path d="M64 102c9-8 23-8 32 0" stroke="#785b49" stroke-width="2" stroke-linecap="round" opacity="0.28"/>`
    ]);
  }
  if (asset.id === "sticker_bow_20") {
    return cleanSvg(160, 160, [
      `<defs>`,
      `<linearGradient id="bowLeftFill" x1="29" y1="58" x2="76" y2="107" gradientUnits="userSpaceOnUse">`,
      `<stop stop-color="#fff7f5"/>`,
      `<stop offset="0.58" stop-color="#f0c7ca"/>`,
      `<stop offset="1" stop-color="#d895a0"/>`,
      `</linearGradient>`,
      `<linearGradient id="bowRightFill" x1="131" y1="58" x2="84" y2="107" gradientUnits="userSpaceOnUse">`,
      `<stop stop-color="#fff7f5"/>`,
      `<stop offset="0.58" stop-color="#f0c7ca"/>`,
      `<stop offset="1" stop-color="#d895a0"/>`,
      `</linearGradient>`,
      `<linearGradient id="bowKnotFill" x1="69" y1="66" x2="91" y2="99" gradientUnits="userSpaceOnUse">`,
      `<stop stop-color="#e8aab4"/>`,
      `<stop offset="1" stop-color="#c87886"/>`,
      `</linearGradient>`,
      `<filter id="bowShadow" x="17" y="47" width="126" height="76" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">`,
      `<feDropShadow dx="2" dy="3" stdDeviation="2" flood-color="#704b51" flood-opacity="0.2"/>`,
      `</filter>`,
      `</defs>`,
      `<path d="M76 81C61 58 43 51 31 62C19 73 24 101 43 107C58 112 71 98 78 85C77 83 77 82 76 81Z" fill="url(#bowLeftFill)" stroke="#946971" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#bowShadow)"/>`,
      `<path d="M84 81C99 58 117 51 129 62C141 73 136 101 117 107C102 112 89 98 82 85C83 83 83 82 84 81Z" fill="url(#bowRightFill)" stroke="#946971" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#bowShadow)"/>`,
      `<path d="M72 69C79 64 88 67 92 75C96 83 92 95 84 99C77 103 68 98 66 89C64 81 66 73 72 69Z" fill="url(#bowKnotFill)" stroke="#946971" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`,
      `<g opacity="0.46">`,
      `<path d="M58 77C51 72 45 67 37 64" stroke="#946971" stroke-width="2" stroke-linecap="round"/>`,
      `<path d="M102 77C109 72 115 67 123 64" stroke="#946971" stroke-width="2" stroke-linecap="round"/>`,
      `<path d="M57 94C64 93 70 89 74 84" stroke="#946971" stroke-width="2" stroke-linecap="round"/>`,
      `<path d="M103 94C96 93 90 89 86 84" stroke="#946971" stroke-width="2" stroke-linecap="round"/>`,
      `</g>`,
      `<g opacity="0.34">`,
      `<path d="M35 72C45 68 57 71 68 80" stroke="#fff8f6" stroke-width="1.4" stroke-linecap="round"/>`,
      `<path d="M125 72C115 68 103 71 92 80" stroke="#fff8f6" stroke-width="1.4" stroke-linecap="round"/>`,
      `<path d="M71 75C77 72 84 74 88 80" stroke="#fff8f6" stroke-width="1.2" stroke-linecap="round"/>`,
      `<circle cx="52" cy="90" r="1" fill="#8f626b" opacity="0.24"/>`,
      `<circle cx="109" cy="90" r="1" fill="#8f626b" opacity="0.24"/>`,
      `</g>`
    ]);
  }
  if (asset.id === "paper_checklist_15") {
    return cleanSvg(220, 170, [
      `<path d="M32 24C72 20 144 20 188 29C184 70 187 108 194 142C142 148 78 146 28 136C35 93 37 58 32 24Z" fill="#fff6df" stroke="#8c755b" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M48 43C82 40 138 41 170 47" stroke="#a38b6a" stroke-width="2.2" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M54 62h14v14H54zM54 86h14v14H54zM54 110h14v14H54z" fill="#fffaf0" stroke="#8c755b" stroke-width="2" stroke-linejoin="round"/>`,
      `<path d="M57 68l5 5l11-13M57 92l5 5l11-13" stroke="#6f8063" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`,
      `<path d="M84 68C112 65 141 66 165 69M84 92C108 90 138 90 160 93M84 116C112 114 134 115 154 118" stroke="#8c755b" stroke-width="2.2" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M41 133C82 141 136 142 184 136" stroke="#fffaf0" stroke-width="2.4" stroke-linecap="round" opacity="0.7"/>`
    ]);
  }
  if (asset.id === "paper_bus_ticket_16") {
    return cleanSvg(220, 170, [
      `<path d="M27 55C58 48 139 45 190 52C186 62 190 72 202 75C196 88 196 103 204 116C193 118 188 126 192 137C139 143 74 139 25 129C32 119 28 110 17 107C25 92 25 70 27 55Z" fill="#dfeaf5" stroke="#5f7f9a" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M72 53C68 82 69 109 75 134" stroke="#5f7f9a" stroke-width="2" stroke-linecap="round" stroke-dasharray="5 7" opacity="0.58"/>`,
      `<path d="M91 67C122 64 151 65 174 69M91 88C125 86 152 87 173 91M92 109C119 108 144 108 163 112" stroke="#4d687f" stroke-width="2.3" stroke-linecap="round" opacity="0.62"/>`,
      `<path d="M40 70h34M40 92h34M40 114h34" stroke="#fff8ea" stroke-width="2.4" stroke-linecap="round" opacity="0.85"/>`,
      `<path d="M145 54C147 78 147 107 143 136" stroke="#8da6ba" stroke-width="1.7" stroke-linecap="round" stroke-dasharray="3 8" opacity="0.55"/>`,
      `<circle cx="51" cy="83" r="5" fill="#5f7f9a" opacity="0.28"/>`,
      `<circle cx="55" cy="105" r="3.5" fill="#5f7f9a" opacity="0.22"/>`
    ]);
  }
  if (asset.id === "paper_movie_ticket_17") {
    return cleanSvg(220, 170, [
      `<path d="M28 52C58 44 141 44 190 51C184 62 189 73 202 76C194 88 194 104 202 116C190 119 185 129 191 139C138 145 72 140 26 130C31 118 26 109 16 106C25 91 25 70 28 52Z" fill="#efe0f2" stroke="#6f5c83" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M74 52C70 82 71 109 77 136" stroke="#6f5c83" stroke-width="2" stroke-linecap="round" stroke-dasharray="5 7" opacity="0.58"/>`,
      `<path d="M93 67C119 64 150 65 174 70M93 91C120 89 148 90 171 94M94 114C119 113 143 114 160 118" stroke="#574568" stroke-width="2.3" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M39 72h42v30H39z" fill="#f8edf8" stroke="#6f5c83" stroke-width="2" stroke-linejoin="round" opacity="0.72"/>`,
      `<path d="M44 77l10 8l-10 8M60 77l10 8l-10 8" stroke="#6f5c83" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.52"/>`,
      `<path d="M145 54C148 79 148 106 144 137" stroke="#957faa" stroke-width="1.7" stroke-linecap="round" stroke-dasharray="3 8" opacity="0.5"/>`,
      `<circle cx="56" cy="118" r="4" fill="#6f5c83" opacity="0.23"/>`,
      `<path d="M112 54l5 10l11 2l-8 8l2 11l-10-5l-10 5l2-11l-8-8l11-2Z" fill="#fff6d8" stroke="#6f5c83" stroke-width="1.8" opacity="0.76"/>`
    ]);
  }
  if (asset.id === "paper_shopping_receipt_18") {
    return cleanSvg(220, 170, [
      `<path d="M46 25C78 31 132 28 174 24C169 67 170 107 181 144C136 137 82 140 39 147C45 103 47 65 46 25Z" fill="#fff5de" stroke="#9b7c57" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M52 29l8 8l9-8l9 8l9-8l9 8l9-8l9 8l9-8l9 8l9-8l9 8l9-8l9 8l9-8" stroke="#9b7c57" stroke-width="1.8" stroke-linecap="round" opacity="0.48"/>`,
      `<path d="M65 53C97 49 126 50 153 55M64 73C97 70 132 71 161 75M65 94C91 92 119 93 144 96M65 115C101 113 131 114 159 118" stroke="#8a6b4c" stroke-width="2.2" stroke-linecap="round" opacity="0.52"/>`,
      `<path d="M64 132C94 128 127 129 157 134" stroke="#8a6b4c" stroke-width="2.4" stroke-linecap="round" opacity="0.34"/>`,
      `<path d="M148 43h18v19h-18z" fill="#fffaf0" stroke="#9b7c57" stroke-width="1.8" stroke-linejoin="round" opacity="0.82"/>`,
      `<path d="M151 48l5 5l10-12" stroke="#7a8a62" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" opacity="0.62"/>`,
      `<circle cx="54" cy="58" r="2" fill="#9b7c57" opacity="0.38"/>`,
      `<circle cx="54" cy="78" r="2" fill="#9b7c57" opacity="0.34"/>`
    ]);
  }
  if (asset.id === "paper_exhibition_ticket_19") {
    return cleanSvg(220, 170, [
      `<path d="M27 50C63 43 145 43 190 51C184 63 190 75 202 78C195 90 195 107 203 118C190 120 185 130 191 139C141 145 72 141 25 130C31 118 26 109 16 106C25 91 25 69 27 50Z" fill="#efe7d5" stroke="#6d665c" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M73 52C69 82 70 109 76 136" stroke="#6d665c" stroke-width="2" stroke-linecap="round" stroke-dasharray="5 7" opacity="0.58"/>`,
      `<path d="M94 66C121 63 151 64 174 69M94 89C127 86 151 87 171 91M95 113C118 112 143 113 162 117" stroke="#5c554d" stroke-width="2.3" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M40 67h38v43H40z" fill="#f8f1e6" stroke="#6d665c" stroke-width="2" stroke-linejoin="round" opacity="0.82"/>`,
      `<path d="M47 99C52 84 61 75 75 68" stroke="#8c7861" stroke-width="2.2" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M47 75C57 80 66 88 73 99" stroke="#8c7861" stroke-width="2" stroke-linecap="round" opacity="0.4"/>`,
      `<path d="M143 54C147 78 147 107 143 136" stroke="#8d8277" stroke-width="1.7" stroke-linecap="round" stroke-dasharray="3 8" opacity="0.5"/>`,
      `<circle cx="55" cy="121" r="4" fill="#6d665c" opacity="0.22"/>`,
      `<path d="M111 53l6 10l12 2l-9 8l2 12l-11-6l-10 6l2-12l-9-8l12-2Z" fill="#f6dfae" stroke="#6d665c" stroke-width="1.8" opacity="0.76"/>`
    ]);
  }
  if (asset.id === "sticker_fountain_pen_36") {
    return cleanSvg(160, 160, [
      `<path d="M44 118C58 93 78 56 101 31C109 35 116 42 121 50C98 73 68 101 49 123C47 123 45 121 44 118Z" fill="#f4dfbb" stroke="#4f6170" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M91 40C100 43 110 52 114 61" stroke="#fff6df" stroke-width="2.2" stroke-linecap="round" opacity="0.72"/>`,
      `<path d="M44 118L31 134C42 133 49 129 56 121" fill="#fff6df"/>`,
      `<path d="M44 118L31 134C42 133 49 129 56 121" stroke="#4f6170" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M38 126L45 131" stroke="#4f6170" stroke-width="2.3" stroke-linecap="round"/>`,
      `<path d="M104 28C113 32 122 41 126 50L118 58C113 48 104 39 96 35Z" fill="#6f7f8b" stroke="#4f6170" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M57 105C72 93 88 76 104 58" stroke="#4f6170" stroke-width="2.2" stroke-linecap="round" opacity="0.32"/>`,
      `<path d="M66 127C85 125 101 127 118 132" stroke="#9c8063" stroke-width="2.2" stroke-linecap="round" opacity="0.3"/>`
    ]);
  }
  if (asset.id === "sticker_torn_photo_corner_37") {
    return cleanSvg(160, 160, [
      `<path d="M43 39C65 35 105 36 128 42C116 60 104 79 95 102C75 93 58 88 36 83C45 65 49 51 43 39Z" fill="#f7ead2" stroke="#8b6c52" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M51 47C69 44 101 45 116 50" stroke="#fff8ec" stroke-width="2.4" stroke-linecap="round" opacity="0.72"/>`,
      `<path d="M47 74C67 77 82 82 99 92" stroke="#b58a63" stroke-width="2.2" stroke-linecap="round" opacity="0.45"/>`,
      `<path d="M43 39C57 52 77 70 95 102" stroke="#8b6c52" stroke-width="2" stroke-linecap="round" stroke-dasharray="5 7" opacity="0.48"/>`,
      `<path d="M33 86C51 90 70 95 91 106" stroke="#fff8ec" stroke-width="2.4" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M70 40L75 48M88 40L92 49M107 43L111 52" stroke="#8b6c52" stroke-width="1.8" stroke-linecap="round" opacity="0.32"/>`
    ]);
  }
  if (asset.id === "sticker_pressed_leaf_38") {
    return cleanSvg(160, 160, [
      `<path d="M38 121C44 69 83 32 126 31C122 78 91 119 38 121Z" fill="#edf0d2" stroke="#6e7e55" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M45 114C67 88 92 62 122 36" stroke="#6e7e55" stroke-width="2.4" stroke-linecap="round" opacity="0.62"/>`,
      `<path d="M67 92C66 74 62 64 54 55M78 80C89 70 94 60 96 45M88 70C101 69 112 63 121 54M59 104C75 104 87 100 99 91" stroke="#7f9160" stroke-width="2" stroke-linecap="round" opacity="0.46"/>`,
      `<path d="M35 123C57 124 82 119 103 105" stroke="#fff8df" stroke-width="2.2" stroke-linecap="round" opacity="0.6"/>`,
      `<path d="M50 129C73 135 96 133 118 125" stroke="#a28a62" stroke-width="1.8" stroke-linecap="round" opacity="0.24"/>`
    ]);
  }
  if (asset.id === "sticker_umbrella_39") {
    return cleanSvg(160, 160, [
      `<path d="M31 82C42 47 76 32 114 46C129 51 140 63 145 80C126 74 112 78 99 89C84 78 68 78 53 90C44 80 37 79 31 82Z" fill="#e5f0f3" stroke="#6f8fa2" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M80 40C76 59 76 72 80 97" stroke="#6f8fa2" stroke-width="2.4" stroke-linecap="round" opacity="0.62"/>`,
      `<path d="M80 96v31c0 13 18 13 18 1" stroke="#6f8fa2" stroke-width="3" stroke-linecap="round"/>`,
      `<path d="M47 79C61 65 76 61 94 83M94 83C104 68 119 66 139 78" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M50 112c-5 8-2 16 7 17M122 109c-5 8-2 16 7 17" stroke="#6f8fa2" stroke-width="2.2" stroke-linecap="round" opacity="0.38"/>`,
      `<circle cx="44" cy="118" r="3" fill="#6f8fa2" opacity="0.28"/>`,
      `<circle cx="118" cy="128" r="2.5" fill="#6f8fa2" opacity="0.24"/>`
    ]);
  }
  if (asset.id === "sticker_window_lamp_40") {
    return cleanSvg(160, 160, [
      `<path d="M40 37C61 33 102 33 125 38C122 74 124 104 130 132C95 137 62 136 34 130C41 95 42 67 40 37Z" fill="#f2edf4" stroke="#6c6275" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M52 48h32v35H52zM91 48h24v35H91zM52 90h32v33H52zM91 90h24v33H91z" fill="#f6dfa8" stroke="#6c6275" stroke-width="2.1" stroke-linejoin="round" opacity="0.88"/>`,
      `<path d="M61 57C67 53 74 53 80 57M98 99C103 96 108 96 113 99" stroke="#fff8da" stroke-width="2.2" stroke-linecap="round" opacity="0.8"/>`,
      `<path d="M124 43C135 52 140 67 139 83M31 50C25 64 25 79 31 91" stroke="#6c6275" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`,
      `<circle cx="43" cy="32" r="3" fill="#f6dfa8" opacity="0.7"/>`,
      `<circle cx="128" cy="29" r="2" fill="#f6dfa8" opacity="0.55"/>`
    ]);
  }
  if (asset.id === "sticker_sleeping_cat_41") {
    return cleanSvg(160, 160, [
      `<path d="M38 100C45 70 70 55 100 60C124 64 140 82 137 108C111 124 67 124 38 100Z" fill="#f3dfc8" stroke="#8b6b57" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M62 63L67 43L79 61M104 61L119 45L119 70" fill="#f3dfc8" stroke="#8b6b57" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`,
      `<path d="M78 83c7 6 17 6 24 0M65 81c4 3 8 3 12 0M108 82c4 3 8 3 12 0" stroke="#8b6b57" stroke-width="2.3" stroke-linecap="round" opacity="0.56"/>`,
      `<path d="M112 102C128 99 138 105 141 117C132 122 119 120 111 112" stroke="#8b6b57" stroke-width="3" stroke-linecap="round" fill="none"/>`,
      `<path d="M48 106C70 114 100 114 128 105" stroke="#fff5e6" stroke-width="2.4" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M44 132C73 139 105 139 132 130" stroke="#9c8063" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`
    ]);
  }
  if (asset.id === "sticker_birthday_cake_42") {
    return cleanSvg(160, 160, [
      `<path d="M43 82C65 76 105 76 128 82V119C102 128 70 128 42 118Z" fill="#fff0d6" stroke="#8f6465" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M48 82C60 97 75 95 85 85C96 100 111 97 126 82" fill="#f1b8b4" stroke="#8f6465" stroke-width="2.5" stroke-linejoin="round"/>`,
      `<path d="M61 78V52M82 76V48M105 78V54" stroke="#8f6465" stroke-width="3" stroke-linecap="round"/>`,
      `<path d="M61 39C70 48 63 54 59 55C54 51 54 43 61 39ZM82 34C91 45 84 51 80 52C75 48 75 39 82 34ZM105 41C113 50 106 56 102 56C98 52 98 45 105 41Z" fill="#ffe28d" stroke="#8f6465" stroke-width="2" stroke-linejoin="round"/>`,
      `<path d="M53 111C75 118 102 118 121 110" stroke="#8f6465" stroke-width="2.2" stroke-linecap="round" opacity="0.34"/>`,
      `<circle cx="69" cy="99" r="3" fill="#d8898b" opacity="0.65"/>`,
      `<circle cx="94" cy="102" r="3" fill="#d8898b" opacity="0.55"/>`,
      `<circle cx="113" cy="96" r="2.5" fill="#d8898b" opacity="0.55"/>`
    ]);
  }
  if (asset.id === "sticker_shopping_bag_43") {
    return cleanSvg(160, 160, [
      `<path d="M48 58C69 54 104 54 125 59C121 91 123 112 130 133C97 139 67 138 39 130C46 100 48 80 48 58Z" fill="#fff2dc" stroke="#8d6842" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M67 60C67 40 106 40 106 61" stroke="#8d6842" stroke-width="3" stroke-linecap="round" fill="none"/>`,
      `<path d="M57 83C77 80 101 81 117 85M57 104C82 102 99 103 115 107" stroke="#8d6842" stroke-width="2.2" stroke-linecap="round" opacity="0.42"/>`,
      `<path d="M44 132C72 139 101 140 128 132" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" opacity="0.58"/>`,
      `<circle cx="57" cy="68" r="3" fill="#c99562" opacity="0.45"/>`,
      `<circle cx="118" cy="69" r="3" fill="#c99562" opacity="0.45"/>`
    ]);
  }
  if (asset.id === "sticker_bookmark_44") {
    return cleanSvg(160, 160, [
      `<path d="M39 42C59 35 102 35 123 43C119 74 120 103 128 129C103 124 76 124 38 132C45 101 46 70 39 42Z" fill="#fff7e7" stroke="#8f6f5b" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M66 39C61 69 61 101 66 128L80 112L96 129C90 100 90 70 96 40" fill="#f4dfbb" stroke="#8f6f5b" stroke-width="2.6" stroke-linejoin="round"/>`,
      `<path d="M49 58C64 55 83 55 111 59M49 77C68 74 92 74 114 79M49 96C66 94 85 94 108 98" stroke="#8f6f5b" stroke-width="2.1" stroke-linecap="round" opacity="0.42"/>`,
      `<path d="M74 51C80 47 88 48 92 54" stroke="#fffaf0" stroke-width="2.1" stroke-linecap="round" opacity="0.82"/>`,
      `<path d="M36 132C63 139 100 137 130 128" stroke="#9c8063" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`
    ]);
  }
  if (asset.id === "sticker_table_plate_45") {
    return cleanSvg(160, 160, [
      `<ellipse cx="80" cy="90" rx="54" ry="39" fill="#fff2da" stroke="#b98465" stroke-width="3"/>`,
      `<ellipse cx="80" cy="90" rx="31" ry="22" fill="#fffaf0" stroke="#b98465" stroke-width="2.3" opacity="0.72"/>`,
      `<path d="M43 51C52 43 65 43 72 52C62 58 52 59 43 51Z" fill="#f0cfa8" stroke="#b98465" stroke-width="2.4" stroke-linejoin="round"/>`,
      `<path d="M107 54C117 47 130 50 136 60C125 65 115 64 107 54Z" fill="#d9e2bf" stroke="#7f8d60" stroke-width="2.3" stroke-linejoin="round"/>`,
      `<path d="M49 118C71 127 105 126 130 116" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" opacity="0.62"/>`,
      `<path d="M53 84C64 78 77 77 92 84M67 99C78 104 91 104 104 98" stroke="#b98465" stroke-width="2" stroke-linecap="round" opacity="0.34"/>`,
      `<circle cx="58" cy="94" r="3" fill="#d19a75" opacity="0.44"/>`,
      `<circle cx="106" cy="87" r="2.5" fill="#d19a75" opacity="0.38"/>`
    ]);
  }
  if (asset.id === "sticker_shell_46") {
    return cleanSvg(160, 160, [
      `<path d="M36 112C40 67 62 38 82 36C103 38 126 68 131 113C101 126 67 126 36 112Z" fill="#f7ead6" stroke="#7a9aa4" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M82 38C75 68 74 94 80 120M82 38C91 70 92 95 87 120M62 50C67 78 68 100 62 117M104 51C99 78 99 99 105 117M47 80C59 91 70 102 80 121M118 81C107 93 96 104 87 121" stroke="#7a9aa4" stroke-width="2.2" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M36 112C61 119 101 119 131 113" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" opacity="0.65"/>`,
      `<path d="M41 132C66 139 101 138 127 130" stroke="#9c8063" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`,
      `<circle cx="83" cy="40" r="3" fill="#7a9aa4" opacity="0.34"/>`
    ]);
  }
  if (asset.id === "sticker_bus_stop_47") {
    return cleanSvg(160, 160, [
      `<path d="M43 39C60 34 96 34 115 40C111 70 112 96 118 123C95 127 62 127 38 121C45 91 46 65 43 39Z" fill="#e6eef4" stroke="#5f7f9a" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M53 51h58v34H53z" fill="#fffaf0" stroke="#5f7f9a" stroke-width="2.3" stroke-linejoin="round"/>`,
      `<path d="M62 58h16M87 58h16M62 71h41" stroke="#5f7f9a" stroke-width="2" stroke-linecap="round" opacity="0.55"/>`,
      `<path d="M63 101C76 96 99 96 110 102V112C97 118 75 118 61 112Z" fill="#fffaf0" stroke="#5f7f9a" stroke-width="2.3" stroke-linejoin="round"/>`,
      `<circle cx="70" cy="113" r="5" fill="#5f7f9a" opacity="0.42"/>`,
      `<circle cx="101" cy="113" r="5" fill="#5f7f9a" opacity="0.42"/>`,
      `<path d="M120 50h16M128 50v78" stroke="#5f7f9a" stroke-width="3" stroke-linecap="round" opacity="0.7"/>`,
      `<path d="M117 129C91 136 61 134 36 126" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" opacity="0.56"/>`
    ]);
  }
  if (asset.id === "sticker_sleeping_dog_48") {
    return cleanSvg(160, 160, [
      `<path d="M37 101C44 72 69 58 100 62C124 65 140 82 137 108C109 123 66 123 37 101Z" fill="#ead4bd" stroke="#8b6b57" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M59 64C51 48 43 49 39 67C45 72 53 71 59 64Z" fill="#d2b292" stroke="#8b6b57" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M105 64C116 48 126 50 127 72C119 76 111 72 105 64Z" fill="#d2b292" stroke="#8b6b57" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M70 83c6 5 15 5 21 0M56 82c4 3 8 3 12 0M96 82c4 3 8 3 12 0" stroke="#8b6b57" stroke-width="2.3" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M115 102C130 100 139 107 139 118C128 122 117 119 110 111" stroke="#8b6b57" stroke-width="3" stroke-linecap="round" fill="none"/>`,
      `<path d="M46 107C70 115 101 115 128 106" stroke="#fff5e6" stroke-width="2.4" stroke-linecap="round" opacity="0.58"/>`,
      `<path d="M43 132C72 139 107 138 133 130" stroke="#9c8063" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`
    ]);
  }
  if (asset.id === "sticker_houseplant_49") {
    return cleanSvg(160, 160, [
      `<path d="M57 93C76 88 104 88 123 94L116 130C96 137 72 136 51 128Z" fill="#f0d8b8" stroke="#6e7e55" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M78 92C70 65 48 55 36 65C42 83 58 92 78 92Z" fill="#edf0d2" stroke="#6e7e55" stroke-width="2.7" stroke-linejoin="round"/>`,
      `<path d="M84 91C83 61 96 39 113 40C121 62 108 82 84 91Z" fill="#dfe8c0" stroke="#6e7e55" stroke-width="2.7" stroke-linejoin="round"/>`,
      `<path d="M91 91C103 68 127 62 139 73C131 91 112 98 91 91Z" fill="#edf0d2" stroke="#6e7e55" stroke-width="2.7" stroke-linejoin="round"/>`,
      `<path d="M80 93C78 76 76 61 72 46M84 92C94 72 102 58 113 43M90 92C107 84 121 77 136 73" stroke="#6e7e55" stroke-width="2.1" stroke-linecap="round" opacity="0.52"/>`,
      `<path d="M55 119C73 126 97 126 116 119" stroke="#fff8df" stroke-width="2.2" stroke-linecap="round" opacity="0.62"/>`,
      `<path d="M48 132C73 139 100 139 122 130" stroke="#9c8063" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`
    ]);
  }
  if (asset.id === "sticker_gallery_map_50") {
    return cleanSvg(160, 160, [
      `<path d="M32 44C49 36 69 42 82 37C96 32 111 34 130 42C126 69 128 94 134 122C115 113 98 111 83 117C68 123 49 115 31 123C36 95 36 69 32 44Z" fill="#f3ead8" stroke="#6f7f8b" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M58 41C55 70 56 94 60 118M102 38C99 65 101 90 106 116" stroke="#6f7f8b" stroke-width="2" stroke-linecap="round" opacity="0.48"/>`,
      `<path d="M43 58C55 54 64 56 72 62C80 68 89 68 99 62C108 56 116 58 126 65" stroke="#7e8f73" stroke-width="2.4" stroke-linecap="round" opacity="0.56"/>`,
      `<path d="M44 93C58 86 70 91 80 97C90 103 105 96 123 100" stroke="#b89466" stroke-width="2.3" stroke-linecap="round" opacity="0.52"/>`,
      `<circle cx="73" cy="76" r="5" fill="#b86f5b" opacity="0.75"/>`,
      `<circle cx="111" cy="90" r="4" fill="#6f7f8b" opacity="0.55"/>`,
      `<path d="M73 81C72 88 70 93 66 98" stroke="#b86f5b" stroke-width="2" stroke-linecap="round" opacity="0.56"/>`,
      `<path d="M42 126C66 132 96 131 126 125" stroke="#8c755b" stroke-width="2" stroke-linecap="round" opacity="0.24"/>`,
      `<path d="M45 70h16M91 51h19M92 108h20" stroke="#6f7f8b" stroke-width="1.8" stroke-linecap="round" opacity="0.34"/>`
    ]);
  }
  if (asset.id === "sticker_gallery_label_51") {
    return cleanSvg(160, 160, [
      `<path d="M30 54C55 47 111 48 136 55C132 81 133 99 140 123C104 129 63 127 26 121C34 94 35 73 30 54Z" fill="#fff7e8" stroke="#725f52" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M45 70C74 67 103 68 124 72M45 90C82 87 103 88 119 92M46 110C72 108 94 109 112 112" stroke="#725f52" stroke-width="2.4" stroke-linecap="round" opacity="0.52"/>`,
      `<path d="M38 57C55 62 78 63 99 60C116 58 126 60 135 65" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" opacity="0.72"/>`,
      `<path d="M38 124C63 118 101 120 135 124" stroke="#8c755b" stroke-width="2" stroke-linecap="round" opacity="0.22"/>`,
      `<circle cx="43" cy="72" r="2.5" fill="#b86f5b" opacity="0.42"/>`,
      `<circle cx="43" cy="92" r="2.2" fill="#b86f5b" opacity="0.34"/>`,
      `<path d="M117 50C122 42 130 39 137 43C132 46 129 51 129 58" stroke="#725f52" stroke-width="2" stroke-linecap="round" opacity="0.34"/>`
    ]);
  }
  if (asset.id === "sticker_installation_art_52") {
    return cleanSvg(160, 160, [
      `<path d="M46 121C66 110 97 111 121 121" stroke="#8c755b" stroke-width="3" stroke-linecap="round" opacity="0.34"/>`,
      `<path d="M53 107C57 82 67 60 81 38C96 59 108 81 113 107C93 116 72 116 53 107Z" fill="#eadfc7" stroke="#6c6275" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M81 38C78 63 78 88 82 112" stroke="#6c6275" stroke-width="2.2" stroke-linecap="round" opacity="0.54"/>`,
      `<path d="M61 91C71 84 92 83 104 91M66 72C75 67 90 67 99 73" stroke="#fff8e8" stroke-width="2.4" stroke-linecap="round" opacity="0.72"/>`,
      `<path d="M49 108C67 101 95 101 114 108" stroke="#b86f5b" stroke-width="2.3" stroke-linecap="round" opacity="0.36"/>`,
      `<path d="M42 50C52 45 61 44 70 48M102 48C116 43 126 45 136 53" stroke="#6c6275" stroke-width="2" stroke-linecap="round" opacity="0.28"/>`,
      `<circle cx="62" cy="116" r="3" fill="#6c6275" opacity="0.28"/>`,
      `<circle cx="102" cy="116" r="3" fill="#6c6275" opacity="0.24"/>`
    ]);
  }
  return null;
}

function cleanSvg(width, height, children) {
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" fill="none">`,
    `<rect width="${width}" height="${height}" fill="none"/>`,
    ...children,
    `</svg>`
  ].join("\n");
}

function roundedRect(x, y, width, height, radius, fill, stroke, strokeWidth) {
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
}

function svg(width, height, children) {
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" fill="none">`,
    `<rect width="${width}" height="${height}" fill="none"/>`,
    ...children,
    `</svg>`
  ].join("\n");
}

function roughShape(shape, args, asset, seed, options = {}) {
  const [primary, secondary] = asset.colors;
  const drawable = generator[shape](...args, {
    fill: options.fill ?? secondary ?? "#fff7ef",
    fillStyle: options.fillStyle ?? "solid",
    hachureGap: options.hachureGap ?? 8,
    seed,
    stroke: options.stroke ?? darken(primary),
    strokeWidth: options.strokeWidth ?? 2,
    roughness: options.roughness ?? 1.2
  });
  return paths(drawable);
}

function roughPath(d, asset, seed, options = {}) {
  const [primary, secondary] = asset.colors;
  const drawable = generator.path(d, {
    fill: options.fill ?? secondary ?? "#fff7ef",
    fillStyle: options.fillStyle ?? "solid",
    hachureGap: options.hachureGap ?? 8,
    seed,
    stroke: options.stroke ?? darken(primary),
    strokeWidth: options.strokeWidth ?? 2,
    roughness: options.roughness ?? 1.2
  });
  return paths(drawable);
}

function paths(drawable) {
  return generator
    .toPaths(drawable)
    .map((pathInfo) => {
      const fill = pathInfo.fill ? ` fill="${pathInfo.fill}"` : ` fill="none"`;
      return `<path d="${pathInfo.d}" stroke="${pathInfo.stroke}" stroke-width="${pathInfo.strokeWidth}" stroke-linecap="round" stroke-linejoin="round"${fill}/>`;
    })
    .join("\n");
}

function tapePattern(asset, seed) {
  const [primary] = asset.colors;
  const stroke = darken(primary);
  if (asset.id.includes("grid")) {
    return [
      line(38, 18, 38, 55, stroke, 0.42),
      line(76, 18, 76, 55, stroke, 0.42),
      line(114, 18, 114, 55, stroke, 0.42),
      line(152, 18, 152, 55, stroke, 0.42),
      line(190, 18, 190, 55, stroke, 0.42),
      line(14, 29, 226, 29, stroke, 0.42),
      line(14, 43, 226, 43, stroke, 0.42)
    ];
  }
  if (asset.id.includes("dot")) {
    return dots([[36, 35], [70, 28], [102, 43], [138, 31], [174, 44], [204, 34]], primary, seed);
  }
  if (asset.id.includes("dash")) {
    return Array.from({ length: 8 }, (_, index) => line(26 + index * 24, 36, 38 + index * 24, 32, stroke, 0.55));
  }
  if (asset.id.includes("line")) {
    return [line(24, 30, 216, 28, stroke, 0.5), line(22, 44, 214, 43, stroke, 0.35)];
  }
  return [
    `<path d="M28 20L214 54" stroke="${stroke}" stroke-width="4" stroke-linecap="round" opacity="0.25"/>`,
    `<path d="M18 52L188 20" stroke="${stroke}" stroke-width="3" stroke-linecap="round" opacity="0.22"/>`
  ];
}

function paperShape(asset, seed) {
  const [primary, secondary] = asset.colors;
  if (asset.id.includes("ticket")) {
    return [
      roughShape("rectangle", [18, 28, 184, 108], asset, seed, { fill: secondary }),
      line(70, 36, 70, 126, darken(primary), 0.3, "6 7"),
      ...dots([[35, 54], [35, 110], [168, 54], [168, 110]], primary, seed)
    ];
  }
  if (asset.id.includes("tag")) {
    return [
      roughPath("M64 24h92l26 30v82H40V54z", asset, seed, { fill: secondary }),
      roughShape("circle", [62, 54, 16], asset, seed + 1, { fill: "#fffaf5" })
    ];
  }
  if (asset.id.includes("stamp")) {
    return [
      roughShape("rectangle", [34, 28, 152, 112], asset, seed, { fill: secondary, fillStyle: "hachure" }),
      roughShape("ellipse", [68, 54, 84, 50], asset, seed + 1, { fill: "none", stroke: darken(primary) }),
      line(62, 112, 158, 112, darken(primary), 0.35)
    ];
  }
  if (asset.id.includes("torn")) {
    return [
      roughPath("M22 34 C52 24 66 42 94 32 C124 20 138 42 170 34 C192 30 202 48 198 72 L188 138 C150 130 128 146 96 136 C62 126 44 146 20 132 Z", asset, seed, { fill: secondary })
    ];
  }
  if (asset.id.includes("label")) {
    return [
      roughPath("M32 50h156l-14 68H46z", asset, seed, { fill: secondary }),
      line(58, 84, 160, 84, darken(primary), 0.3)
    ];
  }
  return [
    roughShape("rectangle", [26, 24, 168, 122], asset, seed, { fill: secondary }),
    line(48, 62, 168, 62, darken(primary), 0.26),
    line(48, 86, 154, 86, darken(primary), 0.22),
    line(48, 110, 176, 110, darken(primary), 0.18)
  ];
}

function stickerShape(asset, seed) {
  const [primary, secondary] = asset.colors;
  if (asset.id.includes("sun")) {
    return [
      ...rays(80, 78, 46, primary),
      roughShape("circle", [48, 46, 66], asset, seed, { fill: secondary, fillStyle: "hachure" })
    ];
  }
  if (asset.id.includes("cloud")) {
    return [
      roughPath("M38 98 C20 96 18 70 38 64 C42 42 72 40 82 58 C100 42 132 56 126 82 C144 84 146 108 124 112 H42 C34 112 28 104 38 98 Z", asset, seed, { fill: secondary })
    ];
  }
  if (asset.id.includes("heart")) {
    return [roughPath("M80 130 C28 92 28 42 66 48 C76 50 80 58 82 64 C90 50 104 44 120 52 C150 68 130 108 80 130 Z", asset, seed, { fill: secondary })];
  }
  if (asset.id.includes("flower")) {
    return [
      roughShape("ellipse", [64, 28, 34, 54], asset, seed, { fill: secondary }),
      roughShape("ellipse", [92, 58, 42, 36], asset, seed + 1, { fill: secondary }),
      roughShape("ellipse", [62, 90, 38, 44], asset, seed + 2, { fill: secondary }),
      roughShape("ellipse", [30, 58, 44, 36], asset, seed + 3, { fill: secondary }),
      roughShape("circle", [64, 64, 34], asset, seed + 4, { fill: primary })
    ];
  }
  if (asset.id.includes("leaf")) {
    return [
      roughPath("M34 112 C56 46 106 28 132 36 C126 82 92 126 34 112 Z", asset, seed, { fill: secondary }),
      line(45, 105, 126, 42, darken(primary), 0.45)
    ];
  }
  if (asset.id.includes("coffee")) {
    return [
      roughPath("M50 56h62v38c0 26-62 26-62 0z", asset, seed, { fill: secondary }),
      roughPath("M112 66 C148 62 146 102 112 96", asset, seed + 1, { fill: "none" }),
      line(62, 44, 62, 28, darken(primary), 0.3),
      line(82, 44, 86, 26, darken(primary), 0.3)
    ];
  }
  if (asset.id.includes("camera")) {
    return [
      roughShape("rectangle", [28, 54, 104, 62], asset, seed, { fill: secondary }),
      roughShape("rectangle", [46, 42, 42, 18], asset, seed + 1, { fill: primary }),
      roughShape("circle", [80, 84, 42], asset, seed + 2, { fill: "#fffaf5" }),
      roughShape("circle", [80, 84, 20], asset, seed + 3, { fill: primary, fillStyle: "hachure" }),
      roughShape("circle", [118, 68, 9], asset, seed + 4, { fill: primary })
    ];
  }
  if (asset.id.includes("star")) {
    return [roughPath("M80 28 L94 62 L130 62 L100 84 L112 122 L80 98 L48 122 L60 84 L30 62 L66 62 Z", asset, seed, { fill: secondary })];
  }
  if (asset.id.includes("moon")) {
    return [roughPath("M104 32 C72 42 58 68 66 94 C74 120 102 132 128 118 C92 112 76 86 86 60 C90 48 96 40 104 32 Z", asset, seed, { fill: secondary })];
  }
  if (asset.id.includes("wave")) {
    return [
      roughPath("M24 94 C50 62 72 126 102 90 C120 68 134 66 146 82", asset, seed, { fill: "none", strokeWidth: 4 }),
      roughPath("M22 112 C54 82 76 138 114 106", asset, seed + 1, { fill: "none", strokeWidth: 3 })
    ];
  }
  if (asset.id.includes("birthday")) {
    return [
      roughShape("rectangle", [68, 54, 26, 66], asset, seed, { fill: secondary }),
      roughPath("M80 24 C96 42 82 52 78 52 C70 48 68 36 80 24 Z", asset, seed + 1, { fill: primary })
    ];
  }
  if (asset.id.includes("spark")) {
    return [
      roughPath("M80 22 L92 68 L136 80 L92 92 L80 138 L68 92 L24 80 L68 68 Z", asset, seed, { fill: secondary }),
      roughShape("circle", [116, 34, 12], asset, seed + 1, { fill: primary })
    ];
  }
  if (asset.id.includes("route")) {
    return [
      roughPath("M22 112 C46 84 62 102 80 76 C96 52 120 54 136 40", asset, seed, { fill: "none", strokeWidth: 4 }),
      roughPath("M120 34 L138 40 L128 58", asset, seed + 1, { fill: "none", strokeWidth: 4 }),
      ...dots([[42, 104], [66, 91], [92, 62], [118, 50]], primary, seed)
    ];
  }
  if (asset.id.includes("book")) {
    return [
      roughPath("M32 44 C54 36 70 42 80 54 V124 C66 112 50 108 32 116 Z", asset, seed, { fill: secondary }),
      roughPath("M80 54 C94 42 112 38 132 46 V118 C114 108 96 112 80 124 Z", asset, seed + 1, { fill: secondary })
    ];
  }
  if (asset.id.includes("music")) {
    return [
      roughShape("ellipse", [48, 98, 34, 24], asset, seed, { fill: secondary }),
      roughShape("ellipse", [102, 86, 34, 24], asset, seed + 1, { fill: secondary }),
      line(64, 96, 64, 38, darken(primary), 1),
      line(118, 84, 118, 26, darken(primary), 1),
      line(64, 38, 118, 26, darken(primary), 1)
    ];
  }
  if (asset.id.includes("paw")) {
    return [
      roughShape("ellipse", [80, 94, 56, 44], asset, seed, { fill: secondary }),
      roughShape("ellipse", [50, 66, 20, 26], asset, seed + 1, { fill: secondary }),
      roughShape("ellipse", [72, 48, 22, 28], asset, seed + 2, { fill: secondary }),
      roughShape("ellipse", [96, 50, 22, 28], asset, seed + 3, { fill: secondary }),
      roughShape("ellipse", [118, 70, 20, 26], asset, seed + 4, { fill: secondary })
    ];
  }
  if (asset.id.includes("picnic")) {
    return [
      roughShape("rectangle", [36, 42, 88, 80], asset, seed, { fill: secondary }),
      line(58, 44, 58, 120, darken(primary), 0.3),
      line(84, 44, 84, 120, darken(primary), 0.3),
      line(38, 68, 122, 68, darken(primary), 0.3),
      line(38, 94, 122, 94, darken(primary), 0.3)
    ];
  }
  if (asset.id.includes("train")) {
    return [
      roughShape("rectangle", [28, 66, 76, 42], asset, seed, { fill: secondary }),
      roughShape("rectangle", [96, 48, 36, 60], asset, seed + 1, { fill: secondary }),
      roughShape("rectangle", [38, 54, 20, 14], asset, seed + 2, { fill: primary }),
      roughShape("rectangle", [106, 60, 16, 16], asset, seed + 3, { fill: "#fffaf5" }),
      roughShape("circle", [50, 110, 18], asset, seed + 4, { fill: primary }),
      roughShape("circle", [100, 110, 18], asset, seed + 5, { fill: primary }),
      line(24, 126, 136, 126, darken(primary), 0.55)
    ];
  }
  if (asset.id.includes("rain_")) {
    return [
      roughPath("M42 52 C54 30 78 30 88 52 C112 48 126 64 124 82 H34 C22 78 24 58 42 52 Z", asset, seed, { fill: secondary }),
      ...dots([[52, 110], [82, 124], [112, 108]], primary, seed)
    ];
  }
  if (asset.id.includes("bow")) {
    return [
      roughPath("M78 80 C48 48 22 62 34 96 C48 122 68 98 78 84 Z", asset, seed, { fill: secondary, roughness: 0.75 }),
      roughPath("M82 80 C112 48 138 62 126 96 C112 122 92 98 82 84 Z", asset, seed + 1, { fill: secondary, roughness: 0.75 }),
      roughShape("ellipse", [80, 82, 30, 28], asset, seed + 2, { fill: primary, roughness: 0.7 }),
      line(54, 78, 35, 62, darken(primary), 0.36),
      line(106, 78, 125, 62, darken(primary), 0.36)
    ];
  }
  return [roughShape("circle", [42, 42, 76], asset, seed, { fill: secondary })];
}

function textureShape(asset, seed) {
  const [primary] = asset.colors;
  const stroke = darken(primary);
  if (asset.id.includes("dots")) {
    return dots(
      Array.from({ length: 28 }, (_, index) => [24 + (index % 7) * 28, 24 + Math.floor(index / 7) * 30]),
      primary,
      seed
    );
  }
  if (asset.id.includes("grid")) {
    return [
      ...Array.from({ length: 5 }, (_, index) => line(24 + index * 38, 16, 24 + index * 38, 144, stroke, 0.22)),
      ...Array.from({ length: 4 }, (_, index) => line(14, 28 + index * 34, 204, 28 + index * 34, stroke, 0.22))
    ];
  }
  if (asset.id.includes("wave")) {
    return Array.from({ length: 5 }, (_, index) =>
      roughPath(
        `M18 ${34 + index * 20} C54 ${18 + index * 20} 84 ${50 + index * 20} 120 ${34 + index * 20} S178 ${18 + index * 20} 206 ${34 + index * 20}`,
        asset,
        seed + index,
        { fill: "none", strokeWidth: 2, roughness: 0.75 }
      )
    );
  }
  if (asset.id.includes("scribble")) {
    return Array.from({ length: 6 }, (_, index) =>
      roughPath(`M28 ${34 + index * 18} C58 ${18 + index * 22} 92 ${58 + index * 8} 126 ${34 + index * 16} C150 ${18 + index * 18} 174 ${44 + index * 16} 194 ${30 + index * 16}`, asset, seed + index, { fill: "none", strokeWidth: 2 })
    );
  }
  if (asset.id.includes("dash")) {
    return Array.from({ length: 25 }, (_, index) => line(24 + (index % 5) * 38, 28 + Math.floor(index / 5) * 24, 38 + (index % 5) * 38, 24 + Math.floor(index / 5) * 24, stroke, 0.42));
  }
  if (asset.id.includes("flower")) {
    return dots([[42, 38], [96, 72], [154, 38], [62, 118], [168, 118]], primary, seed);
  }
  if (asset.id.includes("sun")) {
    return [
      ...dots([[42, 44], [108, 82], [166, 44], [72, 122], [182, 122]], primary, seed),
      ...Array.from({ length: 4 }, (_, index) => line(42 + index * 42, 22, 50 + index * 42, 12, stroke, 0.3))
    ];
  }
  return [
    roughPath("M30 128 C58 58 104 28 184 34", asset, seed, { fill: "none", strokeWidth: 3 }),
    roughPath("M52 116 C86 84 124 64 190 74", asset, seed + 1, { fill: "none", strokeWidth: 2 })
  ];
}

function line(x1, y1, x2, y2, stroke, opacity = 1, dash = "") {
  const dashAttribute = dash ? ` stroke-dasharray="${dash}"` : "";
  return `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${stroke}" stroke-width="2" stroke-linecap="round" opacity="${opacity}"${dashAttribute}/>`;
}

function dots(points, color, seed) {
  return points.map(([x, y], index) => {
    const radius = 4 + ((seed + index) % 4);
    return `<circle cx="${x}" cy="${y}" r="${radius}" fill="${color}" opacity="0.42"/>`;
  });
}

function rays(cx, cy, radius, color) {
  return Array.from({ length: 10 }, (_, index) => {
    const angle = (Math.PI * 2 * index) / 10;
    const x1 = Math.round(cx + Math.cos(angle) * (radius + 8));
    const y1 = Math.round(cy + Math.sin(angle) * (radius + 8));
    const x2 = Math.round(cx + Math.cos(angle) * (radius + 22));
    const y2 = Math.round(cy + Math.sin(angle) * (radius + 22));
    return line(x1, y1, x2, y2, darken(color), 0.55);
  });
}

function darken(hex) {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((start) => Math.max(0, Math.round(parseInt(value.slice(start, start + 2), 16) * 0.68)));
  return `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}
