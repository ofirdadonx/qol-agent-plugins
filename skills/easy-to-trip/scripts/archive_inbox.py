#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Move a processed inbox item into sources/ and print the archive path.

Does not write JSON — record the returned path as the entry's `source` field
after verifying the place (open, hours, prices, recent reviews, diet, map, dedupe).
Does not delete the file; it is moved. Any matching `.unresolved.txt` sidecar
is moved alongside it (renamed to `<archive-name>.unresolved.txt`) only if you
pass --with-sidecar; by default a leftover sidecar is an error so nothing is lost.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trip_lib import sidecar_for  # noqa: E402


def safe_slug(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-").lower()
    return (slug or "item")[:60]


def main(argv=None):
    p = argparse.ArgumentParser(description="Move one inbox item into sources/ and print the new relative path.")
    p.add_argument("data_dir", type=Path)
    p.add_argument("item", help="Filename or path of an item inside inbox/")
    p.add_argument("--date", default=None, help="Archive date YYYY-MM-DD (default: today).")
    p.add_argument("--slug", default=None, help="Override the slug used in the archive filename.")
    p.add_argument("--with-sidecar", action="store_true",
                   help="Also move a matching .unresolved.txt sidecar into sources/.")
    args = p.parse_args(argv)
    data = Path(args.data_dir)
    inbox = data / "inbox"
    sources = data / "sources"
    if not inbox.is_dir():
        print("No inbox/ folder.", file=sys.stderr)
        return 2
    sources.mkdir(exist_ok=True)
    src = Path(args.item)
    if not src.is_absolute():
        src = inbox / src.name if src.parent == Path(".") or src.parent == Path("inbox") else (data / src)
    if not src.exists():
        # try inbox / name
        alt = inbox / Path(args.item).name
        if alt.exists():
            src = alt
        else:
            print(f"Not found: {args.item}", file=sys.stderr)
            return 2
    try:
        src.relative_to(inbox.resolve())
    except ValueError:
        print(f"{src} is not inside inbox/.", file=sys.stderr)
        return 2
    if src.name.lower() in {"readme", "readme.md", "readme.txt", ".gitkeep"}:
        print("Refusing to archive the inbox README.", file=sys.stderr)
        return 2
    side = sidecar_for(src)
    if side and side.exists() and not args.with_sidecar:
        print(
            f"Refusing to archive {src.name}: unresolved sidecar {side.name} is still present. "
            "Resolve the item (or pass --with-sidecar if you are recording it as unresolved in the archive).",
            file=sys.stderr,
        )
        return 2
    day = args.date or date.today().isoformat()
    slug = args.slug or safe_slug(src.name)
    ext = src.suffix
    dest = sources / f"{day}-{slug}{ext}"
    n = 2
    while dest.exists():
        dest = sources / f"{day}-{slug}-{n}{ext}"
        n += 1
    shutil.move(str(src), str(dest))
    rel = dest.relative_to(data).as_posix()
    print(rel)
    if side and side.exists() and args.with_sidecar:
        side_dest = sources / (dest.name + ".unresolved.txt")
        shutil.move(str(side), str(side_dest))
        print(side_dest.relative_to(data).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
