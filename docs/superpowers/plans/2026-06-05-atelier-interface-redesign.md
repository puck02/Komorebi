# Atelier Interface Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the logged-in Komorebi interface to the approved “手帐工作室” visual direction while preserving existing routes, API flows, journal rendering, and PNG export.

**Architecture:** Keep the existing React + Vite app and its current custom CSS approach. Centralize the new atelier palette and interaction states in `globals.css`, then update the shared `Button`, `Input`, `Card`, `AssetCard`, and affected page shells to use the same paper-like visual language.

**Tech Stack:** React 19, Vite 7, TypeScript, Tailwind v4, class-variance-authority, lucide-react, existing CSS in `frontend/src/styles/globals.css`.

---

## File Structure

- Modify `frontend/src/styles/globals.css`: global design tokens, app shell, nav, auth, create page, uploader, history, asset library, account, preview page, responsive styles.
- Modify `frontend/src/components/ui/button.tsx`: replace hardcoded pink/blue variants with atelier color classes and consistent focus/active states.
- Modify `frontend/src/components/ui/input.tsx`: align input styling with the new paper/input tokens.
- Modify `frontend/src/components/ui/card.tsx`: make shared cards look like quiet paper surfaces.
- Modify `frontend/src/components/AssetCard.tsx`: update status tones, card layout classes, status menu, and tags.
- Modify `frontend/src/pages/AssetLibraryPage.tsx`: replace hardcoded filter/stat classes with semantic class names backed by `globals.css`.
- Do not modify backend code, journal canvas rendering logic, auth flow, upload flow, generation flow, or export behavior.

## Task 1: Global Tokens, Shared Controls, And App Shell

**Files:**
- Modify: `frontend/src/styles/globals.css`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/input.tsx`
- Modify: `frontend/src/components/ui/card.tsx`

- [ ] **Step 1: Capture baseline build**

Run:

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build complete successfully. If it fails before any edits, record the failure and do not fix unrelated issues in this task.

- [ ] **Step 2: Replace global design tokens and base surfaces**

In `frontend/src/styles/globals.css`, replace the existing `:root`, `body`, `.app-shell`, `.top-nav`, `.brand-link`, `.nav-actions`, `.nav-link`, and mobile nav blocks with:

```css
:root {
  --color-background: #f5efe5;
  --color-headline: #332319;
  --color-paragraph: #6f5645;
  --color-button: #b86f5b;
  --color-main: #ead8c8;
  --color-highlight: #fffaf2;
  --color-secondary: #b9c8a9;
  --color-tertiary: #8d6a56;
  --color-stroke: #332319;
  --color-peach-light: var(--color-background);
  --color-peach: var(--color-main);
  --color-rose: var(--color-secondary);
  --color-mauve: var(--color-button);
  --color-ink: var(--color-headline);
  --color-paper: var(--color-highlight);
  --color-paper-strong: #fffdf8;
  --color-border: #dcc7b6;
  --shadow-soft: 0 18px 42px rgb(67 46 31 / 12%);
  --shadow-paper: 0 10px 28px rgb(67 46 31 / 10%);
  --focus-ring: 0 0 0 3px rgb(184 111 91 / 22%);
  color: var(--color-paragraph);
  background: var(--color-background);
  font-family:
    ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 8%, rgb(255 250 242 / 72%), transparent 30%),
    radial-gradient(circle at 86% 14%, rgb(185 200 169 / 22%), transparent 28%),
    repeating-linear-gradient(-8deg, rgb(67 46 31 / 2%) 0 1px, transparent 1px 18px),
    linear-gradient(135deg, #fffaf2 0%, #f5efe5 58%, #ead8c8 100%);
}

:focus-visible {
  outline: 0;
  box-shadow: var(--focus-ring);
}

.app-shell {
  position: relative;
  min-height: 100vh;
  padding-top: 88px;
  background:
    radial-gradient(circle at 8% 0%, rgb(255 250 242 / 78%), transparent 30%),
    radial-gradient(circle at 92% 18%, rgb(185 200 169 / 18%), transparent 26%),
    repeating-linear-gradient(90deg, rgb(67 46 31 / 2%) 0 1px, transparent 1px 22px),
    linear-gradient(135deg, #fffaf2 0%, #f5efe5 62%, #ead8c8 100%);
}

.top-nav {
  position: fixed;
  top: 12px;
  left: 50%;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  width: min(1120px, calc(100% - 32px));
  margin: 0;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 10px 14px;
  background:
    linear-gradient(135deg, rgb(255 253 248 / 92%), rgb(255 250 242 / 82%)),
    var(--color-paper);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 70%),
    0 16px 36px rgb(67 46 31 / 12%);
  transform: translateX(-50%);
}

.brand-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  border-radius: 8px;
  padding: 0 10px;
  color: var(--color-ink);
  font-weight: 900;
  letter-spacing: 0.01em;
  text-decoration: none;
}

.brand-link::before {
  position: absolute;
  inset: 6px 4px 5px;
  z-index: -1;
  border-radius: 6px;
  background: rgb(234 216 200 / 62%);
  content: "";
  transform: rotate(-1.2deg);
}

.nav-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  color: var(--color-ink);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  border-radius: 8px;
  padding: 0 10px;
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 800;
  text-decoration: none;
  transition:
    background 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.nav-link:hover {
  background: rgb(255 253 248 / 78%);
  box-shadow: inset 0 0 0 1px rgb(220 199 182 / 60%);
}

.nav-link.is-active {
  color: #fffdf8;
  background: var(--color-button);
  box-shadow: 0 8px 18px rgb(184 111 91 / 22%);
}

.nav-link:active {
  transform: translateY(1px);
}

@media (max-width: 520px) {
  .top-nav {
    left: 12px;
    width: calc(100% - 24px);
    gap: 10px;
    padding: 10px 12px;
    transform: none;
  }

  .nav-link {
    width: 36px;
    justify-content: center;
    padding: 0;
  }

  .nav-label {
    display: none;
  }
}
```

- [ ] **Step 3: Replace shared button variants**

In `frontend/src/components/ui/button.tsx`, replace the `buttonVariants` definition with:

```tsx
const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-[8px] px-4 text-sm font-semibold transition-[background,border-color,box-shadow,color,transform,opacity] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b86f5b]/25 disabled:pointer-events-none disabled:opacity-55 active:translate-y-px",
  {
    defaultVariants: {
      size: "default",
      variant: "default"
    },
    variants: {
      size: {
        default: "h-10 px-4",
        icon: "h-10 w-10 px-0",
        sm: "h-8 px-3 text-xs"
      },
      variant: {
        default: "bg-[#b86f5b] text-[#fffdf8] shadow-[0_10px_22px_rgba(184,111,91,0.24)] hover:bg-[#a7604f]",
        ghost: "text-[#332319] hover:bg-[#fffdf8]/75 hover:shadow-[inset_0_0_0_1px_rgba(220,199,182,0.7)]",
        outline: "border border-[#dcc7b6] bg-[#fffaf2] text-[#332319] hover:border-[#c8ad99] hover:bg-[#fffdf8]",
        selected: "border border-[#b86f5b] bg-[#b86f5b] text-[#fffdf8] shadow-[0_8px_18px_rgba(184,111,91,0.2)] hover:bg-[#a7604f]"
      }
    }
  }
);
```

- [ ] **Step 4: Replace shared input styles**

In `frontend/src/components/ui/input.tsx`, replace the class string with:

```tsx
"h-10 rounded-[8px] border border-[#dcc7b6] bg-[#fffdf8] px-3 text-sm font-medium text-[#332319] outline-none transition-[background,border-color,box-shadow] placeholder:text-[#8d6a56]/70 focus:border-[#b86f5b] focus:shadow-[0_0_0_3px_rgba(184,111,91,0.16)]"
```

- [ ] **Step 5: Replace shared card styles**

In `frontend/src/components/ui/card.tsx`, replace the exported component class strings with:

```tsx
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-[12px] border border-[#dcc7b6] bg-[#fffaf2] shadow-[0_12px_30px_rgba(67,46,31,0.1)]", className)}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("grid gap-1.5 p-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-base font-semibold text-[#332319]", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4 pt-0", className)} {...props} />;
}
```

- [ ] **Step 6: Verify Task 1**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes. If class strings introduce TypeScript or JSX errors, fix only the touched files.

- [ ] **Step 7: Commit Task 1**

```bash
git add frontend/src/styles/globals.css frontend/src/components/ui/button.tsx frontend/src/components/ui/input.tsx frontend/src/components/ui/card.tsx
git commit -m "统一手帐工作室基础样式"
```

## Task 2: Create Page And Image Uploader Atelier Treatment

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Update create page layout and form styles**

In `frontend/src/styles/globals.css`, replace the blocks from `.hero-panel` through `.create-submit` with:

```css
.hero-panel {
  max-width: 1120px;
  margin: 96px auto 0;
  padding: 0 20px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--color-tertiary);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-panel h1 {
  max-width: 760px;
  margin: 0;
  color: var(--color-ink);
  font-size: clamp(40px, 7vw, 82px);
  line-height: 1.02;
  text-wrap: balance;
}

.hero-copy {
  max-width: 560px;
  margin: 24px 0 0;
  color: var(--color-paragraph);
  font-size: 16px;
  line-height: 1.7;
}

.create-page {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 54px 20px 84px;
}

.create-header {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
}

.create-header h1 {
  max-width: 680px;
  margin: 0;
  color: var(--color-ink);
  font-size: clamp(34px, 5vw, 58px);
  line-height: 1.04;
  text-wrap: balance;
}

.create-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 440px);
  gap: 22px;
  align-items: start;
}

.create-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  background:
    linear-gradient(135deg, rgb(255 253 248 / 94%), rgb(255 250 242 / 82%)),
    var(--color-paper);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 70%),
    var(--shadow-soft);
}

.create-panel::before {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(-7deg, rgb(67 46 31 / 2%) 0 1px, transparent 1px 16px);
  content: "";
  pointer-events: none;
}

.create-panel > * {
  position: relative;
}

.create-form-panel {
  display: grid;
  gap: 16px;
}

.field-label {
  display: grid;
  gap: 8px;
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 850;
}

.field-label span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.textarea-field {
  width: 100%;
  min-height: 180px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 12px;
  color: var(--color-ink);
  background: var(--color-paper-strong);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 78%);
  font: inherit;
  font-weight: 500;
  line-height: 1.65;
  outline: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.textarea-field:focus {
  border-color: var(--color-button);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 78%),
    var(--focus-ring);
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mood-field {
  position: relative;
}

.mood-picker-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0 12px;
  color: var(--color-ink);
  background: var(--color-paper-strong);
  font: inherit;
  font-weight: 800;
  text-align: left;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.mood-picker-trigger:hover,
.mood-picker-trigger[aria-expanded="true"] {
  border-color: var(--color-button);
  background: #fffdf8;
  box-shadow: var(--focus-ring);
}

.mood-picker-trigger:active {
  transform: translateY(1px);
}

.mood-picker {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 10px;
  background: var(--color-paper);
  box-shadow: 0 18px 42px rgb(67 46 31 / 16%);
}

.mood-picker button {
  min-height: 34px;
  border: 1px solid rgb(220 199 182 / 82%);
  border-radius: 7px;
  color: var(--color-ink);
  background: rgb(255 253 248 / 78%);
  font: inherit;
  font-weight: 850;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.mood-picker button:hover {
  border-color: var(--color-button);
}

.mood-picker button.is-selected {
  border-color: var(--color-button);
  color: #fffdf8;
  background: var(--color-button);
}

.mood-picker button:active {
  transform: translateY(1px);
}

.create-submit {
  width: 100%;
}
```

- [ ] **Step 2: Update uploader styles**

In `frontend/src/styles/globals.css`, replace the `.image-uploader` through `.upload-grid button` blocks with:

```css
.image-uploader {
  display: grid;
  gap: 16px;
}

.upload-hint {
  margin: -6px 0 0;
  color: rgb(111 86 69 / 82%);
  font-size: 13px;
  line-height: 1.5;
}

.upload-zone {
  appearance: none;
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 146px;
  border: 1px dashed var(--color-button);
  border-radius: 12px;
  color: var(--color-ink);
  background:
    repeating-linear-gradient(-10deg, rgb(184 111 91 / 6%) 0 1px, transparent 1px 18px),
    var(--color-paper-strong);
  font: inherit;
  font-weight: 850;
  text-align: center;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.upload-zone:hover {
  background:
    repeating-linear-gradient(-10deg, rgb(184 111 91 / 7%) 0 1px, transparent 1px 18px),
    #fffdf8;
  box-shadow: inset 0 0 0 1px rgb(184 111 91 / 12%);
}

.upload-zone:active {
  transform: translateY(1px);
}

.upload-zone.is-disabled {
  cursor: wait;
  opacity: 0.7;
}

.upload-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  opacity: 0;
  cursor: pointer;
}

.upload-input:disabled {
  cursor: wait;
}

.upload-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  align-items: start;
}

.upload-grid figure {
  position: relative;
  display: grid;
  gap: 8px;
  margin: 0;
  touch-action: pan-y;
  transition:
    opacity 160ms ease,
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 180ms cubic-bezier(0.22, 1, 0.36, 1);
  user-select: none;
  -webkit-touch-callout: none;
}

.upload-grid figure:nth-child(3n + 1) img {
  transform: rotate(-1.4deg);
}

.upload-grid figure:nth-child(3n + 2) img {
  transform: rotate(1.2deg);
}

.upload-grid img {
  width: 100%;
  aspect-ratio: 1;
  border: 8px solid var(--color-paper-strong);
  border-bottom-width: 16px;
  border-radius: 7px;
  box-shadow: 0 12px 24px rgb(67 46 31 / 16%);
  object-fit: cover;
  pointer-events: none;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
  user-select: none;
  -webkit-touch-callout: none;
  -webkit-user-drag: none;
}

.upload-grid figure.is-drag-target {
  transform: scale(0.96);
  opacity: 0.72;
}

.upload-grid figure.is-drag-placeholder {
  opacity: 0.36;
  pointer-events: none;
  transform: scale(0.94);
}

.upload-drag-ghost {
  position: fixed;
  top: var(--drag-top);
  left: var(--drag-left);
  z-index: 90;
  display: grid;
  width: var(--drag-width);
  margin: 0;
  filter: saturate(1.04);
  pointer-events: none;
  touch-action: none;
  transform: translate3d(var(--drag-x, 0), var(--drag-y, 0), 0) scale(1.055) rotate(-1.5deg);
  will-change: transform;
}

.upload-drag-ghost img {
  width: 100%;
  aspect-ratio: 1;
  border: 8px solid var(--color-paper-strong);
  border-bottom-width: 16px;
  border-radius: 7px;
  object-fit: cover;
  box-shadow:
    0 0 0 4px rgb(184 111 91 / 20%),
    0 18px 42px rgb(67 46 31 / 24%);
  user-select: none;
  -webkit-touch-callout: none;
  -webkit-user-drag: none;
}

.upload-grid button {
  min-height: 32px;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  color: var(--color-ink);
  background: var(--color-paper-strong);
  font: inherit;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}

.upload-grid button:hover {
  border-color: var(--color-button);
}

.upload-grid button:active {
  transform: translateY(1px);
}
```

- [ ] **Step 3: Verify create page build**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes.

- [ ] **Step 4: Commit Task 2**

```bash
git add frontend/src/styles/globals.css
git commit -m "优化创建页手帐工作台质感"
```

## Task 3: History, Account, And Auth Paper Surfaces

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Replace auth, history, account, and lightbox surface blocks**

In `frontend/src/styles/globals.css`, update these selector groups while preserving existing layout breakpoints:

```css
.form-error {
  margin: 0;
  color: #9b4f40;
  font-size: 14px;
  font-weight: 750;
}

.login-scene {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100dvh;
  overflow: hidden;
  padding: 32px 20px;
  background:
    radial-gradient(circle at 18% 24%, rgb(255 250 242 / 90%), transparent 34%),
    radial-gradient(circle at 82% 18%, rgb(185 200 169 / 34%), transparent 32%),
    repeating-linear-gradient(-8deg, rgb(67 46 31 / 3%) 0 1px, transparent 1px 18px),
    linear-gradient(115deg, #fffaf2 0%, #f5efe5 54%, #ead8c8 100%);
}

.login-scene::before {
  position: absolute;
  inset: -18% 18% -22% -18%;
  background:
    radial-gradient(closest-side at 36% 52%, rgb(185 200 169 / 36%), transparent 72%),
    radial-gradient(closest-side at 18% 22%, rgb(255 253 248 / 72%), transparent 76%),
    linear-gradient(155deg, rgb(184 111 91 / 22%), rgb(255 250 242 / 0) 58%);
  content: "";
  filter: blur(22px);
  opacity: 0.92;
  pointer-events: none;
}

.login-scene::after {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgb(255 253 248 / 34%), rgb(255 253 248 / 8%) 45%, rgb(255 253 248 / 26%)),
    repeating-linear-gradient(90deg, rgb(67 46 31 / 3%) 0 1px, transparent 1px 16px);
  content: "";
  pointer-events: none;
}

.login-form {
  position: relative;
  z-index: 1;
  width: min(720px, 100%);
  max-width: none;
  min-height: 420px;
  margin: 0;
  justify-items: center;
  align-content: center;
  gap: 18px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: clamp(36px, 8vw, 74px) clamp(24px, 8vw, 112px);
  background:
    linear-gradient(110deg, rgb(255 253 248 / 90%), rgb(255 250 242 / 72%)),
    var(--color-paper);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 70%),
    0 30px 80px rgb(67 46 31 / 16%);
  color: var(--color-ink);
}

.login-brand {
  margin: 0;
  color: var(--color-ink);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.login-form h1 {
  margin: 0 0 18px;
  color: var(--color-ink);
  font-size: clamp(34px, 6vw, 48px);
  font-weight: 900;
  line-height: 1;
}

.login-form label {
  width: min(360px, 100%);
  gap: 5px;
  color: var(--color-ink);
  font-size: 12px;
  font-weight: 800;
}

.login-form input {
  width: 100%;
  min-height: 34px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0 14px;
  color: var(--color-ink);
  background: var(--color-paper-strong);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 78%);
  font-weight: 700;
}

.login-form input:focus {
  border-color: var(--color-button);
  outline: 0;
  box-shadow: var(--focus-ring);
}

.login-register-link {
  margin-top: 14px;
  color: var(--color-button);
  font-size: 13px;
}

.login-register-link:hover {
  color: var(--color-ink);
}

.login-submit {
  width: min(360px, 100%);
  min-height: 38px;
  border-radius: 8px;
  color: #fffdf8;
  background: var(--color-button);
  box-shadow: 0 12px 28px rgb(184 111 91 / 24%);
}

.login-submit:hover:not(:disabled) {
  background: #a7604f;
  box-shadow: 0 16px 34px rgb(184 111 91 / 28%);
}

.login-error {
  width: min(360px, 100%);
  border-radius: 8px;
  padding: 8px 10px;
  background: rgb(255 253 248 / 86%);
  font-weight: 800;
}

.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  border: 0;
  padding: 24px;
  color: var(--color-ink);
  background: rgb(51 35 25 / 68%);
  cursor: zoom-out;
}

.image-lightbox img {
  display: block;
  max-width: min(1040px, 94vw);
  max-height: 88vh;
  border: 10px solid var(--color-paper-strong);
  border-radius: 8px;
  background: var(--color-paper-strong);
  box-shadow: 0 24px 80px rgb(51 35 25 / 34%);
  object-fit: contain;
}

.image-lightbox span {
  position: absolute;
  top: 24px;
  left: 50%;
  border-radius: 8px;
  padding: 8px 12px;
  background: var(--color-paper-strong);
  font-size: 13px;
  font-weight: 800;
  transform: translateX(-50%);
}

.history-page,
.account-page {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px 20px 88px;
}

.history-header,
.account-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 20px;
}

.history-header h1,
.account-header h1 {
  margin: 0;
  color: var(--color-ink);
  font-size: clamp(34px, 5vw, 54px);
  line-height: 1.05;
  text-wrap: balance;
}

.history-grid {
  display: grid;
  gap: 14px;
}

.history-card {
  position: relative;
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 16px;
  min-height: 156px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 14px;
  color: inherit;
  background: var(--color-paper);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 72%),
    var(--shadow-paper);
  text-decoration: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.history-card:hover {
  border-color: #c8ad99;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 76%),
    0 16px 36px rgb(67 46 31 / 14%);
  transform: translateY(-2px) rotate(-0.2deg);
}

.history-card:active {
  transform: translateY(0);
}

.history-thumb {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border: 8px solid var(--color-paper-strong);
  border-bottom-width: 14px;
  border-radius: 7px;
  color: var(--color-button);
  background: #ead8c8;
  box-shadow: 0 10px 22px rgb(67 46 31 / 14%);
}

.history-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.history-card-body {
  display: grid;
  min-width: 0;
  gap: 12px;
  align-content: start;
}

.history-card-title-row {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.history-card-title-row h2 {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--color-ink);
  font-size: 22px;
  line-height: 1.22;
}

.history-card-title-row span,
.history-card-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  padding: 5px 9px;
  color: var(--color-paragraph);
  background: rgb(255 253 248 / 72%);
  font-size: 12px;
  font-weight: 850;
  overflow-wrap: anywhere;
}

.history-card-title-row span {
  flex: 0 0 auto;
  color: var(--color-ink);
}

.history-card-body p {
  display: -webkit-box;
  max-width: 760px;
  margin: 0;
  overflow: hidden;
  color: var(--color-paragraph);
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-empty {
  display: grid;
  justify-items: start;
  gap: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 28px;
  color: var(--color-ink);
  background: var(--color-paper);
  box-shadow: var(--shadow-soft);
}

.history-empty h2 {
  margin: 0;
  color: var(--color-ink);
  font-size: 24px;
}

.history-empty p {
  margin: 0;
  color: var(--color-paragraph);
  line-height: 1.7;
}

.account-panel {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  background: var(--color-paper);
  box-shadow: var(--shadow-soft);
}

.account-avatar {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  color: var(--color-ink);
  background: var(--color-paper-strong);
}

.account-info {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.account-info span {
  color: var(--color-tertiary);
  font-size: 13px;
  font-weight: 850;
}

.account-info p {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin: 0;
  color: var(--color-ink);
  font-size: 17px;
  font-weight: 850;
  overflow-wrap: anywhere;
}

.account-logout {
  white-space: nowrap;
}
```

- [ ] **Step 2: Verify Task 3**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit Task 3**

```bash
git add frontend/src/styles/globals.css
git commit -m "统一历史账号登录纸张界面"
```

## Task 4: Asset Library And Asset Cards

**Files:**
- Modify: `frontend/src/pages/AssetLibraryPage.tsx`
- Modify: `frontend/src/components/AssetCard.tsx`
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Replace asset library JSX class names**

In `frontend/src/pages/AssetLibraryPage.tsx`, replace the outer returned section with class-based markup:

```tsx
return (
  <section className="asset-library-page">
    <div className="asset-library-header">
      <div className="asset-status-strip">
        <span data-status="approved">approved {statusCounts.approved}</span>
        <span data-status="draft">draft {statusCounts.draft}</span>
        <span data-status="rejected">rejected {statusCounts.rejected}</span>
      </div>
      <div className="asset-count">
        <strong>{filteredAssets.length}</strong> / {assets.length} assets
      </div>
    </div>

    <div className="asset-filter-panel">
      <FilterRow label="分类" options={categories} value={category} onChange={setCategory} />
      <FilterRow label="状态" options={statuses} value={status} onChange={setStatus} />
      <FilterRow label="标签" options={tags} value={tag} onChange={setTag} />
    </div>

    {isLoading ? <p className="asset-state-text">正在加载素材...</p> : null}
    {error instanceof Error ? <p className="asset-state-text is-error">{error.message}</p> : null}
    {!isLoading && filteredAssets.length === 0 ? <p className="asset-state-text">没有符合筛选条件的素材。</p> : null}

    <div className="asset-grid">
      {filteredAssets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          canManage={permissionsQuery.data?.can_manage_assets ?? false}
          isUpdating={updateStatusMutation.isPending && updateStatusMutation.variables?.assetId === asset.id}
          onStatusChange={(qualityStatus) => updateStatusMutation.mutate({ assetId: asset.id, qualityStatus })}
        />
      ))}
    </div>
  </section>
);
```

Replace `FilterRow` return markup with:

```tsx
return (
  <div className="asset-filter-row">
    <span>{label}</span>
    <div>
      {options.map((option) => (
        <Button
          key={option}
          size="sm"
          type="button"
          variant={value === option ? "selected" : "outline"}
          onClick={() => onChange(option)}
        >
          {option === allValue ? "全部" : option}
        </Button>
      ))}
    </div>
  </div>
);
```

- [ ] **Step 2: Replace asset card tones and class names**

In `frontend/src/components/AssetCard.tsx`, update `statusMeta`:

```tsx
const statusMeta = {
  approved: {
    icon: BadgeCheck,
    label: "approved",
    tone: "is-approved"
  },
  draft: {
    icon: CircleDashed,
    label: "draft",
    tone: "is-draft"
  },
  rejected: {
    icon: CircleSlash,
    label: "rejected",
    tone: "is-rejected"
  }
} satisfies Record<AssetQualityStatus, { icon: typeof BadgeCheck; label: string; tone: string }>;
```

Replace the component JSX with class-backed markup:

```tsx
return (
  <Card
    className={`asset-card ${canManage ? "is-manageable" : ""}`}
    onClick={() => {
      if (canManage) {
        setIsStatusMenuOpen((isOpen) => !isOpen);
      }
    }}
    onKeyDown={(event) => {
      if (!canManage || (event.key !== "Enter" && event.key !== " ")) {
        return;
      }
      event.preventDefault();
      setIsStatusMenuOpen((isOpen) => !isOpen);
    }}
    role={canManage ? "button" : undefined}
    tabIndex={canManage ? 0 : undefined}
  >
    <div className="asset-card-preview">
      <img src={asset.file_url} alt={asset.name} />
    </div>
    <CardHeader>
      <div className="asset-card-title-row">
        <CardTitle>{asset.name}</CardTitle>
        <span className={`asset-status-pill ${status.tone}`}>
          <StatusIcon size={13} />
          {status.label}
        </span>
      </div>
      <p className="asset-category">{asset.category}</p>
    </CardHeader>
    <CardContent className="asset-card-content">
      {canManage && isStatusMenuOpen ? (
        <div className="asset-status-menu">
          <span>状态</span>
          <div>
            {statusOptions.map((option) => (
              <button
                className={asset.quality_status === option ? "is-selected" : ""}
                disabled={isUpdating || asset.quality_status === option}
                key={option}
                onClick={(event) => {
                  event.stopPropagation();
                  onStatusChange?.(option);
                }}
                type="button"
              >
                {isUpdating && asset.quality_status !== option ? "更新中..." : option}
              </button>
            ))}
          </div>
        </div>
      ) : null}
      <div className="asset-tags">
        {asset.tags.slice(0, 5).map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <dl className="asset-meta-list">
        <div>
          <dt>license</dt>
          <dd>{asset.license}</dd>
        </div>
        <div>
          <dt>source</dt>
          <dd>{asset.source}</dd>
        </div>
      </dl>
    </CardContent>
  </Card>
);
```

- [ ] **Step 3: Add asset library CSS**

Append this section before the final media queries in `frontend/src/styles/globals.css`:

```css
.asset-library-page {
  display: grid;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  gap: 22px;
  padding: 32px 20px 88px;
}

.asset-library-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 18px;
}

.asset-status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  font-weight: 850;
}

.asset-status-strip span,
.asset-count {
  border: 1px solid var(--color-border);
  border-radius: 7px;
  padding: 7px 10px;
  color: var(--color-ink);
  background: var(--color-paper);
}

.asset-status-strip [data-status="approved"] {
  background: rgb(185 200 169 / 46%);
}

.asset-status-strip [data-status="draft"] {
  background: rgb(234 216 200 / 72%);
}

.asset-status-strip [data-status="rejected"] {
  background: rgb(184 111 91 / 16%);
}

.asset-count {
  color: var(--color-paragraph);
  font-size: 14px;
}

.asset-count strong {
  color: var(--color-button);
}

.asset-filter-panel {
  display: grid;
  gap: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 14px;
  background: var(--color-paper);
  box-shadow: var(--shadow-paper);
}

.asset-filter-row {
  display: grid;
  gap: 10px;
}

.asset-filter-row > span {
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 850;
}

.asset-filter-row > div {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (min-width: 768px) {
  .asset-filter-row {
    grid-template-columns: 72px 1fr;
    align-items: center;
  }
}

.asset-state-text {
  margin: 0;
  color: var(--color-paragraph);
  font-size: 14px;
  font-weight: 750;
}

.asset-state-text.is-error {
  color: #9b4f40;
}

.asset-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: 1fr;
}

@media (min-width: 640px) {
  .asset-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .asset-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .asset-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.asset-card {
  overflow: hidden;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.asset-card.is-manageable {
  cursor: pointer;
}

.asset-card.is-manageable:hover {
  border-color: #c8ad99;
  box-shadow: 0 16px 36px rgb(67 46 31 / 14%);
  transform: translateY(-2px);
}

.asset-card-preview {
  display: grid;
  aspect-ratio: 4 / 3;
  place-items: center;
  border-bottom: 1px solid var(--color-border);
  background:
    repeating-linear-gradient(-8deg, rgb(67 46 31 / 3%) 0 1px, transparent 1px 18px),
    #fffdf8;
  padding: 20px;
}

.asset-card-preview img {
  max-width: 100%;
  max-height: 100%;
  filter: drop-shadow(0 8px 14px rgb(67 46 31 / 14%));
}

.asset-card-title-row {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.asset-status-pill {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  padding: 5px 7px;
  color: var(--color-ink);
  font-size: 12px;
  font-weight: 850;
}

.asset-status-pill.is-approved {
  background: rgb(185 200 169 / 48%);
}

.asset-status-pill.is-draft {
  background: rgb(234 216 200 / 74%);
}

.asset-status-pill.is-rejected {
  background: rgb(184 111 91 / 16%);
}

.asset-category {
  margin: 0;
  color: var(--color-tertiary);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
}

.asset-card-content {
  display: grid;
  gap: 12px;
}

.asset-status-menu {
  display: grid;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px;
  background: var(--color-paper-strong);
}

.asset-status-menu > span {
  color: var(--color-paragraph);
  font-size: 12px;
  font-weight: 850;
}

.asset-status-menu > div {
  display: flex;
  gap: 8px;
}

.asset-status-menu button {
  min-height: 32px;
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  padding: 0 8px;
  color: var(--color-ink);
  background: var(--color-paper);
  font: inherit;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
}

.asset-status-menu button.is-selected {
  border-color: var(--color-button);
  color: #fffdf8;
  background: var(--color-button);
}

.asset-status-menu button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.asset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.asset-tags span {
  border: 1px solid rgb(220 199 182 / 72%);
  border-radius: 7px;
  padding: 4px 7px;
  color: var(--color-ink);
  background: rgb(255 253 248 / 68%);
  font-size: 12px;
}

.asset-meta-list {
  display: grid;
  gap: 4px;
  color: var(--color-paragraph);
  font-size: 12px;
}

.asset-meta-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.asset-meta-list dd {
  margin: 0;
  overflow: hidden;
  color: var(--color-ink);
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 4: Verify Task 4**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes. If the `statusMeta` `tone` type is too narrow, keep the `satisfies` type exactly as shown in Step 2.

- [ ] **Step 5: Commit Task 4**

```bash
git add frontend/src/pages/AssetLibraryPage.tsx frontend/src/components/AssetCard.tsx frontend/src/styles/globals.css
git commit -m "优化素材库纸质抽屉界面"
```

## Task 5: Journal Preview Page And Generation Panel

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Replace generation and journal preview surface styles**

In `frontend/src/styles/globals.css`, update generation and journal detail selectors:

```css
.generation-page {
  display: grid;
  min-height: calc(100dvh - 88px);
  place-items: center;
  padding: 32px 20px 88px;
}

.generation-panel {
  display: grid;
  justify-items: center;
  width: min(520px, 100%);
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 36px 28px;
  background: var(--color-paper);
  box-shadow: var(--shadow-soft);
  text-align: center;
}

.generation-mark {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 12px;
  color: var(--color-ink);
  background: rgb(185 200 169 / 62%);
  box-shadow: 0 12px 28px rgb(67 46 31 / 12%);
}

.generation-panel h1 {
  margin: 0;
  color: var(--color-ink);
  font-size: 25px;
}

.generation-panel p {
  margin: 0;
  color: var(--color-paragraph);
  font-size: 14px;
  line-height: 1.7;
}

.generation-progress {
  width: min(340px, 100%);
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(220 199 182 / 74%);
}

.generation-progress span {
  display: block;
  width: 42%;
  height: 100%;
  border-radius: inherit;
  background: var(--color-button);
  animation: generation-progress 1.6s ease-in-out infinite;
}

.journal-canvas-frame {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background);
  box-shadow: 0 18px 54px rgb(67 46 31 / 16%);
}

.journal-photo {
  margin: 0;
  border: 16px solid #fffaf2;
  border-bottom-width: 42px;
  background: #fffaf2;
  box-shadow: 0 14px 26px rgb(67 46 31 / 18%);
  cursor: zoom-in;
}

.journal-detail-page {
  --glass-scroll: 0;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px 20px 88px;
}

.journal-detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px;
  background: var(--color-paper);
  box-shadow: var(--shadow-paper);
}

.journal-detail-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.journal-detail-actions .liquid-glass-button {
  border: 1px solid var(--color-border);
  color: var(--color-ink);
  background: var(--color-paper-strong);
  box-shadow: none;
  text-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.journal-detail-actions .liquid-glass-button::before,
.journal-detail-actions .liquid-glass-button::after {
  display: none;
}

.journal-detail-actions .liquid-glass-button:hover {
  border-color: var(--color-button);
  box-shadow: var(--focus-ring);
}

.journal-detail-actions .liquid-glass-button:disabled {
  filter: saturate(70%);
}

.journal-detail-single {
  display: block;
}

.journal-preview-panel {
  display: grid;
  justify-items: center;
  overflow: visible;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 22px;
  background:
    repeating-linear-gradient(-8deg, rgb(67 46 31 / 2%) 0 1px, transparent 1px 18px),
    var(--color-paper);
  box-shadow: var(--shadow-soft);
}

.journal-canvas-fit-shell {
  display: grid;
  justify-items: center;
  width: 100%;
  min-width: 0;
}

.journal-image-loading {
  margin: 12px 0 0;
  color: var(--color-paragraph);
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.journal-export-error {
  margin: 12px auto 0;
  max-width: 520px;
  text-align: center;
}
```

Remove the previous long `.journal-detail-actions .liquid-glass-button::before` and `::after` visual blocks if they remain duplicated after this replacement.

- [ ] **Step 2: Verify Task 5**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit Task 5**

```bash
git add frontend/src/styles/globals.css
git commit -m "弱化预览页外层工具栏"
```

## Task 6: Responsive Audit, Visual Verification, And Final Commit

**Files:**
- Modify if needed: `frontend/src/styles/globals.css`
- No planned source changes unless verification finds overflow or broken states.

- [ ] **Step 1: Run full frontend checks**

Run:

```bash
cd frontend
npm run build
```

Expected: `tsc --noEmit` and Vite build both pass.

- [ ] **Step 2: Start or reuse the dev server**

Run:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Expected: Vite prints a local URL. If port `5173` is busy, use the next Vite-assigned port.

- [ ] **Step 3: Browser-check responsive pages**

Open these routes in desktop width and mobile width:

```text
/
/history
/assets
/account
/login
```

Expected:

- Top nav is visible and does not overlap page content.
- At widths below 520px, nav labels are hidden and icons remain centered.
- Create page collapses to one column below 860px.
- Buttons and filter labels do not overflow.
- Asset grid uses 1, 2, 3, then 4 columns at the existing breakpoints.
- History card title/date/meta do not overlap.
- Account logout button fits on mobile.

- [ ] **Step 4: Browser-check interactive states**

Manually verify:

```text
Button hover and active states
Keyboard focus-visible on nav, buttons, asset cards, upload zone, mood picker
Disabled submit state during login or create submit
Asset card management menu with Enter/Space when canManage is true
Image uploader drag target and placeholder visuals
```

Expected: visible focus ring, no layout shift, no text overflow, no broken pointer state.

- [ ] **Step 5: Browser-check journal preview behavior**

Open an existing journal detail page if data exists:

```text
/journals/<journalId>
```

Expected:

- `JournalCanvas` still scales inside the preview panel.
- Export button remains clickable when images finish loading.
- Lightbox still opens and closes on image click.
- No horizontal overflow on mobile.

If no local journal exists, record that preview behavior could not be manually checked with data and rely on `npm run build` plus unchanged `JournalDetailPage.tsx`.

- [ ] **Step 6: Fix verification-only issues**

If visual verification finds overflow, make the smallest CSS adjustment. Use these specific fixes when applicable:

```css
.journal-detail-actions > * {
  min-width: 0;
}

.asset-filter-row button,
.history-card-meta span,
.nav-link {
  max-width: 100%;
}

.asset-filter-row > div,
.history-card-meta {
  min-width: 0;
}
```

Run `npm run build` again after any fix.

- [ ] **Step 7: Final status check**

Run:

```bash
git status --short
```

Expected: only intentional frontend files are modified. The pre-existing untracked database backup files may still appear and must not be added.

- [ ] **Step 8: Commit verification fixes if any**

If Step 6 changed files:

```bash
git add frontend/src/styles/globals.css
git commit -m "修复手帐工作室界面响应式细节"
```

If Step 6 made no changes, do not create an empty commit.

## Self-Review

- Spec coverage: global tokens, app shell, create page, history, asset library, preview page, login, interaction states, and responsive requirements all map to Tasks 1-6.
- Non-goals respected: no new UI framework, no new animation library, no icon-library replacement, no backend/API/database changes, no journal canvas layout changes.
- Verification: every task runs `npm run build`; final task includes browser checks for desktop/mobile and interactive states.
- Known pre-existing workspace state: `backend/komorebi.db.before-layout-regenerate-20260531-165314.bak` and `backend/komorebi.db.before-layout-regenerate-22-20260531-172309.bak` are untracked and must remain uncommitted.
