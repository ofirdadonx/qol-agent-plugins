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
- Pairs that carry meaning: `seal-check` verdict · `check-circle` preferred · `warning-circle` less preferred · `warning-octagon` main risk · `hourglass-medium` checkpoint · `coins`/`bank` money · `calendar-dots` timeline · `sliders-horizontal` sandbox · `magnifying-glass-plus` L2 · `arrow-circle-left` L3 · `moon-stars`/`sun` theme · `copy` copy.
- Icons reinforce meaning, never decorate. Icon-only buttons need `aria-label`.
