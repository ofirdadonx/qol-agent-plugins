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

Do **not** also set `scroll-margin-top: var(--header-h)` on the targets — `scroll-padding` and `scroll-margin` add, the jump lands at twice the header height, and the scrollspy highlights the previous section. Use one offset (`html { scroll-padding-top: var(--header-h) }`) and set `scroll-margin-top: 0` on `#itinerary`, `#map`, `.sec` and the rest. The scrollspy threshold is `--header-h + 2`, and the last matching section wins (do not `break` on the first). After a dock or nav jump, test with `scroll-behavior: auto` and check that the target's top is just under `header.top`, not two header-heights down, and that the matching nav chip is `.on`.

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

## 21. Timeline is a 3-column grid; paint only the card cell

The itinerary row is `display: grid` with columns `var(--date-w) var(--rail-w) minmax(0,1fr)` (52px / 28px, tighter 44/24 under 360). The rail is `inset-inline-start: calc(var(--date-w) + var(--rail-w)/2 - 1px)` so it runs through the node centre at every width. The **article is a transparent track** — `padding: 0`, no background, no border, no backdrop-filter. Only `.col` is the painted card (ticket tint and hairline, or the stay's bottom hairline and hover). A rule such as `article.ticket { padding: 11px 14px }` has enough specificity to beat `.tline > .item { padding: 0 }` and pushes the nodes off the rail. Verify in QA that each node's centre is within 1px of the rail and that the rail stays ≥8px outside every `.col`.

## 22. Entrance animations skew measurements

`.rv` starts at `opacity: 0; transform: translateY(18px) scale(.985)`. Until `.in` lands, `getBoundingClientRect` is wrong and rail/overflow QA will flake. Wait until the animation settles, or measure under `prefers-reduced-motion` / `?static=1`. `app.js` sets `data-static` on `<html>` when that query is present and immediately adds `.in` with no transform. QA (`scripts/qa_layout.py`) always opens pages with `?static=1` and reduced motion.

## 23. One scroll offset, last-match scrollspy

See the refinement to item 14. Threshold = `--header-h + 2`; last match wins.

## 24. Transfer-mode icons are a 32px chip, not a duotone in the rail

Put a plain 9px dot on the rail. The mode glyph is a 32px chip (`border-radius: 10px`, `display: grid; place-items: center`, `background: color-mix(… 12%, transparent)`, 12px gap from the title, `margin-block-start: calc((1.25em - 32px) / 2)` so it centres on the title's first line). Use a regular-weight inline SVG (Phosphor fill, MIT) so the page stays offline — not a duotone webfont glyph in the narrow node. Check the optical centre with `path.getBBox()` and `getScreenCTM()` against the chip centre (±1px).

## 25. Rail-dot ring is `--paper`

The ring around a rail dot (`box-shadow: 0 0 0 3px`) must be the colour of the surface the rail sits on (`--paper`), not `--bg`. On this template they often coincide, but a mismatched `--bg` draws a visible halo.

## 26. Overflow QA allow-list

A horizontal-overflow check that walks every element will false-positive on `display: contents` parents (their rect is zero-width) and on real scroll containers (the map, the nav chip strip, tables). Skip those. `scripts/qa_layout.py` does this.

## 27. Accordion “open all” in QA

Fold helpers live inside an IIFE, so a test cannot call `setFold`. An “open all” check either reproduces it (`classList.add('is-open')` plus clearing `inert` / `aria-hidden` on `.fold-inner`) or clicks the toggles one at a time. A bare `querySelectorAll('.fold').forEach(…)` is not enough.

## 28. Nowrap LTR tokens

Phone numbers, booking codes, prices and times are `<bdi class="tnum" dir="ltr">` with `white-space: nowrap`, `overflow-wrap: normal` and no `overflow-wrap: anywhere`. A long emergency number takes its own full-width row (`.emer-wide`, or the odd last cell in the two-column `.emer` grid) and uses `font-size: clamp(16px, 2.4vw + 10px, 22px)` so it shrinks rather than wraps. `qa_layout.py` has a nowrap-tokens check: each token must render on a single line, especially at 390px.

## 29. No chart library and no pocket sheet

The default template no longer ships Chart.js or the pocket sheet. Decision charts are CSS bars (`.optbars`, a `--h` fraction per bar), and the budget uses a small SVG donut. The pocket's content already lives on the page (booking codes in the budget and the stays, emergency numbers in the practical section, phrases in the waiter card). Items 4, 8 and 19 now apply only to the classic template. The QA looks for the word "pocket" even in CSS comments, so keep it out of the default CSS.

## 30. Nav from `data-nav`, in page order

Mark every primary section with `data-nav="short label"` and build the nav bar and the contents panel from those elements in DOM order (the renderer does it, and `app.js` rebuilds it on the client). A hand-kept nav list drifts out of order as soon as a section moves. Scrollspy uses the same list, the threshold from item 23, and sets `aria-current="location"` on the one active chip. While a click-scroll is running, lock the spy so it does not flicker through the sections in between.

## 31. Overview, then the map band, then the itinerary

The overview holds the clocks (first), the at-a-glance tiles (second) and the country cards. The map is its own band between the overview and the itinerary, at the same width, 420px tall from 900px and 280px below. Status legends and "closed" lines do not belong in the overview.

## 32. Clocks follow time zones from data

Each country carries `timezone`; the payload passes it as `countries[].tz`. Clocks and offset text use `Intl.DateTimeFormat` with that zone and the page locale, re-render on the half minute, and never hard-code an offset (daylight saving changes it). The home clock uses `trip.home_tz`, and `trip.home.flag` / `trip.home.name` when present.

## 33. At-a-glance values are computed

Nights, stops, transfers, booked count and the booked budget come from the data and the rendered timeline, not from typed text. The booked bar has one segment per booking unit, with closed segments marked by the `is-closed` class. The budget tile is a link to `#budget` whose `aria-label` repeats the total.

## 34. Definition grids for card details

Stay and transfer details are rows of icon, label and value (`.dl > .dl-row > .dl-ic + .dl-k + .dl-v`). Drop empty values and repeated values inside one grid. When a value starts with its own label (for example a cancellation sentence that starts with the same words as the label), strip the repeat. Times, dates, codes and prices inside a value are LTR chips.

## 35. One compact action row per booking

A booking block shows the code once (`.bk-code`) and its actions in one row (`.bk-actions .act-btn`, 36px tall, 8px apart): copy, mail, manage, check-in. Do not repeat the code as a separate copy button elsewhere in the same card.

## 36. Destination cards have no hover state

Hover must not change the card, its column or its controls (no translate, no tint, no shadow). The keyboard focus ring stays. The whole card summary toggles the fold, except links, buttons, form fields, summaries, the map and a non-collapsed text selection. The caret is a real button labelled by the card title.

## 37. Pairs at 1024px and up

Practical beside phrases, country packing beside entry documents, and shared packing beside shared documents sit in `.pair` two-column rows from 1024px, with a 24px gap between rest items. Emit a single section without the wrapper when one side is missing.

## 38. Practical tiles

Each practical item is a tile with an icon, a short label, one value on one line and one supporting line, plus an optional "more" fold with a definition grid. The time tile computes the offset live (`data-offset-tz`) and the currency tile is built from the FX rates. Emergency numbers are call pills (`a[href^="tel:"]`, number in an LTR isolate, label underneath). The embassy is a small grid of pills (site, address, phone, emergency, email); long addresses break only between their comma-separated parts.

## 39. Budget card and lists

The budget card is at most 561px wide and centred: the total (`data-budget-total`), the FX line, a donut of closed against open estimates, one row per booked item **that has a price**, and a hidden `#budgetExtra[data-budget-hook="expenses"]` for a future expenses form. Bookings with no amount (a restaurant table, a free activity) are omitted from the card, from the closed list, and from `T.budget.booked`, so the row count stays in sync and no empty amount cell is rendered. `window.recalcBudget()` and `window.TRIP_BUDGET` stay available. The closed and open lists are two columns from 900px; each row is one line (name, badge, amount, caret) that opens to the detail.

## 40. Status words appear once

Data text often repeats "booked" or "open" next to the real badge. Strip those words from journal rows, task rows and transfer details with patterns built from the UI strings (`booked`, `open`, `optional_undecided`, `status_nouns`). Done tasks show a checked box, not a badge.

## 41. Search dialog

The search sits in a centred single column up to 880px. Each hit has a category icon and a `--cat` tint. Opening a hit shows a native `<dialog>` that lives at the end of `<body>`, outside the section, and closes with Escape or the close button. Place names are wrapped in `<bdi dir="auto">`.

## 42. Latin text and numbers in a right-to-left page

After rendering, wrap Latin runs in right-to-left text in `<bdi dir="ltr">` (skipping code, script, style, links and existing isolates), give quoted Japanese or Thai text a `lang` and an LTR isolate, and clean right-to-left fragments that ended up inside LTR isolates. Do this once on the finished body, not in each renderer.

## 43. Icons from an inline sprite

Icons are `<svg class="ic"><use href="#i-NAME"></use></svg>` pointing into the sprite at the top of `<body>`. Missing names fall back to the info icon. The layout QA reports any `use` that does not resolve.

## 44. Visible dates are D.M.YYYY

Never show an ISO date such as `2027-01-05` on the page. Convert FX dates and other raw dates before they reach the text.

## 45. Booked activities inside the destination card

A destination's expanded content may include a `.dest-booked` block (`#{dest_id}-booked`, heading from `dest_booked`) after the stay / arrival grids. It lists every booking with `status=booked` and `type=activity` for that `destination_id`, plus any booked item a place in that destination points to with `reservation.booked` (restaurant-like, even if the type is not `activity`). The block is not emitted when the list is empty.

Each `.dbk-row` is `data-booking` + `data-sort` (ISO datetime) and shows, in order: a 28px icon (`fork-knife` when a food rec links to the booking, otherwise `ticket`), the weekday + date + time, `short_title`, and the confirmation code. If `manage_url` is set, the code is that link. If a place rec points at the booking, the title is a `button.dbk-name[data-jump]`; `jumpToRec` opens the search dialog (`#rsDialog`) on that place and selects its `.rs-hit`. Rows wrap at 360px (`min-width: 0`, no nowrap on the title); they must not overflow the card from 360 to 1440 in light or dark.

Do not also put these reservations into the day-journal body — the card list is the place that scales as more dinners and activities are booked.

Destination cards must not include the place-recommendation list (`.recs`, `.recs-g`, `.rec-list`, or an intro such as `recs_intro` / "לא הוזמנו מקומות"). Places stay in the trip data and are reached only through the offline search (`#recs-search`, `#rsList`, `#rsDialog`), which is built from `T.recs`.

Deadline cards that use `checkin_at` take their heading from the booking type: `meal_at` (food-linked), `booking_at` (other activity), or `checkin_by` (stays and flights).
