# trip-page

A generic skill: one folder of trip data in, one self-contained HTML page out. Any kind of trip; language, currency, countries and dietary rules come from the data.

Start with the [skill instructions](SKILL.md). To create a new trip folder, run the [onboarding interview](references/onboarding.md) and then:

```bash
python3 scripts/init_trip.py --from answers.json --out ./my-trip
python3 scripts/validate_trip.py ./my-trip
python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html
```

A sample answers file is [examples/sample-answers.json](examples/sample-answers.json).
