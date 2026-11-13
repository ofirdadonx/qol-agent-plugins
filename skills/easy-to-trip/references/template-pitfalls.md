# Template pitfalls

Patterns found while reviewing and repairing the default (v2 glass) page. Follow these when you change `templates/default` or the renderer. They are generic — none of them depend on a particular trip.

## 1. Fold scoping

Stay and transfer folds live inside `.col`, not always as a direct child of the article. In CSS and in JS use:

```css
.is-open > .fold,
.is-open > .col > .fold { }
```

```js
el.querySelector(':scope > .fold, :scope > .col > .fold')
```

Never a bare `.is-open .fold`. That also opens any nested fold (a booked block inside a stay, a phrase sheet, and so on). A selector that only says `:scope > .fold` misses the fold and the panel stays at height 0 even though `aria-expanded` flips.

## 2. Sticky nav and overflow

`overflow-x: hidden` on `html` or `body` computes to `overflow: hidden auto`, which creates a scroll container and kills `position: sticky` on the nav. Use `overflow-x: clip` and set `scroll-padding-top` to the nav height (`var(--nav-h)`). If something sticks out, fix that child (for example `overflow-wrap: anywhere` on long URLs, or `width: auto` on the progress bar) rather than hiding overflow on the root. Mid-width (900–1279px) should stack the opening folio and the map so neither is squeezed.

## 3. Progress bar

A bar that is `width: 100%` *and* `inset-inline: …` overflows horizontally — that is often why `overflow-x: hidden` got added in the first place. Use:

```css
header.top .progress {
  position: absolute;
  width: auto;
  inset-inline: 56px; /* 16px on small screens */
  inset-block-end: 0;
}
```

Do **not** follow `inset-inline` with `left: auto; right: auto`. The physical sides reset the logical insets and the bar jumps or vanishes in RTL.

## 4. Pocket sheet vs `.glass`

`v2.css` is last in the cascade and sets `.glass { position: relative }`. That overrides `.pocket { position: fixed }` and the sheet disappears or sits in the flow. Keep a later, more specific rule:

```css
.pocket.glass, .pocket { position: fixed; }
```

Do not leave `display: none !important` on `.sheet-close`. Hide only `.fold .sheet-close` (the row toggle closes a fold). The pocket close (`#pocketClose`) stays `inline-flex`, at least 44×44px. The sheet starts with `inert` and `aria-hidden="true"`; opening it removes `inert` and focuses the close button.

## 5. Dark-mode country tokens

Emit a `<style id="trip-theme-dark">` **after** `#trip-theme`, with rules under `html[data-theme="dark"]` (higher specificity than `[data-theme="dark"]`). Compute a lighter tint of each country's colour — same hue, slightly less saturation, lightness raised until contrast against the dark paper (`#1c1f24`) is at least 4.5:1. Never hard-code a country's hex in the template, and never set an inline `style="color:#…"` on a country title; use `var(--region-N)` and `--block-color: var(--region-N)`. `scripts/qa_contrast.py` (run by the build unless `--no-qa`) checks muted and dark region tokens.

## 6. Bidi amounts and times

Render a complete LTR amount or time as one atom:

```html
<bdi class="tnum" dir="ltr">$1,124.75</bdi>
```

The matcher must allow a thousands comma in the first character class, otherwise `1,124.75` becomes `1,` plus a wrapped `124.75`. Never split a number across spans. When an English name and an amount share an RTL line (the budget hero), stack the label over the value (`.bud-pair`), each in its own isolated box.

## 7. Hebrew plurals

Hebrew: 1 is singular, 2 is the dual when one exists, 0 and 3+ are plural (`יום` / `יומיים` / `{n} ימים`, `שעה` / `שעתיים` / `{n} שעות`). Nights have no common dual: `לילה אחד` / `{n} לילות`. English stays at one/other. Forms live in `ui/he.json` and `ui/en.json` as `plural_day`, `plural_day_word`, `plural_hour`, `plural_night`. Both the Python renderer (`trip_lib.pluralize`) and the page (`plural()` in `app.js`) use them. Countdown strings take `{days}` and `{hours}` already declined — never a frozen `{n} שעות` or `{hours} שעות`. Dual is used only when the UI file provides `"two"`. The countdown caption is generic (`ליציאה` / `to departure`); a trip can override it through the UI or `countdown` data, not by hard-coding a carrier.

## 8. Chart.js on narrow screens

Below about 700px: `autoSkip: false`, `indexAxis: 'y'`, and a taller canvas (`max(200, nCats * 56 + 36)`). When you set a height on a map or a chart wrap, also set (or clear) `min-height` — a leftover min-height can block the new height. `applyBarAxis` / `watchCharts` do this for every bar chart and re-run on a viewport change. Preserve the value-axis tick callback (currency, step size) when flipping axes.

## 9. Search ranking and aliases

Rank name (and place `aliases`) above type, then dish/city, then body text (scores 8 / 6 / 4 / 1). If any hit scores 4 or more, drop the weak body-only matches. Places may declare an `aliases` array and a `dish` (see the schema). The UI files also have a small generic Hebrew↔Latin list (`search_aliases`, for example ראמן/ramen) that is not trip-specific. The recommendations payload must include `aliases` and `dish`.

## 10. Badges

"Open" (`badge.wait`) is a status, not a warning: neutral ink on thick glass, not `--warn`. The booked checkmark phrase (`סגור ✓` / `Booked ✓`) lives only on the badge. Do not also put it in the surrounding sentence, the status legend, or a stay label. Legend captions should add a description (`הוזמן`, "flights and stays are confirmed") or be omitted when they would only repeat the badge.

## 11. Tap targets, contrast, map a11y

On small screens, interactive targets are at least 44×44px (nav links, theme / today / search / locate, copy, fold toggles, pocket close, dock). Light `--muted` must be at least 4.5:1 on `--paper` (use `#4a515c` or darker; `#525a66` on `#d2cec6` is 4.44 and fails). In dark mode, dim Leaflet tiles with a filter on `.leaflet-tile-pane`. When the destination list is the keyboard path, create markers with `keyboard: false` and set `tabindex="-1"` on the marker icons after `fitBounds`.

## 12. Performance and fonts

`backdrop-filter` is expensive. Keep it on floating chrome only (the sticky nav, the instrument panel, the dock, the pocket sheet). Section cards, tickets and country blocks keep the glass *look* (tint, hairline, static top-edge highlight) without a blur pass. The offline file is already around 1 MB because libraries and fonts are inlined — embed only the weights you use (Assistant 400/600/700, Inter 400). Do not author `font-weight: 800`; the 800 face is not embedded and the browser would synthesize it. Use 700.
