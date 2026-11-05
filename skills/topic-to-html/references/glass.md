---
description: "iOS-grade glass: 3 thicknesses, animated mesh background, noise, top-edge highlight, shadows, performance and contrast."
---
# Glass

Glass only works when something rich sits under it, so every page needs the mesh + noise layers.

## Background (once per page, first in body)
```html
<div class="mesh" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
<div class="noise" aria-hidden="true"></div>
```
```css
.mesh{position:fixed;inset:0;z-index:-2;overflow:hidden;background:var(--bg)}
.mesh i{position:absolute;width:60vmax;height:60vmax;border-radius:50%;filter:blur(80px);opacity:.85}
.mesh i:nth-child(1){background:var(--mesh-1);top:-20vmax;inset-inline-start:-10vmax;animation:drift1 26s ease-in-out infinite alternate}
.mesh i:nth-child(2){background:var(--mesh-2);top:10vmax;inset-inline-end:-20vmax;animation:drift2 32s ease-in-out infinite alternate}
.mesh i:nth-child(3){background:var(--mesh-3);bottom:-25vmax;inset-inline-start:10vmax;animation:drift3 29s ease-in-out infinite alternate}
.mesh i:nth-child(4){background:var(--mesh-4);bottom:-10vmax;inset-inline-end:5vmax;width:40vmax;height:40vmax;animation:drift1 35s ease-in-out infinite alternate-reverse}
@keyframes drift1{to{transform:translate(8vmax,6vmax) scale(1.1)}}
@keyframes drift2{to{transform:translate(-10vmax,8vmax) scale(.92)}}
@keyframes drift3{to{transform:translate(6vmax,-8vmax) scale(1.08)}}
.noise{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.06;mix-blend-mode:overlay;
 background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
```
Mesh colors are subtle tints (the `--mesh-*` tokens), never saturated.

## Material
```css
.glass{position:relative;-webkit-backdrop-filter:blur(24px) saturate(180%);backdrop-filter:blur(24px) saturate(180%);
  border:1px solid var(--g-border);box-shadow:var(--shadow),inset 0 1px 0 var(--g-edge)}
.glass::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:linear-gradient(180deg,var(--g-edge) 0,transparent 1.5px),linear-gradient(160deg,rgba(150,160,180,.10),transparent 40%)}
.g-thin{background:var(--g-thin)}   /* chips, segmented, steps, summary rows */
.g-reg{background:var(--g-reg)}     /* cards, charts, KPI tiles */
.g-thick{background:var(--g-thick)} /* top bar, bottom-line box, deep-dive panel, tooltips, result cards */
@media (prefers-reduced-transparency:reduce){.g-thin,.g-reg{background:var(--g-thick)}}
```
Always use `class="glass g-reg"` (material + thickness). A tinted state stacks: `background:linear-gradient(var(--neg-tint),var(--neg-tint)),var(--g-reg)`.

## Contrast
- Body text sits on `g-reg` or `g-thick`. Long text never goes on `g-thin`.
- If a token fails 4.5:1 on any level (checked against bg + every mesh color), darken it (light) or lighten it (dark), or move the text to a thicker level.

## Performance
- ≤ ~40 glass elements visible per screen; don't nest blurred glass inside blurred glass more than 1 level (inner = `g-thin`, fine).
- Animate only `transform`/`opacity`; never animate `backdrop-filter`.
- Mesh animation stops under reduced motion (global rule in `interactions.md`).

## Don't: pointer-following sheen
Do not add a pointer- or scroll-following specular highlight. It washes out (whitens) whatever surface is under the cursor. Keep only the static top-edge highlight on `.glass::before`.
