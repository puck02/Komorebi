import type { UploadedImage } from "../api/images";

export type JournalTemplateId =
  | "quiet_story"
  | "hero_memory"
  | "timeline_trip"
  | "pocket_grid"
  | "ticket_day"
  | "magazine_note"
  | "before_after"
  | "moodboard_stack"
  | "recipe_memo"
  | "letter_page";

export type JournalTemplate = {
  id: JournalTemplateId;
  name: string;
  shortDescription: string;
  bestFor: string;
  previewClassName: string;
  minImages: number;
  maxImages: number;
  keywords: string[];
};

export const JOURNAL_TEMPLATES: JournalTemplate[] = [
  {
    id: "quiet_story",
    name: "留白独白",
    shortDescription: "一张主图加大段手写记录，像把当天慢慢说完。",
    bestFor: "1-2 张安静照片",
    previewClassName: "is-quiet-story",
    minImages: 1,
    maxImages: 2,
    keywords: ["安静", "慢", "窗边", "独处", "光", "平静"]
  },
  {
    id: "hero_memory",
    name: "主照片日记",
    shortDescription: "主图占据视线，文字围绕一个具体瞬间展开。",
    bestFor: "1 张核心照片",
    previewClassName: "is-hero-memory",
    minImages: 1,
    maxImages: 2,
    keywords: ["重要", "纪念", "今天", "周末", "散步"]
  },
  {
    id: "timeline_trip",
    name: "时间线小旅行",
    shortDescription: "按顺序把出发、途中、停留串成一段故事。",
    bestFor: "2-6 张过程照片",
    previewClassName: "is-timeline-trip",
    minImages: 2,
    maxImages: 6,
    keywords: ["旅行", "路上", "出发", "抵达", "车站", "路线", "沿途"]
  },
  {
    id: "pocket_grid",
    name: "口袋页",
    shortDescription: "像收藏夹一样分格收纳照片和短句，适合多片段。",
    bestFor: "4-9 张照片",
    previewClassName: "is-pocket-grid",
    minImages: 4,
    maxImages: 9,
    keywords: ["很多", "合集", "一天", "碎片", "相册"]
  },
  {
    id: "ticket_day",
    name: "票根备忘",
    shortDescription: "照片、票据和便签一起出现，像展览或咖啡店小记。",
    bestFor: "咖啡、展览、电影",
    previewClassName: "is-ticket-day",
    minImages: 1,
    maxImages: 4,
    keywords: ["咖啡", "展览", "博物馆", "电影", "票", "小票", "餐厅"]
  },
  {
    id: "magazine_note",
    name: "杂志留白",
    shortDescription: "照片不抢占整页，文字像一段清爽的版面专栏。",
    bestFor: "1-3 张氛围照片",
    previewClassName: "is-magazine-note",
    minImages: 1,
    maxImages: 3,
    keywords: ["留白", "杂志", "简洁", "光线", "下午"]
  },
  {
    id: "before_after",
    name: "前后对照",
    shortDescription: "用两到三张图讲变化：开始、过程、后来。",
    bestFor: "2-3 张对照照片",
    previewClassName: "is-before-after",
    minImages: 2,
    maxImages: 3,
    keywords: ["之前", "之后", "变化", "开始", "后来", "完成"]
  },
  {
    id: "moodboard_stack",
    name: "情绪堆叠",
    shortDescription: "错落照片和短句叠在一起，保留随手贴的感觉。",
    bestFor: "2-5 张生活碎片",
    previewClassName: "is-moodboard-stack",
    minImages: 2,
    maxImages: 5,
    keywords: ["开心", "松快", "热闹", "日常", "朋友"]
  },
  {
    id: "recipe_memo",
    name: "餐桌配方",
    shortDescription: "把餐桌、咖啡、甜点写成有味道的小备忘。",
    bestFor: "食物、咖啡、餐厅",
    previewClassName: "is-recipe-memo",
    minImages: 1,
    maxImages: 4,
    keywords: ["吃", "餐", "咖啡", "甜品", "饭", "茶", "面包"]
  },
  {
    id: "letter_page",
    name: "写给今天",
    shortDescription: "像信纸一样展开，适合把心情写得更完整。",
    bestFor: "想重点写文字时",
    previewClassName: "is-letter-page",
    minImages: 1,
    maxImages: 3,
    keywords: ["想说", "记录", "心情", "纪念", "给"]
  }
];

export function recommendJournalTemplates(
  images: UploadedImage[],
  text: string,
  mood: string
): JournalTemplate[] {
  const query = `${text} ${mood}`.toLowerCase();
  const scored = JOURNAL_TEMPLATES.map((template, index) => {
    let score = 0;
    if (images.length >= template.minImages && images.length <= template.maxImages) {
      score += 8;
    }
    if (images.length > template.maxImages) {
      score -= Math.min(images.length - template.maxImages, 4);
    }
    if (images.length < template.minImages) {
      score -= 3;
    }
    score += template.keywords.filter((keyword) => query.includes(keyword.toLowerCase())).length * 5;
    if (template.id === "pocket_grid" && images.length >= 5) {
      score += 6;
    }
    if (template.id === "timeline_trip" && images.length >= 3) {
      score += 3;
    }
    if (template.id === "quiet_story" && hasPortraitDominance(images)) {
      score += 2;
    }
    return { index, score, template };
  });

  return scored
    .sort((first, second) => second.score - first.score || first.index - second.index)
    .slice(0, 3)
    .map((item) => item.template);
}

function hasPortraitDominance(images: UploadedImage[]) {
  if (images.length === 0) {
    return false;
  }
  const portraitCount = images.filter((image) => image.height > image.width).length;
  return portraitCount >= Math.ceil(images.length / 2);
}
