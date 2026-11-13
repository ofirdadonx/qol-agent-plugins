#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate trip data and build a trip page (single-file or hosted site)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trip_lib import validate_trip, party_dietary, book_first  # noqa: E402
from render import render_page  # noqa: E402
from skill_meta import SKILL_NAME  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "templates" / "default" / "vendor"
APP_JS = ROOT / "templates" / "default" / "app.js"
QA = ROOT.parent / "topic-to-html" / "scripts" / "qa_check.py"

# Opt-in only, via --target drive (or --max-chars / --max-bytes).
DRIVE_CHAR_LIMIT = 1_000_000
DRIVE_BYTE_LIMIT = 3 * 1024 * 1024

CSS_FILES = (
    "template.css",
    "base-extra.css",
    "trip-extra.css",
    "page-ui.css",
    "fonts.css",
    "phosphor.css",
    "leaflet.css",
)
JS_FILES = ("leaflet.js", "chart.js")
FONT_SUFFIXES = {".woff", ".woff2", ".ttf", ".otf", ".eot"}
IMAGE_SUFFIXES = {".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}


def esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def html_shell(body: str, meta: dict, head_extra: str, foot_extra: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{esc(meta["lang"])}" dir="{esc(meta["dir"])}" data-theme="light">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{esc(meta["title"])}</title>\n'
        f'<meta name="description" content="{esc(meta["description"])}">\n'
        + head_extra
        + "</head>\n"
        "<body>\n"
        + body
        + "\n"
        + foot_extra
        + "</body>\n"
        "</html>\n"
    )


def assemble_single(body: str, meta: dict) -> str:
    """One self-contained offline HTML file (CSS, fonts, JS, and data inlined)."""
    css_parts = []
    for name in CSS_FILES:
        p = VENDOR / name
        if p.exists():
            css_parts.append(f"/* {name} */\n" + p.read_text(encoding="utf-8"))
    js_parts = []
    for name in JS_FILES:
        p = VENDOR / name
        if p.exists():
            js_parts.append(p.read_text(encoding="utf-8"))
    payload = json.dumps(meta["payload"], ensure_ascii=False, separators=(",", ":"))
    js_parts.append("window.TRIP=" + payload + ";")
    if APP_JS.exists():
        js_parts.append(APP_JS.read_text(encoding="utf-8"))
    return html_shell(
        body,
        meta,
        "<style>\n" + "\n".join(css_parts) + "\n</style>\n",
        "<script>\n" + "\n".join(js_parts) + "\n</script>\n",
    )


def write_service_worker(site_dir: Path, assets: list[str], cache_name: str) -> None:
    listed = ["./", "./index.html", "./sw.js"] + [
        a if a.startswith("./") else f"./{a}" for a in assets
    ]
    seen = []
    for a in listed:
        if a not in seen:
            seen.append(a)
    sw = f"""/* Hosted-site offline cache. Registered by the page only on http(s). */
const CACHE = {json.dumps(cache_name)};
const ASSETS = {json.dumps(seen, ensure_ascii=False)};

self.addEventListener('install', event => {{
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', event => {{
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', event => {{
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(req).then(hit => {{
      if (hit) return hit;
      return fetch(req).then(resp => {{
        if (resp && resp.ok && resp.type === 'basic') {{
          const copy = resp.clone();
          caches.open(CACHE).then(cache => cache.put(req, copy));
        }}
        return resp;
      }}).catch(() => caches.match('./index.html'));
    }})
  );
}});
"""
    (site_dir / "sw.js").write_text(sw, encoding="utf-8")


def assemble_site(body: str, meta: dict, site_dir: Path) -> str:
    """Folder with index.html, separate cacheable assets, and a service worker."""
    if site_dir.exists() and site_dir.is_file():
        raise SystemExit(f"--mode site output must be a directory, not a file: {site_dir}")
    css_dir = site_dir / "assets" / "css"
    js_dir = site_dir / "assets" / "js"
    img_dir = site_dir / "assets" / "images"
    data_dir = site_dir / "data"
    for d in (css_dir, js_dir, img_dir, data_dir):
        d.mkdir(parents=True, exist_ok=True)

    assets: list[str] = []
    css_hrefs: list[str] = []
    for name in CSS_FILES:
        src = VENDOR / name
        if src.exists():
            shutil.copy2(src, css_dir / name)
            rel = f"assets/css/{name}"
            css_hrefs.append(rel)
            assets.append(rel)

    # Font files and any images sitting next to the CSS (leaflet looks for images/).
    leaflet_images = css_dir / "images"
    for src in VENDOR.iterdir():
        if not src.is_file():
            continue
        suf = src.suffix.lower()
        if suf in FONT_SUFFIXES:
            shutil.copy2(src, css_dir / src.name)
            assets.append(f"assets/css/{src.name}")
        elif suf in IMAGE_SUFFIXES:
            leaflet_images.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, leaflet_images / src.name)
            assets.append(f"assets/css/images/{src.name}")
    vendor_images = VENDOR / "images"
    if vendor_images.is_dir():
        leaflet_images.mkdir(parents=True, exist_ok=True)
        for src in vendor_images.iterdir():
            if src.is_file():
                shutil.copy2(src, leaflet_images / src.name)
                assets.append(f"assets/css/images/{src.name}")

    js_hrefs: list[str] = []
    for name in JS_FILES:
        src = VENDOR / name
        if src.exists():
            shutil.copy2(src, js_dir / name)
            rel = f"assets/js/{name}"
            js_hrefs.append(rel)
            assets.append(rel)

    payload = json.dumps(meta["payload"], ensure_ascii=False, separators=(",", ":"))
    (data_dir / "trip.js").write_text("window.TRIP=" + payload + ";\n", encoding="utf-8")
    js_hrefs.append("data/trip.js")
    assets.append("data/trip.js")

    if APP_JS.exists():
        shutil.copy2(APP_JS, js_dir / "app.js")
        js_hrefs.append("assets/js/app.js")
        assets.append("assets/js/app.js")

    cache_key = (meta.get("payload") or {}).get("storage_key") or meta.get("title") or SKILL_NAME
    cache_name = f"{SKILL_NAME}-{cache_key}-v1"
    write_service_worker(site_dir, assets, cache_name)
    assets.append("sw.js")

    head = "\n".join(f'<link rel="stylesheet" href="{esc(h)}">' for h in css_hrefs) + "\n"
    scripts = "\n".join(f'<script src="{esc(h)}"></script>' for h in js_hrefs)
    # Register the service worker only on http(s). file:// and other origins stay untouched.
    register = """
<script>
(function(){
  var p = location.protocol;
  if ((p === 'https:' || p === 'http:') && 'serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(function(){});
  }
})();
</script>
"""
    html = html_shell(body, meta, head, scripts + "\n" + register)
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    readme = site_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {meta['title']}\n\n"
            "Static site from the "
            f"`{SKILL_NAME}` skill (`--mode site`). Serve this folder over https "
            "(for example GitHub Pages).\n\n"
            "- Assets under `assets/` and trip data under `data/trip.js` are separate "
            "so the browser can cache them.\n"
            "- After the first visit on http(s), a service worker (`sw.js`) keeps the "
            "page available offline. It is not registered on `file://`.\n"
            "- The optional GPS button also requires https.\n",
            encoding="utf-8",
        )
    return html


def resolve_caps(args) -> tuple[int | None, int | None]:
    max_chars = args.max_chars
    max_bytes = args.max_bytes
    if args.target == "drive":
        if max_chars is None:
            max_chars = DRIVE_CHAR_LIMIT
        if max_bytes is None:
            max_bytes = DRIVE_BYTE_LIMIT
    return max_chars, max_bytes


def check_caps(html: str, max_chars, max_bytes, allow_oversize: bool) -> int:
    """Return 0 if OK to write, 2 if over cap and not allowed. Always prints size."""
    chars, raw = len(html), len(html.encode("utf-8"))
    print(f"Assembled {chars:,} characters, {raw:,} bytes.")
    over = False
    if max_chars is not None and chars > max_chars:
        print(f"OVERSIZE: {chars:,} characters exceeds the {max_chars:,} character cap.")
        over = True
    if max_bytes is not None and raw > max_bytes:
        print(f"OVERSIZE: {raw:,} bytes exceeds the {max_bytes:,} byte cap.")
        over = True
    if over and not allow_oversize:
        print("Refusing to write the file. Pass --allow-oversize to override, or drop the size cap.")
        return 2
    if over:
        print("Writing anyway because --allow-oversize was passed.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description=f"Build a {SKILL_NAME} page: one self-contained HTML file, "
        "or a static site folder with cacheable assets."
    )
    p.add_argument("data_dir", type=Path)
    p.add_argument(
        "-o", "--out", type=Path, default=None,
        help="Output path. In --mode single (default) this is the HTML file. "
             "In --mode site this is the site folder.",
    )
    p.add_argument(
        "--mode", choices=["single", "site"], default="single",
        help="single: one self-contained offline HTML file (default). "
             "site: a folder with index.html, separate cacheable assets "
             "(CSS, JS, fonts, images, data), and a service worker that "
             "keeps the page offline after the first http(s) visit.",
    )
    p.add_argument(
        "--target", choices=["drive"], default=None,
        help="Optional size target. 'drive' enforces Google Drive HTML caps "
             f"({DRIVE_CHAR_LIMIT:,} characters and {DRIVE_BYTE_LIMIT:,} bytes). "
             "No size cap is applied by default — the page is meant to be hosted.",
    )
    p.add_argument("--max-chars", type=int, default=None, help="Optional character cap (overrides --target).")
    p.add_argument("--max-bytes", type=int, default=None, help="Optional byte cap (overrides --target).")
    p.add_argument("--exclude-not-ok", action="store_true",
                   help="Omit places whose diet_fit is not_ok.")
    p.add_argument(
        "--site", type=Path, default=None,
        help="Deprecated alias for --mode site -o DIR. Still accepted.",
    )
    p.add_argument("--stale-months", type=float, default=6)
    p.add_argument("--as-of", default=None)
    p.add_argument("--book-by-days", type=int, default=7)
    p.add_argument("--no-qa", action="store_true", help="Skip sibling topic-to-html qa_check.")
    p.add_argument(
        "--allow-oversize", action="store_true",
        help="When a size cap is set (--target or --max-*), write the file even if it exceeds the cap.",
    )
    args = p.parse_args(argv)

    if args.site:
        args.mode = "site"
        if args.out is None:
            args.out = args.site

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    result = validate_trip(
        args.data_dir, as_of=as_of,
        stale_months=args.stale_months, book_by_days=args.book_by_days,
    )
    if result["errors"]:
        print(f"ERRORS ({len(result['errors'])})")
        for e in result["errors"]:
            print(f"  x {e}")
    if result["warnings"]:
        print(f"WARNINGS ({len(result['warnings'])})")
        for w in result["warnings"][:30]:
            print(f"  ! {w}")
        extra = len(result["warnings"]) - 30
        if extra > 0:
            print(f"  ... and {extra} more. Re-run validate_trip.py for the full list.")
    first = result.get("book_first") or (
        book_first(result["data"], as_of=as_of, book_by_days=args.book_by_days) if result.get("data") else []
    )
    if first:
        labels = {0: "overdue", 1: "soon", 2: "required", 3: "transfer", 4: "stay", 5: "recommended"}
        print(f"BOOK FIRST ({len(first)}) — ordered by urgency")
        for item in first:
            by = f" by {item['by']}" if item.get("by") else ""
            lab = labels.get(item.get("urgency"), str(item.get("urgency")))
            print(f"  [{lab}] {item['title']}{by} — {item['reason']}")
    if not result["ok"]:
        print("Build aborted: fix the errors above.")
        return 1

    body, meta = render_page(result["data"], exclude_not_ok=args.exclude_not_ok)
    max_chars, max_bytes = resolve_caps(args)

    if args.mode == "site":
        out = args.out or (Path(args.data_dir) / "build" / "site")
        if out.suffix.lower() in {".html", ".htm"}:
            print(f"Note: --mode site treats -o as a folder; using {out.parent}")
            out = out.parent
        html = assemble_site(body, meta, out)
        rc = check_caps(html, max_chars, max_bytes, args.allow_oversize)
        if rc:
            # assemble_site already wrote; if over cap and not allowed, remove.
            shutil.rmtree(out, ignore_errors=True)
            return rc
        print(f"Wrote site {out / 'index.html'}")
        qa_target = out / "index.html"
    else:
        html = assemble_single(body, meta)
        rc = check_caps(html, max_chars, max_bytes, args.allow_oversize)
        if rc:
            return rc
        out = args.out or (Path(args.data_dir) / "build" / "trip.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Wrote {out}")
        qa_target = out

    if not args.no_qa and QA.exists():
        r = subprocess.run([sys.executable, str(QA), str(qa_target)], capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        if r.returncode != 0:
            print("qa_check reported failures.")
            return r.returncode
    diet = party_dietary(result["data"])
    if diet:
        print(f"Party dietary (union): {', '.join(diet)}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
