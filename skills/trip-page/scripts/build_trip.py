#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate trip data and assemble one self-contained HTML page."""
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

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "templates" / "default" / "vendor"
APP_JS = ROOT / "templates" / "default" / "app.js"
QA = ROOT.parent / "topic-to-html" / "scripts" / "qa_check.py"

CHAR_LIMIT = 1_000_000
BYTE_LIMIT = 3 * 1024 * 1024

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


def esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def assemble(body: str, meta: dict) -> str:
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
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{esc(meta["lang"])}" dir="{esc(meta["dir"])}" data-theme="light">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{esc(meta["title"])}</title>\n'
        f'<meta name="description" content="{esc(meta["description"])}">\n'
        "<style>\n"
        + "\n".join(css_parts)
        + "\n</style>\n"
        "</head>\n"
        "<body>\n"
        + body
        + "\n<script>\n"
        + "\n".join(js_parts)
        + "\n</script>\n"
        "</body>\n"
        "</html>\n"
    )


def write_site(html: str, site_dir: Path, title: str):
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    readme = site_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {title}\n\nSelf-contained trip page. Serve over https "
            f"(for example GitHub Pages) if you want the optional location button.\n",
            encoding="utf-8",
        )


def main(argv=None):
    p = argparse.ArgumentParser(description="Build a self-contained trip HTML page.")
    p.add_argument("data_dir", type=Path)
    p.add_argument("-o", "--out", type=Path, default=None, help="Output HTML path.")
    p.add_argument("--exclude-not-ok", action="store_true",
                   help="Omit places whose diet_fit is not_ok.")
    p.add_argument("--site", type=Path, default=None,
                   help="Also write index.html to this folder for a simple hosted site.")
    p.add_argument("--stale-months", type=float, default=6)
    p.add_argument("--as-of", default=None)
    p.add_argument("--book-by-days", type=int, default=7)
    p.add_argument("--no-qa", action="store_true", help="Skip sibling topic-to-html qa_check.")
    p.add_argument("--allow-oversize", action="store_true",
                   help="Do not fail when the page exceeds the Drive size limits.")
    args = p.parse_args(argv)
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
        # Keep the build log readable: show the first 30 and a count.
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
    html = assemble(body, meta)
    chars, raw = len(html), len(html.encode("utf-8"))
    print(f"Assembled {chars:,} characters, {raw:,} bytes.")
    over = False
    if chars > CHAR_LIMIT:
        print(f"OVERSIZE: {chars:,} characters exceeds the {CHAR_LIMIT:,} Drive character limit.")
        over = True
    if raw > BYTE_LIMIT:
        print(f"OVERSIZE: {raw:,} bytes exceeds the {BYTE_LIMIT:,} byte cap.")
        over = True
    if over and not args.allow_oversize:
        print("Refusing to write the file. Pass --allow-oversize to override.")
        return 2
    out = args.out or (Path(args.data_dir) / "build" / "trip.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")
    if args.site:
        write_site(html, args.site, meta["title"])
        print(f"Wrote site {args.site / 'index.html'}")
    if not args.no_qa and QA.exists():
        r = subprocess.run([sys.executable, str(QA), str(out)], capture_output=True, text=True)
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
