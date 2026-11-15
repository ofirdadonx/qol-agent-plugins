#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a trip data folder: schemas, refs, dates, secrets, place freshness, gaps, book-first."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trip_lib import validate_trip, party_dietary  # noqa: E402

URGENCY = {
    0: "overdue",
    1: "soon",
    2: "required",
    3: "transfer",
    4: "stay",
    5: "recommended",
}


def print_book_first(items):
    if not items:
        print("BOOK FIRST — nothing urgent. Gaps and reservation warnings, if any, are listed above.")
        return
    print(f"BOOK FIRST ({len(items)}) — ordered by urgency")
    for item in items:
        label = URGENCY.get(item.get("urgency"), str(item.get("urgency")))
        by = f" by {item['by']}" if item.get("by") else ""
        print(f"  [{label}] {item['title']}{by} — {item['reason']}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate easy-to-trip data.")
    p.add_argument("data_dir", type=Path, help="Folder containing trip.json")
    p.add_argument("--stale-months", type=float, default=6,
                   help="Warn when last_verified is older than this many months (default 6).")
    p.add_argument("--as-of", default=None, help="As-of date for freshness (YYYY-MM-DD), default today.")
    p.add_argument("--json", action="store_true", help="Print machine-readable result.")
    p.add_argument("--book-by-days", type=int, default=7,
                   help="Warn when an unbooked reservation's book_by is within this many days (default 7).")
    args = p.parse_args(argv)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    result = validate_trip(args.data_dir, as_of=as_of, stale_months=args.stale_months,
                           book_by_days=args.book_by_days)
    first = result.get("book_first") or []
    if args.json:
        out = {k: result[k] for k in ("ok", "errors", "warnings")}
        out["book_first"] = first
        if result.get("budget"):
            out["booked_total_home"] = result["budget"]["booked_total_home"]
        if result.get("data"):
            out["party_dietary"] = party_dietary(result["data"])
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if result["errors"]:
            print(f"ERRORS ({len(result['errors'])})")
            for e in result["errors"]:
                print(f"  ✖ {e}")
        if result["warnings"]:
            print(f"WARNINGS ({len(result['warnings'])})")
            for w in result["warnings"]:
                print(f"  ⚠ {w}")
        print_book_first(first)
        if result["ok"]:
            bud = result["budget"]
            print(
                f"OK — {len(result['warnings'])} warning(s). "
                f"Booked total ({bud['home']}): {bud['booked_total_home']} "
                f"({bud['fx_label']}, {bud['fx_date']})."
            )
        else:
            print(f"FAIL — {len(result['errors'])} error(s), {len(result['warnings'])} warning(s).")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
