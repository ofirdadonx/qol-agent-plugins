---
description: "Page skeleton: hero + bottom line, sticky chips + progress, claim headings, one visual per section, takeaways, sandbox."
---
# Structure

Opening → middle → end is the internal order. The UI never calls it a story.

| Order | Block | Must contain |
|---|---|---|
| 1 | Hero (`.hero`) | kicker chip (doc type · read time), claim H1 with the answer, lede ≤2 lines |
| 1b | Bottom line (`aside.bottom.g-thick`) | verdict with icon + 3 bullets (decision, key number, main risk) |
| 2 | Top bar (`header.topbar.g-thick`) | chips per section, the first chip of each part with `<small>התחלה/אמצע/סוף</small>`, progress line, theme button |
| 3 | Opening | state today: KPI bento + who brings what |
| 4 | Middle | options compare, potential/scenarios, money, timeline |
| 5 | End | exit/risks, checkpoints, decision |
| 6 | Takeaways | `ol.take`, 3–5 items, each starting with a bold claim |
| 7 | Sandbox | 2–4 sliders → live result cards + status + chart. Labelled "המחשה" if modelled |
| 8 | Checklist + footer | action items; disclaimer |

## Section template
```html
<section id="money" class="sec">
  <div class="sec-head rv">
    <div class="act"><i class="ph-duotone ph-coins ph"></i> אמצע · הכסף</div>
    <h2>180K במעבר, ועד 60K נוספים לפי ביצוע.</h2>  <!-- claim, not a topic -->
    <p>One or two sentences of context.</p>
  </div>
  <div class="viz glass g-reg rv"> …one main interactive visual… <p class="caption">what to notice</p>
    <button class="dd-btn press" data-dd="salary">צלילה לעומק: … <small>· 2 דק'</small></button>
  </div>
</section>
```

## Rules
- Heading = the conclusion ("הרכישה ההדרגתית חוסכת 70K בתשלום הראשון"), never just a label ("האפשרויות").
- One dominant visual per section. Secondary visuals go into an L2 expand or an L3 panel.
- Every chart gets a `.caption` that says what to notice.
- Put the answer first: the reader must get the decision from the hero alone.
- Cut text: ≤2 sentences under each heading; details go to deep dives.

## Optional: Playground (user scenarios)
When the user has their own estimates, theories or "what if" games that are **not in the source documents**, keep them out of the main document and put them in one final section:
- Main document = source-grounded only. Cite subtly with `<span class="src">דוח לדוגמה עמ' 6</span>`. A derived number gets `<span class="src">חישוב מהמסמכים</span>` plus the calculation (`.calc` rows).
- `<section id="playground" class="sec pg">` comes last (before the footer), with a chip `<i class="ph-duotone ph-flask ph"></i> פלייגראונד` and a dashed warn banner: "פלייגראונד — ההערכות שלנו · לא מופיע במסמכים".
- Every block inside gets `<span class="est">הערכה</span>`. Put the sandbox sliders, financing examples, scenario ranges and hypothetical timelines here.
- If a user estimate contradicts the sources, the main document uses the source-derived figure and the playground keeps the old estimate labelled "הנחה בלבד" with a link back.
```css
.src{display:inline-flex;font:600 11.5px var(--font);color:var(--muted);padding:2px 8px;border-radius:999px;border:1px solid var(--g-border);background:var(--g-thin);margin-inline-start:6px;white-space:nowrap}
.pg{margin-top:var(--s16);padding-top:var(--s8);border-top:2px dashed var(--g-border)}
.pg-banner{display:flex;gap:14px;padding:var(--s5) var(--s6);border-radius:var(--r-card);border:1.5px dashed color-mix(in srgb,var(--warn) 60%,transparent);background:linear-gradient(var(--warn-tint),var(--warn-tint)),var(--g-reg)}
.est{font:700 12px var(--font);color:var(--warn);background:var(--warn-tint);padding:2px 9px;border-radius:999px}
```
