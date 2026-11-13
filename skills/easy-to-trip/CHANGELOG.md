# Changelog

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
