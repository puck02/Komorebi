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
  | "letter_page"
  | "chapter_scroll"
  | "field_notes"
  | "split_scene"
  | "detail_index";

export type JournalTemplate = {
  id: JournalTemplateId;
  name: string;
  shortDescription: string;
  bestFor: string;
  storyArc: string;
  previewClassName: string;
  minImages: number;
  maxImages: number;
  keywords: string[];
  family: string;
};

export type JournalTemplateRecommendation = JournalTemplate & {
  recommendationReason: string;
};

export const JOURNAL_TEMPLATES: JournalTemplate[] = [
  {
    id: "quiet_story",
    name: "留白独白",
    shortDescription: "一张主图加大段手写记录，像把当天慢慢说完。",
    bestFor: "1-2 张安静照片",
    storyArc: "先看见一个瞬间，再把当时的感受写完整。",
    previewClassName: "is-quiet-story",
    minImages: 1,
    maxImages: 2,
    family: "reflective",
    keywords: ["安静", "慢", "窗边", "独处", "光", "平静"]
  },
  {
    id: "hero_memory",
    name: "主照片日记",
    shortDescription: "主图占据视线，文字围绕一个具体瞬间展开。",
    bestFor: "1 张核心照片",
    storyArc: "把最重要的一张照片当成开场，其他内容都围着它讲。",
    previewClassName: "is-hero-memory",
    minImages: 1,
    maxImages: 2,
    family: "focus",
    keywords: ["重要", "纪念", "今天", "周末", "散步"]
  },
  {
    id: "timeline_trip",
    name: "时间线小旅行",
    shortDescription: "按顺序把出发、途中、停留串成一段故事。",
    bestFor: "2-6 张过程照片",
    storyArc: "从开始到后来，照片顺序就是页面阅读顺序。",
    previewClassName: "is-timeline-trip",
    minImages: 2,
    maxImages: 6,
    family: "sequence",
    keywords: ["旅行", "路上", "出发", "抵达", "车站", "路线", "沿途"]
  },
  {
    id: "pocket_grid",
    name: "口袋页",
    shortDescription: "像收藏夹一样分格收纳照片和短句，适合多片段。",
    bestFor: "4-9 张照片",
    storyArc: "把一天拆成几个小口袋，每格是一件被留下的小事。",
    previewClassName: "is-pocket-grid",
    minImages: 4,
    maxImages: 9,
    family: "collection",
    keywords: ["很多", "合集", "一天", "碎片", "相册", "photo dump"]
  },
  {
    id: "ticket_day",
    name: "票根备忘",
    shortDescription: "照片、票据和便签一起出现，像展览或咖啡店小记。",
    bestFor: "咖啡、展览、电影",
    storyArc: "用票据和便签感记录去过哪里、停在哪里、看见什么。",
    previewClassName: "is-ticket-day",
    minImages: 1,
    maxImages: 4,
    family: "ephemera",
    keywords: ["咖啡", "展览", "博物馆", "电影", "票", "小票", "餐厅"]
  },
  {
    id: "magazine_note",
    name: "杂志留白",
    shortDescription: "照片不抢占整页，文字像一段清爽的版面专栏。",
    bestFor: "1-3 张氛围照片",
    storyArc: "像杂志内页一样保留留白，让照片和文字都有呼吸。",
    previewClassName: "is-magazine-note",
    minImages: 1,
    maxImages: 3,
    family: "editorial",
    keywords: ["留白", "杂志", "简洁", "光线", "下午"]
  },
  {
    id: "before_after",
    name: "前后对照",
    shortDescription: "用两到三张图讲变化：开始、过程、后来。",
    bestFor: "2-3 张对照照片",
    storyArc: "对比两个时刻，让变化本身成为故事。",
    previewClassName: "is-before-after",
    minImages: 2,
    maxImages: 3,
    family: "contrast",
    keywords: ["之前", "之后", "变化", "开始", "后来", "完成"]
  },
  {
    id: "moodboard_stack",
    name: "情绪堆叠",
    shortDescription: "错落照片和短句叠在一起，保留随手贴的感觉。",
    bestFor: "2-5 张生活碎片",
    storyArc: "不强调时间顺序，而是把同一种心情贴在一页上。",
    previewClassName: "is-moodboard-stack",
    minImages: 2,
    maxImages: 5,
    family: "mood",
    keywords: ["开心", "松快", "热闹", "日常", "朋友"]
  },
  {
    id: "recipe_memo",
    name: "餐桌配方",
    shortDescription: "把餐桌、咖啡、甜点写成有味道的小备忘。",
    bestFor: "食物、咖啡、餐厅",
    storyArc: "像写一张配方卡一样记录今天吃到的味道。",
    previewClassName: "is-recipe-memo",
    minImages: 1,
    maxImages: 4,
    family: "food",
    keywords: ["吃", "餐", "咖啡", "甜品", "饭", "茶", "面包"]
  },
  {
    id: "letter_page",
    name: "写给今天",
    shortDescription: "像信纸一样展开，适合把心情写得更完整。",
    bestFor: "想重点写文字时",
    storyArc: "照片只做旁证，主角是一段写给今天的话。",
    previewClassName: "is-letter-page",
    minImages: 1,
    maxImages: 3,
    family: "letter",
    keywords: ["想说", "记录", "心情", "纪念", "给"]
  },
  {
    id: "chapter_scroll",
    name: "长卷章节",
    shortDescription: "把多张照片分成连续章节，像从上往下读一篇小故事。",
    bestFor: "3-9 张连续记录",
    storyArc: "开头、转场、结尾依次出现，适合完整一天或一次出门。",
    previewClassName: "is-chapter-scroll",
    minImages: 3,
    maxImages: 9,
    family: "sequence",
    keywords: ["一整天", "完整", "连续", "过程", "故事", "章节", "从早到晚"]
  },
  {
    id: "field_notes",
    name: "观察手记",
    shortDescription: "照片像采样标本，旁边写下看见的细节和小结论。",
    bestFor: "1-5 张细节照片",
    storyArc: "从一个细节开始，写成观察、补充、想到的事。",
    previewClassName: "is-field-notes",
    minImages: 1,
    maxImages: 5,
    family: "observation",
    keywords: ["细节", "观察", "发现", "植物", "书", "物件", "角落"]
  },
  {
    id: "split_scene",
    name: "双场景切换",
    shortDescription: "把两个地点或两种状态分开放，保留中间的转场。",
    bestFor: "2-4 张两段式照片",
    storyArc: "先讲一个场景，再切到另一个场景，中间留下转场感。",
    previewClassName: "is-split-scene",
    minImages: 2,
    maxImages: 4,
    family: "contrast",
    keywords: ["上午", "下午", "室内", "室外", "转场", "两个地方", "换了"]
  },
  {
    id: "detail_index",
    name: "细节索引",
    shortDescription: "一张主图带几个编号细节，像给当天做一页索引。",
    bestFor: "3-8 张主题相近照片",
    storyArc: "主图定调，细节图负责补充那些容易忘的小东西。",
    previewClassName: "is-detail-index",
    minImages: 3,
    maxImages: 8,
    family: "observation",
    keywords: ["细节", "索引", "清单", "编号", "几样", "小东西", "主题"]
  }
];

const FOOD_TERMS = ["咖啡", "茶", "甜品", "餐厅", "餐桌", "饭", "面包", "蛋糕", "饮料", "食物"];
const EPHEMERA_TERMS = ["票", "票根", "小票", "展览", "展厅", "博物馆", "电影", "标签", "收据", "车票"];
const JOURNEY_TERMS = ["旅行", "旅程", "出门", "路上", "出发", "抵达", "车站", "地铁", "公交", "路线", "沿途", "散步"];
const CHRONOLOGY_TERMS = ["早上", "上午", "中午", "下午", "傍晚", "晚上", "后来", "最后", "从早到晚", "过程", "连续"];
const CONTRAST_TERMS = ["之前", "之后", "前后", "变化", "完成", "开始", "后来", "对比", "两个地方", "室内", "室外", "转场"];
const DETAIL_TERMS = ["细节", "观察", "发现", "植物", "书", "物件", "角落", "编号", "索引", "清单", "小东西"];
const REFLECTIVE_TERMS = ["想说", "心情", "写给", "独处", "平静", "安静", "慢", "纪念", "记下来"];
const SOCIAL_TERMS = ["朋友", "一起", "家人", "聚会", "热闹", "约会", "同事", "陪"];
const FRAGMENT_TERMS = ["很多", "合集", "碎片", "相册", "photo dump", "几张", "几样", "一天"];

export function recommendJournalTemplates(
  images: UploadedImage[],
  text: string,
  mood: string
): JournalTemplateRecommendation[] {
  return recommendLocalJournalTemplates(images, text, mood);
}

export function recommendLocalJournalTemplates(
  images: UploadedImage[],
  text: string,
  mood: string
): JournalTemplateRecommendation[] {
  const query = `${text} ${mood}`.toLowerCase();
  const imageProfile = describeImages(images);
  const storySignals = detectStorySignals(images, query, imageProfile);
  const scored = JOURNAL_TEMPLATES.map((template, index) => {
    const keywordHits = template.keywords.filter((keyword) => query.includes(keyword.toLowerCase()));
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
    score += keywordHits.length * 5;
    score += bonusScore(template, images, imageProfile, storySignals);
    return { index, keywordHits, score, template };
  });

  scored.sort((first, second) => second.score - first.score || first.index - second.index);
  return selectDiverseTemplates(scored).map((item) => ({
    ...item.template,
    recommendationReason: recommendationReason(item.template, images, item.keywordHits, imageProfile, storySignals)
  }));
}

function bonusScore(
  template: JournalTemplate,
  images: UploadedImage[],
  imageProfile: ReturnType<typeof describeImages>,
  storySignals: ReturnType<typeof detectStorySignals>
) {
  let score = 0;
  if (template.id === "pocket_grid") {
    score += images.length >= 5 ? 6 : 0;
    score += storySignals.fragments ? 4 : 0;
  }
  if (template.id === "chapter_scroll") {
    score += images.length >= 5 ? 5 : 0;
    score += storySignals.chronology ? 5 : 0;
    score += storySignals.journey ? 3 : 0;
  }
  if (template.id === "detail_index") {
    score += images.length >= 4 && imageProfile.hasMixedOrientation ? 4 : 0;
    score += storySignals.detail ? 5 : 0;
  }
  if (template.id === "timeline_trip") {
    score += images.length >= 3 ? 3 : 0;
    score += storySignals.journey ? 6 : 0;
    score += storySignals.chronology ? 3 : 0;
  }
  if (template.id === "quiet_story") {
    score += imageProfile.hasPortraitDominance ? 2 : 0;
    score += storySignals.reflective ? 4 : 0;
  }
  if (template.id === "split_scene") {
    score += images.length >= 2 && images.length <= 4 && storySignals.twoScene ? 6 : 0;
  }
  if (template.id === "before_after") {
    score += storySignals.contrast ? 7 : 0;
  }
  if (template.id === "ticket_day") {
    score += storySignals.ephemera ? 7 : 0;
    score += storySignals.food ? 2 : 0;
  }
  if (template.id === "recipe_memo") {
    score += storySignals.food ? 7 : 0;
  }
  if (template.id === "letter_page") {
    score += storySignals.reflective ? 6 : 0;
  }
  if (template.id === "field_notes") {
    score += storySignals.detail ? 6 : 0;
  }
  if (template.id === "moodboard_stack") {
    score += storySignals.social ? 5 : 0;
    score += storySignals.fragments && images.length <= 5 ? 3 : 0;
  }
  if (template.id === "hero_memory") {
    score += images.length === 1 ? 4 : 0;
  }
  if (template.id === "magazine_note") {
    score += storySignals.reflective && images.length <= 3 ? 3 : 0;
  }
  return score;
}

type ScoredTemplate = {
  index: number;
  keywordHits: string[];
  score: number;
  template: JournalTemplate;
};

function selectDiverseTemplates(scored: ScoredTemplate[]) {
  const selected: ScoredTemplate[] = [];
  const usedFamilies = new Set<string>();
  for (const item of scored) {
    if (usedFamilies.has(item.template.family) && hasUnusedFamilyCandidate(scored, selected, usedFamilies)) {
      continue;
    }
    selected.push(item);
    usedFamilies.add(item.template.family);
    if (selected.length === 3) {
      return selected;
    }
  }
  return selected.slice(0, 3);
}

function hasUnusedFamilyCandidate(scored: ScoredTemplate[], selected: ScoredTemplate[], usedFamilies: Set<string>) {
  const selectedIds = new Set(selected.map((item) => item.template.id));
  return scored.some((item) => !selectedIds.has(item.template.id) && !usedFamilies.has(item.template.family));
}

function recommendationReason(
  template: JournalTemplate,
  images: UploadedImage[],
  keywordHits: string[],
  imageProfile: ReturnType<typeof describeImages>,
  storySignals: ReturnType<typeof detectStorySignals>
) {
  const signalReason = storySignalReason(template, storySignals, images.length);
  if (signalReason) {
    return signalReason;
  }
  if (keywordHits.length > 0) {
    return `匹配到「${keywordHits.slice(0, 2).join("、")}」，适合用这个结构讲。`;
  }
  if (images.length >= template.minImages && images.length <= template.maxImages) {
    return `${images.length} 张照片落在它的舒适范围里。`;
  }
  if (template.id === "quiet_story" && imageProfile.hasPortraitDominance) {
    return "竖图偏多，适合留白和长段文字。";
  }
  if (template.id === "detail_index" && imageProfile.hasMixedOrientation) {
    return "横竖图混合，适合主图加细节索引。";
  }
  return "作为不同叙事节奏的备选。";
}

function storySignalReason(
  template: JournalTemplate,
  storySignals: ReturnType<typeof detectStorySignals>,
  imageCount: number
) {
  if (template.id === "chapter_scroll" && imageCount >= 5) {
    return "照片数量多，适合拆成开头、转场和结尾来读。";
  }
  if (template.id === "timeline_trip" && (storySignals.journey || storySignals.chronology)) {
    return "有路上或时间顺序线索，适合按经历推进。";
  }
  if (template.id === "ticket_day" && storySignals.ephemera) {
    return "有票据、展览或地点凭证线索，适合做票根备忘。";
  }
  if (template.id === "recipe_memo" && storySignals.food) {
    return "食物或咖啡线索明显，适合写成餐桌小记。";
  }
  if (template.id === "field_notes" && storySignals.detail) {
    return "细节主体比较明确，适合写成观察手记。";
  }
  if (template.id === "detail_index" && storySignals.detail) {
    return "有可编号的小细节，适合用主图带出索引。";
  }
  if (template.id === "split_scene" && storySignals.twoScene) {
    return "出现两个场景或状态，适合分成两段讲。";
  }
  if (template.id === "before_after" && storySignals.contrast) {
    return "有前后变化线索，适合把变化本身讲清楚。";
  }
  if (template.id === "pocket_grid" && storySignals.fragments) {
    return "片段感强，适合用口袋卡片收纳照片和短句。";
  }
  if (template.id === "letter_page" && storySignals.reflective) {
    return "描述更像一段想说的话，适合让文字成为主角。";
  }
  if (template.id === "moodboard_stack" && storySignals.social) {
    return "有人物或相处线索，适合把同一种心情贴成一页。";
  }
  return null;
}

function describeImages(images: UploadedImage[]) {
  const portraitCount = images.filter((image) => image.height > image.width).length;
  const landscapeCount = images.filter((image) => image.width >= image.height).length;
  return {
    hasMixedOrientation: portraitCount > 0 && landscapeCount > 0,
    hasPortraitDominance: images.length > 0 && portraitCount >= Math.ceil(images.length / 2)
  };
}

function detectStorySignals(
  images: UploadedImage[],
  query: string,
  imageProfile: ReturnType<typeof describeImages>
) {
  return {
    food: containsAny(query, FOOD_TERMS),
    ephemera: containsAny(query, EPHEMERA_TERMS),
    journey: containsAny(query, JOURNEY_TERMS),
    chronology: containsAny(query, CHRONOLOGY_TERMS),
    contrast: containsAny(query, CONTRAST_TERMS),
    detail: containsAny(query, DETAIL_TERMS),
    reflective: containsAny(query, REFLECTIVE_TERMS),
    social: containsAny(query, SOCIAL_TERMS),
    fragments: containsAny(query, FRAGMENT_TERMS) || images.length >= 5,
    twoScene: containsAny(query, CONTRAST_TERMS),
    mixedOrientation: imageProfile.hasMixedOrientation
  };
}

function containsAny(query: string, terms: string[]) {
  return terms.some((term) => query.includes(term.toLowerCase()));
}
