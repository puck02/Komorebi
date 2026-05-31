import type { Asset } from "../types/asset";
import type { JournalLayout } from "../types/journal";

type JournalCanvasImage = {
  id: string;
  src: string;
  alt?: string;
};

type Props = {
  layout: JournalLayout;
  images: JournalCanvasImage[];
  assets: Asset[];
  scale?: number;
};

export default function JournalCanvas({ assets, images, layout, scale = 0.42 }: Props) {
  const imageMap = new Map(images.map((image) => [image.id, image]));
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
  const titlePlacement = layout.layout.texts.find((text) => text.role === "title");
  const bodyPlacement = layout.layout.texts.find((text) => text.role === "body");

  return (
    <div className="journal-canvas-frame" style={{ width: layout.canvas.width * scale }}>
      <div
        className="journal-canvas"
        style={{
          background: layout.canvas.background,
          height: layout.canvas.height,
          transform: `scale(${scale})`,
          width: layout.canvas.width
        }}
      >
        <PaperTexture />

        {layout.layout.images.map((placement) => {
          const image = imageMap.get(placement.imageId);
          if (!image) {
            return null;
          }

          return (
            <figure
              className="journal-photo"
              key={placement.imageId}
              style={{
                height: placement.height,
                left: placement.x,
                top: placement.y,
                transform: `rotate(${placement.rotation}deg)`,
                width: placement.width
              }}
            >
              <img alt={image.alt ?? ""} src={image.src} />
            </figure>
          );
        })}

        {layout.layout.decorations.map((decoration) => {
          const asset = assetMap.get(decoration.assetId);
          if (!asset) {
            return null;
          }

          return (
            <img
              alt=""
              className="journal-decoration"
              key={`${decoration.assetId}-${decoration.x}-${decoration.y}`}
              src={asset.file_url}
              style={{
                height: decoration.height,
                left: decoration.x,
                top: decoration.y,
                transform: `rotate(${decoration.rotation}deg)`,
                width: decoration.width
              }}
            />
          );
        })}

        <section
          className="journal-title"
          style={{
            fontSize: titlePlacement?.fontSize ?? 56,
            left: titlePlacement?.x ?? 80,
            top: titlePlacement?.y ?? 72,
            width: titlePlacement?.width ?? 720
          }}
        >
          {layout.content.title}
        </section>

        <section
          className="journal-body"
          style={{
            fontSize: bodyPlacement?.fontSize ?? 28,
            left: bodyPlacement?.x ?? 80,
            top: bodyPlacement?.y ?? 1040,
            width: bodyPlacement?.width ?? 760
          }}
        >
          {layout.content.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </section>
      </div>
    </div>
  );
}

function PaperTexture() {
  return (
    <svg className="journal-paper-texture" aria-hidden="true" viewBox="0 0 1080 1440">
      <path d="M88 156C240 132 382 150 548 126C710 102 854 104 990 136" />
      <path d="M78 1264C248 1228 442 1248 612 1218C760 1192 896 1204 1010 1228" />
      <path d="M126 364C254 338 394 372 522 344C668 312 814 320 948 352" />
      <path d="M104 832C246 806 382 828 520 808C704 782 850 782 980 812" />
    </svg>
  );
}
