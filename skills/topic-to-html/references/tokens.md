---
description: "Design tokens: grey-only light theme (no white), dark theme, status colors, spacing, radius, motion, RTL."
---
# Tokens

## Hard rule: no white
No `#fff`, `#ffffff`, `white`, `rgb(255,255,255)` and no hex with every channel ≥ F2, in the light theme, the dark theme, text, highlights or tooltips. Light surfaces are greys; glass edges are grey-white at most (`rgba(244,246,249,.85)`). `scripts/qa_check.py` enforces this.

```css
:root{
  --font:'Assistant','Inter',system-ui,sans-serif;
  --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:20px;--s6:24px;--s8:32px;--s10:40px;--s12:48px;--s16:64px;
  --r-chip:999px;--r-card:20px;--r-panel:28px;
  --spring:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.2,.8,.2,1);--fold-ease:cubic-bezier(.22,1,.36,1);
  --dur-1:160ms;--dur-2:280ms;--dur-3:520ms;--fold-dur:280ms;
}
[data-theme="light"]{
  --bg:#d9dde3;
  --mesh-1:#c6d3e6;--mesh-2:#d8cde2;--mesh-3:#c9e0d8;--mesh-4:#e3d8c8;
  --text:#1b1f26;--text-2:#3a414c;--muted:#525a66;
  --accent:#3b5fc4;--accent-ink:#2a4596;--accent-tint:rgba(59,95,196,.14);
  --pos:#13653d;--neg:#9c2d2d;--warn:#74470a;           /* AA on every glass level */
  --pos-tint:rgba(29,122,76,.13);--neg-tint:rgba(178,58,58,.11);--warn-tint:rgba(143,90,14,.12);
  --g-thin:rgba(232,235,240,.42);--g-reg:rgba(226,230,236,.58);--g-thick:rgba(221,225,232,.84);
  --g-edge:rgba(244,246,249,.85);--g-border:rgba(180,188,200,.45);
  --shadow:0 1px 1px rgba(30,40,60,.04),0 8px 24px rgba(30,40,60,.08),0 24px 48px -16px rgba(30,40,60,.12);
  --grid:rgba(40,50,70,.08);
}
[data-theme="dark"]{
  --bg:#111318;
  --mesh-1:#1d2a4a;--mesh-2:#2e2140;--mesh-3:#15342c;--mesh-4:#3a2a1a;
  --text:#dfe2e7;--text-2:#c3c8d0;--muted:#9aa1ac;
  --accent:#8ea6f0;--accent-ink:#a9bcf5;--accent-tint:rgba(142,166,240,.16);
  --pos:#6cc79a;--neg:#ee8d8d;--warn:#e0b26a;
  --pos-tint:rgba(108,199,154,.14);--neg-tint:rgba(238,141,141,.13);--warn-tint:rgba(224,178,106,.13);
  --g-thin:rgba(48,52,62,.40);--g-reg:rgba(40,44,54,.56);--g-thick:rgba(30,33,41,.86);
  --g-edge:rgba(170,178,192,.28);--g-border:rgba(120,128,142,.28);
  --shadow:0 1px 1px rgba(0,0,0,.2),0 8px 24px rgba(0,0,0,.3),0 24px 48px -16px rgba(0,0,0,.45);
  --grid:rgba(200,210,230,.08);
}
```

## Usage
| Token | Use |
|---|---|
| `--text` | headings, numbers, body |
| `--text-2` | paragraphs, captions |
| `--muted` | labels, meta (still ≥4.5:1) |
| `--accent` / `--accent-ink` | links, active chips, primary series / text on tint |
| `--pos` `--neg` `--warn` + `-tint` | meaning only: gain, loss/caution (less-preferred option = `--neg-tint` + warning icon, not disabled), attention |
One accent color. Status colors never decorate.

## Theme switch
```js
let theme=new URLSearchParams(location.search).get('theme')||localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
function setTheme(t){document.documentElement.dataset.theme=t;localStorage.setItem('theme',t);charts.forEach(c=>{styleChart(c);c.update('none')})}
```
Icon: `ph-moon-stars` in light, `ph-sun` in dark.

## RTL
- `<html lang="he" dir="rtl">`. Only logical properties: `inset-inline-start/end`, `margin-inline-*`, `padding-inline-*`, `border-inline-*`, `text-align:start`.
- Numbers and Latin go in Inter with `font-variant-numeric:tabular-nums`; wrap mixed strings in `<bdi>` if they flip.
- Phones, booking codes, amounts and date ranges: `<span class="ltr tnum">`. `.ltr{direction:ltr;unicode-bidi:isolate;display:inline-block;white-space:nowrap}`.
- Directional icons point to the reading direction (`ph-caret-left` = forward in RTL). Isolate Phosphor duotone icons with `.ph-duotone{direction:ltr;unicode-bidi:isolate}` (see `icons.md`).
- Hide only with the `hidden` attribute. Put `[hidden]{display:none!important}` in the base CSS so it wins over component `display:flex` / `grid` rules. Do not use a global `:empty{display:none}` — it hides icon `<i>` tags and mesh blobs.
