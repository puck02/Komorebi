import { CREATE_JOURNAL_MOOD_OPTIONS } from "./createJournalOptions";

assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "治愈");
assertDoesNotInclude(CREATE_JOURNAL_MOOD_OPTIONS, "珍贵");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "松快");
assertIncludes(CREATE_JOURNAL_MOOD_OPTIONS, "满足");

function assertIncludes(values: string[], expected: string) {
  if (!values.includes(expected)) {
    throw new Error(`Expected options to include ${expected}`);
  }
}

function assertDoesNotInclude(values: string[], expected: string) {
  if (values.includes(expected)) {
    throw new Error(`Expected options not to include ${expected}`);
  }
}
