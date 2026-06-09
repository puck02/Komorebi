import type { Asset } from "../types/asset";
import type { JournalLayout, JournalTextPlacement } from "../types/journal";
import type { Ref } from "react";

import { getJournalRenderLayers } from "./journalRenderLayers";

type JournalCanvasImage = {
  id: string;
  src: string;
  alt?: string;
};

type Props = {
  layout: JournalLayout;
  images: JournalCanvasImage[];
  assets: Asset[];
  canvasRef?: Ref<HTMLDivElement>;
  editableTextKey?: string | null;
  editableTextValue?: string;
  onEditableTextCancel?: () => void;
  onEditableTextChange?: (value: string) => void;
  onEditableTextSave?: () => void;
  onImageClick?: (imageId: string) => void;
  onTextDoubleClick?: (key: string, value: string) => void;
  scale?: number;
};

export default function JournalCanvas({
  assets,
  canvasRef,
  editableTextKey,
  editableTextValue = "",
  images,
  layout,
  onEditableTextCancel,
  onEditableTextChange,
  onEditableTextSave,
  onImageClick,
  onTextDoubleClick,
  scale = 0.42
}: Props) {
  const imageMap = new Map(images.map((image) => [image.id, image]));
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
  const renderLayers = getJournalRenderLayers(layout);
  const titlePlacement = renderLayers.titlePlacement;
  const scaledWidth = layout.canvas.width * scale;
  const scaledHeight = layout.canvas.height * scale;
  const backgroundDecorations = renderLayers.decorations.filter((decoration) =>
    isBackgroundDecoration(assetMap.get(decoration.assetId)?.category)
  );
  const foregroundDecorations = renderLayers.decorations.filter(
    (decoration) => !isBackgroundDecoration(assetMap.get(decoration.assetId)?.category)
  );

  return (
    <div className="journal-canvas-frame" style={{ height: scaledHeight, width: scaledWidth }}>
      <div
        className="journal-canvas"
        ref={canvasRef}
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

        <div className={renderLayers.usesSections ? "journal-section-layer" : undefined}>
          {renderLayers.images.map((placement) => {
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
        </div>

        {foregroundDecorations.map((decoration) => (
          <JournalDecorationImage
            asset={assetMap.get(decoration.assetId)}
            decoration={decoration}
            key={`${decoration.assetId}-${decoration.x}-${decoration.y}`}
          />
        ))}

        <JournalTextBlock
          className="journal-title"
          editableTextKey={editableTextKey}
          editableTextValue={editableTextValue}
          keyName="title"
          onEditableTextCancel={onEditableTextCancel}
          onEditableTextChange={onEditableTextChange}
          onEditableTextSave={onEditableTextSave}
          onTextDoubleClick={onTextDoubleClick}
          paragraph={layout.content.title}
          placement={{
            role: "title",
            fontSize: titlePlacement?.fontSize ?? 56,
            x: titlePlacement?.x ?? 80,
            y: titlePlacement?.y ?? 72,
            width: titlePlacement?.width ?? 720
          }}
          tag="section"
        />

        {renderLayers.metaTexts.map(({ key, paragraph, placement }) => (
          <JournalTextBlock
            className="journal-meta"
            editableTextKey={editableTextKey}
            editableTextValue={editableTextValue}
            key={key}
            keyName={key}
            onEditableTextCancel={onEditableTextCancel}
            onEditableTextChange={onEditableTextChange}
            onEditableTextSave={onEditableTextSave}
            onTextDoubleClick={onTextDoubleClick}
            paragraph={paragraph}
            placement={placement}
            tag="section"
          />
        ))}

        {renderLayers.sectionTitleTexts.map(({ key, paragraph, placement }) => (
          <JournalTextBlock
            className="journal-section-title"
            editableTextKey={editableTextKey}
            editableTextValue={editableTextValue}
            key={key}
            keyName={key}
            onEditableTextCancel={onEditableTextCancel}
            onEditableTextChange={onEditableTextChange}
            onEditableTextSave={onEditableTextSave}
            onTextDoubleClick={onTextDoubleClick}
            paragraph={paragraph}
            placement={placement}
            tag="section"
          />
        ))}

        {renderLayers.bodyTexts.map(({ key, paragraph, placement }) => (
          <JournalTextBlock
            className="journal-body"
            editableTextKey={editableTextKey}
            editableTextValue={editableTextValue}
            key={key}
            keyName={key}
            onEditableTextCancel={onEditableTextCancel}
            onEditableTextChange={onEditableTextChange}
            onEditableTextSave={onEditableTextSave}
            onTextDoubleClick={onTextDoubleClick}
            paragraph={paragraph}
            placement={placement}
            tag="section"
          />
        ))}

        {renderLayers.captionTexts.map(({ key, paragraph, placement }) => (
          <JournalTextBlock
            className="journal-caption"
            editableTextKey={editableTextKey}
            editableTextValue={editableTextValue}
            key={key}
            keyName={key}
            onEditableTextCancel={onEditableTextCancel}
            onEditableTextChange={onEditableTextChange}
            onEditableTextSave={onEditableTextSave}
            onTextDoubleClick={onTextDoubleClick}
            paragraph={paragraph}
            placement={placement}
            tag="figcaption"
          />
        ))}
      </div>
    </div>
  );
}

type JournalTextBlockProps = {
  className: string;
  editableTextKey?: string | null;
  editableTextValue: string;
  keyName: string;
  onEditableTextCancel?: () => void;
  onEditableTextChange?: (value: string) => void;
  onEditableTextSave?: () => void;
  onTextDoubleClick?: (key: string, value: string) => void;
  paragraph: string;
  placement: JournalTextPlacement;
  tag: "section" | "figcaption";
};

function JournalTextBlock({
  className,
  editableTextKey,
  editableTextValue,
  keyName,
  onEditableTextCancel,
  onEditableTextChange,
  onEditableTextSave,
  onTextDoubleClick,
  paragraph,
  placement,
  tag
}: JournalTextBlockProps) {
  const Component = tag;
  const isEditing = editableTextKey === keyName;
  const canEdit = Boolean(onTextDoubleClick);

  return (
    <Component
      className={`${className}${canEdit ? " journal-editable-text" : ""}${isEditing ? " is-editing" : ""}`}
      onDoubleClick={canEdit ? () => onTextDoubleClick?.(keyName, paragraph) : undefined}
      style={{
        fontSize: placement.fontSize,
        left: placement.x,
        top: placement.y,
        width: placement.width
      }}
      title={canEdit ? "双击编辑文字" : undefined}
    >
      {isEditing ? (
        <span className="journal-text-edit-shell">
          <textarea
            aria-label="编辑手帐文字"
            onChange={(event) => onEditableTextChange?.(event.target.value)}
            value={editableTextValue}
          />
          <span className="journal-text-edit-actions">
            <button onClick={onEditableTextCancel} type="button">
              取消
            </button>
            <button onClick={onEditableTextSave} type="button">
              保存
            </button>
          </span>
        </span>
      ) : className === "journal-body" ? (
        <p>{paragraph}</p>
      ) : (
        paragraph
      )}
    </Component>
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

  if (asset.category === "paper") {
    const isNotePaper = isNotePaperAsset(asset);

    return (
      <div
        aria-hidden="true"
        className={`journal-decoration journal-decoration-paper journal-decoration-paper-surface${
          isNotePaper ? " journal-decoration-paper-note-surface" : ""
        }`}
        style={{
          ...(isNotePaper
            ? {
                backgroundColor: "#fff7ed",
                border: "1px solid rgb(194 164 132 / 44%)",
                borderRadius: 18
              }
            : {}),
          backgroundImage: `url("${asset.file_url}")`,
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          backgroundSize: paperBackgroundSize(asset),
          height: decoration.height,
          left: decoration.x,
          top: decoration.y,
          transform: `rotate(${decoration.rotation}deg)`,
          width: decoration.width
        }}
      />
    );
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

function paperBackgroundSize(asset: Asset) {
  return isNotePaperAsset(asset) ? "126% 138%" : "100% 100%";
}

function isNotePaperAsset(asset: Asset) {
  return asset.tags.includes("note") || asset.id.includes("_note_");
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
