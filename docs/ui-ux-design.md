# TrackerCG — UI/UX Design

TrackerCG uses a **dark Slate/Zinc theme** with an amber accent. The visual
language is defined in `static/css/style.css` (design tokens + components) on
top of the Tailwind CDN, with the layout built in `templates/index.html`.

---

## 1. Color palette

| Role | Token | Hex | Tailwind |
|------|-------|-----|----------|
| Main background | `--bg` | `#020617` | `bg-slate-950` |
| Card background | `--card-bg` | `#0f172a` | `bg-slate-900` |
| Hover / surface | `--hover` | `#1e293b` | `bg-slate-800` |
| Borders | `--border` | `#334155` | `border-slate-700` |
| Primary text | `--text` | `#f1f5f9` | `text-slate-100` |
| Muted text | `--muted` | `#94a3b8` | `text-slate-400` |
| Gain / success | `--gain` | `#10b981` | `text-emerald-500` |
| Loss | `--loss` | `#ef4444` | `text-red-500` |
| Accent / CTA | `--accent` | `#f59e0b` | `text-amber-500` |

## 2. Typography

- **Font**: Inter (Google Fonts), fallback to `system-ui`/`sans-serif`.
- **Prices** use `font-variant-numeric: tabular-nums` so digits align.
- Headings are bold white; secondary text is small (`text-sm`) slate-300/400.

## 3. Layout

- Centered container: `max-w-7xl mx-auto`.
- Responsive card grid:

  | Breakpoint | Columns |
  |------------|---------|
  | < 640px | 1 |
  | sm (640px) | 2 |
  | md (768px) | 3 |
  | lg (1024px) | 4 |

- Sticky header with brand, desktop + mobile navigation, language toggle, and
  auth controls.

## 4. Key components

**Portfolio hero** — total portfolio value with total/unique card counters.

**Filter pills** — horizontally scrollable game badges; the active one is
filled amber (`#f59e0b`) with dark text.

**Card component (`.tcg-card`)** — image with a `5:7` aspect ratio (gradient
placeholder when no image), card name, game badge, quantity, condition, and
per-item value. Hover: `scale(1.02)`, shadow, amber border tint. Action
buttons for edit / remove.

**Modals** — used for login, register, logout confirmation, details, edit/add,
and remove. Accessible by design:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at the
  modal title;
- focus moves to the first focusable element on open and is restored on
  close;
- **focus trap** (Tab/Shift+Tab cycle within the dialog);
- background **scroll lock** via the `.modal-open-body` class;
- close with the X button, Cancel, or `Esc`.

**Toasts** — transient notifications (success / error / info) with a slide-in
animation; color-coded borders (emerald / red / amber).

**Skeletons** — shimmer placeholders while collection/search load.

**Pagination** — numbered page buttons with ellipsis for large ranges.

**Price change flash** — a brief green (`flash-up`) or red (`flash-down`)
background pulse when a price updates.

## 5. States

- **Loading**: skeleton cards with a shimmer animation.
- **Empty collection**: centered icon + "No cards yet. Search and add your
  first card!" with a shortcut to Search.
- **No search results**: "No cards found. Try a different search."
- **Errors**: inline messages inside the modal (`showError`), translated and
  readable — never raw error keys.

## 6. Localization

A one-click ES/EN toggle swaps all copy through the `I18N` dictionary without
reloading; modals, toasts, and pills all re-render with the new language.
