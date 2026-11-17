/* easy-to-trip default template app. Driven entirely by window.TRIP. No trip-specific data. */
(function(){
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const T=window.TRIP||{};
const UI=T.ui||{};
const TYPE_ICON=Object.assign({restaurants:'fork-knife',food:'fork-knife',cafes:'coffee',attractions:'camera',sights:'camera',shopping:'shopping-bag',daytrip:'mountains',daytrips:'mountains'},UI.type_icons||{});
function typeIcon(t){
  return `<svg class="ic" aria-hidden="true" focusable="false"><use href="#i-${esc(TYPE_ICON[t]||'map-pin')}"></use></svg>`;
}
function fmtUI(key,fallback,vars){let s=UI[key]||fallback||'';for(const k in (vars||{}))s=s.split('{'+k+'}').join(vars[k]);return s;}
const root=document.documentElement,qs=new URLSearchParams(location.search);
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
if(qs.has('static')){root.setAttribute('data-static','');}
const STORE=T.storage_key||'easy-to-trip';
let theme=qs.get('theme')||localStorage.getItem(STORE+'-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
const css=v=>getComputedStyle(root).getPropertyValue(v).trim();
const locale=T.locale||T.lang||'en';
const rtl=(T.dir||document.documentElement.dir)==='rtl';
function setTheme(t){theme=t;root.dataset.theme=t;try{localStorage.setItem(STORE+'-theme',t)}catch(e){}
  const btn=$('#themeBtn');if(btn)btn.innerHTML=`<i class="ph-duotone ${t==='dark'?'ph-sun':'ph-moon-stars'} ph"></i>`;}
const themeBtn=$('#themeBtn');if(themeBtn)themeBtn.onclick=()=>setTheme(theme==='dark'?'light':'dark');
function segMove(seg,i){if(!seg)return;[...seg.querySelectorAll('button')].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
function regionVar(i){return `--region-${(i||0)%6}`}

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
}
(T.decisions||[]).forEach(dec=>{
  const opts=dec.options||[];
  if(!opts.length)return;
  let i=0;try{i=+(localStorage.getItem(STORE+'-opt-'+dec.id)||0)}catch(e){}
  if(!(i>=0&&i<opts.length))i=0;
  $$('#optSeg-'+dec.id+' button').forEach(b=>b.onclick=()=>showOpt(dec.id,+b.dataset.s));
  $$('#optCards-'+dec.id+' .opt').forEach(c=>{const go=()=>showOpt(dec.id,+c.dataset.opt);c.onclick=go;c.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
  showOpt(dec.id,i);
  const flag=$('#choiceFlag-'+dec.id);
  let saved=null;try{saved=localStorage.getItem(STORE+'-opt-'+dec.id)}catch(e){}
  if(flag&&saved==null)flag.hidden=true;
});

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
function jumpToToday(trigger){if(window.__v13Today)return window.__v13Today(trigger);}
const jt=$('#jumpToday');if(jt)jt.addEventListener('click',()=>jumpToToday(jt));
document.addEventListener('click',e=>{
  if(e.target.closest('#showTodayPlan')){jumpToToday(e.target.closest('#showTodayPlan'));return;}
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
addEventListener('keydown',e=>{if(e.key==='Escape'){if(window.__v13EscHandled){window.__v13EscHandled=false;return;}closePanel();if(typeof closeAllStops==='function')closeAllStops();}});

/* The nav is generated from the real section order ([data-nav] in DOM order), so the
   chip order and the scrollspy always match the page. The static markup is the same list. */
(function buildNav(){
  const secs=$$('[data-nav]');
  const html=secs.map(s=>`<a href="#${s.id}">${esc(s.dataset.nav)}</a>`).join('');
  const bar=$('.nav-bar');if(bar){bar.innerHTML=html;const f=bar.querySelector('a');if(f)f.classList.add('on');}
  const pnl=$('#panel');if(pnl){pnl.querySelectorAll('a').forEach(a=>a.remove());const c=$('#panelClose');c?c.insertAdjacentHTML('beforebegin',html):pnl.insertAdjacentHTML('beforeend',html);}
})();
const chips=[...$$('.nav-bar a[href^="#"]')];
let navLock=null;
$$('.nav-bar a[href^="#"], #panel a[href^="#"], .dock a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{navLock=a.getAttribute('href').slice(1);requestAnimationFrame(()=>syncNav());setTimeout(syncNav,60);}));
['wheel','touchstart','keydown'].forEach(ev=>addEventListener(ev,e=>{if(ev==='keydown'&&!/^(Arrow|Page|Home|End| )/.test(e.key))return;navLock=null;},{passive:true}));

function syncNav(){
  const h=document.documentElement;
  const pr=$('#prog');
  if(pr)pr.style.width=(h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight)*100)+'%';
  const raw=parseFloat(getComputedStyle(h).getPropertyValue('--header-h'));
  const header=document.querySelector('header.top');
  const headerH=header?header.getBoundingClientRect().height:100;
  const threshold=(Number.isFinite(raw)&&raw>0?raw:headerH)+2;
  /* DOM order == nav order, so the current section is the LAST target whose top has
     reached the threshold (nested country blocks inside #itinerary win naturally). */
  let current=null;
  for(const c of chips){
    const el=document.getElementById((c.getAttribute('href')||'').slice(1));
    if(!el)continue;
    if(el.getBoundingClientRect().top<=threshold)current=el.id;
  }
  if(!current&&chips[0])current=chips[0].getAttribute('href').slice(1);
  /* A nav click that lands at the page end (short last sections) keeps the clicked chip. */
  if(navLock){
    const t=document.getElementById(navLock);
    if(t){
      const tr=t.getBoundingClientRect();
      const atEnd=window.scrollY+innerHeight>=h.scrollHeight-2;
      if(Math.abs(tr.top-(threshold-2))<6||(atEnd&&tr.top<innerHeight))current=navLock;
    }
  }
  chips.forEach(c=>c.classList.toggle('on',c.getAttribute('href')==='#'+current));
  if(window.__v13cSyncAria)window.__v13cSyncAria();
  const on=chips.find(c=>c.classList.contains('on'));
  if(on){
    const bar=on.closest('.nav-bar');
    if(bar){
      const br=bar.getBoundingClientRect(),or=on.getBoundingClientRect(),pad=24;
      if(or.left<br.left+pad||or.right>br.right-pad){bar.scrollBy({left:((or.left+or.right)/2)-((br.left+br.right)/2),behavior:'instant'});}
    }
  }
  const dockMap={map:'map',itinerary:'itinerary'};(T.countries||[]).forEach(c=>{dockMap[c.id]='itinerary';});
  $$('.dock a[href^="#"]').forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+(dockMap[current]||'')));
}
addEventListener('scroll',syncNav,{passive:true});
if('IntersectionObserver' in window){
  const rio=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');rio.unobserve(e.target)}}),{threshold:.12});
  $$('.rv').forEach((el,i)=>{el.style.transitionDelay=(i%4)*60+'ms';(reduce||qs.has('static'))?el.classList.add('in'):rio.observe(el)});
}
setTheme(theme);
syncNav();

const dockToday=$('#dockToday');
if(dockToday)dockToday.addEventListener('click',()=>jumpToToday(dockToday));

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
if(sheetScrim)sheetScrim.addEventListener('click',()=>{closeAllStops();});

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
    const tl=L.tileLayer(tiles,{attribution:attr,maxZoom:18}).addTo(tripMap);window.__tripTiles=tl;
    const pins=T.places||[];
    const byRegion={};
    pins.forEach((p,i)=>{
      const icon=L.divIcon({className:'trip-pin'+(p.optional?' optional':''),html:`<span data-region="${p.region_i||0}"><b>${i+1}</b></span>`,iconSize:[28,28],iconAnchor:[14,28],popupAnchor:[0,-24]});
      const exact=p.exact?(UI.pin_exact||''):(UI.pin_approx||'');
      const opt=p.optional?`<br><strong>${esc(UI.optional||'')}</strong>`:'';
      const popup=`<div dir="${T.dir||'ltr'}" lang="${T.lang||''}"><strong>${esc(p.name)}</strong>${opt}<br><span class="ltr tnum">${esc(p.dates)}</span> · ${esc(p.nights)}<br>${esc(p.note||'')}<br><small>${esc(exact)}</small><br><a href="${esc(p.href)}">${esc(UI.to_dest||'')}</a></div>`;
      (window.__tripMarkers=window.__tripMarkers||[]).push(L.marker([p.lat,p.lng],{icon,title:p.name,keyboard:false,zIndexOffset:p.optional?800:0}).bindPopup(popup).addTo(tripMap));
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
    /* Pins closer than a pin's width fan out around their group centre, with a leader to the real spot */
    const fanPins=()=>{
      const ms=window.__tripMarkers||[];if(!ms.length)return;
      const P=ms.map(m=>tripMap.latLngToLayerPoint(m.getLatLng()));
      const n=ms.length,par=[...Array(n).keys()],f=i=>par[i]===i?i:(par[i]=f(par[i]));
      const MIN=34;
      for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)if(P[i].distanceTo(P[j])<MIN)par[f(i)]=f(j);
      let pos=P.map(p=>({x:p.x,y:p.y}));
      for(let pass=0;pass<6;pass++){
        const G={};for(let i=0;i<n;i++)(G[f(i)]=G[f(i)]||[]).push(i);
        pos=P.map(p=>({x:p.x,y:p.y}));
        Object.values(G).forEach(g=>{
          if(g.length<2)return;
          g.sort((a,b)=>a-b);
          const k=g.length,cx=g.reduce((s,i)=>s+P[i].x,0)/k,cy=g.reduce((s,i)=>s+P[i].y,0)/k;
          const r=Math.max(MIN/2+2,(MIN/2+2)/Math.sin(Math.PI/k));
          const a0=k===2?Math.PI:-Math.PI/2-Math.PI/k*(k-1);
          g.forEach((i,t)=>{const a=k===2?a0+Math.PI*t:-Math.PI/2+2*Math.PI*t/k+(k%2?0:Math.PI/k);pos[i]={x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)};});
        });
        let merged=false;
        for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
          if(f(i)===f(j))continue;
          if(Math.hypot(pos[i].x-pos[j].x,pos[i].y-pos[j].y)<MIN){par[f(i)]=f(j);merged=true;}
        }
        if(!merged)break;
      }
      ms.forEach((m,i)=>{
        const el=m.getElement&&m.getElement();if(!el)return;
        const sp=el.querySelector(':scope > span');if(!sp)return;
        const dx=pos[i].x-P[i].x,dy=pos[i].y-P[i].y,len=Math.hypot(dx,dy);
        sp.style.translate=len>0.5?`${dx.toFixed(1)}px ${dy.toFixed(1)}px`:'';
        el.classList.toggle('is-fanned',len>0.5);
        let ld=el.querySelector('.pin-lead'),dt=el.querySelector('.pin-dot');
        if(len>0.5){
          if(!ld){ld=document.createElement('i');ld.className='pin-lead';ld.setAttribute('aria-hidden','true');el.prepend(ld);}
          if(!dt){dt=document.createElement('i');dt.className='pin-dot';dt.setAttribute('aria-hidden','true');el.prepend(dt);}
          ld.style.width=Math.max(0,len-4).toFixed(1)+'px';ld.style.transform=`rotate(${Math.atan2(dy,dx)}rad)`;
        }else{ld&&ld.remove();dt&&dt.remove();}
      });
    };
    window.__fanPins=fanPins;
    tripMap.on('zoomend viewreset',fanPins);
    fanPins();

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
    return `<li class="rs-hit t-${esc(it.type)}"><div class="rs-item" tabindex="0" role="button" aria-haspopup="dialog" aria-controls="rsDialog" data-rec="${esc(it.id)}" aria-label="${esc(it.name)}">
      <div class="rs-top"><span class="rs-ic">${typeIcon(it.type)}</span><b><bdi dir="auto">${esc(it.name)}</bdi></b>${opt}${caut}${res}</div>
      <div class="rs-meta">${esc(it.city)} · ${esc(it.type_label||it.type||'')}</div>
      ${note?`<p class="rs-note">${esc(note)}</p>`:''}</div><div class="rec-links">${maps}</div></li>`;
  }).join('');
}
function jumpToRec(id){
  /* Open the search dialog on this place. In-card rec lists are gone. */
  const it=REC.find(r=>r.id===id);
  if(!it)return;
  let dirty=false;
  if(it.country&&it.country!==rsCountry){
    rsCountry=it.country;rsCity='';dirty=true;
    $$('#rsCountry button').forEach(x=>x.setAttribute('aria-pressed',x.dataset.c===rsCountry?'true':'false'));
  }
  if(rsCity&&it.city!==rsCity){rsCity='';dirty=true;}
  if(rsTypes.size&&!rsTypes.has(it.type)){
    rsTypes=new Set();
    $$('#rsTypes button').forEach(x=>x.setAttribute('aria-pressed','false'));
    dirty=true;
  }
  if(dirty)renderCityChips();
  const inp=$('#rsq');
  if(inp&&inp.value)inp.value='';
  runRecSearch();
  if(typeof window.__v13openRec==='function')window.__v13openRec(id);
  else{
    const el=document.querySelector('#rsList .rs-item[data-rec="'+id+'"]');
    if(el)el.click();
  }
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
  if(js)js.addEventListener('click',()=>{const sec=$('#recs-search');sec&&sec.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});setTimeout(()=>{$('#rsq')&&$('#rsq').focus({preventScroll:true});},200);});
  renderCityChips();runRecSearch();
}
function syncHeaderH(){
  const h=document.querySelector('header.top');
  if(!h)return;
  const real=Math.ceil(h.getBoundingClientRect().height);
  const floor=matchMedia('(min-width:900px)').matches?104:128;
  const next=Math.max(real+4,floor);
  root.style.setProperty('--header-h',next+'px');
}
syncHeaderH();
addEventListener('resize',syncHeaderH);
addEventListener('orientationchange',syncHeaderH);
if(window.visualViewport)visualViewport.addEventListener('resize',syncHeaderH);
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(syncHeaderH).catch(()=>{});

initRecSearch();
initLocate();
updateDeadlines();
updateTodayCard();
/* ===================== v13: clocks, glance, budget hook, today pop-up, search dialog ===================== */
(function v13(){
  /* --header-h follows the real sticky header (jump target + scrollspy threshold) */
  const hdr=document.querySelector('header.top');
  function setHH(){if(!hdr)return;const h=Math.round(hdr.getBoundingClientRect().height);if(h>0)document.documentElement.style.setProperty('--header-h',h+'px');}
  setHH();if(hdr&&window.ResizeObserver)new ResizeObserver(setHH).observe(hdr);addEventListener('resize',setHH,{passive:true});
  /* --dock-h: the fixed bottom bar's real footprint, so nothing scrolls under it */
  const dock=document.querySelector('.dock');
  function setDH(){if(!dock)return;const cs=getComputedStyle(dock);const on=cs.display!=='none'&&cs.position==='fixed';
    const r=dock.getBoundingClientRect();const h=on?Math.max(0,Math.round(innerHeight-r.top)):0;
    document.documentElement.style.setProperty('--dock-h',h+'px');}
  setDH();if(dock&&window.ResizeObserver)new ResizeObserver(setDH).observe(dock);addEventListener('resize',setDH,{passive:true});
  const HOME=T.home_tz||'UTC';
  /* every country's zone comes from its data file; "home" is the traveller's own zone */
  const ZONE={home:HOME};(T.countries||[]).forEach(c=>{if(c.tz)ZONE[c.id]=c.tz;});
  /* ---- time helpers (Intl only, DST-safe) ---- */
  function parts(tz,d){
    const o={};new Intl.DateTimeFormat('en-GB',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'})
      .formatToParts(d).forEach(p=>{if(p.type!=='literal')o[p.type]=+p.value;});return o;
  }
  function tzOffsetMin(tz,d){const p=parts(tz,d);return Math.round((Date.UTC(p.year,p.month-1,p.day,p.hour,p.minute,p.second)-Math.floor(d.getTime()/1000)*1000)/60000);}
  function ymdIn(tz,d){const p=parts(tz,d);return `${p.year}-${String(p.month).padStart(2,'0')}-${String(p.day).padStart(2,'0')}`;}
  function offsetText(min){
    if(min===0)return UI.offset_same||'same time';
    const sign=min>0?'+':'−',a=Math.abs(min),h=Math.floor(a/60),m=a%60;
    if(m)return fmtUI('offset_hm','{sign}{h}:{m} hours',{sign,h,m:String(m).padStart(2,'0')});
    return h===1?fmtUI('offset_one','{sign}1 hour',{sign}):fmtUI('offset_n','{sign}{n} hours',{sign,n:h});
  }
  window.__v13heOffset=offsetText;
  /* ---- where are we (from page data) ---- */
  const placeRegion={};(T.places||[]).forEach(p=>{placeRegion['#stop-'+p.id]=p.region;if(p.href)placeRegion[p.href]=p.region;});
  const firstRegion=((T.places||[])[0]||{}).region||'home';
  function whereNow(now){
    if(!DEP||!LAND||now<DEP||now>LAND)return 'home';
    const seg=TODAY.find(p=>now>=p.from&&now<p.to);
    if(seg&&seg.stop&&placeRegion[seg.stop])return placeRegion[seg.stop];
    if(seg&&TODAY.indexOf(seg)===0)return firstRegion;
    if(!seg){/* between segments: last started one */
      const past=TODAY.filter(p=>p.from<=now);const last=past[past.length-1];
      if(last&&last.stop&&placeRegion[last.stop])return placeRegion[last.stop];
    }
    return 'home';
  }
  window.__v13where=whereNow;
  /* ---- clocks ---- */
  const dateFmt={};
  function renderClocks(){
    const now=new Date(),here=whereNow(now),homeOff=tzOffsetMin(HOME,now);
    $$('.clk').forEach(c=>{
      const tz=c.dataset.tz,p=parts(tz,now);
      c.querySelector('.clk-time .tnum').textContent=`${String(p.hour).padStart(2,'0')}:${String(p.minute).padStart(2,'0')}`;
      dateFmt[tz]=dateFmt[tz]||new Intl.DateTimeFormat(locale,{timeZone:tz,weekday:'short',day:'numeric',month:'numeric'});
      c.querySelector('.clk-date').textContent=dateFmt[tz].format(now);
      const off=tzOffsetMin(tz,now)-homeOff;
      c.querySelector('.clk-off').textContent=tz===HOME?(UI.home_time||'home time'):offsetText(off);
      c.dataset.off=String(off);
      const on=c.dataset.where===here;
      c.classList.toggle('is-here',on);
      if(on)c.setAttribute('aria-current','true');else c.removeAttribute('aria-current');
    });
    $$('[data-offset-tz]').forEach(e=>{e.textContent=offsetText(tzOffsetMin(e.dataset.offsetTz,now)-homeOff);});
  }
  renderClocks();
  (function schedule(){
    /* every 30s, aligned to the minute boundary (:00 and :30) */
    const ms=30000-(Date.now()%30000);
    setTimeout(()=>{renderClocks();schedule();},ms+30);
  })();
  /* ---- budget data + recalc (hook for a future "add expense"; no UI yet) ---- */
  const BUDGET={
    rate:(T.fx&&T.fx.rates)||{},
    booked:((T.budget&&T.budget.booked)||[]).map(b=>({...b})),
    extra:[],                       /* future 'add expense' entries: {title, amount, currency, home} */
    total(){return [...this.booked,...this.extra].reduce((s,b)=>s+(b.home!=null?b.home:(b.amount||0)*(this.rate[b.currency]||0)),0);}
  };
  const SYM=(T.fx&&T.fx.symbol)||(T.fx&&T.fx.home)||'';
  function fmtHome(n){return '≈ '+SYM+Math.round(n).toLocaleString('en-US');}
  function recalcBudget(){
    const txt=fmtHome(BUDGET.total());
    $$('[data-budget-total],[data-gl="budget"]').forEach(e=>e.textContent=txt);
    const gb=$('.gl-budget');if(gb)gb.setAttribute('aria-label',fmtUI('glance_budget_aria','Booked so far {amount}, to the budget',{amount:txt}));
    return txt;
  }
  window.TRIP_BUDGET=BUDGET;window.recalcBudget=recalcBudget;
  recalcBudget();
  /* ---- at a glance: computed from page data ---- */
  (function glance(){
    const groups=(T.nights&&T.nights.groups)||[];
    const set=(k,v)=>{const e=$(`[data-gl="${k}"]`);if(e)e.textContent=v;};
    set('nights',groups.filter(g=>!g.optional).reduce((s,g)=>s+(+g.nights||0),0));
    set('dests',(T.places||[]).filter(p=>!p.optional).length);
    const items=$$('.tline > article.item').filter(a=>!a.classList.contains('is-optional'));
    set('xfers',items.filter(a=>a.classList.contains('xfer')).length);
    const units=new Map();
    items.forEach(a=>{
      const code=a.classList.contains('xfer')?(a.querySelector('[data-copy]')||{}).dataset?.copy:null;
      const key=code||a.id;
      const closed=a.classList.contains('is-closed');
      const reg=(a.closest('.country-block')||{}).dataset?.region||'0';
      const u=units.get(key);if(u)u.closed=u.closed||closed;else units.set(key,{closed,reg});
    });
    const arr=[...units.values()],n=arr.filter(u=>u.closed).length;
    set('booked',`${n}/${arr.length}`);
    const bar=$('.gl-bar');
    if(bar)bar.innerHTML=[...arr.filter(u=>u.closed).map(u=>`<i class="on r${u.reg}"></i>`),...arr.filter(u=>!u.closed).map(()=>'<i></i>')].join('');
  })();
  /* ---- "Today" ---- */
  const pop=$('#todayPop'),popT=$('#todayPopT'),popGo=$('#todayPopGo'),popX=$('#todayPopX');
  let popTrigger=null;
  function startsIn(n){if(n===0)return UI.trip_starts_today||'The trip starts today';if(n===1)return UI.trip_starts_tomorrow||'The trip starts tomorrow';if(n===2&&UI.trip_starts_two)return UI.trip_starts_two;return fmtUI('trip_starts_n','The trip starts in {n} days',{n});}
  function dayDiff(a,b){return Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86400000);}
  function todayItem(now){
    const where=whereNow(now);
    const ymd=ymdIn(ZONE[where]||HOME,now);
    const items=$$('.tline > article.item');
    return items.find(a=>a.classList.contains('xfer')&&a.dataset.from===ymd)
      ||items.find(a=>a.classList.contains('stop')&&a.dataset.from<=ymd&&ymd<a.dataset.to)
      ||items.filter(a=>a.dataset.from<=ymd).pop()||null;
  }
  function pulse(el){
    $$('.is-pulse').forEach(x=>x.classList.remove('is-pulse'));
    void el.offsetWidth;el.classList.add('is-pulse');
    setTimeout(()=>el.classList.remove('is-pulse'),2600);
  }
  function goItem(el){
    if(!el)return;
    el.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});
    pulse(el);
    const f=el.querySelector('.xfer-sum, .stop-toggle');
    if(f)try{f.focus({preventScroll:true});}catch(e){}
  }
  function closePop(restore){
    if(!pop||pop.hidden)return;
    pop.hidden=true;pop.classList.remove('on');
    if(restore!==false&&popTrigger)try{popTrigger.focus({preventScroll:true});}catch(e){}
    popTrigger=null;
  }
  function openPop(msg,trigger){
    if(!pop)return;
    popTrigger=trigger||document.activeElement;
    popT.textContent=msg;pop.hidden=false;
    requestAnimationFrame(()=>pop.classList.add('on'));
    try{popGo.focus({preventScroll:true});}catch(e){}
  }
  window.__v13Today=function(trigger){
    const now=new Date();
    if(DEP&&now>=DEP&&LAND&&now<=LAND){
      const it=todayItem(now);
      if(it){closePop(false);goItem(it);return it.id;}
    }
    if(DEP&&now<DEP){openPop(startsIn(dayDiff(ymdIn(HOME,now),ymdIn(HOME,DEP))),trigger);return 'pop';}
    openPop(UI.trip_ended||'The trip has ended',trigger);return 'pop';
  };
  if(popGo)popGo.addEventListener('click',()=>{const first=$('.tline > article.item');closePop(false);goItem(first);});
  if(popX)popX.addEventListener('click',()=>closePop());
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&pop&&!pop.hidden){window.__v13EscHandled=true;closePop();}},true);
  document.addEventListener('pointerdown',e=>{if(pop&&!pop.hidden&&!pop.contains(e.target)&&!(popTrigger&&popTrigger.contains(e.target)))closePop();});
  pop&&pop.addEventListener('keydown',e=>{
    if(e.key!=='Tab')return;
    const f=[popGo,popX];const i=f.indexOf(document.activeElement);
    e.preventDefault();f[(i+(e.shiftKey?-1:1)+f.length)%f.length].focus();
  });
  /* ---- search details in a modal dialog (centred on desktop, bottom sheet on phones) ---- */
  const dlg=$('#rsDialog'),det=$('#rsDetail');let detFrom=null;
  const recById=id=>REC.find(r=>r.id===id);
  function stopInfo(stopId){
    const a=document.getElementById(stopId);if(!a)return null;
    const name=(a.querySelector('.stop-sum h3')||{}).textContent||'';
    const dates=(a.querySelector('.stop-meta .ltr.tnum, .stop-meta bdi.tnum')||{}).textContent||'';
    return {name:name.trim(),dates:dates.trim()};
  }
  const isOpen=()=>!!(dlg&&dlg.open);
  /* scroll lock without a layout shift: reserve the gutter only where scrollbars take space */
  const sbCheck=()=>{const r=document.documentElement;if(!r.classList.contains('dlg-open'))r.classList.toggle('sb-classic',innerWidth-r.clientWidth>0);};
  sbCheck();addEventListener('resize',sbCheck);
  function closeDet(){
    if(!isOpen())return;
    const y=window.scrollY;
    dlg.classList.add('is-closing');
    const done=()=>{
      dlg.classList.remove('is-closing');
      if(dlg.open)dlg.close();
      document.documentElement.classList.remove('dlg-open');
      $$('#rsList .rs-hit.is-sel').forEach(x=>x.classList.remove('is-sel'));
      const back=detFrom;detFrom=null;
      if(back&&document.contains(back))try{back.focus({preventScroll:true});}catch(e){}
      if(window.scrollY!==y)window.scrollTo(0,y);
      det.innerHTML='';
    };
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)done();else setTimeout(done,160);
  }
  function openDet(item){
    const it=recById(item.dataset.rec);if(!it||!dlg)return;
    const y=window.scrollY;
    detFrom=item;
    $$('#rsList .rs-hit.is-sel').forEach(x=>x.classList.remove('is-sel'));
    const li=item.closest('.rs-hit');li.classList.add('is-sel');
    const st=stopInfo(it.stop);
    const rows=[];
    const R=(icon,k,v)=>`<div class="dl-row"><span class="dl-ic"><svg class="ic" aria-hidden="true"><use href="#i-${icon}"></use></svg></span><span class="dl-k">${esc(k)}</span><span class="dl-v">${v}</span></div>`;
    if(it.blurb)rows.push(R('info',UI.rec_about||'About',esc(it.blurb)).replace('class="dl-row"','class="dl-row dl-blurb"'));
    if(it.order)rows.push(R('fork-knife',UI.rec_order||'What to order',esc(it.order)));
    if(it.price)rows.push(R('wallet',UI.rec_price||'Price',esc(it.price)));
    if(it.caution)rows.push(R('warning-circle',UI.rec_caution||'Note',esc(it.caution)));
    if(it.reservation)rows.push(R('ticket',UI.rec_booking||'Booking',esc(UI['res_'+it.reservation]||it.reservation)));
    if(st)rows.push(R('map-pin-area',UI.rec_dest||'Destination',`${esc(st.name)} · <bdi dir="ltr" class="tnum tchip">${esc(st.dates)}</bdi>`));
    const maps=(it.maps||[]).filter(m=>m&&(m.href||m.u)).map(m=>`<a class="pill" href="${esc(m.href||m.u)}" target="_blank" rel="noopener noreferrer"><svg class="ic" aria-hidden="true"><use href="#i-map-pin"></use></svg>${esc((m.label&&m.label!==UI.maps)?m.label:(UI.open_in_maps||UI.maps||''))}</a>`).join('');
    det.className='rs-detail t-'+it.type;
    dlg.className='rs-dlg t-'+it.type;
    det.innerHTML=`<div class="rsd-grip" aria-hidden="true"></div><div class="rsd-head"><span class="rs-ic big">${typeIcon(it.type)}</span><div class="rsd-t"><h3 id="rsdTitle"><bdi dir="auto">${esc(it.name)}</bdi></h3><p>${esc(it.city)} · ${esc(it.type_label||'')}${it.optional?' · '+esc(UI.optional||''):''}</p></div>
      <button type="button" class="rsd-x" aria-label="${esc(UI.close||'Close')}"><svg class="ic" aria-hidden="true"><use href="#i-x"></use></svg></button></div>
      <div class="dl">${rows.join('')}</div>${maps?`<div class="rsd-links">${maps}</div>`:''}`;
    det.querySelector('.rsd-x').addEventListener('click',closeDet);
    document.documentElement.classList.add('dlg-open');
    if(!dlg.open)dlg.showModal();
    try{det.focus({preventScroll:true});}catch(e){}
    det.scrollTop=0;
    if(window.scrollY!==y)window.scrollTo(0,y);
  }
  if(dlg){
    /* Esc: the dialog's own cancel event, routed through our close (animation + focus return) */
    dlg.addEventListener('cancel',e=>{e.preventDefault();closeDet();});
    /* backdrop: a click that lands on the <dialog> box itself, outside its content */
    dlg.addEventListener('click',e=>{
      if(e.target!==dlg)return;
      const r=det.getBoundingClientRect();
      if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDet();
    });
  }
  window.__v13openRec=id=>{const el=$(`#rsList .rs-item[data-rec="${id}"]`);if(el)openDet(el);};
  window.__v13closeRec=closeDet;
  document.addEventListener('click',e=>{
    const it=e.target.closest&&e.target.closest('#rsList .rs-item[data-rec]');
    if(!it)return;
    e.preventDefault();
    openDet(it);
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&isOpen()){window.__v13EscHandled=true;return;}
    if(e.key!=='Enter'&&e.key!==' ')return;
    const it=e.target.closest&&e.target.closest('#rsList .rs-item[data-rec]');
    if(it&&e.target===it){e.preventDefault();openDet(it);}
  },true);
  syncNav();
})();
/* aria-current follows the visual active chip: one source of truth (the .on class) */
(function(){
  const sync=()=>{document.querySelectorAll('.nav-bar a[href^="#"], #panel a[href^="#"]').forEach(a=>{
    const on=a.classList.contains('on');
    if(on){if(a.getAttribute('aria-current')!=='location')a.setAttribute('aria-current','location');}
    else if(a.hasAttribute('aria-current'))a.removeAttribute('aria-current');
  });};
  window.__v13cSyncAria=sync;
  const bar=document.querySelector('.nav-bar');
  if(bar)new MutationObserver(sync).observe(bar,{subtree:true,attributes:true,attributeFilter:['class'],childList:true});
  const pnl=document.getElementById('panel');
  if(pnl)new MutationObserver(sync).observe(pnl,{subtree:true,attributes:true,attributeFilter:['class'],childList:true});
  sync();
})();
/* the phrase card is sticky only while it fits under the header */
(function(){
  const cards=[...document.querySelectorAll('.pair > aside.phrases')];
  if(!cards.length)return;
  const fit=()=>{
    const hh=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))||104;
    cards.forEach(c=>{c.classList.toggle('no-sticky',c.offsetHeight>innerHeight-hh-16-16);});
  };
  fit();
  if(window.ResizeObserver){const ro=new ResizeObserver(fit);cards.forEach(c=>ro.observe(c));}
  addEventListener('resize',fit,{passive:true});
  document.addEventListener('toggle',fit,true);
})();
/* Tap a closed destination card anywhere to open it; an open card closes only from its header.
   Interactive children (links, buttons, form fields, summaries) and text selection never toggle it. */
(function(){
  const IGNORE='a,button,input,select,textarea,label,summary,option,[role="button"],[role="link"],[role="checkbox"],[contenteditable],.term,.leaflet-container,[data-no-toggle]';
  document.addEventListener('click',e=>{
    const card=e.target.closest&&e.target.closest('article.stay.card-toggle');
    if(!card||e.defaultPrevented||e.button!==0)return;
    const btn=card.querySelector('.stop-sum .stop-toggle');if(!btn)return;
    const isOpen=btn.getAttribute('aria-expanded')==='true';
    if(isOpen&&!(e.target.closest('.stop-sum')&&card.querySelector('.stop-sum').contains(e.target)))return;
    const hitInteractive=e.target.closest(IGNORE);
    if(hitInteractive&&card.contains(hitInteractive))return;
    const sel=window.getSelection&&window.getSelection();
    if(sel&&!sel.isCollapsed&&String(sel).trim()&&card.contains(sel.anchorNode))return;
    btn.click();
  });
})();
/* Pack and task checklists: ticks are saved on this device only. */
function initCheckLists(){
  function load(key){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch(e){return {}}}
  function save(key,o){try{localStorage.setItem(key,JSON.stringify(o))}catch(e){}}
  function bind(listId, key, onSync){
    const rootEl=document.getElementById(listId);
    if(!rootEl)return;
    const st=load(key);
    const boxes=[...rootEl.querySelectorAll('input[type=checkbox]')];
    boxes.forEach(b=>{
      if(Object.prototype.hasOwnProperty.call(st,b.value))b.checked=!!st[b.value];
      else if(b.dataset.done==='1')b.checked=true;
      b.addEventListener('change',()=>{st[b.value]=b.checked;save(key,st);sync();});
    });
    function sync(){
      boxes.forEach(b=>{const lab=b.closest('label');if(lab)lab.classList.toggle('is-done',b.checked);});
      if(onSync)onSync(boxes);
    }
    sync();
  }
  bind('packList', STORE+'-pack', boxes=>{
    const n=boxes.filter(b=>b.checked).length,t=boxes.length;
    const c=document.getElementById('packCount');if(c)c.textContent=n+'/'+t;
    const e=document.getElementById('packEmpty');if(e)e.hidden=n!==0;
  });
  bind('taskListDone', STORE+'-tasks');
  bind('taskListOpen', STORE+'-tasks', ()=>{
    const all=[...document.querySelectorAll('#taskListDone input, #taskListOpen input')];
    const n=all.filter(b=>b.checked).length,t=all.length;
    const c=document.getElementById('taskCount');if(c)c.textContent=n+'/'+t;
  });
}
initCheckLists();
})();

