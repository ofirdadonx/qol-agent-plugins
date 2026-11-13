# easy-to-trip

A generic skill: one folder of trip data in, one self-contained HTML page — or a static site folder — out. Any kind of trip; language, currency, countries and dietary rules come from the data.

The public name is set in [`scripts/skill_meta.py`](scripts/skill_meta.py) so a rename is a small, documented change.

Start with the [skill instructions](SKILL.md). To create a new trip folder, run the [onboarding interview](references/onboarding.md) and then:

```bash
python3 scripts/init_trip.py --from answers.json --out ./my-trip
python3 scripts/validate_trip.py ./my-trip
# One self-contained offline HTML file (default). No size cap unless you ask for one.
python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html
# Or a static site with cacheable assets and an offline service worker (http(s) only):
python3 scripts/build_trip.py ./my-trip --mode site -o ./my-trip/build/site
# Only when the file must fit in Google Drive:
python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html --target drive
```

A sample answers file is [examples/sample-answers.json](examples/sample-answers.json) (a fictional Tokyo and Kyoto trip).
