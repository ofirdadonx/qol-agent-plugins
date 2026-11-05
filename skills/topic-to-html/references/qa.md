---
description: "QA checklist before delivery: static checks script, real contrast ratios, screenshots (desktop, dark, 390 mobile, deep dive, reduced motion), visual review."
---
# QA (run every time, fix and re-run until clean)

## 1. Static checks
```bash
python3 scripts/qa_check.py page.html
```
This checks for no white or near-white anywhere, no "סיפור/story" wording, and WCAG contrast of `--text --text-2 --muted --accent-ink --pos --neg --warn` (≥4.5) and `--accent` (≥3) on every glass level, composited over the bg and each mesh color, in both themes. If it fails, darken (light) or lighten (dark) the token, or use a thicker glass.

## 2. Console errors
```bash
google-chrome --headless=new --no-sandbox --virtual-time-budget=6000 --enable-logging=stderr --dump-dom "file://$PWD/page.html?static=1" 2>&1 | grep CONSOLE
```
It must print nothing from the page.

## 3. Screenshots (`?static=1` disables reveal and chart animation; `?theme=dark`; `#dd-<id>` opens the panel)
```bash
S="google-chrome --headless=new --no-sandbox --hide-scrollbars --virtual-time-budget=6000"; F="file://$PWD/page.html"
$S --window-size=1440,900 --screenshot=desk_light.png "$F?static=1&theme=light"
$S --window-size=1440,900 --screenshot=desk_dark.png  "$F?static=1&theme=dark"
$S --window-size=1440,900 --screenshot=deepdive.png   "$F?static=1#dd-capacity"
$S --window-size=1440,900 --force-prefers-reduced-motion --screenshot=reduced.png "$F"
# mobile 390: headless clamps windows to ~500px → render in an iframe and crop
echo "<body style=margin:0><iframe src='$F?static=1' style='width:390px;height:844px;border:0'></iframe>" > /tmp/m.html
$S --window-size=600,844 --screenshot=/tmp/m.png file:///tmp/m.html && python3 -c "from PIL import Image;Image.open('/tmp/m.png').crop((0,0,390,844)).save('mobile.png')"
```

## 4. Look at every screenshot
- [ ] Icons render (no empty squares or empty buttons)
- [ ] Every chart has bars or lines (not an empty card)
- [ ] Glass is visible: mesh color shows through, top-edge highlight, soft shadow
- [ ] No white surface, text or tooltip
- [ ] Mobile 390: no horizontal overflow, chips scroll, KPI and tables fit, the panel is a bottom sheet
- [ ] Dark mode: charts re-colored, contrast ok
- [ ] Reduced motion: everything visible without scrolling animations
- [ ] Headings are claims; the answer is in the hero
- [ ] Derived or modelled numbers are labelled; no invented data
- [ ] No "סיפור/story" in the UI ("חזרה למסמך", not "חזרה לסיפור")

## Mobile QA with real device emulation (required, v4.3)
A narrow desktop window or a 390px iframe hides bugs. Use `scripts/mobile_audit.py page.html [shot_prefix]` (Playwright + Chrome, `is_mobile`, `has_touch`, `device_scale_factor=2`) at **360 / 390 / 430**, both themes. It fails if `documentElement.scrollWidth > innerWidth` or any non-fixed element sticks out past the viewport without an `overflow:auto/hidden` ancestor (body excluded, since `body{overflow-x:hidden}` masks overflow).
Setup: `pip install --break-system-packages playwright` and pass `executable_path` to a local Chrome.
Full-page screenshots go blank past roughly 16k device px, so scroll and capture in 1500px steps. Check: the deep-dive bottom sheet, tooltips, sliders, segmented controls, tables, and chart axis labels (no rotation: `ticks.maxRotation:0`, split long labels into arrays, `layout.padding`).
Mobile rules: on ≤560px, reduce glass to `blur(14px) saturate(160%)` and stop the mesh animation (iOS GPU cost). Tooltips become a fixed bottom card. Clamp `h1`/`h2`.
Delivery: a Drive preview does not run the page's HTML/JS. On a phone, open it in a real browser (download, then open with Safari/Chrome) or from a hosted URL.
