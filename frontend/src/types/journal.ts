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
  meta?: string | null;
  body: string[];
  captions: JournalCaption[];
  imageUnderstanding?: JournalImageUnderstanding[];
  sections?: JournalContentSection[];
};

export type JournalImageUnderstanding = {
  imageId: string;
  summary: string;
  scene: string;
  subjects: string[];
  mood: string[];
};

export type JournalContentSection = {
  id: string;
  title: string;
  imageIds: string[];
  body: string;
  mood: string[];
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
  role: "title" | "meta" | "body" | "caption";
  imageId?: string | null;
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
  sections?: JournalLayoutSection[];
};

export type JournalLayoutSection = {
  sectionId: string;
  variant: string;
  y: number;
  height: number;
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
