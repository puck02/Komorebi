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
  onImageClick?: (imageId: string) => void;
  scale?: number;
};

export default function JournalCanvas({ assets, images, layout, onImageClick, scale = 0.42 }: Props) {
  const imageMap = new Map(images.map((image) => [image.id, image]));
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
  const titlePlacement = layout.layout.texts.find((text) => text.role === "title");
  const bodyPlacement = layout.layout.texts.find((text) => text.role === "body");
  const scaledWidth = layout.canvas.width * scale;
  const scaledHeight = layout.canvas.height * scale;
  const backgroundDecorations = layout.layout.decorations.filter((decoration) =>
    isBackgroundDecoration(assetMap.get(decoration.assetId)?.category)
  );
  const foregroundDecorations = layout.layout.decorations.filter(
    (decoration) => !isBackgroundDecoration(assetMap.get(decoration.assetId)?.category)
  );

  return (
    <div className="journal-canvas-frame" style={{ height: scaledHeight, width: scaledWidth }}>
      <div
        className="journal-canvas"
        style={{
          background: layout.canvas.background,
          height: layout.canvas.height,
          transform: `scale(${scale})`,
          width: layout.canvas.width
        }}
      >
        <PaperTexture height={layout.canvas.height} />
        {backgroundDecorations.map((decoration) => (
          <JournalDecorationImage
            asset={assetMap.get(decoration.assetId)}
            decoration={decoration}
            key={`${decoration.assetId}-${decoration.x}-${decoration.y}`}
          />
        ))}

        {layout.layout.images.map((placement) => {
          const image = imageMap.get(placement.imageId);

          return (
            <figure
              aria-hidden={image ? undefined : "true"}
              className={`journal-photo ${image ? "" : "journal-photo-placeholder"}`}
              key={placement.imageId}
              onClick={image ? () => onImageClick?.(placement.imageId) : undefined}
              onKeyDown={(event) => {
                if (image && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  onImageClick?.(placement.imageId);
                }
              }}
              role={image && onImageClick ? "button" : undefined}
              style={{
                height: placement.height,
                left: placement.x,
                top: placement.y,
                transform: `rotate(${placement.rotation}deg)`,
                width: placement.width
              }}
              tabIndex={image && onImageClick ? 0 : undefined}
            >
              {image ? <img alt={image.alt ?? ""} src={image.src} /> : <span>加载中</span>}
            </figure>
          );
        })}

        {foregroundDecorations.map((decoration) => (
          <JournalDecorationImage
            asset={assetMap.get(decoration.assetId)}
            decoration={decoration}
            key={`${decoration.assetId}-${decoration.x}-${decoration.y}`}
          />
        ))}

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

type JournalDecorationImageProps = {
  asset?: Asset;
  decoration: JournalLayout["layout"]["decorations"][number];
};

function JournalDecorationImage({ asset, decoration }: JournalDecorationImageProps) {
  if (!asset) {
    return null;
  }

  return (
    <img
      alt=""
      className={`journal-decoration journal-decoration-${asset.category}`}
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
}

function isBackgroundDecoration(category?: string) {
  return category === "paper" || category === "texture";
}

type PaperTextureProps = {
  height: number;
};

function PaperTexture({ height }: PaperTextureProps) {
  const bottomY = Math.max(height - 176, 1264);
  const lowerY = Math.max(height - 612, 832);

  return (
    <svg className="journal-paper-texture" aria-hidden="true" style={{ height }} viewBox={`0 0 1080 ${height}`}>
      <path d="M88 156C240 132 382 150 548 126C710 102 854 104 990 136" />
      <path
        d={`M78 ${bottomY}C248 ${bottomY - 36} 442 ${bottomY - 16} 612 ${bottomY - 46}C760 ${bottomY - 72} 896 ${bottomY - 60} 1010 ${bottomY - 36}`}
      />
      <path d="M126 364C254 338 394 372 522 344C668 312 814 320 948 352" />
      <path
        d={`M104 ${lowerY}C246 ${lowerY - 26} 382 ${lowerY - 4} 520 ${lowerY - 24}C704 ${lowerY - 50} 850 ${lowerY - 50} 980 ${lowerY - 20}`}
      />
    </svg>
  );
}
