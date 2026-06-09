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
    keywords: ["细节", "索引", "清单", "编号", "几样", "小东西", "主题"]
  }
];

export function recommendJournalTemplates(
  images: UploadedImage[],
  text: string,
  mood: string
): JournalTemplateRecommendation[] {
  const query = `${text} ${mood}`.toLowerCase();
  const imageProfile = describeImages(images);
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
    if (template.id === "pocket_grid" && images.length >= 5) {
      score += 6;
    }
    if (template.id === "chapter_scroll" && images.length >= 5) {
      score += 5;
    }
    if (template.id === "detail_index" && images.length >= 4 && imageProfile.hasMixedOrientation) {
      score += 4;
    }
    if (template.id === "timeline_trip" && images.length >= 3) {
      score += 3;
    }
    if (template.id === "quiet_story" && imageProfile.hasPortraitDominance) {
      score += 2;
    }
    if (template.id === "split_scene" && images.length >= 2 && images.length <= 4 && query.includes("转场")) {
      score += 4;
    }
    return { index, keywordHits, score, template };
  });

  return scored
    .sort((first, second) => second.score - first.score || first.index - second.index)
    .slice(0, 3)
    .map((item) => ({
      ...item.template,
      recommendationReason: recommendationReason(item.template, images, item.keywordHits, imageProfile)
    }));
}

function recommendationReason(
  template: JournalTemplate,
  images: UploadedImage[],
  keywordHits: string[],
  imageProfile: ReturnType<typeof describeImages>
) {
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

function describeImages(images: UploadedImage[]) {
  const portraitCount = images.filter((image) => image.height > image.width).length;
  const landscapeCount = images.filter((image) => image.width >= image.height).length;
  return {
    hasMixedOrientation: portraitCount > 0 && landscapeCount > 0,
    hasPortraitDominance: images.length > 0 && portraitCount >= Math.ceil(images.length / 2)
  };
}
