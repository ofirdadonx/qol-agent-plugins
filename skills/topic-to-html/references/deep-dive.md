---
description: "Deep dive in 3 levels: L1 glossary tooltip, L2 inline expand, L3 side panel (bottom sheet on mobile) with breadcrumbs, #links, Esc and focus return."
---
# Deep dive

The main page must make sense without opening anything. Deep dives add depth for whoever wants it.

| Level | Use for | Element |
|---|---|---|
| L1 glossary | an unfamiliar term (≤25 words) | `button.term` + `.tip.glass.g-thick` |
| L2 inline | a method, assumptions, a supporting table or secondary chart (≤150 words) | `details.more.glass.g-thin` |
| L3 panel | a complex sub-topic with its own steps + visual | `aside.panel.glass.g-thick` (max 3–5 per page) |

## L1
```html
<button class="term">תשלום מותנה<span class="tip glass g-thick" role="tooltip"><b>תשלום מותנה</b>חלק מהמחיר משולם רק אם מתקיים יעד מוסכם בדוגמה.</span></button>
```
It opens on hover and on `:focus-visible` (keyboard/touch); dashed accent underline.

## L2
```html
<details class="more glass g-thin"><summary><i class="ph-duotone ph-magnifying-glass-plus ph"></i> איך חישבנו? <i class="ph-duotone ph-caret-down ph chev"></i></summary>
  <div class="fold"><div class="fold-inner"><div class="body">…</div></div></div></details>
```
The body opens downward in place (`grid-template-rows: 0fr → 1fr`, `--fold-ease` / `--fold-dur` ~280ms). Do not `scrollIntoView` on toggle. The chevron rotates with `--fold-ease`. Printing shows it open. See `interactions.md`.

## L3: panel and bottom sheet
Trigger: `<button class="dd-btn press" data-dd="capacity"><i class="ph-duotone ph-arrow-circle-left ph"></i> צלילה לעומק: … <small>· 2 דק'</small></button>`

Panel content order: close button → breadcrumb (`section icon · section › צלילה לעומק`) → H2 → 1-sentence intro → 3 numbered `.step`s → one visual → optional L2 → **"חזרה למסמך"** button.

```css
.panel{position:fixed;z-index:90;top:12px;bottom:12px;inset-inline-end:12px;width:min(500px,calc(100vw - 24px));border-radius:var(--r-panel);padding:var(--s6);overflow-y:auto;
  transform:translateX(calc(-100% - 24px));transition:transform var(--dur-3) var(--spring);visibility:hidden}  /* RTL: inline-end = left */
.panel.on{transform:none;visibility:visible}
@media (max-width:560px){.panel{top:auto;bottom:0;inset-inline:0;width:100%;max-height:86vh;border-radius:var(--r-panel) var(--r-panel) 0 0;transform:translateY(105%)}
  .panel::after{content:"";position:absolute;top:8px;inset-inline-start:50%;translate:50%;width:40px;height:5px;border-radius:5px;background:var(--muted);opacity:.5}}
.scrim{position:fixed;inset:0;z-index:80;background:rgba(15,20,30,.28);opacity:0;pointer-events:none;transition:opacity var(--dur-2)}.scrim.on{opacity:1;pointer-events:auto}
```
```js
let lastFocus;
function openDD(id){lastFocus=document.activeElement;panel.classList.add('on');scrim.classList.add('on');panel.setAttribute('aria-hidden','false');
  document.body.style.overflow='hidden';history.replaceState(null,'','#dd-'+id);setTimeout(()=>ddClose.focus({preventScroll:true}),50);/* lazy charts here */}
function closeDD(){panel.classList.remove('on');scrim.classList.remove('on');panel.setAttribute('aria-hidden','true');document.body.style.overflow='';
  history.replaceState(null,'',location.pathname+location.search);lastFocus?.focus({preventScroll:true})}
addEventListener('keydown',e=>{if(e.key==='Escape')closeDD()});   // Esc, scrim click and the back button all close it
if(location.hash.startsWith('#dd-'))openDD(location.hash.slice(4)); // shareable link
```
The panel has `role="dialog" aria-modal="true" aria-labelledby`. With several panels, keep one `<aside>` per id or swap content from `<template id="dd-…">`.
