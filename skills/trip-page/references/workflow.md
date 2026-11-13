# Workflow

End-to-end path from a new trip to a page. Each step can be repeated as the data grows.

1. **Interview** — ask the required onboarding questions, and any optional preferences the party wants to answer now. See [onboarding.md](onboarding.md).
2. **Answers file** — write `answers.json`. Confirmations can go into `inbox/` at the same time.
3. **Skeleton** — `python3 scripts/init_trip.py --from answers.json --out ./my-trip`.
4. **Automatic checks** — research visa, passport validity, insurance, power adapters, and problem dates; write `entry_checks` and each country's `entry_docs` / packing. Cite sources.
5. **Validate** — `python3 scripts/validate_trip.py ./my-trip`. Read **gaps** (nights without lodging, unbooked or missing transfers) and **BOOK FIRST**. Those lists drive the next bookings.
6. **Fill in stages** — stays, transfers, day plans, places (freshness + reservations), FX rates, estimates, tasks. Drop new links into `inbox/` and process them ([inbox.md](inbox.md)).
7. **Validate again** after each batch.
8. **Build** — `python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html`. Optional `--exclude-not-ok`, `--site <dir>` (writes `index.html` for a simple hosted site), `--allow-oversize`. The default build refuses to write a page over 1,000,000 characters or 3 MB (Google Drive HTML limits). Sibling `topic-to-html` `qa_check.py` runs when present (`--no-qa` to skip).
9. **Publish** — a local `file://` page works offline (date-based "today" view included). The optional GPS "by location" button only appears on a secure context (https, for example GitHub Pages), and only after a user tap. Hosting is optional and independent of the data folder.

The default HTML template can be replaced later with an approved design. Data and scripts stay the same.
