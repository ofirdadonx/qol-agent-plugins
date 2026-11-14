---
description: "Maps in a self-contained page: tile servers that work without a Referer, attribution, and an SVG fallback."
---
# Maps

Standard OpenStreetMap tiles (`tile.openstreetmap.org`) require a Referer. A page opened as a `file://` download, or from a Google Drive download, sends no Referer and the tiles come back "Access blocked".

CARTO basemaps (`basemaps.cartocdn.com`) used to work without a key. As of 2026 they still return HTTP 200 and a 256×256 PNG, but the image is a watermark that says "API KEY REQUIRED" — not a map.

Use the German OSM tile server, which serves real geography with no Referer and no API key:

```js
L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.openstreetmap.de/">OpenStreetMap.de</a>'
})
```

Always credit both OpenStreetMap and OpenStreetMap.de. Check their tile-usage policy before a high-traffic host.

Keep an embedded SVG overview (or a static image) on the page and switch to it automatically when the live map cannot be shown:

- `navigator.onLine === false`
- Leaflet failed to load
- `tileerror` fires repeatedly (a small threshold such as 6 failed tiles)

Give the reader a way to switch back to the SVG map by hand. Put `dir="ltr"` on the map container so pan/zoom controls are not mirrored; keep popup text RTL.
