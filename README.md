# Komorebi

Komorebi 是一个 AI 日记手帐 Web 应用。用户上传 1-9 张生活照片，输入一段简单描述，并可选填写日期、地点和心情标签，系统会生成一篇温柔拼贴风格的图文手帐。

项目目前处于 MVP 开发阶段，目标是先服务 2-10 人小范围自用，优先保证生成闭环、照片隐私、素材质量和部署可控。

## 当前进度

已完成：

- React + Vite + TypeScript 前端脚手架。
- FastAPI 后端脚手架。
- PostgreSQL 数据模型和 Alembic 初始迁移。
- 账号密码注册、登录和当前用户接口。
- 图片上传、原图保存、缩略图生成和访问控制。

开发中：

- 内置素材库和素材预览页。
- 结构化手帐生成和渲染。
- OpenAI 生成链路。
- 手帐历史、轻量编辑和 PNG 导出。
- Docker Compose 部署。

## 技术栈

- 前端：React、Vite、TypeScript、Tailwind CSS、shadcn/ui、Radix UI、lucide-react、TanStack Query。
- 后端：FastAPI、Python、SQLAlchemy、Alembic。
- 数据库：PostgreSQL。
- 文件存储：服务器本地目录。
- AI：OpenAI API。
- 素材：Rough.js 生成统一风格 SVG，外部免费素材人工审核后再引入。
- 部署：Docker Compose + Caddy。

## 本地开发

### 后端

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

启动开发服务：

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run generate:assets
npm run build
```

启动开发服务：

```bash
cd frontend
npm run dev
```

## 环境变量

参考 [.env.example](.env.example)：

```env
DATABASE_URL=postgresql+psycopg://komorebi:komorebi@postgres:5432/komorebi
JWT_SECRET=change-me
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-5.5
STORAGE_ROOT=/data/storage
PUBLIC_API_BASE_URL=/api
```

不要提交 `.env` 或任何真实密钥。

## 测试与验证

后端测试：

```bash
cd backend
.venv/bin/python -m pytest
```

前端构建：

```bash
cd frontend
npm run build
```

当前已验证：

- 后端测试：10 个测试通过。
- 前端生产构建通过。

## 文档

- [需求文档](docs/requirements.md)
- [技术选型](docs/tech-stack.md)
- [素材库策略](docs/asset-strategy.md)
- [详细开发计划](docs/development-plan.md)

## 分支

- `main`：稳定文档和基础配置。
- `feature/mvp`：MVP 开发分支。
