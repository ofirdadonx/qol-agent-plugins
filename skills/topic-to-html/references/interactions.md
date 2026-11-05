---
description: "Motion: spring easing, scroll reveal, hover/press micro-interactions, progress + active chip, reduced motion."
---
# Interactions

Use `--spring` `cubic-bezier(.34,1.56,.64,1)` for things that move (thumbs, panels, chevrons, press) and `--ease` for fades. Durations: 160 (color), 280 (hover/press), 520 (panels/reveal). Animate only `transform` and `opacity`.

```css
.press{cursor:pointer;transition:transform var(--dur-2) var(--spring),box-shadow var(--dur-2) var(--ease)}
.press:hover{transform:translateY(-2px) scale(1.005)}
.press:active{transform:scale(.97);transition-duration:90ms}
.rv{opacity:0;transform:translateY(18px) scale(.985);transition:opacity var(--dur-3) var(--ease),transform 700ms var(--spring)}
.rv.in{opacity:1;transform:none}
:focus-visible{outline:2.5px solid var(--accent);outline-offset:3px;border-radius:8px}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition-duration:1ms!important;scroll-behavior:auto!important}.rv{opacity:1;transform:none}}
```
```js
// reveal (stagger 60ms within groups of 4); ?static=1 or reduced motion → show immediately
const rio=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');e.target.querySelectorAll('.meter b').forEach(b=>b.style.width=b.dataset.w);rio.unobserve(e.target)}}),{threshold:.12});
$$('.rv').forEach((el,i)=>{el.style.transitionDelay=(i%4)*60+'ms';(reduce||qs.has('static'))?el.classList.add('in'):rio.observe(el)});
// progress + active chip
addEventListener('scroll',()=>{const h=document.documentElement;prog.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%'},{passive:true});
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){chips.forEach(c=>c.classList.toggle('on',c.getAttribute('href')==='#'+e.target.id));
  chips.find(c=>c.classList.contains('on'))?.scrollIntoView({block:'nearest',inline:'center'})}}),{rootMargin:'-45% 0px -50% 0px'});
```
Rules:
- Never hijack scrolling.
- The end state is correct without JS or animation.
- Use hover lift only on interactive or tappable things.
- Every control is a real `<button>`/`<input>` with a label.
