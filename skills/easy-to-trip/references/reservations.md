# Reservations

Every restaurant, sight and day trip should say whether a booking is needed, how to make it, how far ahead, and whether it is already booked. Shopping places may omit this.

## The `reservation` object

```json
{
  "need": "required",
  "how": { "method": "website", "url": "https://example.invalid/book", "app_name": null },
  "lead_time": "2 weeks",
  "book_by": "2027-04-02",
  "booked": false,
  "notes": "Opens at 10:00 local, 14 days ahead."
}
```

- `need`: `required`, `recommended`, or `walk_in`. Use `unknown` only when the question has **not yet been researched** — that is a validation warning, not a final answer. After research, pick one of the three.
- `how.method`: `website`, `app`, `phone`, `hotel_concierge`, `at_door`, or `ticket_online`. Add `url` and/or `app_name` when useful.
- `lead_time`: free text (`"2 weeks"`, `"opens 30 days ahead at 10:00 local"`). `validate_trip.py` and `book_first` can derive a `book_by` date from `lead_time` plus `planned_day` when `book_by` is missing.
- `booked`: `true`, `false`, or a booking id in `bookings.json`.
- `planned_day`: optional ISO date of the visit, used to derive `book_by`.

The model is expected to research and fill this. Do not leave `unknown` once a source has been checked.

## Validation and BOOK FIRST

`validate_trip.py` warns when:

- `reservation` is missing or `need` is `unknown` (not yet researched), for food, sights and day trips.
- `need` is `required` and the place is not booked.
- `book_by` is within `--book-by-days` (default 7) or has passed, and the place is not booked.

Those required and deadline items also appear on the **BOOK FIRST** list, ordered by urgency.

The built page shows a badge (required / recommended / walk-in / booked) and the method plus lead time.

## Booking channels — examples only

Channels change by region and by year. Look up the current official route; the names below are **examples**, not defaults and not a complete list.

- **Japan, restaurants:** Tabelog, TableCheck, or Omakase are commonly used, alongside the restaurant's own site or phone. Hotel concierge is often effective for high-demand rooms.
- **Attractions in many regions:** the official site, or a ticket platform such as Klook, GetYourGuide, or a national rail / park operator.
- **Elsewhere:** the venue website, a local booking app, a phone call, or walk-in. Record whichever is actually recommended for that place.

Write the chosen method and URL on the place itself. Do not assume a region's usual app applies to every venue.
