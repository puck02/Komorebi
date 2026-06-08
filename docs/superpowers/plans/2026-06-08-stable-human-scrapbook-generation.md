# 稳定拟人手帐生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升 AI 手帐生成的确定性质量，使正文更像人写、章节分组更稳定、版式和装饰问题可被规则检查发现。

**Architecture:** AI 继续负责图片理解和初稿 JSON，后端新增确定性文案清洗与故事规划层，再交给现有版式模板和 Agent Loop。规则校验补充美观与拟人质量问题，但只把破坏渲染的情况作为硬失败。

**Tech Stack:** Python 3.11, FastAPI 后端服务, Pydantic schema, pytest 单元测试, 现有 Chat Completions 兼容 OpenAI 客户端。

---

## File Structure

- Create `backend/app/services/diary_copy.py`: 手帐标题、正文、章节正文和 caption 的确定性清洗。
- Create `backend/tests/test_diary_copy.py`: 文案清洗单元测试。
- Create `backend/app/services/story_planner.py`: 规范章节分组，保证相邻图片、最多 3 张一组、正文映射稳定。
- Create `backend/tests/test_story_planner.py`: 章节规划单元测试。
- Modify `backend/app/services/journal_generator.py`: 接入 `diary_copy` 和 `story_planner`，减少本文件内的分组职责。
- Modify `backend/app/services/layout_rules.py`: 增加 copy、视觉焦点和装饰功能问题检查。
- Modify `backend/tests/test_generation.py`: 覆盖生成器接入后的文案和章节清洗。
- Modify `backend/tests/test_layout_rules.py`: 覆盖新增质量规则。
- Modify `backend/app/services/openai_client.py`: 收紧 prompt 中的人类手帐写法，不改变 API 形态。

## Tasks

### Task 1: Diary Copy Normalization

- [ ] Write failing tests in `backend/tests/test_diary_copy.py`:
  - `normalize_diary_text` removes cliche phrases such as `治愈`, `仪式感`, `被温柔包裹`, `把时光收藏`, `珍贵回忆`.
  - `normalize_diary_blocks` trims empty entries, keeps concrete short blocks, splits long sentence-like blocks.
  - `normalize_title` returns a short usable title and falls back to `今日小记`.
  - `has_cliche_copy` detects obvious AI-like phrases.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_diary_copy.py -q` and confirm it fails because the module does not exist.
- [ ] Implement `backend/app/services/diary_copy.py` with small pure functions:
  - no external dependencies;
  - deterministic string cleanup;
  - no model calls;
  - Chinese punctuation aware sentence splitting.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_diary_copy.py -q` and confirm it passes.

### Task 2: Story Planner

- [ ] Write failing tests in `backend/tests/test_story_planner.py`:
  - no raw sections groups images evenly by body count and image order;
  - non-adjacent model sections are split into adjacent sections;
  - sections with more than 3 images are split;
  - empty section body uses the matching body fallback;
  - all request images appear exactly once and in order.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_story_planner.py -q` and confirm it fails because the module does not exist.
- [ ] Implement `backend/app/services/story_planner.py`:
  - `plan_content_sections(layout, image_ids)`;
  - `split_adjacent_image_ids(section_image_ids, ordered_image_ids)`;
  - helper functions for title/body fallback.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_story_planner.py -q` and confirm it passes.

### Task 3: Generator Integration

- [ ] Add failing tests in `backend/tests/test_generation.py`:
  - generated body and section body are normalized through diary copy cleanup;
  - model sections still preserve image order after planner integration.
- [ ] Run the specific tests and confirm they fail before integration.
- [ ] Modify `backend/app/services/journal_generator.py`:
  - call `normalize_title`, `normalize_diary_blocks`, and `normalize_diary_text`;
  - replace internal `normalize_content_sections` grouping logic with `plan_content_sections`;
  - keep backward-compatible exported helpers if existing tests import them.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_generation.py backend/tests/test_layout_variants.py -q`.

### Task 4: Layout Rule Quality Checks

- [ ] Add failing tests in `backend/tests/test_layout_rules.py`:
  - cliche copy creates `copyQuality` medium issue;
  - multi-image section with all equal image sizes creates `visualFocus` medium issue;
  - section with image/text but no paper or tape decoration creates `decorationFunction` medium issue when approved paper or tape assets exist.
- [ ] Run the specific tests and confirm they fail.
- [ ] Modify `backend/app/services/layout_rules.py`:
  - import `has_cliche_copy`;
  - add `check_copy_quality`;
  - add `check_visual_focus`;
  - add `check_decoration_function`;
  - keep hard-failure behavior unchanged.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_layout_rules.py -q`.

### Task 5: Prompt Tightening

- [ ] Add or update tests that inspect `build_generation_prompt` if existing prompt tests cover it.
- [ ] Modify `backend/app/services/openai_client.py` prompt wording:
  - ask for concrete, short diary notes;
  - prohibit broad sentimental cliches;
  - make section bodies image-bound;
  - keep `/chat/completions` and JSON object response format unchanged.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_generation.py -q`.

### Task 6: Full Verification and Commit

- [ ] Run `backend/.venv/bin/python -m pytest backend/tests`.
- [ ] Review `git diff` for unrelated changes and secret leakage.
- [ ] Commit with Chinese message, for example `优化手帐生成稳定性`.
