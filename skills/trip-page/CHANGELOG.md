# Changelog

## v1.0

- Initial public `trip-page` skill: a generic data folder, schemas, init / validate / build scripts, and a default self-contained HTML template.
- Onboarding interview (`references/onboarding.md`) and `init_trip.py --from answers.json`, with sample answers for fictional trips.
- Per-traveler dietary restrictions; `diet_fit` is checked against the party's combined restrictions.
- Place freshness warnings, reservation fields and deadline warnings, inbox ingest that archives to `sources/` instead of deleting.
- Date-based "today" view (offline) and an optional GPS button only in a secure context, on a user tap.
- `validate_trip.py` prints timeline gaps and a BOOK FIRST list ordered by urgency.
