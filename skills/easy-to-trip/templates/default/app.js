/* easy-to-trip default template app. Driven entirely by window.TRIP. No trip-specific data. */
(function(){
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const T=window.TRIP||{};
const UI=T.ui||{};
const root=document.documentElement,qs=new URLSearchParams(location.search);
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const STORE=T.storage_key||'easy-to-trip';
let theme=qs.get('theme')||localStorage.getItem(STORE+'-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
const css=v=>getComputedStyle(root).getPropertyValue(v).trim();
const charts=[];
const locale=T.locale||T.lang||'en';
const rtl=(T.dir||document.documentElement.dir)==='rtl';
function setTheme(t){theme=t;root.dataset.theme=t;try{localStorage.setItem(STORE+'-theme',t)}catch(e){}
  const btn=$('#themeBtn');if(btn)btn.innerHTML=`<i class="ph-duotone ${t==='dark'?'ph-sun':'ph-moon-stars'} ph"></i>`;
  charts.forEach(c=>{styleChart(c);c.update('none')})}
const themeBtn=$('#themeBtn');if(themeBtn)themeBtn.onclick=()=>setTheme(theme==='dark'?'light':'dark');
if(window.Chart){Chart.defaults.font.family="'Assistant','Inter',sans-serif";Chart.defaults.font.size=13;}
const ANIM=(reduce||qs.has('static'))?false:{duration:900,easing:'easeOutQuart'};
function styleChart(c){if(!c||!c.options)return;const t=css('--text-2'),g=css('--grid');
  for(const k in (c.options.scales||{})){const s=c.options.scales[k];if(!s)continue;if(s.ticks)s.ticks.color=t;if(s.grid)s.grid.color=g;s.border={display:false}}
  if(c.options.plugins&&c.options.plugins.legend)c.options.plugins.legend.labels={...(c.options.plugins.legend.labels||{}),color:t};
  (c.data.datasets||[]).forEach(d=>{if(d._c){const col=Array.isArray(d._c)?d._c.map(css):css(d._c);d.borderColor=col;
    d.backgroundColor=d._fill?css(d._c)+'22':(c.config.type==='bar'?(Array.isArray(col)?col.map(x=>x+'cc'):col+'cc'):col)}})}

function isNarrowChart(){return matchMedia('(max-width:700px)').matches}
function wrapTick(label, max){
  const s=String(label??'');
  if(s.length<=max)return s;
  const parts=s.split(/\s+/);
  const lines=[]; let cur='';
  parts.forEach(w=>{
    if(!cur)cur=w;
    else if((cur+' '+w).length<=max)cur+=' '+w;
    else{lines.push(cur);cur=w;}
  });
  if(cur)lines.push(cur);
  return lines.length===1?lines[0]:lines;
}
function applyBarAxis(chart, nCats){
  if(!chart||!chart.options||!chart.canvas)return;
  const narrow=isNarrowChart();
  const opts=chart.options;
  const scales=opts.scales||{};
  const currentVal=(opts.indexAxis==='y')?(scales.x||{}):(scales.y||{});
  const valTicks=currentVal.ticks||{};
  const cat={
    reverse:rtl,
    ticks:{
      maxRotation:0,
      autoSkip:false,
      color:valTicks.color,
      callback:function(v){
        const l=this.getLabelForValue?this.getLabelForValue(v):v;
        return wrapTick(l, narrow?22:16);
      }
    },
    grid:{display:false}
  };
  const val={
    position:rtl?'right':'left',
    beginAtZero:currentVal.beginAtZero!==undefined?currentVal.beginAtZero:true,
    max:currentVal.max,
    ticks:{callback:valTicks.callback,stepSize:valTicks.stepSize,color:valTicks.color},
    grid:currentVal.grid||{}
  };
  opts.indexAxis=narrow?'y':'x';
  opts.scales=narrow?{x:val,y:cat}:{x:cat,y:val};
  const wrap=chart.canvas.parentElement;
  if(wrap){
    if(narrow){
      const h=Math.max(200,(nCats||3)*56+36);
      wrap.style.height=h+'px';
      wrap.style.minHeight=h+'px';
    }else{
      wrap.style.height='';
      wrap.style.minHeight='';
    }
  }
  try{chart.resize()}catch(e){}
  chart.update('none');
}
function watchCharts(){
  const mq=matchMedia('(max-width:700px)');
  const on=()=>charts.forEach(c=>{
    if(c.config&&c.config.type==='bar'){
      const n=(c.data&&c.data.labels&&c.data.labels.length)||3;
      applyBarAxis(c,n);
    }
  });
  if(mq.addEventListener)mq.addEventListener('change',on);
  else if(mq.addListener)mq.addListener(on);
}
function mk(id,cfg){if(!window.Chart)return null;const el=document.getElementById(id);if(!el)return null;const c=new Chart(el,cfg);styleChart(c);if((cfg&&cfg.type)==='bar'||(c.config&&c.config.type==='bar')){const n=(cfg.data&&cfg.data.labels&&cfg.data.labels.length)||3;applyBarAxis(c,n);}c.update('none');charts.push(c);return c}
function fmt(n){return Math.round(n).toLocaleString(locale)}
const tipBase={rtl:rtl,padding:12,cornerRadius:12,backgroundColor:'rgba(30,34,42,.92)',titleColor:'#cfd3d9',bodyColor:'#c3c8d0'};
const base=(extra={})=>({animation:ANIM,responsive:true,maintainAspectRatio:false,layout:{padding:{left:10,right:2}},interaction:{mode:'index',intersect:false},
  plugins:{legend:{display:false,labels:{}},tooltip:tipBase},
  scales:{x:{reverse:rtl,ticks:{maxRotation:0,autoSkipPadding:6},grid:{display:false}},y:{position:rtl?'right':'left',ticks:{},grid:{}}},...extra});
function segMove(seg,i){if(!seg)return;[...seg.querySelectorAll('button')].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
function regionVar(i){return `--region-${(i||0)%6}`}

/* --- Nights chart --- */
(function(){
  const n=T.nights||{}; const groups=n.groups||[];
  if(!groups.length)return;
  const labels=groups.map(g=>g.label);
  const planned=groups.map(g=>g.optional?null:g.nights);
  const optional=groups.map(g=>g.optional?g.nights:null);
  const colors=groups.map(g=>g.undecided?'--warn':(g.color?('--'+g.color.replace(/^--/,'')):regionVar(g.region)));
  mk('nightsChart',{
    type:'bar',
    data:{labels,datasets:[
      {label:UI.nights||'nights',data:planned,_c:colors,borderRadius:8,maxBarThickness:44},
      {label:UI.optional||'optional',data:optional,_c:'--muted',borderRadius:8,maxBarThickness:44,borderWidth:2,borderDash:[5,4]}
    ]},
    options:base({
      plugins:{legend:{display:false,labels:{}},tooltip:{...tipBase,callbacks:{
        label:function(c){
          if(c.raw==null||c.raw==='')return;
          const g=groups[c.dataIndex]||{};
          if(g.tooltip)return g.tooltip;
          if(g.undecided)return (UI.nights_undecided||'{n} nights - not yet decided').replace('{n}',c.raw);
          if(c.datasetIndex===1)return (UI.nights_optional||'{n} optional nights').replace('{n}',c.raw);
          return (UI.nights_n||'{n} nights').replace('{n}',c.raw);
        }
      }}},
      scales:{
        x:{reverse:rtl,ticks:{maxRotation:0,autoSkip:false},grid:{display:false}},
        y:{position:rtl?'right':'left',beginAtZero:true,max:n.y_max||undefined,ticks:{stepSize:2},grid:{}}
      }
    })
  });
})();

/* --- Booked budget --- */
(function(){
  const rows=(T.budget&&T.budget.booked)||[];
  if(!rows.length)return;
  const sym=(T.fx&&T.fx.symbol)||(T.fx&&T.fx.home)||'';
  mk('bookedChart',{
    type:'bar',
    data:{
      labels:rows.map(r=>r.title),
      datasets:[{label:sym,data:rows.map(r=>r.home),_c:rows.map((_,i)=>regionVar(i)),borderRadius:8,maxBarThickness:56}]
    },
    options:base({
      plugins:{legend:{display:false,labels:{}},tooltip:{...tipBase,callbacks:{
        label:function(c){
          const r=rows[c.dataIndex]||{};
          const home=r.home!=null?(sym+fmt(r.home)):'';
          return (r.amount!=null?(r.amount+' '+(r.currency||'')):'')+(home?(' ~ '+home):'');
        }
      }}},
      scales:{
        x:{reverse:rtl,ticks:{maxRotation:0},grid:{display:false}},
        y:{position:rtl?'right':'left',beginAtZero:true,ticks:{callback:function(v){return sym+fmt(v);}},grid:{}}
      }
    })
  });
})();

/* --- Open estimates chart --- */
(function(){
  const series=(T.budget&&T.budget.estimates_chart)||[];
  if(!series.length)return;
  const labels=series.map(s=>s.label);
  const solid=series.map(s=>s.optional?null:(s.amount!=null?s.amount:(s.amount_min!=null?((s.amount_min+(s.amount_max||s.amount_min))/2):null)));
  const opt=series.map(s=>s.optional?(s.amount!=null?s.amount:(s.amount_min||0)):null);
  mk('xferChart',{
    type:'bar',
    data:{labels,datasets:[
      {label:UI.budget_open||'open',data:solid,_c:'--region-1',borderRadius:8,borderSkipped:false,maxBarThickness:48},
      {label:UI.optional||'optional',data:opt,_c:'--muted',borderRadius:8,borderSkipped:false,maxBarThickness:48,borderWidth:2,borderDash:[5,4]}
    ]},
    options:base({
      plugins:{legend:{display:false,labels:{}},tooltip:{...tipBase,callbacks:{
        label:function(c){
          if(c.raw==null)return;
          const s=series[c.dataIndex]||{};
          if(s.amount_min!=null)return s.amount_min+'-'+(s.amount_max||s.amount_min)+' '+(s.currency||'');
          return c.raw+' '+(s.currency||'');
        }
      }}},
      scales:{
        x:{reverse:rtl,ticks:{maxRotation:0,autoSkip:false},grid:{display:false}},
        y:{position:rtl?'right':'left',beginAtZero:true,grid:{}}
      }
    })
  });
})();

/* --- Decision options --- */
const BAR_BG=['var(--accent-tint)','var(--g-thick)','var(--g-reg)','var(--g-thin)'];
function showOpt(id,i){
  const dec=(T.decisions||[]).find(d=>d.id===id);if(!dec)return;
  const d=dec.options[i];if(!d)return;
  const bar=$('#optBar-'+id);
  if(bar)bar.innerHTML=(d.bar||[]).map((b,j)=>`<span class="glass g-thin" style="flex:${b.n};background:${BAR_BG[j%BAR_BG.length]}"><b>${esc(b.l||'')}</b><em>${esc(b.s||'')}</em></span>`).join('');
  const ol=$('#optSteps-'+id);
  if(ol)ol.innerHTML=(d.steps||[]).map((x,n)=>`<li class="step glass g-thin"><i class="n">${n+1}</i><div><b><span class="ltr tnum">${esc(x[0]||'')}</span> · ${esc(x[1]||'')}</b><span>${esc(x[2]||'')}</span></div></li>`).join('');
  const cap=$('#optCap-'+id+' span');if(cap)cap.textContent=d.cap||'';
  segMove($('#optSeg-'+id),i);
  $$('#optCards-'+id+' .opt').forEach((c,j)=>c.classList.toggle('sel',j===i));
  try{localStorage.setItem(STORE+'-opt-'+id,String(i))}catch(e){}
  const flag=$('#choiceFlag-'+id);
  if(flag){flag.hidden=false;flag.textContent=(UI.saved_on_device||'Saved on this device: {name}').replace('{name}',d.name||'');}
  const canvas=$('#optChart-'+id);
  if(canvas&&window.Chart){
    const existing=charts.find(c=>c.canvas===canvas);
    const labels=dec.options.map(o=>o.name);
    const k=dec.options.map(o=>o.k),o=dec.options.map(o=>o.o);
    if(existing){existing.data.labels=labels;existing.data.datasets[0].data=k;if(existing.data.datasets[1])existing.data.datasets[1].data=o;existing.update('none');}
  }
}
(T.decisions||[]).forEach(dec=>{
  const opts=dec.options||[];
  if(!opts.length)return;
  let i=0;try{i=+(localStorage.getItem(STORE+'-opt-'+dec.id)||0)}catch(e){}
  if(!(i>=0&&i<opts.length))i=0;
  $$('#optSeg-'+dec.id+' button').forEach(b=>b.onclick=()=>showOpt(dec.id,+b.dataset.s));
  $$('#optCards-'+dec.id+' .opt').forEach(c=>{const go=()=>showOpt(dec.id,+c.dataset.opt);c.onclick=go;c.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
  if(opts.some(o=>o.k!=null||o.o!=null)){
    mk('optChart-'+dec.id,{type:'bar',data:{
      labels:opts.map(o=>o.name),
      datasets:[
        {label:'A',data:opts.map(o=>o.k),_c:'--region-0',borderRadius:8,maxBarThickness:36},
        {label:'B',data:opts.map(o=>o.o),_c:'--region-1',borderRadius:8,maxBarThickness:36}
      ]},options:base({plugins:{legend:{display:false,labels:{}},tooltip:{...tipBase}},
        scales:{x:{reverse:rtl,ticks:{maxRotation:0,autoSkip:false},grid:{display:false}},
          y:{position:rtl?'right':'left',beginAtZero:true,ticks:{stepSize:1},grid:{}}}})});
  }
  showOpt(dec.id,i);
  const flag=$('#choiceFlag-'+dec.id);
  let saved=null;try{saved=localStorage.getItem(STORE+'-opt-'+dec.id)}catch(e){}
  if(flag&&saved==null)flag.hidden=true;
});

watchCharts();
/* --- FX --- */
function runFx(){
  const amtEl=$('#fxAmt'),fromEl=$('#fxFrom'),out=$('#fxOut');
  if(!amtEl||!fromEl||!out)return;
  const rates=(T.fx&&T.fx.rates)||{};
  const amt=parseFloat(amtEl.value)||0;
  const from=fromEl.value;
  const rate=rates[from];
  if(rate==null){out.textContent='–';return;}
  const home=amt*rate;
  const n=home>=100?home.toLocaleString(locale,{maximumFractionDigits:0}):home.toLocaleString(locale,{maximumFractionDigits:2,minimumFractionDigits:1});
  out.textContent=((T.fx&&T.fx.symbol)||(T.fx&&T.fx.home)||'')+n;
}
['fxAmt','fxFrom'].forEach(id=>{const el=$('#'+id);if(el){el.addEventListener('input',runFx);el.addEventListener('change',runFx)}});
runFx();

function pad(n){return String(n).padStart(2,'0')}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const DEP=T.departure?new Date(T.departure):null;
const LAND=T.return?new Date(T.return):null;
const TODAY=(T.today||[]).map(s=>({...s,from:new Date(s.from),to:new Date(s.to)}));
const CD=T.countdown||{};

function currentSeg(now){return TODAY.find(p=>now>=p.from&&now<p.to)}

function plural(n, forms){
  forms=forms||{};
  n=Math.round(Number(n)||0);
  const tmpl=(n===1&&forms.one)?forms.one:((n===2&&forms.two)?forms.two:(forms.other||'{n}'));
  return String(tmpl).replace(/\{n\}/g, String(n));
}
function tick(){
  const now=new Date();
  const nEl=$('#countN'),lEl=$('#countL'),ban=$('#todayBanner');
  if(DEP&&now<DEP){
    const ms=DEP-now,d=Math.floor(ms/86400000),h=Math.floor(ms%86400000/3600000);
    if(nEl)nEl.textContent=d;
    const hours=plural(h, UI.plural_hour||{one:'1 hour',other:'{n} hours'});
    const days=plural(d, UI.plural_day_word||{one:'day',two:null,other:'days'});
    const one=CD.before_one||UI.before_one||'{days} to departure, and {hours}';
    const soon=CD.before_soon||UI.before_soon||'{days} to departure · {hours} left';
    const many=CD.before||UI.countdown_label||'{days} to departure';
    let caption=d===1?one:((d<14)?soon:many);
    caption=String(caption).replace(/\{hours\}\s*(שעות|hours)/gi,'{hours}').replace(/\{days\}\s*(ימים|days)/gi,'{days}');
    if(lEl)lEl.textContent=caption.replace(/\{hours\}/g,hours).replace(/\{days\}/g,days);
    if(ban){ban.hidden=true;ban.replaceChildren();}
  }else if(DEP&&LAND&&now<=LAND){
    if(nEl)nEl.textContent=CD.during_short||UI.during_short||'On the trip';
    if(lEl)lEl.textContent=CD.during||UI.during_label||'The trip has started.';
    const here=currentSeg(now);
    if(ban){
      ban.hidden=false;
      ban.className='today-banner glass g-thick';
      const msg=(UI.today_banner||'Today: {title}.').replace('{title}',here?here.title:(UI.today_in_trip||''));
      ban.innerHTML=`<i class="ph-duotone ph-map-pin ph" style="font-size:22px;color:var(--accent)"></i><span>${esc(msg)}</span>`;
    }
  }else if(LAND&&now>LAND){
    if(nEl)nEl.textContent='0';
    if(lEl)lEl.textContent=CD.after||UI.after_label||'The trip has ended.';
    if(ban){ban.hidden=true;ban.replaceChildren();}
  }
}

function updateTodayCard(){
  const box=$('#todayCard');
  if(!box)return;
  const now=new Date();
  if(!DEP||!LAND||now<DEP||now>LAND){
    box.hidden=true;box.replaceChildren();
    $$('.stop.is-today,.day.is-today').forEach(el=>el.classList.remove('is-today'));
    return;
  }
  const info=currentSeg(now);
  box.hidden=false;
  box.className='today-card card glass g-thick';
  if(!info){box.innerHTML=`<h3><i class="ph-duotone ph-map-pin ph"></i> ${esc(UI.today_in_trip||'Today, on the trip')}</h3>`;return;}
  const nav=info.nav?`<a class="navbtn" href="${esc(info.nav)}" target="_blank" rel="noopener noreferrer"><i class="ph-duotone ph-navigation-arrow ph"></i> ${esc(UI.navigate_stay||UI.navigate||'Navigate')}</a>`:'';
  const toStop=info.stop?`<button type="button" class="stop-toggle press" data-goto="${esc(info.stop)}"><i class="ph-duotone ph-caret-down ph"></i> ${esc(UI.dest_card||'Destination card')}</button>`:'';
  const toDay=info.day?`<button type="button" class="stop-toggle press" data-dayjump="${esc(info.day)}"><i class="ph-duotone ph-calendar-blank ph"></i> ${esc(UI.journal_today||'Today in the journal')}</button>`:'';
  const show=`<button type="button" class="stop-toggle press" id="showTodayPlan"><i class="ph-duotone ph-path ph"></i> ${esc(UI.show_today||"Show today's plan")}</button>`;
  box.innerHTML=`<h3><i class="ph-duotone ph-map-pin ph"></i> ${esc((UI.today_here||'Today: {title}').replace('{title}',info.title||''))}</h3>
    <p style="margin:0"><strong>${esc(UI.sleep||'Stay')}:</strong> ${esc(info.sleep||'')}</p>
    <p style="margin:0">${esc(info.plan||'')}</p>
    <div class="today-actions">${nav}${toStop}${toDay}${show}</div>`;
  /* Mark today's destination and journal row; do not auto-scroll (the offer sits in the hero). */
  if(info.stop){const el=$(info.stop);if(el)el.classList.add('is-today');}
  if(info.day){$$('.day').forEach(el=>el.classList.toggle('is-today',el.dataset.day===info.day||el.dataset.iso===info.day));}
}

function jumpToDay(dd){
  const day=$$('.day').find(el=>el.dataset.day===dd||el.dataset.iso===dd);
  if(!day)return;
  const det=day.closest('details');
  if(det){det.open=true;det.classList.add('is-open');}
  day.classList.add('on','is-today');
  day.scrollIntoView({behavior:reduce?'auto':'smooth',block:'center'});
}
function jumpToToday(){
  const now=new Date();
  if(DEP&&now<DEP){const el=$('#deadlines')||$('#overview');el&&el.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});return;}
  if(LAND&&now>LAND){($('#overview')||document.body).scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});return;}
  const info=currentSeg(now);
  const card=$('#todayCard');
  if(card&&!card.hidden){card.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});}
  if(info&&info.stop){const el=$(info.stop);if(el){const btn=el.querySelector('.stop-sum .stop-toggle');if(btn&&typeof openStop==='function')openStop(btn);}}
  if(info&&info.day)jumpToDay(info.day);
}
const jt=$('#jumpToday');if(jt)jt.addEventListener('click',jumpToToday);
document.addEventListener('click',e=>{
  if(e.target.closest('#showTodayPlan')){jumpToToday();return;}
  const g=e.target.closest('[data-goto]');
  if(g){const el=$(g.dataset.goto);if(el){const btn=el.querySelector('.stop-toggle');if(btn)openStop(btn);el.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});}}
  const d=e.target.closest('[data-dayjump]');
  if(d)jumpToDay(d.dataset.dayjump);
});

/* Geolocation: only in a secure context (https). Date-based today is the primary method. */
function haversine(a,b){
  const R=6371,toRad=x=>x*Math.PI/180;
  const dLat=toRad(b.lat-a.lat),dLng=toRad(b.lng-a.lng);
  const s=Math.sin(dLat/2)**2+Math.cos(toRad(a.lat))*Math.cos(toRad(b.lat))*Math.sin(dLng/2)**2;
  return 2*R*Math.asin(Math.min(1,Math.sqrt(s)));
}
function initLocate(){
  const btn=$('#locateBtn'),msg=$('#locateMsg');
  const ok=window.isSecureContext&&location.protocol==='https:'&&navigator.geolocation;
  if(btn)btn.hidden=!ok;
  if(!ok||!btn)return;
  btn.addEventListener('click',()=>{
    btn.disabled=true;
    navigator.geolocation.getCurrentPosition(pos=>{
      btn.disabled=false;
      const here={lat:pos.coords.latitude,lng:pos.coords.longitude};
      const pins=(T.places||[]).filter(p=>p.lat!=null);
      if(!pins.length){if(msg){msg.hidden=false;msg.textContent=UI.locate_failed||'';}return;}
      let best=pins[0],bestD=haversine(here,best);
      pins.forEach(p=>{const d=haversine(here,p);if(d<bestD){best=p;bestD=d;}});
      if(msg){msg.hidden=false;msg.textContent=(UI.locate_nearest||'Nearest destination: {name}').replace('{name}',best.name||best.id);}
      const el=$('#stop-'+best.id);if(el){const b=el.querySelector('.stop-sum .stop-toggle');if(b)openStop(b);el.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});}
    },err=>{
      btn.disabled=false;
      if(msg){msg.hidden=false;msg.textContent=err&&err.code===1?(UI.locate_denied||''):(UI.locate_failed||'');}
    },{enableHighAccuracy:false,timeout:8000,maximumAge:60000});
  });
}

function runTicks(){tick();if(typeof updateDeadlines==='function')updateDeadlines();if(typeof updateTodayCard==='function')updateTodayCard();}
runTicks();
setInterval(runTicks,60000);

/* --- TOC panel --- */
function openPanel(){const p=$('#panel'),s=$('#scrim');if(!p)return;p.classList.add('on');if(s){s.classList.add('on');s.hidden=false;}$('#panelBtn')&&$('#panelBtn').setAttribute('aria-expanded','true');document.body.style.overflow='hidden'}
function closePanel(){const p=$('#panel'),s=$('#scrim');if(!p)return;p.classList.remove('on');if(s){s.classList.remove('on');s.hidden=true;}$('#panelBtn')&&$('#panelBtn').setAttribute('aria-expanded','false');document.body.style.overflow=''}
const pb=$('#panelBtn'),pc=$('#panelClose'),sc=$('#scrim');
if(pb)pb.onclick=openPanel;if(pc)pc.onclick=closePanel;if(sc)sc.onclick=closePanel;
$$('#panel a').forEach(a=>a.addEventListener('click',closePanel));
addEventListener('keydown',e=>{if(e.key==='Escape'){closePanel();if(typeof closePocket==='function')closePocket();if(typeof closeAllStops==='function')closeAllStops();}});

const chips=[...$$('.nav-bar a[href^="#"]'),...$$('.chip')];
function syncNav(){
  const h=document.documentElement;
  const pr=$('#prog');
  if(pr)pr.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';
  const mid=Math.min(160, 80+(document.querySelector('header.top')?.offsetHeight||100));
  let current=null;
  for(const c of chips){
    const id=(c.getAttribute('href')||'').slice(1);
    const el=id&&document.getElementById(id);
    if(!el)continue;
    const r=el.getBoundingClientRect();
    if(r.top<=mid && r.bottom>mid){current=id;break;}
  }
  if(!current && window.scrollY<120){
    current=((chips[0]&&chips[0].getAttribute('href'))||'#overview').slice(1);
  }
  if(current){
    chips.forEach(c=>c.classList.toggle('on',c.getAttribute('href')==='#'+current));
    const on=chips.find(c=>c.classList.contains('on') && c.closest('.nav-bar'));
    if(on){
      const bar=on.closest('.nav-bar');
      if(bar){
        const br=bar.getBoundingClientRect();
        const or=on.getBoundingClientRect();
        const pad=24;
        if(or.left<br.left+pad || or.right>br.right-pad){
          // Scroll only the nav strip; scrollIntoView would also jump the page.
          const delta=((or.left+or.right)/2)-((br.left+br.right)/2);
          bar.scrollBy({left:delta,behavior:'instant'});
        }
      }
    }
    $$('.dock a[href^="#"]').forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+current));
  }
}
addEventListener('scroll',syncNav,{passive:true});
if('IntersectionObserver' in window){
  const rio=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');rio.unobserve(e.target)}}),{threshold:.12});
  $$('.rv').forEach((el,i)=>{el.style.transitionDelay=(i%4)*60+'ms';(reduce||qs.has('static'))?el.classList.add('in'):rio.observe(el)});
}
setTheme(theme);
syncNav();

const dockToday=$('#dockToday'),dockPocket=$('#dockPocket');
if(dockToday)dockToday.addEventListener('click',()=>{if(typeof jumpToToday==='function')jumpToToday();});
if(dockPocket)dockPocket.addEventListener('click',()=>{if($('#pocket')?.classList.contains('on')){if(typeof closePocket==='function')closePocket();}else{if(typeof openPocket==='function'){openPocket();if(typeof pocketTab==='function')pocketTab(typeof inferPocketTab==='function'?inferPocketTab():'trip');}}});

/* deadlines */
/* Count calendar days in the deadline's own timezone (from the ISO offset
   on data-end), so "days left" matches the itinerary's local date — not the
   browser's. Evening in UTC+2 is already the next morning in UTC+9. */
function offsetMinutes(iso){
  if(!iso)return -new Date().getTimezoneOffset();
  const s=String(iso);
  if(/Z$/i.test(s))return 0;
  const m=s.match(/([+-])(\d{2}):?(\d{2})$/);
  if(!m)return -new Date().getTimezoneOffset();
  return (m[1]==='-'?-1:1)*(parseInt(m[2],10)*60+parseInt(m[3],10));
}
function ymdAtOffset(date, off){
  const wall=new Date(date.getTime()+off*60000);
  return wall.getUTCFullYear()+'-'+pad(wall.getUTCMonth()+1)+'-'+pad(wall.getUTCDate());
}
function daysUntil(end, now, iso){
  const off=offsetMinutes(iso);
  const a=ymdAtOffset(now, off), b=ymdAtOffset(end, off);
  return Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86400000);
}
function deadlineKind(end, now, iso){
  if(end-now<0)return 'passed';
  const d=daysUntil(end, now, iso);
  if(d<=3)return 'danger';
  if(d<=7)return 'warn';
  return 'upcoming';
}
function deadlineLabel(kind, d){
  if(kind==='passed')return UI.deadline_passed||'Passed';
  if(d===0)return UI.deadline_today||'Today';
  if(d===1)return UI.deadline_one||plural(d, UI.plural_day||{one:'1 day left',other:'{n} days left'});
  if(d===2&&UI.deadline_two)return UI.deadline_two;
  if(UI.plural_deadline)return plural(d, UI.plural_deadline);
  return (UI.deadline_n||'{n} days left').replace('{n}',d);
}
function updateDeadlines(){
  const now=new Date();
  $$('[data-end]').forEach(el=>{
    const iso=el.dataset.end;
    const end=new Date(iso);
    if(isNaN(+end))return;
    const kind=deadlineKind(end, now, iso);
    const d=Math.max(0, daysUntil(end, now, iso));
    el.classList.remove('upcoming','warn','danger','passed');
    el.classList.add(kind);
    const st=el.querySelector('[data-st]');
    if(st)st.textContent=deadlineLabel(kind, d)+(kind==='passed'?' ✓':'');
  });
}

/* v6-style inline fold, no sheet, no scrollIntoView jump */
const FOLD_MS=reduce?1:280;
let lastStopBtn=null;
function foldUnit(el){return el&&(el.closest('.stop, .xfer')||el);}
function isFoldOpen(el){return !!(el&&el.classList.contains('is-open'));}
function setFold(el, open, instant){
  if(!el)return;
  const fold=el.querySelector(':scope > .fold, :scope > .col > .fold');
  const inner=fold&&fold.querySelector(':scope > .fold-inner');
  const btn=el.querySelector('.stop-toggle, .xfer-sum');
  const snap=instant||reduce;
  if(snap&&fold){fold.style.transition='none';}
  if(open){
    if(inner){inner.removeAttribute('inert');inner.removeAttribute('aria-hidden');}
    el.classList.add('is-open');
    if(btn)btn.setAttribute('aria-expanded','true');
  }else{
    el.classList.remove('is-open');
    if(btn)btn.setAttribute('aria-expanded','false');
    if(inner){inner.setAttribute('inert','');inner.setAttribute('aria-hidden','true');}
  }
  if(snap&&fold){void fold.offsetHeight;fold.style.transition='';}
}
function closeAllStops(instant){$$('.stop.is-open, .xfer.is-open').forEach(el=>setFold(el,false,instant));lastStopBtn=null;}
function keepTop(el, y, duration){
  const r=document.documentElement;
  r.classList.add('is-anchoring');
  const t0=performance.now();
  let live=true,raf=0;
  const align=()=>{const d=el.getBoundingClientRect().top-y;if(Math.abs(d)>0.5)scrollBy(0,d);};
  const tickK=()=>{if(!live)return;align();if(performance.now()-t0<duration)raf=requestAnimationFrame(tickK);
    else{align();requestAnimationFrame(()=>{align();r.classList.remove('is-anchoring');});}};
  raf=requestAnimationFrame(tickK);
  return ()=>{live=false;cancelAnimationFrame(raf);align();r.classList.remove('is-anchoring');};
}
function toggleFold(el, btn){
  if(!el)return;
  if(isFoldOpen(el)){setFold(el,false);return;}
  const top0=el.getBoundingClientRect().top;
  $$('.stop.is-open, .xfer.is-open').filter(o=>o!==el).forEach(o=>setFold(o,false,true));
  const pin=()=>{const d=el.getBoundingClientRect().top-top0;if(Math.abs(d)>0.5)scrollTo({top:scrollY+d,left:0,behavior:'instant'});};
  pin();pin();
  const unlock=keepTop(el, top0, FOLD_MS+80);
  setFold(el,true);
  lastStopBtn=btn||null;
  setTimeout(()=>{unlock();pin();},FOLD_MS+100);
}
function openStop(btn){
  if(!btn)return;
  const el=btn.closest('.stop, .xfer');
  if(!el)return;
  if(isFoldOpen(el)){setFold(el,false);return;}
  toggleFold(el, btn);
}
$$('.stop-sum .stop-toggle').forEach(b=>b.addEventListener('click',()=>openStop(b)));
$$('.xfer-sum').forEach(b=>b.addEventListener('click',()=>openStop(b)));
$$('.sheet-close').forEach(b=>b.addEventListener('click',()=>{const el=b.closest('.stop, .xfer');if(el)setFold(el,false);}));
const sheetScrim=$('#sheetScrim');
if(sheetScrim)sheetScrim.addEventListener('click',()=>{closeAllStops();if(typeof closePocket==='function')closePocket();});

function initAnimDetails(){
  $$('details').forEach(d=>{
    if(d.dataset.anim==='1')return;
    const sum=d.querySelector(':scope > summary');
    if(!sum)return;
    d.dataset.anim='1';
    let fold=d.querySelector(':scope > .fold, :scope > .col > .fold');
    if(!fold){
      fold=document.createElement('div');fold.className='fold';
      const inner=document.createElement('div');inner.className='fold-inner';
      [...d.childNodes].forEach(n=>{if(n!==sum)inner.appendChild(n);});
      fold.appendChild(inner);d.appendChild(fold);
    }
    const inner=fold.querySelector('.fold-inner');
    const startOpen=d.hasAttribute('open')||d.open;
    d.open=true;
    d.classList.toggle('is-open', startOpen);
    if(!startOpen&&inner){inner.setAttribute('inert','');inner.setAttribute('aria-hidden','true');}
    sum.addEventListener('click',e=>{
      e.preventDefault();
      const willOpen=!d.classList.contains('is-open');
      const top0=d.getBoundingClientRect().top;
      const unlock=keepTop(d, top0, FOLD_MS+40);
      if(willOpen){if(inner){inner.removeAttribute('inert');inner.removeAttribute('aria-hidden');}void d.offsetHeight;d.classList.add('is-open');}
      else{d.classList.remove('is-open');setTimeout(()=>{if(!d.classList.contains('is-open')&&inner){inner.setAttribute('inert','');inner.setAttribute('aria-hidden','true');}},FOLD_MS+40);}
      setTimeout(unlock,FOLD_MS+100);
    });
  });
}
initAnimDetails();

function copied(el){
  const t=document.createElement('span');t.className='copied';t.textContent=UI.copied||'Copied';
  el.after(t);setTimeout(()=>t.remove(),1800);
}
$$('[data-copy]').forEach(b=>b.addEventListener('click',async()=>{
  const v=b.getAttribute('data-copy');
  try{await navigator.clipboard.writeText(v);copied(b);}
  catch(e){const ta=document.createElement('textarea');ta.value=v;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');copied(b);}catch(err){}ta.remove();}
}));

function openPocket(){
  const p=$('#pocket'),s=$('#sheetScrim')||$('#scrim');
  if(!p)return;
  closePanel();
  p.classList.add('on');
  p.setAttribute('aria-hidden','false');
  p.removeAttribute('inert');
  p.removeAttribute('hidden');
  $('#pocketBtn')&&$('#pocketBtn').setAttribute('aria-expanded','true');
  $('#dockPocket')&&$('#dockPocket').setAttribute('aria-expanded','true');
  if(s){s.hidden=false;s.classList.add('on');}
  document.body.style.overflow='hidden';
  const close=$('#pocketClose');
  if(close){try{close.focus()}catch(e){}}
}
function closePocket(){
  const p=$('#pocket'),s=$('#sheetScrim');
  if(!p)return;
  p.classList.remove('on');
  p.setAttribute('aria-hidden','true');
  p.setAttribute('inert','');
  $('#pocketBtn')&&$('#pocketBtn').setAttribute('aria-expanded','false');
  $('#dockPocket')&&$('#dockPocket').setAttribute('aria-expanded','false');
  if(s&&!$('#panel')?.classList.contains('on')){s.classList.remove('on');s.hidden=true;document.body.style.overflow='';}
}
function pocketTab(t){
  $$('#pocket [data-pane]').forEach(p=>{
    const on=p.dataset.pane===t;
    p.classList.toggle('on',on);
    p.setAttribute('aria-hidden', on?'false':'true');
    if(on)p.removeAttribute('inert');else p.setAttribute('inert','');
  });
  $$('#pocketSeg button').forEach(b=>b.setAttribute('aria-pressed', b.dataset.tab===t?'true':'false'));
}
function inferPocketTab(){
  const vis=id=>{const el=document.getElementById(id);if(!el)return 0;const r=el.getBoundingClientRect();return Math.max(0,Math.min(r.bottom,innerHeight)-Math.max(r.top,0));};
  let best='trip',bestV=0;
  (T.countries||[]).forEach(c=>{const v=vis(c.id);if(v>120&&v>=bestV){best=c.id;bestV=v;}});
  return best;
}
$$('#pocketSeg button').forEach(b=>b.addEventListener('click',()=>pocketTab(b.dataset.tab)));
const pbtn=$('#pocketBtn'),pclose=$('#pocketClose');
if(pbtn)pbtn.onclick=()=>{if($('#pocket')?.classList.contains('on'))closePocket();else{openPocket();pocketTab(inferPocketTab());}};
if(pclose)pclose.onclick=closePocket;

/* Map: OSM.de tiles, SVG fallback. Works on file:// for the fallback; live tiles need a network. */
let tripMap=null;
function showMapFallback(reason){
  const live=$('#mapLive'),fb=$('#mapFallback'),note=$('#mapOfflineNote');
  if(live)live.hidden=true;if(fb)fb.hidden=false;
  $('#btnLiveMap')&&$('#btnLiveMap').setAttribute('aria-pressed','false');
  $('#btnSvgMap')&&$('#btnSvgMap').setAttribute('aria-pressed','true');
  if(note){note.hidden=!reason;note.textContent=reason||UI.map_offline||'';}
}
function showMapLive(){
  const live=$('#mapLive'),fb=$('#mapFallback'),note=$('#mapOfflineNote');
  if(live)live.hidden=false;if(fb)fb.hidden=true;if(note)note.hidden=true;
  $('#btnLiveMap')&&$('#btnLiveMap').setAttribute('aria-pressed','true');
  $('#btnSvgMap')&&$('#btnSvgMap').setAttribute('aria-pressed','false');
  if(tripMap)setTimeout(()=>tripMap.invalidateSize(),80);
}
function initMap(){
  const el=$('#mapLive');
  if(!el||!window.L){showMapFallback(UI.map_offline||'');return;}
  try{
    const tiles=(T.map&&T.map.tile_url)||'https://tile.openstreetmap.de/{z}/{x}/{y}.png';
    const attr=(T.map&&T.map.attribution)||'&copy; OpenStreetMap';
    tripMap=L.map(el,{scrollWheelZoom:false});
    L.tileLayer(tiles,{attribution:attr,maxZoom:18}).addTo(tripMap);
    const pins=T.places||[];
    const byRegion={};
    pins.forEach((p,i)=>{
      const icon=L.divIcon({className:'trip-pin'+(p.optional?' optional':''),html:`<span data-region="${p.region_i||0}"><b>${i+1}</b></span>`,iconSize:[28,28],iconAnchor:[14,28],popupAnchor:[0,-24]});
      const exact=p.exact?(UI.pin_exact||''):(UI.pin_approx||'');
      const opt=p.optional?`<br><strong>${esc(UI.optional||'')}</strong>`:'';
      const popup=`<div dir="${T.dir||'ltr'}" lang="${T.lang||''}"><strong>${esc(p.name)}</strong>${opt}<br><span class="ltr tnum">${esc(p.dates)}</span> · ${esc(p.nights)}<br>${esc(p.note||'')}<br><small>${esc(exact)}</small><br><a href="${esc(p.href)}">${esc(UI.to_dest||'')}</a></div>`;
      L.marker([p.lat,p.lng],{icon,title:p.name,keyboard:false,zIndexOffset:p.optional?800:0}).bindPopup(popup).addTo(tripMap);
      (byRegion[p.region_i||0]||(byRegion[p.region_i||0]=[])).push(p);
    });
    Object.keys(byRegion).forEach(k=>{
      const arr=byRegion[k];
      const solid=arr.filter(p=>!p.optional);
      const col=css(regionVar(+k))||'#555';
      if(solid.length>1)L.polyline(solid.map(p=>[p.lat,p.lng]),{color:col,weight:3,opacity:.85}).addTo(tripMap);
      /* dashed segments through optional stops, in trip order */
      for(let i=0;i<arr.length-1;i++){
        if(arr[i].optional||arr[i+1].optional){
          L.polyline([[arr[i].lat,arr[i].lng],[arr[i+1].lat,arr[i+1].lng]],{color:col,weight:3,opacity:.7,dashArray:'6 8'}).addTo(tripMap);
        }
      }
    });
    /* dashed between last of one region and first of the next */
    const regions=Object.keys(byRegion).sort((a,b)=>+a-+b);
    for(let i=0;i<regions.length-1;i++){
      const a=byRegion[regions[i]].filter(p=>!p.optional).at(-1)||byRegion[regions[i]].at(-1);
      const b=byRegion[regions[i+1]][0];
      if(a&&b)L.polyline([[a.lat,a.lng],[b.lat,b.lng]],{color:'#7a7e8a',weight:2,opacity:.7,dashArray:'6 8'}).addTo(tripMap);
    }
    if(pins.length)tripMap.fitBounds(pins.map(p=>[p.lat,p.lng]),{padding:[32,32],maxZoom:6});
    else tripMap.setView([20,0],2);
    const mc=tripMap.getContainer&&tripMap.getContainer();
    if(mc)mc.querySelectorAll('.leaflet-marker-icon,.leaflet-marker-shadow,.trip-pin').forEach(n=>n.setAttribute('tabindex','-1'));
    showMapLive();
  }catch(e){showMapFallback(UI.map_offline||'');}
}
$('#btnLiveMap')?.addEventListener('click',()=>{if(!tripMap)initMap();else showMapLive();});
$('#btnSvgMap')?.addEventListener('click',()=>showMapFallback());
initMap();
addEventListener('offline',()=>showMapFallback(UI.map_offline||''));

/* Offline place search */
const HE_FINAL={'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ'};
function normQ(s){
  s=String(s||'').normalize('NFD').toLowerCase();
  s=s.replace(/[\u0591-\u05C7\u064B-\u065F]/g,'');
  s=s.replace(/[ךםןףץ]/g,c=>HE_FINAL[c]||c);
  s=s.replace(/[^\p{L}\p{N}]+/gu,' ');
  return s.replace(/\s+/g,' ').trim();
}
function aliasExpand(parts){
  const toks=(parts||[]).filter(Boolean).map(String);
  const out=toks.slice();
  const lower=toks.map(s=>s.toLowerCase());
  (UI.search_aliases||[]).forEach(g=>{
    const gl=(g||[]).map(x=>String(x).toLowerCase());
    if(gl.some(x=>lower.some(t=>t.includes(x)||x.includes(t))))out.push(...g);
  });
  return out;
}
function recHay(it){
  const aliases=[].concat(it.aliases||[]);
  const name=normQ(aliasExpand([it.name, ...aliases]).join(' '));
  const type=normQ([it.type,it.type_label].filter(Boolean).join(' '));
  const dish=normQ([it.dish,it.order,it.city].filter(Boolean).join(' '));
  const body=normQ([it.blurb,it.caution,it.dest,it.price].filter(Boolean).join(' '));
  const all=normQ(aliasExpand([it.name,...aliases,it.type,it.type_label,it.dish,it.order,it.city,it.blurb,it.caution,it.dest,it.price]).join(' '));
  return {name,type,dish,body,all};
}
function recScore(it,q){
  if(!q)return 1;
  const toks=q.split(' ').filter(Boolean);
  const h=it._h||recHay(it);
  let score=0;
  for(const tok of toks){
    const inName=h.name.includes(tok);
    const inType=h.type.includes(tok);
    const inDish=h.dish.includes(tok);
    const inBody=h.body.includes(tok);
    const inAll=h.all.includes(tok);
    if(!(inName||inType||inDish||inBody||inAll))return 0;
    if(inName)score+=8;
    else if(inType)score+=6;
    else if(inDish)score+=4;
    else if(inAll)score+=4;
    else score+=1;
  }
  return score;
}
const REC=(T.recs||[]).map(it=>{const h=recHay(it);return {...it,_h:h,_hay:h.all};});
let rsCountry=(T.countries&&T.countries[0]&&T.countries[0].id)||'',rsTypes=new Set(),rsCity='';
function rsCitiesFor(c){
  const seen=[],set=new Set();
  REC.forEach(it=>{if(it.country!==c)return;if(!set.has(it.city)){set.add(it.city);seen.push(it.city);}});
  return seen;
}
function renderCityChips(){
  const box=$('#rsCities');if(!box)return;
  const cities=rsCitiesFor(rsCountry);
  box.innerHTML=cities.map(c=>`<button type="button" class="press" aria-pressed="${c===rsCity?'true':'false'}" data-city="${esc(c)}">${esc(c)}</button>`).join('');
  box.querySelectorAll('button').forEach(b=>b.onclick=()=>{rsCity=(rsCity===b.dataset.city)?'':b.dataset.city;renderCityChips();runRecSearch();});
}
function recMatch(it,q){
  if(it.country!==rsCountry)return false;
  if(rsTypes.size&&!rsTypes.has(it.type))return false;
  if(rsCity&&it.city!==rsCity)return false;
  if(!q)return true;
  return recScore(it,q)>0;
}
function runRecSearch(){
  const q=normQ(($('#rsq')||{}).value||'');
  let scored=REC.filter(it=>recMatch(it,q)).map(it=>({it,s:q?recScore(it,q):1}));
  const strong=scored.filter(h=>h.s>=4);
  if(q&&strong.length)scored=strong;
  scored.sort((a,b)=>b.s-a.s||String(a.it.name||'').localeCompare(String(b.it.name||''),locale));
  const hits=scored.map(h=>h.it);
  const list=$('#rsList'),empty=$('#rsEmpty'),count=$('#rsCount');
  const cName=((T.countries||[]).find(c=>c.id===rsCountry)||{}).name||rsCountry;
  if(count){
    count.textContent=hits.length===1?(UI.results_one||'1 result in {country}').replace('{country}',cName)
      :hits.length?(UI.results_n||'{n} results in {country}').replace('{n}',hits.length).replace('{country}',cName)
      :(UI.results_none||'No results in {country}').replace('{country}',cName);
  }
  if(!list)return;
  if(!hits.length){list.innerHTML='';if(empty)empty.hidden=false;return;}
  if(empty)empty.hidden=true;
  list.innerHTML=hits.map(it=>{
    const opt=it.optional?` <span class="badge opt">${esc(UI.optional||'')}</span>`:'';
    const caut=it.caution?` <span class="caution"><i class="ph-duotone ph-warning ph"></i> ${esc(it.caution)}</span>`:'';
    const res=it.reservation?` <span class="badge res-${esc(it.reservation)}">${esc(UI['res_'+it.reservation]||it.reservation)}</span>`:'';
    const note=it.blurb||it.order||'';
    const maps=(it.maps||[]).map(p=>{
      const t=p.label||p.t||(Array.isArray(p)?p[0]:''),u=p.href||p.u||(Array.isArray(p)?p[1]:'');
      if(!u)return '';
      return `<a class="maps" href="${esc(u)}" target="_blank" rel="noopener noreferrer"><i class="ph-duotone ph-map-pin ph"></i> ${esc(t||UI.maps||'')}</a>`;
    }).join('');
    return `<li class="rs-hit"><div class="rs-item" tabindex="0" role="link" data-jump="${esc(it.id)}" aria-label="${esc(it.name)}">
      <div class="rs-top"><b>${esc(it.name)}</b>${opt}${caut}${res}</div>
      <div class="rs-meta">${esc(it.city)} · ${esc(it.type_label||it.type||'')}</div>
      ${note?`<p class="rs-note">${esc(note)}</p>`:''}</div><div class="rec-links">${maps}</div></li>`;
  }).join('');
}
function jumpToRec(id){
  const el=document.getElementById(id);if(!el)return;
  if(typeof closePocket==='function')closePocket();
  const stop=el.closest('.stop');
  const btn=stop&&stop.querySelector('.stop-sum .stop-toggle');
  if(btn&&btn.getAttribute('aria-expanded')!=='true')openStop(btn);
  let n=el.parentElement;while(n){if(n.tagName==='DETAILS')n.open=true;n=n.parentElement;}
  const go=()=>{el.classList.add('rec-hl');
    const y=el.getBoundingClientRect().top+window.scrollY-Math.max(90,window.innerHeight*0.2);
    window.scrollTo({top:Math.max(0,y),behavior:reduce?'auto':'smooth'});
    setTimeout(()=>el.classList.remove('rec-hl'),3200);};
  requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(go,FOLD_MS+40)));
}
function initRecSearch(){
  if(!$('#recs-search'))return;
  $$('#rsCountry button').forEach(b=>b.onclick=()=>{rsCountry=b.dataset.c;rsCity='';$$('#rsCountry button').forEach(x=>x.setAttribute('aria-pressed',x===b?'true':'false'));renderCityChips();runRecSearch();});
  $$('#rsTypes button').forEach(b=>b.onclick=()=>{const t=b.dataset.t;if(rsTypes.has(t))rsTypes.delete(t);else rsTypes.add(t);b.setAttribute('aria-pressed',rsTypes.has(t)?'true':'false');runRecSearch();});
  const inp=$('#rsq');let tmr=null;
  if(inp){const fire=()=>{clearTimeout(tmr);tmr=setTimeout(runRecSearch,40);};inp.addEventListener('input',fire);inp.addEventListener('search',fire);}
  document.addEventListener('click',e=>{const j=e.target.closest('[data-jump]');if(j)jumpToRec(j.dataset.jump);});
  document.addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;const j=e.target.closest&&e.target.closest('[data-jump]');if(j&&e.target===j){e.preventDefault();jumpToRec(j.dataset.jump);}});
  const js=$('#jumpSearch');
  if(js)js.addEventListener('click',()=>{const sec=$('#recs-search');sec&&sec.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});setTimeout(()=>{$('#rsq')&&$('#rsq').focus();closePocket();},200);});
  renderCityChips();runRecSearch();
}
initRecSearch();
initLocate();
updateDeadlines();
updateTodayCard();
})();
