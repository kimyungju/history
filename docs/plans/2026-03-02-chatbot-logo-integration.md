# Chatbot Logo Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all placeholder diamond icons with the Merlion logo and add it as the favicon, so the chatbot has a cohesive branded identity.

**Architecture:** The logo PNG already lives at `frontend/public/logo.png`. We replace the unicode diamond `◆` in the header and chat empty state with `<img>` tags, add a small avatar next to bot messages, and set the favicon in `index.html`.

**Tech Stack:** React, Tailwind CSS, HTML

---

### Task 1: Add favicon to index.html

**Files:**
- Modify: `frontend/index.html:4-9`

**Step 1: Add favicon link tag**

In `frontend/index.html`, add a favicon `<link>` inside `<head>` after the charset meta tag:

```html
<link rel="icon" type="image/png" href="/logo.png" />
```

The full `<head>` should become:

```html
<head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/png" href="/logo.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Colonial Archives Graph-RAG</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=IBM+Plex+Mono&display=swap" rel="stylesheet" />
</head>
```

**Step 2: Verify**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests still pass (no functional change).

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add Merlion logo as favicon"
```

---

### Task 2: Replace header diamond with logo image

**Files:**
- Modify: `frontend/src/App.tsx:16-21`

**Step 1: Replace the diamond span with an img tag**

In `AppHeader` (App.tsx), replace lines 17-21:

```tsx
{/* OLD */}
<div className="flex items-center gap-2.5">
    <span className="text-ink-500 text-lg leading-none select-none">&#9670;</span>
    <h1 className="font-display text-[15px] font-semibold text-stone-200 tracking-wide">
      Colonial Archives
    </h1>
</div>
```

With:

```tsx
{/* NEW */}
<div className="flex items-center gap-2.5">
    <img src="/logo.png" alt="Colonial Archives" className="w-7 h-7 rounded-full" />
    <h1 className="font-display text-[15px] font-semibold text-stone-200 tracking-wide">
      Colonial Archives
    </h1>
</div>
```

Key details:
- `w-7 h-7` = 28px, fits the 40px header height nicely
- `rounded-full` clips the circular badge cleanly
- No lazy loading needed — header is always visible

**Step 2: Verify**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass.

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: replace header diamond with Merlion logo"
```

---

### Task 3: Replace chat empty state diamond with logo image

**Files:**
- Modify: `frontend/src/components/ChatPanel.tsx:37-46`

**Step 1: Replace the empty state diamond with the logo**

In `ChatPanel.tsx`, replace the empty state block (lines 37-49):

```tsx
{/* OLD */}
<div className="text-center max-w-xs animate-fade-in">
    <span className="text-ink-500/60 text-3xl select-none">&#9670;</span>
    <h2 className="font-display text-xl font-semibold text-stone-300 mt-3">
      Research Assistant
    </h2>
    <p className="text-stone-500 text-sm mt-2 leading-relaxed">
      Ask questions about colonial-era documents. Every answer traces back to specific archive pages.
    </p>
    <p className="text-stone-600 text-xs mt-4 italic font-display">
      Try: &ldquo;Who was the Resident of Singapore in 1830?&rdquo;
    </p>
</div>
```

With:

```tsx
{/* NEW */}
<div className="text-center max-w-xs animate-fade-in">
    <img src="/logo.png" alt="Research Assistant" className="w-16 h-16 rounded-full mx-auto" />
    <h2 className="font-display text-xl font-semibold text-stone-300 mt-3">
      Research Assistant
    </h2>
    <p className="text-stone-500 text-sm mt-2 leading-relaxed">
      Ask questions about colonial-era documents. Every answer traces back to specific archive pages.
    </p>
    <p className="text-stone-600 text-xs mt-4 italic font-display">
      Try: &ldquo;Who was the Resident of Singapore in 1830?&rdquo;
    </p>
</div>
```

Key details:
- `w-16 h-16` = 64px — large enough to be the visual anchor of the empty state
- `rounded-full` for clean circular crop
- `mx-auto` centers the image

**Step 2: Verify**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass.

**Step 3: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx
git commit -m "feat: replace chat empty state icon with Merlion logo"
```

---

### Task 4: Add small logo avatar next to bot messages

**Files:**
- Modify: `frontend/src/components/ChatMessage.tsx:106-108`

**Step 1: Add avatar to bot message bubble**

In `ChatMessage.tsx`, wrap the bot message in a flex row with a small avatar. Replace lines 106-108:

```tsx
{/* OLD */}
<div className="flex justify-start mb-3 animate-fade-in">
    <div className="bg-stone-800/80 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
```

With:

```tsx
{/* NEW */}
<div className="flex justify-start mb-3 animate-fade-in gap-2 items-start">
    <img src="/logo.png" alt="" className="w-6 h-6 rounded-full mt-1 shrink-0" />
    <div className="bg-stone-800/80 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
```

Key details:
- `w-6 h-6` = 24px — small avatar beside the bubble
- `mt-1` aligns it with the first line of text
- `shrink-0` prevents it from collapsing on narrow screens
- `gap-2` spacing between avatar and bubble
- `items-start` top-aligns avatar with bubble
- Empty `alt=""` since avatar is decorative (the role "assistant" is implied by left alignment)

**Step 2: Also add avatar to the typing indicator**

In `ChatPanel.tsx`, replace the typing indicator (lines 55-63):

```tsx
{/* OLD */}
{isQuerying && (
    <div className="flex justify-start mb-3 animate-fade-in">
      <div className="bg-stone-800/80 rounded-2xl px-4 py-3">
```

With:

```tsx
{/* NEW */}
{isQuerying && (
    <div className="flex justify-start mb-3 animate-fade-in gap-2 items-start">
      <img src="/logo.png" alt="" className="w-6 h-6 rounded-full mt-1 shrink-0" />
      <div className="bg-stone-800/80 rounded-2xl px-4 py-3">
```

This keeps the typing indicator visually consistent with bot messages.

**Step 3: Verify**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass.

**Step 4: Commit**

```bash
git add frontend/src/components/ChatMessage.tsx frontend/src/components/ChatPanel.tsx
git commit -m "feat: add Merlion avatar to bot messages and typing indicator"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `frontend/index.html` | Add favicon `<link>` |
| `frontend/src/App.tsx` | Header: diamond → `<img>` logo (28px) |
| `frontend/src/components/ChatPanel.tsx` | Empty state: diamond → logo (64px); typing indicator: add avatar (24px) |
| `frontend/src/components/ChatMessage.tsx` | Bot messages: add 24px avatar |

All changes are purely visual — no logic, no new dependencies, no backend changes.
