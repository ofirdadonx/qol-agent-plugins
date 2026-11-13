# Building the page

`build_trip.py` validates the data folder, then writes one of two outputs. Size caps are **off** unless you opt in. The page is meant to be hosted; a Google Drive file is only one possible target.

```bash
# Default: one self-contained HTML file, no size cap.
python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html

# A static site folder with cacheable assets, for GitHub Pages or any static host.
python3 scripts/build_trip.py ./my-trip --mode site -o ./my-trip/build/site

# Only when the file must be stored as a Google Drive HTML file:
python3 scripts/build_trip.py ./my-trip -o ./my-trip/build/trip.html --target drive
```

## `--mode single` (default)

Writes **one HTML file**. CSS, fonts, Leaflet, Chart.js, the trip payload (`window.TRIP`), and the app script are all inlined. The file opens offline, including from `file://`.

`-o` is the file path. If omitted, it defaults to `<data-dir>/build/trip.html`.

This is the right mode for emailing a file, opening it on a plane without a prior visit, or uploading a single document.

## `--mode site`

Writes a **folder** suitable for GitHub Pages or any static host:

```
site/
  index.html          # markup only; links out to assets
  sw.js               # service worker (see below)
  README.md
  assets/
    css/              # vendored styles and fonts
    js/               # Leaflet, Chart.js, app.js
    images/           # any vendored images
  data/
    trip.js           # window.TRIP = …;
```

`-o` is the folder path. If omitted, it defaults to `<data-dir>/build/site`. `--site DIR` is a deprecated alias for `--mode site -o DIR`.

Assets are separate so the browser can cache them and only re-download what changed.

### Service worker and offline use

`index.html` registers `sw.js` **only** when the page is served on `http:` or `https:`. It does **not** register on `file://` (browsers also refuse a service worker there).

On the first visit over http(s) the worker caches `index.html`, the assets, and `data/trip.js`. Later visits, including with no network, load from that cache. Cross-origin requests (for example map tiles) are not intercepted; the page already has a map fallback for when tiles are blocked.

The optional GPS "by location" button also requires https. Date-based "today" works in every mode, including `file://`.

## Optional size caps

There is **no** default character or byte limit.

| Flag | Effect |
|---|---|
| *(none)* | Print the assembled size and write the file. |
| `--target drive` | Enforce Google Drive HTML caps: 1,000,000 characters and 3 MB. Use this only when the output will be stored as a Drive HTML file. |
| `--max-chars N` | Set a character cap (overrides the matching `--target` value). |
| `--max-bytes N` | Set a byte cap (overrides the matching `--target` value). |
| `--allow-oversize` | When a cap is set and exceeded, write the file anyway instead of refusing. |

`--target drive` applies to the assembled HTML (`trip.html` in single mode, `index.html` in site mode). Site-mode `index.html` is typically small because assets sit next to it, so a Drive cap is rarely relevant there — Drive itself wants a single HTML file, which is `--mode single --target drive`.

## Other flags

`--exclude-not-ok` omits places whose `diet_fit` is `not_ok`. `--no-qa` skips the sibling `topic-to-html` `qa_check.py` when that script is present. `--as-of`, `--stale-months`, and `--book-by-days` are passed through to validation.
