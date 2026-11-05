# QoL Agent Plugins

Quality-of-life plugins and reusable skills for AI agents. This monorepo keeps independent capabilities in separate folders so they can grow without requiring a repository per skill.

## Repository layout

```text
skills/
  topic-to-html/     # Premium, interactive, self-contained explainer pages
```

More skills and non-skill plugins can live alongside them as the collection grows.

## Topic to HTML

`topic-to-html` turns a concept, analysis, report, or difficult decision into a polished HTML page. It includes grey-only light glass, dark mode, Hebrew RTL support, Chart.js visuals, Phosphor duotone icons, three levels of deep dive, source chips, an interactive playground, and mobile/reduced-motion support.

- Start with the skill instructions: [`skills/topic-to-html/SKILL.md`](skills/topic-to-html/SKILL.md)
- Working fictional demo and implementation template: [`skills/topic-to-html/assets/template.html`](skills/topic-to-html/assets/template.html)
- Depth on structure, components, charts, glass, icons, typography, and QA: [`skills/topic-to-html/references/INDEX.md`](skills/topic-to-html/references/INDEX.md)
- Static checks: `python3 scripts/qa_check.py page.html` from the skill folder.
- Mobile overflow checks (requires Playwright and local Chrome): `python3 scripts/mobile_audit.py /absolute/path/to/page.html`

The included demo analyzes a **fully fictional neighborhood coffee-shop acquisition**. Every person, business, figure, document, and scenario in it is invented to demonstrate the components; it contains no private case-study content.

To use a skill in a compatible agent environment, add or link the relevant folder under `skills/` according to that environment's skill-loading mechanism. The template is a normal HTML file and can also be opened directly in a browser; fonts, icons, and Chart.js load from pinned CDN URLs.

## עברית

מונו־ריפו לסקילים ולתוספים שמשפרים את העבודה היומית עם סוכני AI. כל יכולת עצמאית נמצאת בתיקייה משלה, כדי שאפשר יהיה לתחזק ולשתף אותה בלי לפתוח ריפו נפרד לכל סקיל.

הסקיל הראשון הוא `topic-to-html`: יצירת דף HTML אחד, ויזואלי ואינטראקטיבי, שמסביר נושא או החלטה מורכבת. הסקיל כולל עיצוב זכוכית אפור ללא לבן, מצב כהה, עברית RTL, גרפים, אייקונים, שלוש רמות של צלילה לעומק, פלייגראונד ובדיקות מובייל ונגישות.

הוראות הסקיל נמצאות ב־[`skills/topic-to-html/SKILL.md`](skills/topic-to-html/SKILL.md). אפשר לפתוח בדפדפן את [`assets/template.html`](skills/topic-to-html/assets/template.html) כדי לראות דוגמה עובדת על רכישת בית קפה בדיוני. כל השמות, הנתונים והמסמכים בדוגמה הומצאו ואינם מכילים מידע אישי או עסקי אמיתי.

## License

MIT — see [LICENSE](LICENSE).
