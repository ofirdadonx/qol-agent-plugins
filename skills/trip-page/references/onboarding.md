# Onboarding interview

Run this interview **before** `init_trip.py`. The answers become a trip skeleton: `trip.json`, stub destination folders, booking rows for anything already reserved, and empty place files that can be filled in stages.

Optional preferences can be skipped and added later by editing `trip.json`. Automatic entry checks (visa, passport, insurance, adapters, problem dates) are researched by the model *after* the interview, from the party's passports and destinations — they are not invented by the init script.

## 1. Ask these questions

### Required for the skeleton (about eight)

1. **Travelers.** How many people? Ages, and who is a child? Names as they should appear on bookings (and a shorter display name if that differs). Issuing country of each passport (never a passport number).
2. **Departure.** Which city and airport are they leaving from?
3. **Dates.** Fixed or flexible? If flexible, roughly how many nights, and is there a provisional window? Record a start and end even when flexible — use a provisional window and set `dates.flexible`.
4. **Destinations.** Which countries and stops are already sure, and which are still open? Open stops can be marked optional, with provisional dates.
5. **Already booked.** Any flights, stays, trains, or other reservations already made? Confirmation emails and PDFs can be dropped into `inbox/` (they will be archived to `sources/` once recorded). Do not put confirmation codes into a public repository.
6. **Trip type.** For example honeymoon, family, backpacking, work+leisure, city-break, road-trip.
7. **Budget.** A total, or a level (`budget` / `mid` / `luxury`), and the currency of that figure.
8. **Page language and display currency.** Language (and `rtl` or `ltr`) for the HTML page, and the home currency used for totals and FX.

### Optional preferences (can be skipped)

- **Priorities**, in order: food, culture, nature, shopping, nightlife, rest, or others they name.
- **Pace:** many stops, or fewer places in depth? How often are they willing to change hotels?
- **Lodging:** hotel, apartment, ryokan, boutique, or something else; bed type (double, twin, family).
- **Dietary restrictions and allergies, per traveler.** These become `travelers[].dietary` and `travelers[].allergies`. Place `diet_fit` is later judged against the **union** of every traveler's restrictions.
- **Accessibility, medical notes, special gear**, per traveler or for the party.
- **Transport:** rental car (is an international driving permit needed?), trains, or taxis only.

### Automatic checks the model does itself

After the skeleton exists, research and write findings into `trip.json` → `entry_checks` and into each country's `entry_docs`, `packing`, and `climate`. Cite official sources and a date. Do not invent.

- Visa and entry rules for each destination country, for each traveler's passport.
- Passport validity rules (often a minimum validity beyond the stay — look up the current rule).
- Travel insurance expectations or requirements.
- Power adapters and voltage.
- Problem dates: local holidays, closures, high season, or events that affect the window.

## 2. Write an answers file

Save the replies as JSON. A complete fictional example is [`examples/sample-answers.json`](../examples/sample-answers.json) (a Lisbon long weekend). A second shape, with flexible dates, a child, and two countries, is [`examples/sample-answers-alps.json`](../examples/sample-answers-alps.json).

The useful keys:

```json
{
  "title": "Trip title",
  "trip_type": "city-break",
  "language": "en",
  "dir": "ltr",
  "currency": "USD",
  "home_tz": "America/New_York",
  "departure_city": "Boston",
  "departure_airport": "BOS",
  "travelers": [
    {
      "name": "Maya Chen",
      "booking_name": "MAYA CHEN",
      "age": 34,
      "child": false,
      "passport": "US",
      "dietary": ["vegetarian"],
      "allergies": []
    }
  ],
  "dates": {
    "start": "2027-04-16",
    "end": "2027-04-19",
    "flexible": false,
    "approx_nights": 3
  },
  "destinations": [
    { "id": "lisbon", "country": "portugal", "name": "Lisbon", "certainty": "sure" },
    { "id": "sintra", "country": "portugal", "name": "Sintra", "certainty": "open", "optional": true }
  ],
  "already_booked": [
    { "kind": "flight", "title": "Outbound", "status": "booked", "from_id": "home", "to_id": "lisbon" },
    { "kind": "hotel", "title": "City hotel", "status": "booked", "destination_id": "lisbon" }
  ],
  "already_booked_notes": "Flights and the first stay are booked. Confirmations are in inbox/.",
  "budget": { "total": 2500, "level": "mid", "currency": "USD" },
  "preferences": {
    "priorities": ["food", "culture"],
    "pace": { "style": "few_in_depth", "hotel_changes": "one hotel for the stay" },
    "lodging": { "types": ["hotel"], "bed": "double" },
    "transport": { "rental_car": false, "trains": true }
  }
}
```

Partial files are fine. Missing optional keys are skipped. If dates are flexible and only a start plus `approx_nights` is known, init computes a provisional end.

**Confirmation codes:** if a code is present in the answers, init does **not** copy it into `bookings.json`. It leaves a note pointing at `inbox/` instead, so a public repo does not receive booking codes.

## 3. Create the skeleton

```bash
python3 scripts/init_trip.py --from answers.json --out ./my-trip
```

Flags override matching answers (`--name`, `--start`, `--end`, `--currency`, `--language`, `--dir`, `--travelers`, `--out`, and so on). The original flag-only invocation still works when you already know the tree and do not have an answers file.

Init will not overwrite a non-empty folder. Filling in more data later is done by editing the JSON (and by dropping files into `inbox/`), not by running init again.

## 4. What the skeleton gives you

- A **destination tree by dates**, including open/optional stops with provisional nights.
- Stub country files, destination folders (`info`, `days`, `food`, `sights`, `shopping`, `daytrips`), empty `tasks`, `decisions`, `today`, `inbox/`, and `sources/`.
- Booking and transfer stubs for items listed under `already_booked`. A booked hotel with a `destination_id` marks that destination's stay as booked.
- `trip.entry_checks` ready for the model's research.
- Preferences, budget plan, trip type, departure city, and per-traveler diet when they were in the answers.

Then run:

```bash
python3 scripts/validate_trip.py ./my-trip
```

The validator prints:

- **Gaps** on the timeline: nights without a booked stay, transfers that exist but are not booked, missing legs between consecutive required stops, and a missing outbound or return when a home city or airport is known.
- **BOOK FIRST**, ordered by urgency (overdue reservations and deadlines first, then required bookings, unbooked or missing transfers, unbooked stays, recommended reservations).

Those two lists are the natural to-do for the next stage of filling. Re-run validate whenever the data changes.

## 5. Filling in stages

After init, any of the following can be added at any time:

- Preferences, dietary details, and `dietary_note`.
- Real coordinates, stay addresses, day-by-day plans.
- Places (with freshness and reservation fields — see [reservations.md](reservations.md)).
- Inbox items (see [inbox.md](inbox.md)).
- Entry-check research.
- Estimates, tasks, decisions, FX rates.

Nothing requires a complete file on day one. `validate_trip.py` keeps telling you what is still thin or urgent; `build_trip.py` can produce a page from a partial skeleton.
