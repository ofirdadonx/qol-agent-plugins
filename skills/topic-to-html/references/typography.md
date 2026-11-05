---
description: "Fonts (Assistant + Inter) and type scale."
---
# Typography
```html
<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```
- **Hebrew/body:** Assistant. **Latin and numbers:** Inter (`.num`, `.tnum` → `font-family:'Inter',var(--font);font-variant-numeric:tabular-nums`).

| Element | Size | Weight |
|---|---|---|
| H1 (claim) | `clamp(34px,5.2vw,58px)`, lh 1.08, ls -.02em | 800 |
| H2 (claim) | `clamp(24px,3vw,32px)`, lh 1.2 | 800 |
| Lede | 20px | 400 |
| Body | 17px (16.5 mobile), lh 1.65, max 68ch | 400 |
| Caption / card text | 14.5–15.5px | 400–500 |
| Label / act / chip | 13–14px | 600–700 |
| KPI | 40px; hero KPI 56px (46 mobile), ls -.03em | 700 |
