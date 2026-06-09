import type { TemplateRecommendationResponse } from "../api/journals";
import {
  createTemplateRecommendationRequestKey,
  initialTemplateRecommendationState,
  mergeServerTemplateRecommendations,
  templateRecommendationReducer
} from "./templateRecommendationState";

const firstKey = createTemplateRecommendationRequestKey(["img_1"], "咖啡", "");
const nextKey = createTemplateRecommendationRequestKey(["img_2"], "旅行", "松快");

const pendingState = templateRecommendationReducer(initialTemplateRecommendationState, {
  requestKey: nextKey,
  type: "requestStarted"
});

const staleResultState = templateRecommendationReducer(pendingState, {
  message: null,
  recommendations: mergeServerTemplateRecommendations(serverResult("ticket_day")),
  requestKey: firstKey,
  source: "ai",
  type: "requestSucceeded"
});

assertEqual(staleResultState.requestKey, nextKey);
assertEqual(staleResultState.serverRecommendedTemplates, null);
assertEqual(staleResultState.isPending, true);

const staleFailureState = templateRecommendationReducer(pendingState, {
  requestKey: firstKey,
  type: "requestFailed"
});

assertEqual(staleFailureState.requestKey, nextKey);
assertEqual(staleFailureState.recommendationSource, null);
assertEqual(staleFailureState.isPending, true);

const currentResultState = templateRecommendationReducer(pendingState, {
  message: null,
  recommendations: mergeServerTemplateRecommendations(serverResult("timeline_trip")),
  requestKey: nextKey,
  source: "ai",
  type: "requestSucceeded"
});

assertEqual(currentResultState.serverRecommendedTemplates?.[0]?.id, "timeline_trip");
assertEqual(currentResultState.recommendationSource, "ai");
assertEqual(currentResultState.isPending, false);

const failedState = templateRecommendationReducer(pendingState, {
  requestKey: nextKey,
  type: "requestFailed"
});

assertEqual(failedState.serverRecommendedTemplates, null);
assertEqual(failedState.recommendationSource, "local");
assertEqual(failedState.isPending, false);

function serverResult(templateId: string): TemplateRecommendationResponse {
  return {
    imageUnderstanding: [],
    message: null,
    recommendations: [
      {
        name: "模板",
        reason: "根据图片内容推荐。",
        storyArc: "讲成一个故事。",
        templateId
      }
    ],
    source: "ai"
  };
}

function assertEqual(actual: unknown, expected: unknown) {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, received ${String(actual)}`);
  }
}
