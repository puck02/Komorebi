import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "frontend", "package.json"));
const rough = require("roughjs");

const assetRoot = path.join(root, "backend", "app", "assets");
const manifestPath = path.join(assetRoot, "manifest.json");
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

await Promise.all(
  manifest.filter((asset) => asset.source === "internal").map((asset, index) => {
    const svg = renderAsset(asset, index + 1);
    return writeFile(path.join(assetRoot, asset.file), svg, "utf8");
  })
);

console.log(`Generated ${manifest.filter((asset) => asset.source === "internal").length} internal assets.`);

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
      `<path d="M76 80C50 48 25 58 31 93c5 30 31 22 45-8Z" fill="#fff0f2" stroke="#946971" stroke-width="3" stroke-linejoin="round"/>`,
      `<path d="M84 80c26-32 51-22 45 13c-5 30-31 22-45-8Z" fill="#fff0f2" stroke="#946971" stroke-width="3" stroke-linejoin="round"/>`,
      `<ellipse cx="80" cy="82" rx="17" ry="16" fill="#d99aa6" stroke="#946971" stroke-width="3"/>`,
      `<path d="M57 79L36 63M103 79l21-16M58 91c6-1 11-4 16-9M102 91c-6-1-11-4-16-9" stroke="#946971" stroke-width="2" stroke-linecap="round" opacity="0.45"/>`
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
