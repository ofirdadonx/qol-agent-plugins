---
description: "Components: KPI bento with copy, options compare, caution state, timeline, tables, segmented control, checklist, sandbox."
---
# Components (all in assets/template.html)

### KPI bento
`.bento` = `2fr 1fr 1fr` (mobile: hero tile full row). Tile = `.kpi.glass.g-reg.press`: icon + label, big `.n.num`, subtext, optional `.meter` (progress toward a goal, `data-w="43%"`). Key numbers get a copy button:
```html
<div class="n num">30,300 ₪ <button class="copy press" data-copy="30300" aria-label="העתקה"><i class="ph-duotone ph-copy"></i></button></div>
```
```js
$$('.copy').forEach(b=>b.onclick=()=>{navigator.clipboard?.writeText(b.dataset.copy);b.innerHTML='<i class="ph-duotone ph-check"></i>';setTimeout(()=>b.innerHTML='<i class="ph-duotone ph-copy"></i>',1200)});
```

### Options compare
`.opts` 2 columns. Preferred = `.opt.best` (pos outline + `ph-star` tag "מומלצת"). Less preferred = `.opt.weak` (`--neg-tint` over glass + `ph-warning-circle` tag "פחות כדאית"). It stays fully readable, never disabled.

### Segmented control (tabs)
```html
<div class="seg glass g-thin" role="group" aria-label="תרחיש"><span class="thumb"></span>
  <button aria-pressed="true" data-s="0">בסיס</button>…</div>
```
```js
function segMove(seg,i){const btns=[...seg.querySelectorAll('button')];btns.forEach((b,j)=>b.setAttribute('aria-pressed',j===i));
  const b=btns[i],th=seg.querySelector('.thumb');th.style.width=b.offsetWidth+'px';th.style.left=b.offsetLeft+'px'}
```
The thumb slides with `--spring`. Use it to switch scenarios and timelines.

### Timeline
Numbered `.step.glass.g-thin` list (`ol.steps`), switchable with a segmented control; caption with the trade-off. Checkpoints = 3 cards (`.tl`) with an hourglass icon, "when" and "condition → action".

### Table
Always `<div class="table-wrap">` (horizontal scroll on mobile). Header row uses `--accent-tint`. Put tables inside L2 expands when they back up a chart.

### Risks
`.risks` grid; the main risk is `.risk.main` (neg tint, `ph-warning-octagon`); others use the warn icon.

### Takeaways
`ol.take` with CSS counters, 2 columns (1 on mobile).

### Sandbox
Sliders (`input[type=range]` with a glass thumb) → `.result` thick cards + `.status` (pos/warn/neg icon and text) + a line chart. Recompute on `input`. Label the model: "המחשה בלבד · …".

### Checklist
`.checklist label.glass.g-thin.press` with `<input type=checkbox>` (`accent-color:var(--accent)`).

## v4 fixes (generic)
- **Lists, not dot-separated lines.** Any "what X brings / includes" card uses `<ul class="bul">` (accent dot, 8px gap). Never join items with ` · `.
- **Hanging number badges.** Counters on cards (`.take li::before`) are `position:absolute; top:-11px; inset-inline-start:-9px`, thick-glass, so they never cover text; give the list `padding-top:10px`.
- **Segmented control.** No JS-measured sliding thumb (it misaligns in RTL / before fonts load). The pressed button itself gets `background:var(--g-thick)` + inset edge; `white-space:nowrap`, `max-width:100%`.
- **Slider rows.** `label` = flex + `gap:12px`; `output` is a pill (`flex:none`, `unicode-bidi:isolate`, no `direction:ltr` — it flips "12 חודשים"). The range input is inset by half the thumb (`width:calc(100% - 26px); margin-inline:13px`) so the thumb never overflows the card.
- **Mixed RTL numbers.** Signed/ranged numbers in calc rows: `.calc b{direction:ltr;unicode-bidi:isolate}`; inside sentences wrap phones, codes, amounts and ranges in `<span class="ltr tnum">`. Target rows: write the claim first ("יעד תרחיש: מחזור 220,000 ₪") and the consequence on its own line, never "A = B".
