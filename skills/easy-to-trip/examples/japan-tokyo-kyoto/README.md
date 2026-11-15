# Tokyo and Kyoto, nine days (fictional sample)

A complete-enough sample trip used to illustrate this skill: onboarding answers, already-booked flights, two stays and a Shinkansen, per-traveler dietary restrictions (vegetarian, on one traveler — `diet_fit` uses the union), Japan-typical reservation channels (TableCheck, Tabelog, Omakase), a walk-in ramen shop, an IC-card note, an attraction with timed tickets, and an archived inbox item under `sources/`.

Places, names, prices, flight numbers and confirmation-style notes are **invented**. Do not treat them as real recommendations, and do not confuse them with any real trip.

Built from [`../sample-answers.json`](../sample-answers.json):

```bash
python3 scripts/init_trip.py --from examples/sample-answers.json --out /tmp/japan-tokyo-kyoto
```

Then filled in stages (places, FX, entry checks, a processed inbox item, the Shinkansen).
