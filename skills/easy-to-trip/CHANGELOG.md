# Changelog

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
