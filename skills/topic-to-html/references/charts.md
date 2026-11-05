---
description: "Chart.js 4.4.1 setup: token colors, RTL, theme re-style, per-chart animation (bug fix), floating ranges, lazy charts in hidden containers."
---
# Charts

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```
Pick the chart by meaning: bar = compare categories · floating bar `[min,max]` = ranges/scenarios · line = trend over time (loan balance, cumulative cost) · area = accumulation · meter = one metric toward a goal.

## Setup (copy as-is)
```js
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches, qs=new URLSearchParams(location.search);
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
Chart.defaults.font.family="'Assistant','Inter',sans-serif";Chart.defaults.font.size=13;
// ⚠️ NEVER assign Chart.defaults.animation = {...} or = false → "this._fn is not a function" and every chart renders blank.
const ANIM=(reduce||qs.has('static'))?false:{duration:900,easing:'easeOutQuart'};
const charts=[];
const base=(extra={})=>({animation:ANIM,responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
  plugins:{legend:{position:'top',align:'start',rtl:true,labels:{usePointStyle:true,boxWidth:8,padding:16}},
           tooltip:{rtl:true,padding:12,cornerRadius:12,backgroundColor:'rgba(30,34,42,.92)',titleColor:'#cfd3d9',bodyColor:'#c3c8d0'}},
  scales:{x:{reverse:true,ticks:{},grid:{display:false}},y:{position:'right',ticks:{},grid:{}}},...extra});
function styleChart(c){const t=css('--text-2'),g=css('--grid');
  for(const k in c.options.scales){const s=c.options.scales[k];s.ticks.color=t;s.grid.color=g;s.border={display:false}}
  if(c.options.plugins.legend)c.options.plugins.legend.labels.color=t;
  c.data.datasets.forEach(d=>{if(d._c){d.borderColor=css(d._c);d.backgroundColor=d._fill?css(d._c)+'22':(c.config.type==='bar'?css(d._c)+'cc':css(d._c))}})}
function mk(id,cfg){const c=new Chart(document.getElementById(id),cfg);styleChart(c);c.update('none');charts.push(c);return c}
```
Datasets name a token in `_c` (`'--accent'`, `'--pos'`, `'--neg'`) and `_fill:true` for areas. `setTheme()` re-runs `styleChart` on every chart.

## Examples
```js
mk('balanceChart',{type:'line',data:{labels:['Q1','Q2','Q3','Q4','Q5','Q6'],datasets:[
 {label:'יתרה בדוגמה',data:[240,200,155,105,50,0],_c:'--accent',_fill:true,fill:true,borderWidth:3,tension:0,pointRadius:4}]},options:base()});
// ranges: data:[[30,36],[38,46]] + tooltip callback label:c=>c.dataset.label+': '+c.raw[0]+'–'+c.raw[1]+'K'
```

## Rules
- The canvas lives in `.chart{position:relative;height:300px}` (250 on mobile) with an `aria-label` that states the takeaway.
- Charts inside closed `<details>` or the hidden panel are created lazily (on `toggle` or after the panel opens, `setTimeout(…,420)`); otherwise they get size 0.
- Real numbers only; derived series get "(חישוב לפי …)" in the title; midpoints get "(אמצע הטווח)".
- Direct, short labels, the unit in the title ("אלפי ₪"), max 2–3 series.

## Legends (v4) — HTML, not canvas
Chart.js canvas legends in RTL glue the dot to the label and collide with y-tick values. Always set `plugins.legend.display:false` and render an HTML legend `<ul class="lg">` right above `.chart` (see `legend(c)` in the template): `gap:8px` between dot and label, `gap:8px 18px` between items, wraps on mobile, dashed datasets get a dash swatch, colours via `var(--token)` so theme switches need no redraw.
Stacked "where every shekel goes" bars: `stacked:true` on x and y, one dataset per cost line, profit as the last dataset (negative = loss below zero); state in the caption what the bar height is (e.g. turnover incl. VAT).
