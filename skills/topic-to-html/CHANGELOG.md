# Changelog

## v4.5 · RTL, mobile, maps and Drive QA
- Fixed Phosphor duotone in RTL (`direction:ltr` plus `margin-inline-start:-1em` instead of `margin-left`).
- `qa_check.py` now validates every `ph-*` class against the pinned Phosphor 2.1.1 name list, warns on a global `:empty{display:none}`, and enforces Drive's 1,000,000-character HTML cap alongside the 3 MB file-size cap.
- Documented common wrong icon names (`palm-tree` → `tree-palm`, `passport` → `identification-card`, `skyscraper` → `city`, `hot-springs` is not in 2.1.1).
- Hide only with `[hidden]{display:none!important}`; never a global `:empty` rule.
- Map tiles: prefer `tile.openstreetmap.de` with attribution and an automatic SVG fallback; OSM.org blocks requests with no Referer, and CARTO watermarks without an API key.
- `.ltr` utility for phones, codes and amounts; embed only the font weights the page uses.
- Collapsibles expand downward in place (`grid-template-rows` 0fr→1fr, ease-out ~280ms) with no `scrollIntoView` jump, and respect `prefers-reduced-motion`.
- Playwright / `mobile_audit.py` screenshots use `device_scale_factor: 1` to avoid false gaps on `position:fixed` + `backdrop-filter`.

## v4.4 · Public template
- Renamed the skill and all internal references to `topic-to-html`.
- Replaced the example with a fully fictional neighborhood-coffee-shop acquisition demo.
- Removed all real names, business details, private dates, personal financing and document citations.
- Generic source chips now cite invented example documents; modelled content remains clearly labelled.

## v4.3
- Mobile hardening: lighter phone blur, static mesh, fixed-bottom tooltips, clamped headings and device-emulation QA.

## v4.2
- Removed pointer/scroll sheen; glass keeps the static top-edge highlight.

## v4.1
- Improved HTML chart legends, list spacing, hanging badges, segmented controls, sliders and RTL number isolation.

## v4.0
- Added interactive financial visuals, source chips and a clearly separated playground.

## Earlier
- Established the lean skill map, grey-only light theme, dark theme, three glass levels, Assistant + Inter typography, Phosphor duotone icons, Chart.js helpers and three-level deep dives.
