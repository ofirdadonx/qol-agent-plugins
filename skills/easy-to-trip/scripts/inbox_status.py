#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List pending and unresolved items in a trip's inbox/ folder."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trip_lib import list_inbox, sidecar_for, inbox_ignore  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="Show pending and unresolved inbox items.")
    p.add_argument("data_dir", type=Path, help="Folder containing trip.json and inbox/")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    pending, unresolved, missing = list_inbox(args.data_dir)
    if missing:
        print(f"No inbox/ folder in {args.data_dir}", file=sys.stderr)
        return 2
    rows = []
    for path in pending:
        side = sidecar_for(path)
        note = ""
        if side and side.exists():
            note = side.read_text(encoding="utf-8", errors="replace").strip()
        rows.append({
            "file": f"inbox/{path.name}",
            "status": "unresolved" if side else "pending",
            "sidecar": f"inbox/{side.name}" if side else None,
            "note": note or None,
        })
    for path in unresolved:
        # already covered as a sidecar?
        if any(r.get("sidecar") == f"inbox/{path.name}" for r in rows):
            continue
        rows.append({
            "file": f"inbox/{path.name}",
            "status": "unresolved",
            "sidecar": f"inbox/{path.name}",
            "note": path.read_text(encoding="utf-8", errors="replace").strip() or None,
        })
    if args.json:
        print(json.dumps({"inbox": "inbox", "items": rows}, ensure_ascii=False, indent=2))
        return 0 if not rows else 1
    if not rows:
        print("Inbox is empty (apart from the README). Nothing is waiting.")
        return 0
    pending_n = sum(1 for r in rows if r["status"] == "pending")
    unr_n = sum(1 for r in rows if r["status"] == "unresolved")
    print(f"Inbox: {pending_n} pending, {unr_n} unresolved.")
    for r in rows:
        print(f"  [{r['status']}] {r['file']}" + (f"  ({r['sidecar']})" if r['sidecar'] and r['sidecar'] != r['file'] else ""))
        if r["note"]:
            first = r["note"].splitlines()[0][:200]
            print(f"           {first}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
