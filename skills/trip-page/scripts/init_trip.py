#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a trip data folder tree with valid skeleton JSON files.

Prefer an onboarding answers file:  python3 init_trip.py --from answers.json --out ./my-trip
Command-line flags still work, and override matching keys from --from.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def slug(text: str, fallback: str = "item") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


def loc_name(text: str, language: str) -> dict:
    """A localized name in the trip language, with an English fallback when different."""
    text = (text or "").strip() or "Destination"
    out = {language: text}
    if language != "en":
        out["en"] = text
    return out


def parse_dests(raw: str, countries: list[str]):
    """lisbon:portugal,sintra:portugal  — or just lisbon,sintra (first country)."""
    out = []
    default = countries[0] if countries else "country"
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            did, cid = part.split(":", 1)
        else:
            did, cid = part, default
        out.append({
            "id": did.strip().lower().replace(" ", "-"),
            "country": cid.strip().lower().replace(" ", "-"),
            "name": did.strip().replace("-", " ").title(),
            "optional": False,
            "certainty": "sure",
        })
    return out


def parse_travelers_flag(raw: str) -> list:
    names = [n.strip() for n in (raw or "").split(",") if n.strip()]
    if not names:
        names = ["Traveler"]
    return [{"name": n, "dietary": []} for n in names]


def _as_list(val):
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return val
    return [val]


def traveler_from_answer(t, index: int) -> dict:
    if isinstance(t, str):
        t = {"name": t}
    name = (t.get("name") or t.get("booking_name") or f"Traveler {index + 1}").strip()
    age = t.get("age")
    child = t.get("child")
    if child is None and isinstance(age, int) and age < 18:
        child = True
    out = {
        "name": name,
        "dietary": _as_list(t.get("dietary")),
    }
    if t.get("role"):
        out["role"] = t["role"]
    if t.get("passport"):
        out["passport"] = t["passport"]
    if t.get("booking_name"):
        out["booking_name"] = t["booking_name"]
    if age is not None and age != "":
        out["age"] = int(age)
    if child is not None:
        out["child"] = bool(child)
    for key in ("allergies",):
        if t.get(key) not in (None, "", []):
            out[key] = t[key] if not isinstance(t[key], str) else [t[key]]
    for key in ("accessibility", "medical", "gear"):
        if t.get(key):
            out[key] = t[key]
    return out


def dest_from_answer(d, default_country: str, language: str) -> dict:
    if isinstance(d, str):
        d = {"name": d, "id": slug(d)}
    name = d.get("name") or d.get("id") or "destination"
    did = slug(d.get("id") or name)
    cid = slug(d.get("country") or default_country or "country")
    sure = d.get("sure")
    certainty = d.get("certainty")
    if certainty not in ("sure", "open"):
        if sure is False or d.get("open") is True:
            certainty = "open"
        else:
            certainty = "sure"
    optional = d.get("optional")
    if optional is None:
        optional = certainty == "open"
    out = {
        "id": did,
        "country": cid,
        "name": d["name"] if isinstance(d.get("name"), dict) else loc_name(str(name).replace("-", " ").title() if name == did else str(name), language),
        "optional": bool(optional),
        "certainty": certainty,
        "icon": d.get("icon") or "ph-map-pin",
        "coords": d.get("coords") or {"lat": 0, "lng": 0, "exact": False},
    }
    if d.get("dates") and d["dates"].get("start") and d["dates"].get("end"):
        out["dates"] = {
            "start": d["dates"]["start"],
            "end": d["dates"]["end"],
        }
        if d["dates"].get("flexible") is not None:
            out["dates"]["flexible"] = bool(d["dates"]["flexible"])
        try:
            out["nights"] = (date.fromisoformat(d["dates"]["end"]) - date.fromisoformat(d["dates"]["start"])).days
        except ValueError:
            out["nights"] = d.get("nights")
    elif d.get("nights") is not None:
        out["nights"] = d["nights"]
    if d.get("nights_min") is not None:
        out["nights_min"] = d["nights_min"]
    if d.get("nights_max") is not None:
        out["nights_max"] = d["nights_max"]
    return out


def load_answers(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"{path} must be a JSON object")
    return raw


def merge_cfg(answers: dict, args) -> dict:
    """Build a normalized config. Flag values override answers when the flag was actually passed."""
    dates = answers.get("dates") or {}
    start = dates.get("start") or answers.get("start")
    end = dates.get("end") or answers.get("end")
    approx = dates.get("approx_nights") or dates.get("approx_length")
    flexible = dates.get("flexible")
    if start and not end and approx:
        end = (date.fromisoformat(start) + timedelta(days=int(approx))).isoformat()
    if getattr(args, "start", None):
        start = args.start
    if getattr(args, "end", None):
        end = args.end

    name = answers.get("title") or answers.get("name")
    if args.name:
        name = args.name

    lang = answers.get("language") or "en"
    if args.language_explicit:
        lang = args.language
    text_dir = answers.get("dir") or answers.get("text_dir") or "ltr"
    if args.dir_explicit:
        text_dir = args.text_dir
    currency = answers.get("currency") or answers.get("display_currency") or "USD"
    if args.currency_explicit:
        currency = args.currency
    home_tz = answers.get("home_tz") or "UTC"
    if args.tz_explicit:
        home_tz = args.home_tz

    dests_raw = answers.get("destinations") or []
    countries_raw = answers.get("countries")
    if args.destinations:
        countries_flag = []
        if args.countries:
            countries_flag = [c.strip().lower().replace(" ", "-") for c in args.countries.split(",") if c.strip()]
        elif countries_raw:
            countries_flag = [slug(c) if isinstance(c, str) else slug(c.get("id") or c.get("name")) for c in _as_list(countries_raw)]
        dests_raw = parse_dests(args.destinations, countries_flag)
    if args.countries:
        countries_raw = [c.strip() for c in args.countries.split(",") if c.strip()]

    travelers_raw = answers.get("travelers") or []
    if args.travelers_explicit:
        travelers_raw = parse_travelers_flag(args.travelers)

    departure_city = answers.get("departure_city") or answers.get("departure")
    home_airport = answers.get("departure_airport") or answers.get("home_airport") or ""
    if getattr(args, "home_airport", None):
        home_airport = args.home_airport

    out = Path(args.out) if args.out else (Path(answers["out"]) if answers.get("out") else None)

    return {
        "title": name,
        "start": start,
        "end": end,
        "approx_nights": approx,
        "flexible": flexible,
        "dates_note": dates.get("note"),
        "language": lang,
        "dir": text_dir,
        "currency": currency,
        "home_tz": home_tz,
        "departure_city": departure_city,
        "home_airport": home_airport,
        "countries_raw": countries_raw,
        "destinations_raw": dests_raw,
        "travelers_raw": travelers_raw,
        "trip_type": answers.get("trip_type") or answers.get("type"),
        "budget_plan": answers.get("budget_plan") or answers.get("budget"),
        "preferences": answers.get("preferences"),
        "already_booked": answers.get("already_booked") or [],
        "already_booked_notes": answers.get("already_booked_notes") or answers.get("booked_notes"),
        "entry_checks": answers.get("entry_checks"),
        "dietary_note": answers.get("dietary_note") or "",
        "subtitle": answers.get("subtitle") or "",
        "lede": answers.get("lede") or "",
        "id": answers.get("id"),
        "storage_key": answers.get("storage_key"),
        "locale": answers.get("locale"),
        "out": out,
    }


def normalize_budget(raw, fallback_currency: str):
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        raw = {"total": raw}
    if isinstance(raw, str):
        raw = {"level": raw} if raw in ("budget", "mid", "luxury") else {"notes": raw}
    level = raw.get("level")
    if level not in ("budget", "mid", "luxury", None):
        # keep as notes rather than failing
        notes = " ".join(x for x in (raw.get("notes"), f"level: {level}" if level else None) if x)
        level = None
    else:
        notes = raw.get("notes")
    out = {
        "total": raw.get("total"),
        "level": level,
        "currency": (raw.get("currency") or fallback_currency),
        "notes": notes,
    }
    # drop all-null
    if out["total"] is None and out["level"] is None and not out["notes"]:
        if out["currency"] == fallback_currency:
            return None
    return out


def normalize_preferences(raw):
    if not raw:
        return None
    if isinstance(raw, str):
        return {"notes": raw}
    pace = raw.get("pace")
    if isinstance(pace, str):
        pace = {"style": pace}
    lodging = raw.get("lodging")
    if isinstance(lodging, str):
        lodging = {"types": [lodging]}
    elif isinstance(lodging, list):
        lodging = {"types": lodging}
    transport = raw.get("transport")
    if isinstance(transport, str):
        transport = {"notes": transport}
    out = {}
    if raw.get("priorities"):
        out["priorities"] = list(raw["priorities"])
    if pace:
        out["pace"] = pace
    if lodging:
        out["lodging"] = lodging
    if transport:
        out["transport"] = transport
    for k in ("accessibility", "medical", "gear", "notes"):
        if raw.get(k):
            out[k] = raw[k]
    return out or None


def booking_type(kind: str) -> str:
    k = (kind or "other").lower().replace(" ", "_")
    alias = {
        "stay": "hotel", "hotel": "hotel", "lodging": "hotel", "accommodation": "hotel",
        "flight": "flight", "flights": "flight", "air": "flight",
        "train": "train", "ferry": "ferry", "bus": "bus", "car": "car", "rental_car": "car",
        "activity": "activity", "insurance": "insurance",
    }
    return alias.get(k, "other") if k in alias or k == "other" else "other"


def write_inbox_docs(out: Path):
    docs = out / "docs"
    docs.mkdir()
    (docs / "README.md").write_text(
        "# Documents\n\n"
        "Confirmation PDFs, insurance, and other personal files live outside this folder\n"
        "(for example in Google Drive). The trip page only **links** to them\n"
        "(a Drive URL or a mailbox search). Do not put card numbers, passport numbers,\n"
        "or other secrets in the JSON data, and do not commit personal documents to a\n"
        "public repository.\n",
        encoding="utf-8",
    )
    (out / "assets").mkdir(exist_ok=True)
    inbox = out / "inbox"
    inbox.mkdir()
    (inbox / "README.md").write_text(
        "# Inbox\n\n"
        "Drop links, screenshots, saved posts, or short `.txt` / `.md` notes here.\n"
        "A short text file may contain several links.\n\n"
        "When the trip is next updated, each item is read, identified, checked "
        "(still open, current hours and prices, recent reviews, dietary fit, a map link, "
        "and a check for duplicates) and written into the right destination file — "
        "or into `inbox_items.json` if the destination or category is unclear.\n\n"
        "Processed files are **moved** to `sources/` (they are not deleted) and the "
        "archive path is stored on the JSON entry as `source`. The inbox is then empty "
        "apart from this README.\n\n"
        "If an item cannot be identified confidently, it stays here with a sidecar "
        "file named `<original>.unresolved.txt` that says what is missing.\n\n"
        "Video links (TikTok, Instagram Reels and similar) often only expose a title "
        "or caption. A screenshot of the place name, or a one-line note, helps a lot.\n\n"
        "Booking confirmations can also be dropped here during onboarding; the model "
        "will turn them into bookings.json rows and (for stays) destination stay fields.\n",
        encoding="utf-8",
    )
    sources = out / "sources"
    sources.mkdir()
    (sources / "README.md").write_text(
        "# Sources archive\n\n"
        "Original inbox files land here after they have been recorded in the trip data.\n"
        "The matching JSON entry's `source` field points at the file in this folder.\n"
        "Do not put secrets or card numbers in files you drop in the inbox.\n",
        encoding="utf-8",
    )
    (out / "inbox_items.json").write_text(dumps({"items": []}), encoding="utf-8")


def create_trip(cfg: dict) -> Path:
    if not cfg.get("title"):
        raise SystemExit("A trip title is required (--name or answers.title).")
    if not cfg.get("start") or not cfg.get("end"):
        raise SystemExit(
            "Start and end dates are required (--start/--end or answers.dates). "
            "If dates are flexible, pick a provisional window and set dates.flexible, "
            "and/or set dates.approx_nights with a provisional start."
        )
    start = date.fromisoformat(cfg["start"])
    end = date.fromisoformat(cfg["end"])
    if end < start:
        raise SystemExit("end is before start")
    lang = cfg["language"] or "en"
    text_dir = cfg["dir"] if cfg["dir"] in ("rtl", "ltr") else "ltr"
    currency = (cfg["currency"] or "USD").upper()

    dests_raw = cfg.get("destinations_raw") or []
    if not dests_raw:
        raise SystemExit("At least one destination is required (--destinations or answers.destinations).")

    countries_raw = cfg.get("countries_raw")
    countries = []
    if countries_raw:
        for c in _as_list(countries_raw):
            if isinstance(c, str):
                countries.append(slug(c))
            elif isinstance(c, dict):
                countries.append(slug(c.get("id") or c.get("name")))
    default_country = countries[0] if countries else "country"

    dest_list = []
    for d in dests_raw:
        dest_list.append(dest_from_answer(d, default_country, lang) if not (
            isinstance(d, dict) and "country" in d and "id" in d and "name" in d and isinstance(d.get("name"), dict) and "dates" in d
        ) else d if "certainty" in d or True else d)
    # dest_from_answer always — cleaner:
    dest_list = [dest_from_answer(d, default_country, lang) for d in dests_raw]

    for d in dest_list:
        if d["country"] not in countries:
            countries.append(d["country"])
    if not countries:
        raise SystemExit("Could not determine countries. Pass --countries or set country on each destination.")

    out = Path(cfg["out"])
    if out is None:
        raise SystemExit("--out is required (the folder to create).")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} already exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)

    travelers_raw = cfg.get("travelers_raw") or []
    if not travelers_raw:
        travelers = [{"name": "Traveler", "dietary": []}]
    else:
        travelers = [traveler_from_answer(t, i) for i, t in enumerate(travelers_raw)]

    # Assign dates across dests that do not already have them.
    need = [d for d in dest_list if "dates" not in d]
    have_nights = sum((d.get("nights") or 0) for d in dest_list if "dates" in d)
    total_nights = (end - start).days
    remaining = max(total_nights - have_nights, 0)
    # Walk the whole list in order, filling gaps so the tree is contiguous.
    cursor = start
    n_need = len(need) or 1
    # Precompute nights for those without dates
    base = remaining // len(need) if need else 0
    rem = remaining % len(need) if need else 0
    ni = 0
    for i, d in enumerate(dest_list):
        if "dates" in d:
            # If there's a hole before this dest, it's left as-is (validate will flag date gaps).
            cursor = date.fromisoformat(d["dates"]["end"])
            continue
        nights = d.get("nights")
        if nights is None:
            nights = base + (1 if ni < rem else 0)
            if i == len(dest_list) - 1 or (ni == len(need) - 1):
                nights = (end - cursor).days
            ni += 1
        d_end = cursor + timedelta(days=max(int(nights), 0))
        if i == len(dest_list) - 1:
            d_end = end
        d["dates"] = {"start": cursor.isoformat(), "end": d_end.isoformat()}
        if cfg.get("flexible"):
            d["dates"]["flexible"] = True
        d["nights"] = (d_end - cursor).days
        cursor = d_end

    budget_plan = normalize_budget(cfg.get("budget_plan"), currency)
    preferences = normalize_preferences(cfg.get("preferences"))
    trip_id = cfg.get("id") or slug(cfg["title"])
    storage_key = cfg.get("storage_key") or trip_id

    trip = {
        "id": trip_id,
        "storage_key": storage_key,
        "title": cfg["title"],
        "subtitle": cfg.get("subtitle") or "",
        "tag": cfg.get("trip_type") or "",
        "kicker": cfg["title"],
        "headline": cfg["title"],
        "lede": cfg.get("lede") or "",
        "brand": cfg["title"],
        "footer": "",
        "dietary_note": cfg.get("dietary_note") or "",
        "dates": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "departure_at": f"{start.isoformat()}T12:00:00+00:00",
        "return_at": f"{end.isoformat()}T12:00:00+00:00",
        "departure_city": cfg.get("departure_city") or "",
        "home_airport": cfg.get("home_airport") or "",
        "home_tz": cfg.get("home_tz") or "UTC",
        "travelers": travelers,
        "currency": currency,
        "fx": {
            "date": date.today().isoformat(),
            "label": "estimated conversion",
            "home": currency,
            "rates_to_home": {currency: 1},
            "cross_rates": {},
            "sources": {},
        },
        "language": lang,
        "dir": text_dir,
        "destinations": dest_list,
        "kpis": [],
        "nav": [
            {"href": "#overview", "label": "Overview", "group": "start"},
            {"href": "#map", "label": "Map"},
            {"href": "#budget", "label": "Budget"},
            {"href": "#tasks", "label": "Tasks"},
        ],
        "shared_docs": {"headline": "", "lede": "", "items": []},
        "shared_packing": {"headline": "", "lede": "", "items": [], "note": ""},
        "overview_notes": [],
        "map": {
            "headline": "",
            "lede": "",
            "tile_url": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            "attribution": "&copy; OpenStreetMap, OpenStreetMap.de",
            "fallback_svg": "assets/map-fallback.html",
        },
        "nights_chart_caption": "",
        "status_legend": [],
    }
    if cfg.get("locale"):
        trip["locale"] = cfg["locale"]
    if cfg.get("flexible") is not None:
        trip["dates"]["flexible"] = bool(cfg["flexible"])
    if cfg.get("approx_nights") is not None:
        trip["dates"]["approx_nights"] = int(cfg["approx_nights"])
    if cfg.get("dates_note"):
        trip["dates"]["note"] = cfg["dates_note"]
    if cfg.get("trip_type"):
        trip["trip_type"] = cfg["trip_type"]
    if budget_plan:
        trip["budget_plan"] = budget_plan
    if preferences:
        trip["preferences"] = preferences
    if cfg.get("already_booked_notes"):
        trip["already_booked_notes"] = cfg["already_booked_notes"]
    # Stub entry_checks so the model has a place to write automatic research.
    trip["entry_checks"] = cfg.get("entry_checks") or {
        "visa": None,
        "passport_validity": None,
        "insurance": None,
        "power_adapters": None,
        "problem_dates": [],
        "sources": [],
        "as_of": None,
        "notes": "Fill after researching visa/entry rules, passport validity, insurance, power adapters, and problem dates (holidays, high season) for this party's passports and destinations.",
    }

    open_dests = [d["id"] for d in dest_list if d.get("certainty") == "open" or d.get("optional")]
    if open_dests:
        trip["overview_notes"].append(
            "Destinations still open (dates and lodging are provisional): " + ", ".join(open_dests) + "."
        )

    bookings = []
    transfers = []
    stay_bookings = {}  # dest_id -> booking
    already = cfg.get("already_booked") or []
    used_ids = set()
    for i, item in enumerate(already):
        if isinstance(item, str):
            item = {"title": item, "type": "other", "status": "booked"}
        btype = booking_type(item.get("type") or item.get("kind") or "other")
        bid = slug(item.get("id") or item.get("title") or f"{btype}-{i+1}", fallback=f"{btype}-{i+1}")
        if bid in used_ids:
            bid = f"{bid}-{i+1}"
        used_ids.add(bid)
        status = item.get("status") or "booked"
        if status not in ("booked", "open", "optional"):
            status = "booked"
        rec = {
            "id": bid,
            "type": btype,
            "title": item.get("title") or bid,
            "status": status,
            "price": None,
            "notes": item.get("notes") or None,
            "destination_id": item.get("destination_id") or None,
            "confirmation_code": None,
            "confirmation_link": None,
        }
        if item.get("carrier"):
            rec["carrier"] = item["carrier"]
        if item.get("number"):
            rec["number"] = item["number"]
        if item.get("price"):
            rec["price"] = item["price"]
        elif item.get("amount") is not None:
            rec["price"] = {
                "amount": item["amount"],
                "currency": item.get("currency") or currency,
                "note": item.get("price_note"),
            }
        # Never copy a confirmation code from answers into a file that may be
        # committed; leave a note pointing at inbox/ instead.
        if item.get("confirmation_code"):
            note = rec.get("notes") or ""
            rec["notes"] = (note + " " if note else "") + "Confirmation was provided; store the code outside the public repo (or in inbox/, then a private bookings copy)."
        bookings.append(rec)
        if btype == "hotel" and rec.get("destination_id"):
            stay_bookings[rec["destination_id"]] = rec
        # Optional transfer stub when from/to are given
        if btype in ("flight", "train", "ferry", "bus", "car") and (item.get("from") or item.get("from_id")):
            tid = slug(item.get("transfer_id") or f"{btype}-{bid}")
            transfers.append({
                "id": tid,
                "from": item.get("from") or item.get("from_id") or "",
                "to": item.get("to") or item.get("to_id") or "",
                "from_id": item.get("from_id"),
                "to_id": item.get("to_id"),
                "depart_at": item.get("depart_at"),
                "arrive_at": item.get("arrive_at"),
                "mode": "flight" if btype == "flight" else ("car" if btype == "car" else btype),
                "icon": "ph-airplane-tilt" if btype == "flight" else "ph-path",
                "carrier": item.get("carrier"),
                "number": item.get("number"),
                "route_label": item.get("route_label") or rec["title"],
                "booking_id": bid if status == "booked" else None,
                "optional": status == "optional",
                "boundary": bool(item.get("boundary", btype == "flight")),
                "tips": [],
                "details_blocks": [],
                "notes": item.get("transfer_notes"),
            })

    (out / "trip.json").write_text(dumps(trip), encoding="utf-8")
    (out / "bookings.json").write_text(dumps({"bookings": bookings}), encoding="utf-8")
    (out / "transfers.json").write_text(dumps({"transfers": transfers}), encoding="utf-8")
    (out / "estimates.json").write_text(dumps({"estimates": []}), encoding="utf-8")
    (out / "tasks.json").write_text(dumps({"headline": "", "lede": "", "done": [], "open": []}), encoding="utf-8")
    (out / "decisions.json").write_text(dumps({"decisions": []}), encoding="utf-8")
    (out / "today.json").write_text(dumps({"segments": []}), encoding="utf-8")

    country_meta = {}
    if isinstance(cfg.get("countries_raw"), list):
        for c in cfg["countries_raw"]:
            if isinstance(c, dict):
                country_meta[slug(c.get("id") or c.get("name"))] = c

    cdir = out / "countries"
    cdir.mkdir()
    for cid in countries:
        meta = country_meta.get(cid) or {}
        cname = meta.get("name")
        (cdir / f"{cid}.json").write_text(dumps({
            "id": cid,
            "name": cname if isinstance(cname, dict) else loc_name(str(cname or cid.replace("-", " ").title()), lang),
            "badge": meta.get("badge") or cid,
            "timezone": meta.get("timezone") or "",
            "utc_offset": meta.get("utc_offset") or "",
            "hours_ahead_of_home": meta.get("hours_ahead_of_home"),
            "currency": meta.get("currency") or "",
            "practical_headline": "",
            "practical_lede": "",
            "practical": [],
            "emergency": [],
            "embassy": {
                "name": "", "url": "", "address": "", "phone": "",
                "phone_emergency": "", "email": "", "source": "",
            },
            "phrases": {
                "headline": "",
                "intro": [],
                "groups": [],
            },
            "entry_docs": {
                "headline": "Entry and practical checks",
                "lede": "Fill visa, passport validity, and other entry rules for this country's destinations. The model researches these from the party's passports; do not invent.",
                "items": [],
            },
            "packing": {
                "headline": "",
                "lede": "",
                "callout": "Include the power adapter type for this country once researched.",
                "items": [],
            },
            "climate": "",
            "transport_notes": "",
            "act_label": "",
            "timeline_headline": "",
            "timeline_lede": "",
            "journal_act": "",
            "journal_headline": "",
            "journal_lede": "",
        }), encoding="utf-8")

    empty_places = dumps({"group_heading": "", "places": []})
    for d in dest_list:
        dd = out / "destinations" / d["id"]
        dd.mkdir(parents=True)
        booked = stay_bookings.get(d["id"])
        (dd / "info.json").write_text(dumps({
            "id": d["id"],
            "stay_booking_id": booked["id"] if booked else None,
            "stay_label": booked["title"] if booked else None,
            "stay_status": "booked" if booked and booked["status"] == "booked" else ("open" if booked else "open"),
            "summary_transfer": None,
            "local_address": None,
            "local_address_latin": None,
            "phone": None,
            "nav_url": None,
            "checkin": None,
            "checkout": None,
            "arrival": {"title": "", "status": "open", "items": []},
            "weather": {"title": "", "source": "", "items": []},
            "food_notes": {"title": "", "source": "", "items": []},
            "season_note": None,
            "notes": [],
            "blocks": [],
            "recs_intro": "",
        }), encoding="utf-8")
        (dd / "days.json").write_text(dumps({"days": []}), encoding="utf-8")
        for fname in ("food.json", "sights.json", "shopping.json", "daytrips.json"):
            (dd / fname).write_text(empty_places, encoding="utf-8")

    write_inbox_docs(out)

    print(f"Created trip skeleton at {out}")
    print(f"  {len(countries)} countries, {len(dest_list)} destinations, {total_nights} nights.")
    kids = [t["name"] for t in travelers if t.get("child")]
    diet = [t["name"] for t in travelers if t.get("dietary")]
    print(f"  {len(travelers)} traveler(s)" + (f", children: {', '.join(kids)}" if kids else "") + ".")
    if diet:
        print("  Dietary restrictions were recorded per traveler; diet_fit is checked against their union.")
    else:
        print("  Travelers start with empty dietary lists — fill travelers[].dietary as needed.")
    if cfg.get("flexible"):
        print("  Dates are marked flexible — treat the window as provisional.")
    if bookings:
        print(f"  {len(bookings)} booking stub(s) from already_booked; confirmation codes were not copied.")
    print("  Drop contributed links, screenshots, and confirmations in inbox/.")
    print("  Next: research entry_checks (visa, passport, insurance, adapters, problem dates),")
    print("  then run validate_trip.py (gaps + BOOK FIRST) and fill data in stages.")
    return out


def build_parser():
    p = argparse.ArgumentParser(
        description="Create a trip-page data folder from an onboarding answers file "
                    "or from flags. All traveler, currency, language and country values "
                    "come from the answers or flags — nothing is assumed."
    )
    p.add_argument("--from", dest="from_file", type=Path, metavar="ANSWERS.json",
                   help="Onboarding answers JSON (see references/onboarding.md and examples/sample-answers.json).")
    p.add_argument("--name", default=None, help="Trip title")
    p.add_argument("--start", default=None, help="Start date YYYY-MM-DD (provisional is fine if flexible)")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    p.add_argument("--countries", default=None,
                   help="Comma-separated country ids, e.g. portugal or france,italy")
    p.add_argument("--destinations", default=None,
                   help="Comma-separated ids, optionally id:country, e.g. lisbon:portugal,lyon:france")
    p.add_argument("--out", default=None, help="Output folder")
    p.add_argument("--language", default="en", help="Primary content language (default: en)")
    p.add_argument("--dir", dest="text_dir", default="ltr", choices=["rtl", "ltr"],
                   help="Text direction (default: ltr)")
    p.add_argument("--currency", default="USD", help="Display / home currency code (default: USD, change to suit the trip)")
    p.add_argument("--travelers", default="Traveler", help="Comma-separated traveler names")
    p.add_argument("--home-tz", default="UTC", help="Home time zone (IANA), default UTC")
    p.add_argument("--home-airport", default=None, help="Departure airport IATA code")
    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)

    # Detect which defaults were actually passed so --from is not overridden by argparse defaults.
    import sys as _sys
    argv_list = list(argv) if argv is not None else _sys.argv[1:]
    def passed(*flags):
        return any(a == f or a.startswith(f + "=") for a in argv_list for f in flags)
    args.language_explicit = passed("--language")
    args.dir_explicit = passed("--dir")
    args.currency_explicit = passed("--currency")
    args.tz_explicit = passed("--home-tz")
    args.travelers_explicit = passed("--travelers")

    answers = load_answers(args.from_file) if args.from_file else {}
    if args.from_file and not args.from_file.exists():
        raise SystemExit(f"answers file not found: {args.from_file}")
    if not args.from_file:
        # Flags-only path still requires the original required arguments.
        missing = [f for f, v in (("--name", args.name), ("--start", args.start),
                                  ("--end", args.end), ("--countries", args.countries),
                                  ("--destinations", args.destinations), ("--out", args.out)) if not v]
        if missing:
            raise SystemExit("Missing required arguments: " + ", ".join(missing)
                             + ". Or pass --from answers.json (see references/onboarding.md).")
    cfg = merge_cfg(answers, args)
    create_trip(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
