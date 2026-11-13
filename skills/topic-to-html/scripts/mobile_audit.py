import sys,json
from playwright.sync_api import sync_playwright
src=sys.argv[1];out=sys.argv[2] if len(sys.argv)>2 else None
JS="""()=>{const W=innerWidth,bad=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width&&(r.right>W+1||r.left<-1)){let q=e,hid=false;while(q&&q!==document.body){const cs=getComputedStyle(q);if(cs.opacity==='0'||cs.visibility==='hidden'||cs.display==='none'){hid=true;break}q=q.parentElement}if(hid)return;let p=e.parentElement,clip=false;while(p&&p!==document.body&&p!==document.documentElement){const o=getComputedStyle(p).overflowX;if(o==='auto'||o==='hidden'||o==='scroll'){clip=true;break}p=p.parentElement}if(!clip&&getComputedStyle(e).position!=='fixed')bad.push((e.id||e.className||e.tagName).toString().slice(0,40)+' '+Math.round(r.left)+'..'+Math.round(r.right))}});
return {sw:document.documentElement.scrollWidth,W,bad:bad.slice(0,15),vp:!!document.querySelector('meta[name=viewport]')}}"""
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  fails=0
  for w in (360,390,430):
    for th in ('light','dark'):
      ctx=b.new_context(viewport={'width':w,'height':800},device_scale_factor=1,is_mobile=True,has_touch=True,user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1')
      pg=ctx.new_page();pg.goto('file://'+src+'?static&theme='+th);pg.wait_for_timeout(2500)
      r=pg.evaluate(JS);ok=r['sw']<=r['W'] and not r['bad'];fails+=not ok
      print(w,th,'scrollWidth',r['sw'],'OK' if ok else 'OVERFLOW',r['bad'][:8])
      if out and th=='light' or (out and w==390):
        pg.screenshot(path=f'{out}_{w}_{th}_full.png',full_page=True)
        if w==390 and th=='light':
          pg.click('[data-dd="capacity"]');pg.wait_for_timeout(1200);pg.screenshot(path=f'{out}_{w}_sheet.png')
      ctx.close()
  b.close();sys.exit(1 if fails else 0)
