# 手帐视觉 Agent Loop 开发计划

## 目标

将同步手帐生成改造成后台 Agent Loop：生成初稿后使用真实前端画布截图，由 `gpt-5.4-mini` 视觉评审，必要时由 `gpt-5.5` 定向修订，最多调整 5 轮，并保存历史最高分版本。

## 技术方案

- 后端使用 SQLite 任务表和进程内 `ThreadPoolExecutor(max_workers=2)`。
- `JournalAgent` 负责初稿、规则清洗、截图、评审、修订和最佳版本选择。
- Playwright Python 包调用服务器已有 `/usr/bin/google-chrome`。
- 前端新增内部渲染页，复用 `JournalCanvas` 和现有 CSS。
- 内部草稿接口使用一次性短时随机 token，只允许截图任务访问。
- 用户创建手帐后进入生成状态页，每 2 秒轮询任务状态。

## 任务 1：生成任务模型和 API

文件：

- 新增 `backend/app/models/generation_job.py`
- 新增 `backend/app/schemas/generation_job.py`
- 新增 `backend/app/api/routes/generation_jobs.py`
- 新增 `backend/alembic/versions/0002_generation_jobs.py`
- 修改 `backend/app/main.py`
- 修改 `backend/app/models/user.py`
- 修改 `backend/alembic/env.py`
- 新增 `backend/tests/test_generation_jobs.py`

步骤：

1. 先写 API 测试：创建任务需要登录、不能使用他人图片、只能查询自己的任务、创建后立即返回 `queued`。
2. 新增任务表，保存输入 payload、阶段、轮次、最佳分数、生成手帐 ID 和错误。
3. 新增任务 API，并通过可替换的提交函数启动后台处理器。
4. 跑 `backend/tests/test_generation_jobs.py`。
5. 提交：`实现手帐生成任务接口`。

## 任务 2：视觉评审和修订客户端

文件：

- 修改 `backend/app/core/config.py`
- 修改 `backend/.env.example`
- 修改 `backend/app/services/openai_client.py`
- 修改 `backend/tests/test_generation.py`

步骤：

1. 先写客户端测试：默认评审模型为 `gpt-5.4-mini`，视觉评审请求包含截图、原图和 JSON，定向修订请求包含问题列表、轮次和最佳分数。
2. 新增 `review_layout()` 和 `revise_layout()`。
3. Prompt 按设计文档拆分为初稿、评审和定向修订三个职责。
4. 跑 `backend/tests/test_generation.py`。
5. 提交：`实现手帐视觉评审客户端`。

## 任务 3：Agent Loop 和规则检查

文件：

- 新增 `backend/app/services/journal_agent.py`
- 修改 `backend/app/services/journal_generator.py`
- 新增 `backend/tests/test_journal_agent.py`

步骤：

1. 先写 Agent 测试：评分达到阈值提前停止、硬失败继续修订、最多修订 5 轮、评分下降时保留历史最佳版、图片顺序不变。
2. 新增确定性规则检查函数，输出结构化问题列表。
3. 实现 `JournalAgent.generate()`，始终基于历史最佳版本做下一轮修订。
4. 跑 `backend/tests/test_journal_agent.py backend/tests/test_generation.py`。
5. 提交：`实现手帐视觉优化闭环`。

## 任务 4：内部渲染 token 和 Playwright 截图

文件：

- 新增 `backend/app/services/render_drafts.py`
- 新增 `backend/app/services/journal_renderer.py`
- 新增 `backend/app/api/routes/internal_render.py`
- 修改 `backend/app/main.py`
- 修改 `backend/pyproject.toml`
- 新增 `backend/tests/test_internal_render.py`
- 新增 `backend/tests/test_journal_renderer.py`

步骤：

1. 先写 token API 测试：合法 token 可读取草稿和展示图，未知或过期 token 返回 404，消费后 token 失效。
2. 实现线程安全的短时 token 注册表。
3. 新增内部草稿和图片接口。
4. 新增 Playwright 截图器，使用 `/usr/bin/google-chrome` 和 `INTERNAL_RENDER_URL`。
5. 截图器等待 `[data-render-ready="true"]`，截取 `.journal-canvas`。
6. 跑内部接口测试和截图冒烟测试。
7. 提交：`实现手帐内部截图渲染`。

## 任务 5：后台执行器

文件：

- 新增 `backend/app/services/generation_jobs.py`
- 修改 `backend/app/api/routes/generation_jobs.py`
- 修改 `backend/app/api/routes/journals.py`
- 新增 `backend/tests/test_generation_job_runner.py`

步骤：

1. 先写任务执行测试：阶段更新、成功保存手帐、失败保存错误、完成后关联 `journal_id`。
2. 实现最多并发 2 个任务的线程池。
3. 后台线程重新创建数据库 Session，不复用请求 Session。
4. 服务启动时把遗留 `queued/running` 任务标记失败。
5. 保留旧同步接口作为兼容入口，前端改用任务接口。
6. 跑任务执行和 journals API 测试。
7. 提交：`接入后台手帐生成任务`。

## 任务 6：前端内部渲染页和生成状态页

文件：

- 新增 `frontend/src/pages/InternalJournalRenderPage.tsx`
- 新增 `frontend/src/pages/GenerationJobPage.tsx`
- 新增 `frontend/src/api/generationJobs.ts`
- 修改 `frontend/src/App.tsx`
- 修改 `frontend/src/pages/CreateJournalPage.tsx`
- 修改 `frontend/src/styles/globals.css`

步骤：

1. 内部渲染页在登录判断前挂载，读取 token，预加载字体、图片和装饰素材，完成后设置 `data-render-ready="true"`。
2. 创建页提交后创建后台任务并跳转 `/generation/:jobId`。
3. 状态页每 2 秒轮询，完成后跳转详情，失败时显示错误和返回按钮。
4. 跑 `npm run build`。
5. 提交：`实现手帐后台生成状态页`。

## 任务 7：部署和完整验证

步骤：

1. 安装 Playwright Python 包：`.venv/bin/pip install playwright`。
2. 运行迁移：`.venv/bin/alembic upgrade head`。
3. 跑后端完整测试：`.venv/bin/python -m pytest`。
4. 跑前端构建：`npm run build`。
5. 跑 `git diff --check`。
6. 重启 `komorebi-backend.service` 和 `komorebi-frontend.service`。
7. 检查 `/api/health` 和前端页面。

