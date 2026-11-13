---
description: "Phosphor duotone icons via pinned CSS."
---
# Icons
```html
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/duotone/style.css">
<i class="ph-duotone ph-chart-line-up ph"></i>
```
- Load the CSS file. The `index.js` from that path renders nothing in a plain `<script>` tag.
- `.ph{font-size:1.25em;vertical-align:-.2em}`. Color via `color:` (accent for neutral, pos/neg/warn for status). The duotone second layer is automatic at ~20% opacity.
- **RTL duotone fix (required).** Official 2.1.1 CSS positions the second layer with `margin-left: -1em`, which does not become `margin-inline-start` in RTL, so the layers sit side by side and the icon looks broken. After the Phosphor stylesheet, add:
```css
.ph-duotone{direction:ltr;unicode-bidi:isolate}
.ph-duotone[class*="ph-"]:after{margin-left:0;margin-inline-start:-1em}
```
  The attribute selector matches the specificity of `.ph-duotone.ph-*:after` and must come *after* the Phosphor CSS. If you inline the stylesheet, also replace `margin-left: -1em` there with `margin-inline-start: -1em`.
- **Use only names that exist in 2.1.1.** `scripts/qa_check.py` checks every `ph-*` class against `assets/phosphor-2.1.1-names.txt`. Common wrong names render as an empty square: `ph-palm-tree` → `ph-tree-palm`; `ph-passport` → `ph-identification-card`; `ph-skyscraper` → `ph-city`; `ph-hot-springs` is not in 2.1.1 (a common stand-in is `ph-bathtub`).
- **Never** write a global `:empty{display:none}`. Icon tags are empty; the glyph comes from `::before` / `::after`. Hide things only with `[hidden]`, and set `[hidden]{display:none!important}` so it wins over component `display` rules.
- Pairs that carry meaning: `seal-check` verdict · `check-circle` preferred · `warning-circle` less preferred · `warning-octagon` main risk · `hourglass-medium` checkpoint · `coins`/`bank` money · `calendar-dots` timeline · `sliders-horizontal` sandbox · `magnifying-glass-plus` L2 · `arrow-circle-left` L3 · `moon-stars`/`sun` theme · `copy` copy.
- Icons reinforce meaning, never decorate. Icon-only buttons need `aria-label`.
