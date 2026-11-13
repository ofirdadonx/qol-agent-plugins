---
name: easy-to-trip
description: "Turn a trip into a self-contained, mobile-first HTML page from a structured data folder: travelers, destinations, bookings, transfers, day plans, food and sights. Use when starting a new trip page, creating a trip data skeleton from an onboarding interview, validating or building trip HTML, ingesting inbox links and screenshots, or replacing a monolithic travel page with separate JSON files. Works for any kind of trip; language, currency, countries and dietary rules come from the trip's own data."
type: workflow
lifecycle: active
---

# Easy to trip

A reusable workflow that turns **one folder of trip data** into a trip page: either **one self-contained HTML file**, or a **static site folder** with cacheable assets. The page is the trip's "ID card": mobile-first, usable on a phone, including offline.

The public name of this skill (`easy-to-trip`) lives in [`scripts/skill_meta.py`](scripts/skill_meta.py), in this file's `name:` frontmatter, and in the folder name. To rename it, change those three and grep for the old name (see [Renaming](#renaming-this-skill)).

The skill is **generic**. It has no built-in travelers, diet, currency, language, countries, or trip type. Those values always come from the trip's own files (or from an onboarding answers file). Examples in this folder are clearly fictional and exist only to show patterns.

## When to use

- Someone wants a trip page, or a structured folder they can fill and then build into HTML.
- A trip is still being planned and needs a **skeleton** (destinations by date, gaps, a "book first" list) that can grow in stages.
- You need to validate bookings, stays, transfers, dietary fit, reservation deadlines, or inbox items.
- You need one offline HTML file (and optionally a small folder for GitHub Pages or similar).

## Workflow

Follow [references/workflow.md](references/workflow.md). The short path:

1. **Onboarding interview first.** Read [references/onboarding.md](references/onboarding.md). Ask the required questions **before** running `init_trip.py`. Optional preferences can be skipped and filled later. Write `answers.json`.
2. **Skeleton.** `python3 scripts/init_trip.py --from answers.json --out ./my-trip`
3. **Automatic checks** (the model does these from passports and destinations; init does not invent them): visa and entry rules, passport validity, insurance, power adapters, problem dates (local holidays, high season). Write them to `trip.entry_checks` and each country's `entry_docs` / packing. Cite sources.
4. **Validate.** `python3 scripts/validate_trip.py ./my-trip` prints **gaps** (nights without lodging, unbooked or missing transfers) and **BOOK FIRST** (urgency-ordered). Fill the next bookings and data from those lists.
5. **Fill in stages.** Destinations, stays, transfers, places, inbox drops, estimates, tasks. Re-validate after each batch.
6. **Build.** `python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html` for one self-contained file (default, `--mode single`). For a hosted site with separate assets and an offline service worker: `python3 scripts/build_trip.py ./my-trip --mode site -o ./my-trip/build/site`. Size caps are **off** by default; pass `--target drive` only when the file must fit in Google Drive. See [references/build.md](references/build.md).

Flag-only init (no answers file) still works when the tree is already known: `--name`, `--start`, `--end`, `--countries`, `--destinations`, `--out`, plus optional `--language`, `--dir`, `--currency`, `--travelers`, `--home-tz`, `--home-airport`.

## Onboarding (required questions)

About eight questions build the skeleton. Details and the answers-file shape are in [references/onboarding.md](references/onboarding.md).

1. Travelers: count, ages / children, names as on bookings, passport **issuing country** (never a number).
2. Departure city and airport.
3. Dates: fixed or flexible, approximate length. Always store a start and end; when flexible, mark `dates.flexible` and use a provisional window.
4. Destinations that are sure, and those still open (`certainty`, `optional`).
5. What is already booked (flights, hotels, …). Confirmations can be dropped into `inbox/`.
6. Trip type (honeymoon, family, backpacking, work+leisure, city-break, road-trip, …).
7. Budget: a total or a level (`budget` / `mid` / `luxury`), and its currency. Stored as `budget_plan` — distinct from the booked-only total derived later.
8. Page language (and `rtl` / `ltr`) and display currency.

Optional, skippable: priorities; pace and hotel-change comfort; lodging type and bed; dietary restrictions and allergies **per traveler**; accessibility, medical notes, special gear; transport (rental car and international licence, trains, taxis only).

`init_trip.py --from answers.json` fills `trip.json` and stub destinations from those answers. An example file is [`examples/sample-answers.json`](examples/sample-answers.json). Init refuses to overwrite a non-empty folder; later stages are ordinary JSON edits, not a second init.

## Data

The folder layout is in [references/structure.md](references/structure.md). Schemas live in `schema/`. Important rules:

- **Dietary restrictions are per traveler:** `travelers[].dietary` (an array of tags and/or free text, or a single string). Place `diet_fit` is judged against the **union** of every traveler's restrictions. An optional `dietary_note` is prose for the page. When nobody has restrictions, missing `diet_fit` is not a dietary warning.
- **Places** (food, sights, shopping, day trips) require `url`, `last_verified`, `hours`, `price_range`, and `diet_fit` (`ok` / `caution` / `not_ok` plus a note). The validator **warns** (it does not fail) on a missing URL, missing or stale `last_verified` (default six months), missing hours, and — only if the party has restrictions — a missing or `not_ok` `diet_fit`. `build_trip.py --exclude-not-ok` omits `not_ok` places.
- **Reservations** on restaurants, sights and day trips: see [references/reservations.md](references/reservations.md). `need` is `required`, `recommended`, or `walk_in` (`unknown` only means not yet researched). Record how to book, lead time, optional `book_by`, and whether it is booked. The model researches this. Validate warns on missing/unknown need, a required place that is not booked, and a `book_by` within `--book-by-days` (default 7) or already passed. Those items feed **BOOK FIRST**.
- **Budget on the page** is derived from **booked** rows only, converted with `trip.fx`. Do not treat `budget_plan` as a paid total.
- **No secrets.** Card numbers, CVV, IBAN and passport numbers must not appear in the data. Booking confirmation codes must not go into a **public** repository. The page may link to a private Drive file or a mailbox search. Init will not copy a confirmation code from an answers file into `bookings.json`.

## Inbox

See [references/inbox.md](references/inbox.md). Users drop links, screenshots, posts and notes into `inbox/`. The model reads each item, identifies it, **verifies** it (still open, current hours and prices, recent reviews, dietary fit, map link, **dedupe / merge**), and writes a JSON entry with `source`, `added_by`, `added_date`, and `raw_note`. Processed files are **moved to `sources/`**, never deleted; `source` stores the archive path. Unidentified items stay in `inbox/` with a `<name>.unresolved.txt` sidecar. `inbox_status.py` lists pending files; `archive_inbox.py` performs the move. `validate_trip.py` warns when the inbox is not empty. Video links (TikTok, Reels) often expose only a title or caption — a screenshot or a one-line note helps.

## Where we are now

On load, the page uses **today's date** (and `today.json` / destination dates) to find the current stop and offer a jump to **today's plan**. This is the primary method and works **offline**, including from a `file://` page.

A **by location** button uses the phone's GPS **only on a user tap**, and only when `window.isSecureContext` and `navigator.geolocation` are available (https, for example GitHub Pages — **not** `file://`). Handle denial and unsupported browsers. Nearest destination is chosen by lat/lng. Outside the trip dates, the page stays quiet. The button is hidden when location is not available.

## Page and build

`python3 scripts/build_trip.py <data-dir> -o trip.html`

- **`--mode single`** (default): one self-contained HTML file (CSS, fonts, Leaflet, Chart.js, and a compact `window.TRIP` payload inlined). It opens offline, including from `file://`.
- **`--mode site`**: a folder with `index.html`, separate cacheable assets (vendored libraries, fonts, images, trip data), and a service worker so the page works offline after the first visit. The service worker is registered only on `http:` and `https:` (not on `file://`). Suitable for GitHub Pages or any static host. Details in [references/build.md](references/build.md).
- **No size cap by default.** The page is meant to be hosted. Pass `--target drive` to enforce Google Drive HTML limits (1,000,000 characters and 3 MB), or set `--max-chars` / `--max-bytes` yourself. `--allow-oversize` writes the file anyway when a cap is set and exceeded.
- `--site <dir>` is a deprecated alias for `--mode site -o DIR`.
- Region colours are `--region-0` … `--region-5`, assigned in destination order — not hard-coded to any country.
- Transfer rows sit on the timeline (outbound at the start of the first country; a `boundary` leg that leaves country A is rendered at the **end of A**).
- **`--template default`** (the default): the v2 glass design — a single scrolling page, a sticky glass nav with scrollspy, calm mesh washes, country flags as inline SVG, and glass on the nav, instrument panel, section cards and tickets. Stays are hairline rows that expand in place (320ms ease-out). The live map is Leaflet. Dark mode, the countdown, the journal, recommendations, the pocket sheet, today-mode and the https-only GPS button are all included.
- **`--template classic`** keeps the previous self-contained design.
- Flags, mesh washes and region colours come from each country in the trip data (`flag`, `color`, `color_2`, `tint`, `mesh` on the country schema). The template does not hard-code any country. Flag fields that stand in for white should use a light grey (for example `#efece6`), never `#fff`.
- UI strings live in `templates/<name>/ui/<lang>.json` (English is the fallback).
- Sibling `topic-to-html` `qa_check.py` runs when present.

## Scripts

| Script | Role |
|---|---|
| `scripts/init_trip.py` | Create the folder tree. Prefer `--from answers.json`. |
| `scripts/validate_trip.py` | Schemas, refs, dates, secrets, freshness, reservations, inbox, **gaps**, **BOOK FIRST**. `--json`, `--as-of`, `--stale-months`, `--book-by-days`. |
| `scripts/build_trip.py` | Validate, then assemble HTML. `--template default|classic`, `--mode single|site`, `--target drive`, `--max-chars` / `--max-bytes`, `--exclude-not-ok`, `--allow-oversize`, `--no-qa`. |
| `scripts/inbox_status.py` | List pending and unresolved inbox files. |
| `scripts/archive_inbox.py` | Move one inbox file to `sources/` and print the archive path. |
| `scripts/render.py`, `scripts/trip_lib.py` | Shared render and validation library (not usually invoked directly). |

## Examples

Fictional sample trips, for patterns only:

- [`examples/sample-answers.json`](examples/sample-answers.json) — answers file for a fictional Tokyo and Kyoto trip (fixed dates, already-booked flights, two stays and a Shinkansen, vegetarian traveler).
- [`examples/japan-tokyo-kyoto/`](examples/japan-tokyo-kyoto/) — a more filled-in folder built from those answers (TableCheck / Tabelog / Omakase reservations, a walk-in ramen shop, an IC-card note, timed tickets, an archived inbox item).
- [`examples/sample-answers-alps.json`](examples/sample-answers-alps.json) and [`examples/alps-road-trip/`](examples/alps-road-trip/) — a two-country family road trip with flexible dates, a child, gluten-free restrictions, and intentional stay / transfer **gaps** so BOOK FIRST has something to show.

## References

| File | Read when |
|---|---|
| [references/onboarding.md](references/onboarding.md) | Starting a trip: interview, answers file, `--from`, staged fill. |
| [references/workflow.md](references/workflow.md) | The end-to-end path. |
| [references/structure.md](references/structure.md) | Folder and field layout. |
| [references/inbox.md](references/inbox.md) | Ingesting dropped links and screenshots. |
| [references/reservations.md](references/reservations.md) | Booking need, methods, deadlines; regional channel **examples**. |
| [references/build.md](references/build.md) | `--mode single` vs `--mode site`, optional Drive size caps. |

## Renaming this skill

The public name is meant to be easy to change:

1. Edit `SKILL_NAME` in [`scripts/skill_meta.py`](scripts/skill_meta.py).
2. Rename this folder so it matches.
3. Change the `name:` field in the frontmatter of this file.
4. Grep the repository for the old name (you can leave CHANGELOG history lines).
