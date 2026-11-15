# Data folder structure

One folder per trip. `init_trip.py` creates this tree. Personal documents (PDFs, passport scans, card details) stay **out** of it — the page only links to them.

```text
my-trip/
  trip.json              # Party, dates, destinations, language, currency, preferences
  bookings.json          # Single source of truth for booked / open / optional spend
  transfers.json         # Legs between stops (and outbound / return)
  estimates.json         # Open estimates (food, local transit, …)
  tasks.json
  decisions.json         # Optional decision cards
  today.json             # Optional journal segments for the "today" view
  inbox_items.json       # Inbox drops that are not yet a place or booking
  inbox/                 # Drop folder (README + pending items only)
  sources/               # Archived originals, referenced from JSON as `source`
  docs/                  # README only; real docs live in Drive or mail
  assets/                # Optional local images or a map fallback
  countries/
    <country-id>.json    # Practical info, entry docs, packing, phrases
  destinations/
    <dest-id>/
      info.json          # Stay, arrival, weather, notes
      days.json          # Day-by-day plan
      food.json
      sights.json
      shopping.json
      daytrips.json
```

`trip.json` is the index: travelers (with per-person `dietary`), `dates`, `departure_city` / `home_airport`, `trip_type`, `budget_plan`, `preferences`, `entry_checks`, `language`, `dir`, `currency`, and the destination list (ids, countries, dates, `optional`, `certainty`).

Budget totals on the page are **derived from booked rows only** (`bookings.json`), converted with `trip.fx`. `budget_plan` is the intended spend from onboarding and is not mixed into that total.

Destination ids and country ids are lowercase kebab-case (`tokyo`, `kyoto`, `porto-alegre`).

## Places

Each places file is `{ "group_heading": "", "places": [ … ] }`. Required on every place: `id`, `name`, `url`, `last_verified`, `hours`, `price_range`, `diet_fit`. Missing or stale `last_verified` (default older than six months), a missing URL or hours, and (when the party has any dietary restrictions) a missing or `not_ok` `diet_fit` are **warnings**, not errors. `build_trip.py --exclude-not-ok` omits `not_ok` places from the page.

## Transfers and the timeline

Transfers are interleaved on the destination timeline:

- Outbound (home → first stop) at the start of the first country.
- Intra-country legs between that country's destinations.
- A `boundary` leg that **leaves** country A is rendered at the **end** of A (not at the start of B).

## Secrets

No card numbers, CVV, IBAN, or passport numbers in any JSON file. Booking confirmation codes must not go into a **public** repository; a private data folder may store them, or the page can link to a Drive file or a mailbox search. The validator scans for card-like and passport-number patterns.
