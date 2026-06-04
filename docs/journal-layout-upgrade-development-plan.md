# 手帐版式升级开发计划

## 目标

把当前手帐布局从固定模板升级为章节式长图拼贴。新版系统根据图片内容选择版式族，生成多章节日记，使用规则引擎稳定摆放图片、文字和装饰，并接入现有 Agent Loop 做视觉复审。

## 阶段 1：扩展布局数据结构

文件：

- 修改 `backend/app/services/journal_generator.py`
- 修改 `backend/app/services/openai_client.py`
- 修改 `frontend/src/types/journal.ts`
- 修改 `frontend/src/components/JournalCanvas.tsx`
- 新增或修改后端生成测试

内容：

- 在 layout JSON 中新增 `content.sections` 和 `layout.sections`。
- 保留旧的扁平字段，保证历史手帐还能渲染。
- 新增 section 类型：`id`、`title`、`imageIds`、`body`、`mood`。
- 新增 section layout 类型：`sectionId`、`variant`、`y`、`height`、`images`、`texts`、`decorations`。
- 测试历史 layout 和新版 layout 都能通过 schema。

验收：

- 老手帐不需要迁移也能打开。
- 新生成手帐包含章节信息。
- 前端类型检查通过。

## 阶段 2：图片理解和章节分组 Prompt

文件：

- 修改 `backend/app/services/openai_client.py`
- 修改 `backend/app/services/journal_generator.py`
- 修改 `docs/journal-agent-loop-design.md`
- 新增或修改 `backend/tests/test_generation.py`

内容：

- Prompt 要求 AI 先输出图片理解摘要。
- 只允许把相邻图片合并成章节，禁止打乱用户顺序。
- 每章绑定 1-3 张图片。
- 每章生成 30-80 字自然日记。
- caption 必须对应具体 imageId。

验收：

- 多图输入会生成 2-5 个章节。
- 章节 imageIds 顺序和用户上传顺序一致。
- 文案不再只是一大段总结。

## 阶段 3：版式族规则引擎

文件：

- 新增 `backend/app/services/layout_variants.py`
- 修改 `backend/app/services/journal_generator.py`
- 新增 `backend/tests/test_layout_variants.py`

内容：

- 实现第一批版式族：
  - `hero_note`
  - `staggered_collage`
  - `timeline_strip`
  - `photo_wall`
  - `magazine_whitespace`
  - `ticket_memo`
- 根据章节图片数量、横竖比例和主题选择版式。
- 生成章节内图片、文字和装饰的初始坐标。
- 自动计算章节高度和总画布高度。

验收：

- 同样图片数量可以根据内容选择不同版式。
- 图片较多时画布高度自动增长。
- 每个章节至少有一个主图或主视觉区域。

## 阶段 4：装饰功能化放置

文件：

- 新增 `backend/app/services/decoration_placement.py`
- 修改 `backend/app/services/assets.py`
- 修改 `backend/app/services/journal_generator.py`
- 新增 `backend/tests/test_decoration_placement.py`

内容：

- 将素材按功能类别使用：`tape`、`note`、`ticket`、`label`、`sticker`、`line`、`flower`、`star`。
- 胶带自动吸附到图片或便签边缘。
- 便签纸和票据优先作为文字底板。
- 小贴纸优先放在角落和留白区。
- 限制每篇最多 22 个装饰，每章建议 3-6 个。
- 非法素材按类别回退，不固定回退到第一个素材。

验收：

- 胶带不再漂浮在画布空处。
- 贴纸不会覆盖文字块。
- 自动生成结果能使用不同类别素材。

## 阶段 5：布局硬约束校验

文件：

- 新增 `backend/app/services/layout_rules.py`
- 修改 `backend/app/services/journal_agent.py`
- 新增 `backend/tests/test_layout_rules.py`

内容：

- 检查图片集合和顺序。
- 检查文字和图片重叠。
- 检查图片可见比例。
- 检查胶带边缘吸附。
- 检查装饰是否超出画布。
- 检查装饰数量上限。
- 检查章节间距和图片间距。
- 自动扩展画布高度。

验收：

- 规则检查能输出结构化问题。
- 硬失败会触发 Agent Loop 修订。
- 达到修订上限时保存历史最高分版本。

## 阶段 6：前端章节式渲染

文件：

- 修改 `frontend/src/components/JournalCanvas.tsx`
- 修改 `frontend/src/pages/JournalDetailPage.tsx`
- 修改 `frontend/src/pages/InternalJournalRenderPage.tsx`
- 修改 `frontend/src/styles/globals.css`

内容：

- 支持 `layout.sections` 渲染。
- 按章节顺序渲染长图。
- 每章按层级渲染：底纸、图片、胶带、文字、贴纸、线条。
- 旧 layout 继续走兼容渲染。
- 移动端按画布宽度缩放，继续上下滚动。

验收：

- 新版章节手帐能正常显示。
- 老手帐仍能正常显示。
- 手机端不会横向溢出。
- 导出 PNG 中图片、文字和装饰完整。

## 阶段 7：视觉评审 Prompt 升级

文件：

- 修改 `backend/app/services/openai_client.py`
- 修改 `backend/app/services/journal_agent.py`
- 修改 `docs/journal-agent-loop-design.md`
- 修改 `backend/tests/test_journal_agent.py`

内容：

- 评审模型新增检查项：
  - 是否有视觉焦点。
  - 章节文字是否对应章节图片。
  - 装饰是否有功能。
  - 是否像电子手账而不是普通图文列表。
- 修订模型只修复评审指出的问题。
- 每轮优先处理 3-6 个主要问题，避免整版推翻。

验收：

- 视觉评审能指出主次关系、留白、图文匹配和装饰功能问题。
- 修订后不会改变图片顺序。
- 最多 3 轮后保存最高分版本。

## 阶段 8：完整验证

验证命令：

```bash
cd backend
.venv/bin/python -m pytest
cd ../frontend
npm run build
cd ..
git diff --check
```

人工验证：

- 1-2 张图生成主图便签式。
- 3-5 张图生成错落拼贴或时间线。
- 6-9 张图生成章节式长图或相册墙。
- 历史手帐加载正常。
- 手机端详情页完整缩放。
- 导出图片不缺图。

