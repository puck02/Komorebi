import { generationJobErrorMessage } from "./generationJobStatus";
import type { GenerationJob } from "../api/generationJobs";

const brokenCompletedJob: GenerationJob = {
  id: "job_1",
  status: "completed",
  stage: "completed",
  revisionRound: 0,
  maxRevisionRounds: 3,
  bestScore: null,
  journalId: null,
  errorMessage: null,
  createdAt: "2026-06-08T10:00:00Z",
  updatedAt: "2026-06-08T10:00:10Z"
};

const failedJob: GenerationJob = {
  ...brokenCompletedJob,
  status: "failed",
  stage: "failed",
  errorMessage: "AI服务连接失败"
};

assertEqual(
  generationJobErrorMessage(brokenCompletedJob, null),
  "手帐已生成，但没有拿到保存后的入口。请返回后重新生成。"
);
assertEqual(generationJobErrorMessage(failedJob, null), "AI服务连接失败");
assertEqual(generationJobErrorMessage(null, new Error("请求失败")), "请求失败");
assertEqual(generationJobErrorMessage(null, null), null);

function assertEqual(actual: string | null, expected: string | null) {
  if (actual !== expected) {
    throw new Error(`Expected ${expected}, received ${actual}`);
  }
}
