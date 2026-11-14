---
name: topic-to-html
description: "Generate premium, interactive, self-contained HTML pages that explain a concept, decision, analysis or hard topic visually: iOS-grade glass over a soft mesh background, grey-only light theme (never white) + dark theme, Phosphor duotone icons, interactive Chart.js visuals, 3-level deep dives and a sandbox. Use for informative pages, explainers, decision docs, reports, dashboards, visual summaries. Hebrew RTL first."
type: workflow
lifecycle: active
---

# Topic to HTML

One self-contained `.html` file that makes a hard topic easy to grasp: visual first, interactive where it builds understanding, readable by everyone.

## Page skeleton (always)
1. **Hero + bottom line** — claim-style H1, lede, and a thick-glass "השורה התחתונה" box with the verdict and 3 bullets.
2. **Sticky top bar** — section chips grouped by opening / middle / end, progress line, theme toggle.
3. **Sections** — opening (state today) → middle (options, mechanics, money, timeline) → end (risks, exit, decision). Each: act label + **claim heading** + ≤2 sentences + **one main interactive visual** + optional deep dive.
4. **Key takeaways** (3–5 numbered) → **sandbox** (sliders that recompute the result) → checklist → footer disclaimer.
5. *Optional* **Playground** — the user's own estimates and what-ifs, clearly separated from source-grounded content (`structure.md`).

Opening / middle / end is internal structure only. Never write "story / סיפור" anywhere in the UI.

## Golden rules
- **No white anywhere.** Light theme uses greys only, and dark-theme text is light grey. `tokens.md`
- **Glass in 3 thicknesses** (thin chips, regular cards, thick nav/bottom-line/panel) over the animated mesh with noise. `glass.md`
- **Fonts:** Assistant (Hebrew) + Inter (Latin and numbers, `tabular-nums`). Do not swap them. `typography.md`
- **Real data only; cite sources subtly** (`.src` chip with document + page). Anything derived or modelled is labelled ("חישוב לפי…", "המחשה בלבד").
- **Contrast is AA** (≥4.5:1 text) on every glass level in both themes. If it fails, make the surface more opaque or darken the token.
- **Motion** is spring-like and subtle; `prefers-reduced-motion` gets a fully static, correct page.
- **RTL:** `dir="rtl" lang="he"`, logical CSS properties only, Chart.js `x.reverse:true`, `rtl:true`. Isolate Phosphor duotone and wrap phones/codes/amounts in `.ltr.tnum` (`icons.md`, `tokens.md`).
- **CDNs pinned:** Chart.js 4.4.1, Phosphor 2.1.1 (CSS).
- **Hide with `[hidden]` only.** A global `:empty{display:none}` hides every icon. `[hidden]{display:none!important}` must win over component `display` rules.

## Workflow
1. Extract the main message, the key numbers and what the reader must decide or understand.
2. Map the content onto the skeleton (`structure.md`) and pick one visual per section (`charts.md`).
3. Choose deep dives for the complex parts (`deep-dive.md`).
4. Build from `assets/template.html`: replace content, keep tokens, CSS and JS helpers.
5. Run QA (`qa.md`): `python3 scripts/qa_check.py page.html`, screenshots, and a visual check. Fix, then deliver.

## References — read when
| File | Read when |
|---|---|
| `references/structure.md` | Always, before writing content |
| `references/tokens.md` | Setting colors, spacing, radius, themes, RTL |
| `references/glass.md` | Any surface, background or overlay |
| `references/typography.md` | Type scale and fonts |
| `references/components.md` | KPI bento, option compare, timeline, tables, tabs/segmented, checklist, caution states |
| `references/charts.md` | Any chart |
| `references/deep-dive.md` | Glossary, inline expand, side panel / bottom sheet |
| `references/interactions.md` | Motion, reveal, hover/press, reduced motion |
| `references/icons.md` | Icons |
| `references/maps.md` | Any Leaflet / tile map |
| `references/qa.md` | Before delivering, every time |
| `assets/template.html` | Starting point (full working example) |
