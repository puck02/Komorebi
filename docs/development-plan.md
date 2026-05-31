# AI 日记手帐应用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable MVP of the AI journal scrapbook web app for 2-10 private users.

**Architecture:** The app is a single-server Docker Compose deployment with a React/Vite frontend, FastAPI backend, PostgreSQL database, and local file storage. The backend owns auth, uploads, OpenAI calls, asset matching, journal persistence, and access control; the frontend owns the 1080 x 1440 journal renderer, lightweight editing, asset preview, history, and PNG export.

**Tech Stack:** React, Vite, TypeScript, Tailwind CSS, shadcn/ui, Radix UI, lucide-react, React Router, TanStack Query, react-hook-form, Zod, Rough.js, FastAPI, Python, SQLAlchemy, Alembic, PostgreSQL, Pillow, OpenAI API, Docker Compose, Caddy.

---

## 1. MVP Scope

Build these capabilities first:

- Account/password registration and login.
- Upload 1-9 JPG, PNG, or WebP images.
- Store original images long-term and generate thumbnails.
- Create a journal from images, free text, optional date, location, and mood tags.
- Call OpenAI for structured journal JSON.
- Select only `approved` built-in assets for decorations.
- Render a fixed `1080 x 1440` warm collage journal page.
- Let users edit generated title and body text.
- Let users change a layout variant.
- Let users regenerate copy.
- Save journals to PostgreSQL.
- Show a history page.
- Delete a journal and its associated original images and thumbnails.
- Export preview as PNG from the browser.
- Provide an asset library preview page with filters and quality status.
- Deploy with Docker Compose on the current server.

Keep these out of MVP:

- Invite codes.
- Payment, subscription, quota, or credit system.
- Public sharing links.
- PDF export.
- Full drag-and-drop editor.
- User-uploaded sticker library.
- Backend screenshot export.
- Mobile native app or PWA.

## 2. Planned File Structure

```text
backend/
  pyproject.toml
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    main.py
    core/
      config.py
      security.py
    db/
      base.py
      session.py
    models/
      user.py
      image.py
      journal.py
      asset.py
    schemas/
      auth.py
      image.py
      journal.py
      asset.py
    api/
      deps.py
      routes/
        auth.py
        images.py
        journals.py
        assets.py
    services/
      storage.py
      thumbnails.py
      assets.py
      openai_client.py
      journal_generator.py
    assets/
      manifest.json
      stickers/
    tests/
      conftest.py
      test_auth.py
      test_images.py
      test_assets.py
      test_journals.py
      test_generation.py
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx
    api/
      client.ts
      auth.ts
      images.ts
      journals.ts
      assets.ts
    components/
      ui/
        button.tsx
        card.tsx
        input.tsx
        tabs.tsx
      AppShell.tsx
      JournalCanvas.tsx
      JournalEditor.tsx
      ImageUploader.tsx
      AssetCard.tsx
    lib/
      utils.ts
    pages/
      LoginPage.tsx
      RegisterPage.tsx
      CreateJournalPage.tsx
      JournalDetailPage.tsx
      HistoryPage.tsx
      AssetLibraryPage.tsx
    types/
      journal.ts
      asset.ts
    utils/
      exportPng.ts
    styles/
      globals.css
tools/
  generate-assets.mjs
docker-compose.yml
.env.example
docs/
  requirements.md
  tech-stack.md
  asset-strategy.md
  development-plan.md
```

## 3. Shared Data Contracts

Use these names consistently across backend and frontend.

### 3.1 Journal Layout JSON

```json
{
  "canvas": {
    "width": 1080,
    "height": 1440,
    "background": "#f8f1e8"
  },
  "theme": {
    "style": "soft-collage",
    "palette": ["#f8f1e8", "#d9a98f", "#8f6b57", "#b9c7aa"],
    "mood": ["warm", "gentle"]
  },
  "content": {
    "title": "周末小记",
    "body": ["今天的风很轻，照片里都是慢下来的瞬间。"],
    "captions": [
      { "imageId": "img_1", "text": "海边的傍晚" }
    ]
  },
  "layout": {
    "variant": "collage_a",
    "images": [
      {
        "imageId": "img_1",
        "x": 92,
        "y": 210,
        "width": 420,
        "height": 320,
        "rotation": -3
      }
    ],
    "texts": [
      {
        "role": "title",
        "x": 80,
        "y": 72,
        "width": 680,
        "fontSize": 56
      }
    ],
    "decorations": [
      {
        "assetId": "tape_warm_grid_01",
        "x": 60,
        "y": 180,
        "width": 220,
        "height": 54,
        "rotation": -8
      }
    ]
  }
}
```

### 3.2 Asset Metadata

```json
{
  "id": "tape_warm_grid_01",
  "name": "暖色格纹胶带",
  "category": "tape",
  "tags": ["warm", "daily", "collage"],
  "style": ["soft-collage", "paper"],
  "colors": ["#e7b99f", "#f7efe6"],
  "file": "stickers/tape_warm_grid_01.svg",
  "license": "internal",
  "source": "internal",
  "qualityStatus": "approved"
}
```

## 4. Development Tasks

### Task 1: Project Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `.env.example`

- [ ] **Step 1: Create backend package skeleton**

  Include FastAPI, SQLAlchemy, Alembic, psycopg, python-jose, passlib, Pillow, OpenAI SDK, pytest, and httpx in `backend/pyproject.toml`.

- [ ] **Step 2: Add FastAPI health endpoint**

  `GET /api/health` returns:

  ```json
  { "status": "ok" }
  ```

- [ ] **Step 3: Add backend smoke test**

  `backend/tests/test_health.py` verifies `GET /api/health` returns HTTP 200 and `status=ok`.

- [ ] **Step 4: Create frontend Vite skeleton**

  `frontend/src/App.tsx` renders an app shell with navigation labels for Create, History, and Assets.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd backend && python -m pytest
  cd frontend && npm install && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend frontend .env.example
  git commit -m "搭建项目脚手架"
  ```

### Task 2: Database and Migrations

**Files:**
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/image.py`
- Create: `backend/app/models/journal.py`
- Create: `backend/app/models/asset.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Define SQLAlchemy models**

  Required tables:

  - `users`: `id`, `email`, `password_hash`, `created_at`.
  - `images`: `id`, `user_id`, `original_path`, `thumbnail_path`, `content_type`, `width`, `height`, `created_at`.
  - `journals`: `id`, `user_id`, `title`, `input_text`, `journal_date`, `location`, `mood_tags`, `layout_json`, `created_at`, `updated_at`.
  - `journal_images`: `journal_id`, `image_id`.
  - `assets`: `id`, `name`, `category`, `tags`, `style`, `colors`, `file`, `license`, `source`, `quality_status`.

- [ ] **Step 2: Add initial Alembic migration**

  Migration creates all tables, foreign keys, indexes on `user_id`, and a unique index on `users.email`.

- [ ] **Step 3: Add database connection test**

  `backend/tests/test_database.py` verifies metadata can create and drop tables against the test database.

- [ ] **Step 4: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_database.py
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/db backend/app/models backend/alembic.ini backend/alembic backend/tests/test_database.py
  git commit -m "添加数据库模型和迁移"
  ```

### Task 3: Account Password Auth

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth.py`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Add auth backend tests**

  Test cases:

  - Register with email and password creates a user.
  - Duplicate email returns HTTP 409.
  - Login with correct password returns access token.
  - Login with wrong password returns HTTP 401.
  - `GET /api/auth/me` requires token and returns current user.

- [ ] **Step 2: Implement password hashing and JWT**

  Use bcrypt-compatible hashing through `passlib`. Access token payload contains `sub=<user_id>`.

- [ ] **Step 3: Implement auth routes**

  Routes:

  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`

- [ ] **Step 4: Add frontend auth API**

  Store token in `localStorage` under `komorebi_access_token`. Add an API client that attaches `Authorization: Bearer <token>`.

- [ ] **Step 5: Add login and register pages**

  Forms need email, password, loading state, and visible error messages.

- [ ] **Step 6: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_auth.py
  cd frontend && npm run build
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add backend frontend
  git commit -m "实现账号密码登录"
  ```

### Task 4: Local File Storage and Image Upload

**Files:**
- Create: `backend/app/services/storage.py`
- Create: `backend/app/services/thumbnails.py`
- Create: `backend/app/schemas/image.py`
- Create: `backend/app/api/routes/images.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_images.py`
- Create: `frontend/src/api/images.ts`
- Create: `frontend/src/components/ImageUploader.tsx`

- [ ] **Step 1: Add upload tests**

  Test cases:

  - Authenticated user uploads one valid image.
  - Original file is saved under configured storage root.
  - Thumbnail is generated.
  - Unsupported content type returns HTTP 400.
  - User cannot fetch another user's image metadata.

- [ ] **Step 2: Implement storage service**

  Store files under:

  ```text
  storage/users/<user_id>/images/<image_id>/original.<ext>
  storage/users/<user_id>/images/<image_id>/thumb.webp
  ```

- [ ] **Step 3: Implement thumbnail generation**

  Use Pillow to generate WebP thumbnails with max dimension 512 px.

- [ ] **Step 4: Implement image routes**

  Routes:

  - `POST /api/images`
  - `GET /api/images/{image_id}`
  - `GET /api/images/{image_id}/file`
  - `GET /api/images/{image_id}/thumbnail`

- [ ] **Step 5: Implement frontend uploader**

  Support selecting 1-9 files, show thumbnails, upload progress, and remove selected images before generation.

- [ ] **Step 6: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_images.py
  cd frontend && npm run build
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add backend frontend
  git commit -m "实现图片上传和缩略图"
  ```

### Task 5: Built-In Asset Library

**Files:**
- Create: `backend/app/assets/manifest.json`
- Create: `backend/app/assets/stickers/*.svg`
- Create: `tools/generate-assets.mjs`
- Create: `backend/app/services/assets.py`
- Create: `backend/app/schemas/asset.py`
- Create: `backend/app/api/routes/assets.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_assets.py`
- Create: `frontend/src/types/asset.ts`
- Create: `frontend/src/api/assets.ts`
- Create: `frontend/src/components/AssetCard.tsx`
- Create: `frontend/src/pages/AssetLibraryPage.tsx`

- [ ] **Step 1: Create initial asset manifest**

  Start with at least 50 SVG assets across tape, paper, sticker, and texture categories. Prefer deterministic SVGs generated with Rough.js and project templates so the style is unified and reproducible. Every asset must include `qualityStatus`, `license`, and `source`.

  External free assets are allowed only after manual review. They must include source and license metadata and should default to `draft` until checked in the website preview page.

- [ ] **Step 2: Add asset tests**

  Test cases:

  - Manifest loads successfully.
  - Every referenced SVG file exists.
  - Each asset has non-empty `id`, `category`, `tags`, `license`, `source`, and `qualityStatus`.
  - Asset matching returns only `approved` assets.

- [ ] **Step 3: Implement asset API**

  Routes:

  - `GET /api/assets`
  - `GET /api/assets/{asset_id}`
  - `GET /api/assets/{asset_id}/file`

- [ ] **Step 4: Implement asset preview page**

  Page requirements:

  - Filter by category.
  - Filter by tag.
  - Show name, category, tags, license, source, and status.
  - Render each SVG on a warm paper-like background.
  - Visually distinguish `approved`, `draft`, and `rejected`.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_assets.py
  cd frontend && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend frontend
  git commit -m "添加内置素材库和预览页"
  ```

### Task 6: Journal Schema and Renderer

**Files:**
- Create: `backend/app/schemas/journal.py`
- Create: `backend/tests/test_journal_schema.py`
- Create: `frontend/src/types/journal.ts`
- Create: `frontend/src/components/JournalCanvas.tsx`
- Create: `frontend/src/styles/globals.css`

- [ ] **Step 1: Define backend Pydantic schemas**

  Include schemas for canvas, theme, content, image placement, text placement, decoration placement, and full journal layout.

- [ ] **Step 2: Add schema validation tests**

  Test valid layout with `1080 x 1440`. Test invalid layout with unsupported canvas size and missing title.

- [ ] **Step 3: Define frontend TypeScript types**

  Mirror backend field names exactly. Use `JournalLayout`, `JournalImagePlacement`, `JournalTextPlacement`, and `JournalDecoration`.

- [ ] **Step 4: Implement `JournalCanvas`**

  Render:

  - Fixed 1080 x 1440 canvas.
  - Warm paper background.
  - Uploaded images at layout coordinates.
  - Title and body text.
  - Decoration SVGs.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_journal_schema.py
  cd frontend && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend frontend
  git commit -m "定义手帐结构并实现画布渲染"
  ```

### Task 7: OpenAI Journal Generation

**Files:**
- Create: `backend/app/services/openai_client.py`
- Create: `backend/app/services/journal_generator.py`
- Create: `backend/tests/test_generation.py`

- [ ] **Step 1: Add generator tests with fake OpenAI client**

  Test cases:

  - Generator returns valid `JournalLayout`.
  - Generated layout includes only provided image IDs.
  - Generated decorations include only `approved` asset IDs.
  - Invalid model JSON is rejected and converted to a generation error.

- [ ] **Step 2: Implement OpenAI client wrapper**

  Wrapper accepts user input, image metadata, and approved asset candidates. It returns raw model JSON.

- [ ] **Step 3: Implement generator service**

  Responsibilities:

  - Build prompt.
  - Call OpenAI client.
  - Validate JSON with Pydantic schema.
  - Clamp canvas size to 1080 x 1440.
  - Replace unknown asset IDs with approved alternatives.
  - Return a typed layout.

- [ ] **Step 4: Add real-call guard**

  Tests use a fake client. Production requires `OPENAI_API_KEY`; startup should fail with a clear error only when generation route is called without the key.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_generation.py
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend/app/services backend/tests/test_generation.py
  git commit -m "实现手帐生成服务"
  ```

### Task 8: Journal API

**Files:**
- Create: `backend/app/api/routes/journals.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_journals.py`
- Create: `frontend/src/api/journals.ts`

- [ ] **Step 1: Add journal API tests**

  Test cases:

  - `POST /api/journals/generate` requires auth.
  - Generate requires 1-9 image IDs and non-empty description.
  - User cannot generate with another user's image IDs.
  - Generated journal is saved.
  - `GET /api/journals` returns only current user's journals.
  - `GET /api/journals/{id}` enforces ownership.
  - `PATCH /api/journals/{id}` updates title, body, and layout variant.
  - `DELETE /api/journals/{id}` deletes journal and associated image files.

- [ ] **Step 2: Implement routes**

  Routes:

  - `POST /api/journals/generate`
  - `GET /api/journals`
  - `GET /api/journals/{journal_id}`
  - `PATCH /api/journals/{journal_id}`
  - `DELETE /api/journals/{journal_id}`

- [ ] **Step 3: Implement delete cleanup**

  When deleting a journal, remove:

  - `journal_images` rows.
  - `journals` row.
  - Associated image rows.
  - Original image files.
  - Thumbnail files.

- [ ] **Step 4: Add frontend journal API client**

  Include functions for generate, list, detail, update, and delete.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_journals.py
  cd frontend && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend frontend
  git commit -m "实现手帐接口和历史保存"
  ```

### Task 9: Create Journal Flow

**Files:**
- Create: `frontend/src/pages/CreateJournalPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ImageUploader.tsx`

- [ ] **Step 1: Build create form**

  Fields:

  - Images, required 1-9.
  - Description, required.
  - Date, optional.
  - Location, optional.
  - Mood tags, optional comma-separated input.

  Use shadcn/ui form controls, react-hook-form, and Zod validation. Use TanStack Query for API mutation state.

- [ ] **Step 2: Add validation states**

  Show clear errors for empty description, missing images, and more than 9 images.

- [ ] **Step 3: Wire generation call**

  On submit, upload selected images, call generate API, then navigate to journal detail page.

- [ ] **Step 4: Add loading and failure states**

  Loading copy: `正在生成手帐...`  
  Failure copy: `生成失败，请稍后重试。`

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd frontend && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend
  git commit -m "实现手帐创建流程"
  ```

### Task 10: Journal Detail, Editing, and Regeneration

**Files:**
- Create: `frontend/src/pages/JournalDetailPage.tsx`
- Create: `frontend/src/components/JournalEditor.tsx`
- Modify: `frontend/src/components/JournalCanvas.tsx`
- Modify: `backend/app/api/routes/journals.py`
- Modify: `backend/tests/test_journals.py`

- [ ] **Step 1: Add backend tests for text regeneration**

  Test `POST /api/journals/{journal_id}/regenerate-copy` keeps image placements and decorations but replaces title/body/captions.

- [ ] **Step 2: Implement regeneration route**

  Route:

  - `POST /api/journals/{journal_id}/regenerate-copy`

- [ ] **Step 3: Build editor UI**

  Support:

  - Edit title.
  - Edit body paragraphs.
  - Select layout variant from `collage_a`, `collage_b`, `collage_c`.
  - Save changes.
  - Regenerate copy.

- [ ] **Step 4: Verify**

  Run:

  ```bash
  cd backend && python -m pytest backend/tests/test_journals.py
  cd frontend && npm run build
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add backend frontend
  git commit -m "实现手帐预览和轻量编辑"
  ```

### Task 11: History Page

**Files:**
- Create: `frontend/src/pages/HistoryPage.tsx`
- Modify: `frontend/src/api/journals.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Build history list**

  Show journal title, updated time, first thumbnail, and status actions.

- [ ] **Step 2: Add empty state**

  Empty copy: `还没有手帐，先创建一篇吧。`

- [ ] **Step 3: Add delete action**

  Confirm before delete. After delete, remove item from list.

- [ ] **Step 4: Verify**

  Run:

  ```bash
  cd frontend && npm run build
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend
  git commit -m "实现手帐历史页"
  ```

### Task 12: PNG Export

**Files:**
- Create: `frontend/src/utils/exportPng.ts`
- Modify: `frontend/src/pages/JournalDetailPage.tsx`
- Modify: `frontend/package.json`

- [ ] **Step 1: Add export dependency**

  Use `html-to-image`.

- [ ] **Step 2: Implement export helper**

  Export the `JournalCanvas` DOM node as PNG with width `1080` and height `1440`.

- [ ] **Step 3: Add export UI**

  Button label: `导出 PNG`  
  Filename pattern: `komorebi-<journal_id>.png`

- [ ] **Step 4: Add export readiness guard**

  Disable export until images and SVG decorations have loaded.

- [ ] **Step 5: Verify**

  Run:

  ```bash
  cd frontend && npm run build
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend
  git commit -m "实现 PNG 导出"
  ```

### Task 13: Docker Compose Deployment

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `Caddyfile`
- Modify: `.env.example`
- Create: `docs/deployment.md`

- [ ] **Step 1: Add backend Dockerfile**

  Backend container runs FastAPI with Uvicorn and mounts persistent storage volume.

- [ ] **Step 2: Add frontend Dockerfile**

  Frontend builds static files with Vite and serves them through the proxy service.

- [ ] **Step 3: Add Docker Compose services**

  Services:

  - `postgres`
  - `backend`
  - `frontend`
  - `proxy`

- [ ] **Step 4: Add environment example**

  Required variables:

  - `DATABASE_URL`
  - `JWT_SECRET`
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `STORAGE_ROOT`
  - `PUBLIC_API_BASE_URL`

- [ ] **Step 5: Add deployment doc**

  Include commands:

  ```bash
  docker compose up -d --build
  docker compose logs -f backend
  docker compose exec backend alembic upgrade head
  ```

- [ ] **Step 6: Verify**

  Run:

  ```bash
  docker compose config
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add docker-compose.yml backend/Dockerfile frontend/Dockerfile Caddyfile .env.example docs/deployment.md
  git commit -m "添加 Docker 部署配置"
  ```

### Task 14: End-to-End Smoke Test

**Files:**
- Create: `docs/smoke-test.md`
- Modify: `README.md`

- [ ] **Step 1: Add manual smoke test checklist**

  Checklist:

  - Register a user.
  - Log in.
  - Upload 1-9 images.
  - Generate journal with real OpenAI call.
  - Open generated journal.
  - Edit title and body.
  - Save changes.
  - View history.
  - Open asset preview page and filter approved assets.
  - Export PNG.
  - Delete journal and verify associated image files are removed.

- [ ] **Step 2: Add README**

  Include project purpose, local dev commands, Docker commands, environment variables, and links to docs.

- [ ] **Step 3: Run full verification**

  Run:

  ```bash
  cd backend && python -m pytest
  cd frontend && npm run build
  docker compose config
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add docs/smoke-test.md README.md
  git commit -m "补充验收测试文档"
  ```

## 5. Recommended Execution Order

1. Task 1: Project Skeleton
2. Task 2: Database and Migrations
3. Task 3: Account Password Auth
4. Task 4: Local File Storage and Image Upload
5. Task 5: Built-In Asset Library
6. Task 6: Journal Schema and Renderer
7. Task 7: OpenAI Journal Generation
8. Task 8: Journal API
9. Task 9: Create Journal Flow
10. Task 10: Journal Detail, Editing, and Regeneration
11. Task 11: History Page
12. Task 12: PNG Export
13. Task 13: Docker Compose Deployment
14. Task 14: End-to-End Smoke Test

## 6. Verification Policy

Before claiming a task is complete:

- Run the exact verification commands listed in that task.
- Read the output and confirm success.
- Commit only the files listed for the task plus directly required supporting files.
- Do not commit `.env`, uploaded images, generated PNGs, or local storage directories.

## 7. Risk Notes

- Browser PNG export can fail if images or SVG assets are served with incompatible CORS headers. Serve all user images and asset SVGs through the same backend/proxy origin.
- OpenAI responses must be schema-validated. Never persist raw model output without validation.
- The MVP treats uploaded images as journal-owned. Deleting a journal must remove its associated original image files, thumbnail files, image rows, and join rows.
- The asset library quality gate matters. Keep `draft` and `rejected` assets visible in the preview page but exclude them from generation.
- Password auth is acceptable for 2-10 private users, but use strong password hashing and HTTPS in deployment.
