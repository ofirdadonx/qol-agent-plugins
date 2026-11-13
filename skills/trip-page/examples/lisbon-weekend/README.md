# Lisbon long weekend (fictional sample)

A complete-enough sample trip used to illustrate the trip-page skill: onboarding answers, already-booked flights and a stay, per-traveler dietary restrictions (vegetarian, on one traveler — `diet_fit` uses the union), reservation badges, an archived inbox item under `sources/`, and an optional open destination (Sintra).

Places, names, prices and confirmation-style notes are **invented**. Do not treat them as real recommendations.

Built from [`../sample-answers.json`](../sample-answers.json):

```bash
python3 scripts/init_trip.py --from examples/sample-answers.json --out /tmp/lisbon-weekend
```

Then filled in stages (places, FX, entry checks, a processed inbox item).
