import type { TemplateRecommendationResponse } from "../api/journals";
import { JOURNAL_TEMPLATES, type JournalTemplateRecommendation } from "./journalTemplates";

export type TemplateRecommendationState = {
  requestKey: string;
  serverRecommendedTemplates: JournalTemplateRecommendation[] | null;
  recommendationSource: "ai" | "local" | null;
  recommendationMessage: string | null;
  isPending: boolean;
};

export type TemplateRecommendationAction =
  | { type: "localOnly"; requestKey: string }
  | { type: "requestStarted"; requestKey: string }
  | {
      type: "requestSucceeded";
      requestKey: string;
      recommendations: JournalTemplateRecommendation[];
      source: "ai" | "local";
      message: string | null;
    }
  | { type: "requestFailed"; requestKey: string };

export const initialTemplateRecommendationState: TemplateRecommendationState = {
  requestKey: "",
  serverRecommendedTemplates: null,
  recommendationSource: null,
  recommendationMessage: null,
  isPending: false
};

export function templateRecommendationReducer(
  state: TemplateRecommendationState,
  action: TemplateRecommendationAction
): TemplateRecommendationState {
  if (action.type === "localOnly") {
    return {
      ...initialTemplateRecommendationState,
      requestKey: action.requestKey
    };
  }
  if (action.type === "requestStarted") {
    return {
      ...initialTemplateRecommendationState,
      requestKey: action.requestKey,
      isPending: true
    };
  }
  if (action.requestKey !== state.requestKey) {
    return state;
  }
  if (action.type === "requestSucceeded") {
    return {
      requestKey: state.requestKey,
      serverRecommendedTemplates: action.recommendations.length ? action.recommendations : null,
      recommendationSource: action.source,
      recommendationMessage: action.message,
      isPending: false
    };
  }
  return {
    requestKey: state.requestKey,
    serverRecommendedTemplates: null,
    recommendationSource: "local",
    recommendationMessage: "模板推荐服务暂不可用，已按本地规则推荐。",
    isPending: false
  };
}

export function createTemplateRecommendationRequestKey(imageIds: string[], description: string, mood: string) {
  return JSON.stringify({
    description: description.trim(),
    imageIds,
    mood
  });
}

export function mergeServerTemplateRecommendations(result: TemplateRecommendationResponse): JournalTemplateRecommendation[] {
  return result.recommendations
    .map((recommendation) => {
      const template = JOURNAL_TEMPLATES.find((item) => item.id === recommendation.templateId);
      if (!template) {
        return null;
      }
      return {
        ...template,
        recommendationReason: recommendation.reason,
        storyArc: recommendation.storyArc
      };
    })
    .filter((template): template is JournalTemplateRecommendation => template !== null);
}
