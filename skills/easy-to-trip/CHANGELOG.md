# Changelog

## v1.4

- Folded the v10 page-review findings into the default template (see `references/template-pitfalls.md` items 13–20):
  - Phosphor duotone layers stack absolutely in a 1em `overflow: hidden` box; our CSS no longer uses `margin-inline-start: -1em`. The timeline rail inset moves with the node column (49px desktop, 62px under 900px).
  - `--header-h` is at least the real sticky header (128px under 900px, 104px from 900px) and `syncHeaderH()` can raise it. `#itinerary`, `#map` and other non-`.sec` jump targets get `scroll-margin-top`.
  - Date·time groups in transfer meta are `.xfer-leg` nowrap clusters; the middot is a `.sep`, never a bare flex text node. Labels are derived from `depart_at` / `arrive_at` when `date_label` / `time_label` are absent.
  - Deadline rows are a one-column start-aligned grid, not `space-between` plus a `flex: 1 1 100%` child.
  - Budget summaries use `align-items: flex-start`, `text-align: start`, `margin-inline: 0` — they are not centred.
  - Units and currency stay inside the same `<bdi class="tnum" dir="ltr">` as the number (`12.5°C`, `30 min`, `¥1,200`).
  - The pocket FAB is hidden below 900px, where the dock already opens the same sheet; it stays on desktop.
  - Open folds on small screens get `padding-bottom: dock height + 80px` on the article, without clipping, so the last line clears the dock.
- Confirmed: no global `.sheet-close { display: none !important }`, and no `overflow-x: hidden` on `html` or `body` (clip only, overflowing children fixed at the source).


## v1.3

- Folded the v9 page-review findings into the default template (see `references/template-pitfalls.md`):
  - Fold open-state selectors also match a `.fold` inside `.col`; a bare descendant `.is-open .fold` is not used, so nested folds stay closed.
  - `html`/`body` use `overflow-x: clip` and `scroll-padding-top` so the glass nav stays sticky; overflowing children are fixed (progress bar, long URLs) instead of hidden.
  - The progress bar is `position: absolute; width: auto; inset-inline: …` with no physical `left`/`right: auto` after it.
  - `.pocket.glass` stays `position: fixed` even though `.glass` is `relative`. Pocket close is a visible 44px button; leftover `display: none !important` on `.sheet-close` is gone.
  - Dark-mode country tokens are computed (same hue, lighter) and emitted after `#trip-theme` under `html[data-theme="dark"]`. Blocks use `var(--region-N)`, never inline hex. `scripts/qa_contrast.py` checks muted and dark region contrast at 4.5:1.
  - LTR amounts and times render as one `<bdi class="tnum" dir="ltr">` atom (thousands commas included). The budget hero stacks an English label over the amount on RTL lines.
  - Hebrew plurals (1 singular, 2 dual when the UI provides it, 0 and 3+ plural) live in `ui/he.json` and drive both the renderer and the countdown. English stays one/other. No frozen `{n} שעות`.
  - Chart.js bar charts flip to `indexAxis: 'y'` below 700px, with `autoSkip: false`, a taller canvas, and min-height cleared together with height.
  - Search ranks name and aliases, then type, then dish/city, then body text, and accepts a place `aliases` field plus a small generic Hebrew↔Latin list in the UI files.
  - "Open" badges use neutral ink on thick glass, not a warning colour. The booked checkmark phrase sits only on the badge.
  - Mobile tap targets are at least 44px. Light `--muted` is `#4a515c` (5.10:1 on paper). Leaflet tiles dim in dark mode; markers are taken off the tab path when the list is the keyboard path.
  - `backdrop-filter` is limited to floating chrome (nav, dock, pocket, instruments). Display weights use 700, not a synthesized 800. Only the Assistant 400/600/700 and Inter 400 faces stay inlined.


## v1.2

- The default template is the v2 glass design: a sticky two-row glass nav with scrollspy, calm mesh washes, inline SVG country flags, a desktop instrument panel, hairline stays that expand in place, nearly-sharp ticket frames, and glass section cards. The previous design is still available as `--template classic`.
- Template polish: mesh washes are full-bleed (no boxed decorations behind country names); the party line is omitted when the wordmark already names the travelers; booking confirmation codes are shown once, with copy actions in a column inside the panel; optional destinations sit inline in the city list with a dashed style; dietary codes are shown as localized labels from the UI file; the mobile nav is a fade-edged scroll strip; the mobile toolbar sits in the header row; the desktop gap before the itinerary is tightened.
- Country `flag`, `color`, `color_2`, `tint` and `mesh` fields (optional) drive flags, region colours and the background mesh. Nothing in the template is hard-coded to a country.
- `--template default|classic` selects the renderer and the vendor assets.

## v1.1

- Renamed the skill from `trip-page` to `easy-to-trip`. The public name lives in `scripts/skill_meta.py` so it is easy to change again.
- Replaced the fictional Lisbon example with a fictional Tokyo–Kyoto trip (`examples/japan-tokyo-kyoto/`), showing TableCheck / Tabelog / Omakase reservations, a walk-in ramen shop, a Shinkansen transfer, an IC-card note, timed tickets, and an archived inbox item. The Alps example is unchanged.
- The build is no longer bound by Google Drive size limits by default. `--target drive` (or `--max-chars` / `--max-bytes`) opts into those caps. `--mode single` (default) writes one self-contained HTML file; `--mode site` writes a static folder with cacheable assets and a service worker for offline use after the first http(s) load.
- Template refinements: fuller stay-navigation labels, deadline cards with a short title plus detail, calendar-day counts in the deadline's own timezone, `≈` budget figures, destination date en-dashes, and nights-undecided badges.

## v1.0

- Initial public `trip-page` skill: a generic data folder, schemas, init / validate / build scripts, and a default self-contained HTML template.
- Onboarding interview (`references/onboarding.md`) and `init_trip.py --from answers.json`, with sample answers for fictional trips.
- Per-traveler dietary restrictions; `diet_fit` is checked against the party's combined restrictions.
- Place freshness warnings, reservation fields and deadline warnings, inbox ingest that archives to `sources/` instead of deleting.
- Date-based "today" view (offline) and an optional GPS button only in a secure context, on a user tap.
- `validate_trip.py` prints timeline gaps and a BOOK FIRST list ordered by urgency.
