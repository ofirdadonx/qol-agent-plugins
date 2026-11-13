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

`overflow-x: hidden` on `html` or `body` computes to `overflow: hidden auto`, which creates a scroll container and kills `position: sticky` on the nav. Use `overflow-x: clip` and set `scroll-padding-top` to the real sticky header height (`var(--header-h)`; see item 14). A fixed 96px fails on mobile. If something sticks out, fix that child (for example `overflow-wrap: anywhere` on long URLs, or `width: auto` on the progress bar) rather than hiding overflow on the root. Mid-width (900–1279px) should stack the opening folio and the map so neither is squeezed.

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

## 13. Phosphor duotone in RTL

Phosphor's vendor stylesheet overlaps the two duotone layers with `:after { margin-inline-start: -1em }`. In a right-to-left page that push spills the second layer onto the neighbouring title. Do not copy that `-1em` rule into our CSS (and do not rewrite every vendor icon). Stack both pseudo-elements absolutely inside a 1em `overflow: hidden` box, with `direction: ltr`, `unicode-bidi: isolate`, and `margin: 0` (use `!important` only to beat the vendor). Give the title column a `column-gap`. If you change the node column width or the grid gap, move the timeline rail (` .tline::before` / `.tl::before` `inset-inline-start`) by the same amount so the line still runs through the node centre. Current default: desktop columns `46px 32px` with an 8px gap and rail at `49px`; below 900px, columns `40px 28px` and rail at `62px`.

## 14. `--header-h` and jump targets

`scroll-padding-top` must be a `--header-h` token that is at least the real sticky header height at every breakpoint. Measure it. This template uses 128px under 900px and 104px from 900px, and `syncHeaderH()` in `app.js` raises the token if the measured header plus a 4px buffer is taller. A fixed 96px is shorter than the mobile header and hides the target under the nav.

Targets that are not `.sec` also need `scroll-margin-top: var(--header-h)`. The dock jumps to `#itinerary` and `#map`; those elements are a section and a figure, not `.sec`. After a dock jump, test with `scroll-behavior: auto` (smooth scrolling makes the assertion flaky) and check that the target's top is not hidden under `header.top`.

## 15. No bare middot between flex children

A bare `" · "` text node between flex children wraps onto its own line. Wrap each date·time group in an `inline-flex` nowrap `.xfer-leg`, and put the middot in a `<span class="sep" aria-hidden="true">·</span>`. The renderer does this in `xfer_when_bits`: combined labels such as `21.11 · 21:45` (with an optional landing group after a word) become two legs, and when `date_label` / `time_label` are absent it builds the same structure from `depart_at` / `arrive_at`. Do not `raw_ltr()` a string that contains a middot and then drop two `<bdi>` elements plus a text-node middot into `.xfer-meta`.

## 16. Deadline rows: one-column grid

`justify-content: space-between` plus `flex-wrap` plus a child with `flex: 1 1 100%` breaks the shared start edge across rows. The spilled child takes a full row, and the next items jump to the far edge. Use a one-column grid (`grid-template-columns: 1fr; justify-items: start; align-items: start`) and give children `justify-self: start; width: auto; max-width: 100%; flex: none; margin-inline: 0`.

## 17. Do not centre budget summaries

`margin-inline: auto` on a summary column (and `align-items: center; text-align: center` on `.bud-pairs` / `.bud-hero`) breaks page-wide start alignment. Use `align-items: flex-start`, `text-align: start`, and `margin-inline: 0`. Keep the label-over-value stack from item 6.

## 18. Units stay inside the LTR isolate

Wrap the unit or currency with the number in the same `<bdi class="tnum" dir="ltr">`, for example `12.5°C`, `20 °C`, `30 min`, `¥1,200`, `75 km`. If the regex consumes `12.5°` and leaves `C` outside, a right-to-left page renders `C°12.5`. The unit alternative in `_NUM_RE` must come before a bare decimal match, and `°C` / `°F` / `°[CFK]` must be longer than a lone `°`.

## 19. Hide the pocket FAB below the dock breakpoint

When the dock already opens the same pocket sheet (`#dockPocket`), hide `#pocketBtn` / `.pocket-toggle` at `max-width: 899px`. Keep the FAB on desktop, where there is no dock. Do not only nudge it up with `bottom: 76px` — hide it.

## 20. Open folds clear the fixed dock

On small screens an open stay or transfer can scroll its last line clear of the dock. Set `padding-bottom: calc(var(--dock-h, 72px) + 80px + env(safe-area-inset-bottom, 0px))` on the **article** (the open `.item`, `article.stay`, `article.xfer`), not on `.fold-inner` — that inner box must stay `overflow: hidden` for the 0fr/1fr fold animation. The article itself is `overflow: visible`. Verify in a 390-wide viewport: after opening the last fold and scrolling its last child with `block: "end"` and `scroll-behavior: auto`, `lastChild.getBoundingClientRect().bottom` is `<=` `dock.getBoundingClientRect().top`.

## Leftovers to never restore

- No global `.sheet-close { display: none !important }`. Scope a hide to fold close buttons (`.fold .sheet-close`) and keep the pocket close visible at 44px.
- No `overflow-x: hidden` on `html` or `body` (see item 2). Fix the overflowing child at the source. Leaflet's own pane CSS may still use it; do not copy that onto the page root.
- Do not add `.ph-duotone:after { margin-inline-start: -1em }` (see item 13), even with `!important` on a pin.
