export type JournalCanvasConfig = {
  width: 1080;
  height: number;
  background: string;
};

export type JournalTheme = {
  style: string;
  palette: string[];
  mood: string[];
};

export type JournalCaption = {
  imageId: string;
  text: string;
};

export type JournalContent = {
  title: string;
  body: string[];
  captions: JournalCaption[];
};

export type JournalImagePlacement = {
  imageId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
};

export type JournalTextPlacement = {
  role: "title" | "body" | "caption";
  x: number;
  y: number;
  width: number;
  fontSize: number;
};

export type JournalDecoration = {
  assetId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
};

export type JournalLayoutLayer = {
  variant: string;
  images: JournalImagePlacement[];
  texts: JournalTextPlacement[];
  decorations: JournalDecoration[];
};

export type JournalLayout = {
  canvas: JournalCanvasConfig;
  theme: JournalTheme;
  content: JournalContent;
  layout: JournalLayoutLayer;
};
