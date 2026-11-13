#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared load, schema validation, budget, and warning helpers for trip-page."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

FILE_MAP = {
    "trip.json": "trip.schema.json",
    "bookings.json": "bookings.schema.json",
    "transfers.json": "transfers.schema.json",
    "estimates.json": "estimates.schema.json",
    "tasks.json": "tasks.schema.json",
    "decisions.json": "decisions.schema.json",
    "today.json": "today.schema.json",
    "inbox_items.json": "inbox-items.schema.json",
    "info.json": "destination-info.schema.json",
    "days.json": "days.schema.json",
    "food.json": "places.schema.json",
    "sights.json": "places.schema.json",
    "shopping.json": "places.schema.json",
    "daytrips.json": "places.schema.json",
}

# Card numbers (13–19 digits, optional spaces/dashes), CVV-like near "cvv"/"cvc", IBAN-ish.
SECRET_PATTERNS = [
    ("card_number", re.compile(r"(?<!\d)(?:\d[ \-]*){13,19}(?!\d)")),
    ("cvv", re.compile(r"\b(?:cvv|cvc|cid)\s*[:#-]?\s*\d{3,4}\b", re.I)),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
    ("passport_no", re.compile(r"\bpassport\s*(?:no|number|#)\s*[:#]?\s*[A-Z0-9]{6,}\b", re.I)),
]

# Confirmation codes / short booking refs are allowed. Skip card-like matches
# that are clearly Agoda-style ids or amounts when context is "agoda" — still
# flag raw 13–19 digit runs; 10-digit Agoda ids will not match.


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _is_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except (TypeError, ValueError):
        return False


def _is_datetime(s: str) -> bool:
    if not isinstance(s, str):
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_schema(instance, schema, path="$"):
    """Minimal JSON Schema (2020-12 subset) validator. Returns a list of errors."""
    errors = []
    if schema is None:
        return errors
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
        return errors
    types = schema.get("type")
    if types is not None:
        if not isinstance(types, list):
            types = [types]
        if not _type_ok(instance, types):
            errors.append(f"{path}: expected type {types}, got {type(instance).__name__}")
            return errors
    if instance is None:
        return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if "format" in schema and isinstance(instance, str) and instance:
        fmt = schema["format"]
        if fmt == "date" and not _is_date(instance):
            errors.append(f"{path}: not a date (YYYY-MM-DD)")
        elif fmt == "date-time" and not _is_datetime(instance):
            errors.append(f"{path}: not a date-time")
        elif fmt == "uri" and not re.match(r"^[a-z][a-z0-9+.-]*:", instance, re.I):
            errors.append(f"{path}: not a URI")
        elif fmt == "email" and "@" not in instance:
            errors.append(f"{path}: not an email")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errors.append(f"{path}: shorter than minLength {schema['minLength']}")
    if "maxLength" in schema and isinstance(instance, str) and len(instance) > schema["maxLength"]:
        errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        errors.append(f"{path}: below minimum {schema['minimum']}")
    if "minItems" in schema and isinstance(instance, list) and len(instance) < schema["minItems"]:
        errors.append(f"{path}: fewer than minItems {schema['minItems']}")
    if isinstance(instance, dict) and ("properties" in schema or "required" in schema or "additionalProperties" in schema):
        props = schema.get("properties") or {}
        for req in schema.get("required") or []:
            if req not in instance:
                errors.append(f"{path}.{req}: required property missing")
        addl = schema.get("additionalProperties", True)
        for k, v in instance.items():
            if k in props:
                errors.extend(validate_schema(v, props[k], f"{path}.{k}"))
            elif addl is False:
                errors.append(f"{path}.{k}: additional property not allowed")
            elif isinstance(addl, dict):
                errors.extend(validate_schema(v, addl, f"{path}.{k}"))
    if isinstance(instance, list) and "items" in schema:
        item_s = schema["items"]
        for i, v in enumerate(instance):
            errors.extend(validate_schema(v, item_s, f"{path}[{i}]"))
    return errors


def _type_ok(instance, types):
    for t in types:
        if t == "null" and instance is None:
            return True
        if t == "object" and isinstance(instance, dict):
            return True
        if t == "array" and isinstance(instance, list):
            return True
        if t == "string" and isinstance(instance, str):
            return True
        if t == "boolean" and isinstance(instance, bool):
            return True
        if t == "integer" and isinstance(instance, int) and not isinstance(instance, bool):
            return True
        if t == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            return True
    return False


def schema_for(filename: str):
    name = FILE_MAP.get(filename)
    if not name:
        # countries/<id>.json
        if filename.endswith(".json") and "countries" in filename.replace("\\", "/"):
            name = "country.schema.json"
        else:
            return None
    return load_json(SCHEMA_DIR / name)


def walk_strings(obj, prefix="$"):
    if isinstance(obj, str):
        yield prefix, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{prefix}[{i}]")


def scan_secrets(obj, path="$"):
    """Return errors for secret-looking patterns. Skips tel: and known short codes."""
    found = []
    for p, s in walk_strings(obj, path):
        low = p.lower()
        if any(x in low for x in ("phone", "tel", "emergency", "hours", "href", "url", "maps", "maps_url", "confirmation_link", "manage_url", "checkin_url", "nav_url", "tile_url", "src")):
            continue
        if re.match(r"https?://", s):
            continue
        for kind, rx in SECRET_PATTERNS:
            if kind == "card_number":
                # Ignore runs that are part of a URL query or clearly prices with decimals.
                if "." in s and re.search(r"\d+\.\d{2}", s):
                    # check remaining chunks without decimal amounts
                    stripped = re.sub(r"\d+\.\d{2}", "", s)
                    if not rx.search(stripped):
                        continue
                # 13–19 is card territory; confirmation codes are shorter.
                m = rx.search(s)
                if m:
                    digits = re.sub(r"\D", "", m.group(0))
                    if 13 <= len(digits) <= 19:
                        found.append(f"{p}: possible {kind} ({len(digits)} digits)")
                continue
            if rx.search(s):
                found.append(f"{p}: possible {kind}")
    return found


def discover(data_dir: Path):
    """Return a dict of relative path -> Path for every trip JSON file."""
    data_dir = data_dir.resolve()
    files = {}
    for name in ("trip.json", "bookings.json", "transfers.json", "estimates.json",
                 "tasks.json", "decisions.json", "today.json", "inbox_items.json"):
        p = data_dir / name
        if p.exists():
            files[name] = p
    cdir = data_dir / "countries"
    if cdir.is_dir():
        for p in sorted(cdir.glob("*.json")):
            files[f"countries/{p.name}"] = p
    ddir = data_dir / "destinations"
    if ddir.is_dir():
        for dest in sorted(ddir.iterdir()):
            if not dest.is_dir():
                continue
            for fname in ("info.json", "days.json", "food.json", "sights.json",
                          "shopping.json", "daytrips.json"):
                p = dest / fname
                if p.exists():
                    files[f"destinations/{dest.name}/{fname}"] = p
    return files


def load_trip(data_dir: Path) -> dict:
    """Load the full trip into one nested dict."""
    data_dir = Path(data_dir)
    files = discover(data_dir)
    if "trip.json" not in files:
        raise FileNotFoundError(f"no trip.json in {data_dir}")
    out = {
        "dir": str(data_dir),
        "trip": load_json(files["trip.json"]),
        "bookings": (load_json(files["bookings.json"]) if "bookings.json" in files else {"bookings": []}),
        "transfers": (load_json(files["transfers.json"]) if "transfers.json" in files else {"transfers": []}),
        "estimates": (load_json(files["estimates.json"]) if "estimates.json" in files else {"estimates": []}),
        "tasks": load_json(files["tasks.json"]) if "tasks.json" in files else None,
        "decisions": load_json(files["decisions.json"]) if "decisions.json" in files else None,
        "today": load_json(files["today.json"]) if "today.json" in files else None,
        "inbox_items": (load_json(files["inbox_items.json"]) if "inbox_items.json" in files else {"items": []}),
        "countries": {},
        "destinations": {},
    }
    for rel, p in files.items():
        if rel.startswith("countries/"):
            out["countries"][p.stem] = load_json(p)
        elif rel.startswith("destinations/"):
            _, dest, fname = rel.split("/")
            out["destinations"].setdefault(dest, {})[fname[:-5]] = load_json(p)
    return out


def booking_by_id(data: dict, bid):
    if not bid:
        return None
    for b in data["bookings"].get("bookings") or []:
        if b.get("id") == bid:
            return b
    return None


def to_home(amount, currency, fx) -> float | None:
    if amount is None or not currency:
        return None
    rates = fx.get("rates_to_home") or {}
    if currency not in rates:
        return None
    raw = amount * rates[currency]
    home = fx.get("home")
    # Amounts already in the home currency keep cents; converted amounts are whole units.
    if home and currency != home:
        return float(round(raw))
    return round(raw, 2)


def derive_budget(data: dict) -> dict:
    """Booked total from bookings with status=booked only. Optional and open are excluded.
    Estimates stay in a separate labelled list."""
    fx = data["trip"].get("fx") or {}
    home = fx.get("home") or data["trip"].get("currency") or ""
    booked_rows = []
    open_rows = []
    optional_rows = []
    booked_home = 0.0
    for b in data["bookings"].get("bookings") or []:
        price = b.get("price") or {}
        amt = price.get("amount")
        cur = price.get("currency")
        home_amt = to_home(amt, cur, fx) if amt is not None else None
        row = {
            "id": b["id"],
            "title": b.get("title"),
            "status": b.get("status"),
            "amount": amt,
            "currency": cur,
            "home_amount": home_amt,
            "confirmation_code": b.get("confirmation_code"),
            "notes": b.get("notes"),
        }
        if b.get("status") == "booked":
            booked_rows.append(row)
            if home_amt is not None:
                booked_home += home_amt
        elif b.get("status") == "optional":
            optional_rows.append(row)
        else:
            open_rows.append(row)
    estimates = []
    for e in data["estimates"].get("estimates") or []:
        price = e.get("price") or {}
        estimates.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "label": e.get("label") or "estimate",
            "amount": price.get("amount"),
            "amount_min": price.get("amount_min"),
            "amount_max": price.get("amount_max"),
            "currency": price.get("currency"),
            "home_min": to_home(price.get("amount_min"), price.get("currency"), fx)
            if price.get("amount_min") is not None else None,
            "home_max": to_home(price.get("amount_max"), price.get("currency"), fx)
            if price.get("amount_max") is not None else None,
            "home_amount": to_home(price.get("amount"), price.get("currency"), fx)
            if price.get("amount") is not None else None,
            "notes": e.get("notes"),
            "chart_series": e.get("chart_series") or [],
        })
    return {
        "home": home,
        "fx_date": fx.get("date"),
        "fx_label": fx.get("label") or "estimated conversion",
        "booked_rows": booked_rows,
        "open_rows": open_rows,
        "optional_rows": optional_rows,
        "estimates": estimates,
        "booked_total_home": round(booked_home, 2),
    }


def iter_places(data: dict):
    for dest_id, dest in data.get("destinations", {}).items():
        for kind in ("food", "sights", "shopping", "daytrips"):
            blob = dest.get(kind)
            if not blob:
                continue
            for i, pl in enumerate(blob.get("places") or []):
                yield dest_id, kind, i, pl



def party_dietary(data):
    """Union of travelers[].dietary, preserving first-seen order. Strings or lists."""
    out, seen = [], set()
    for trav in (data.get("trip") or {}).get("travelers") or []:
        raw = trav.get("dietary")
        if not raw:
            continue
        items = [raw] if isinstance(raw, str) else list(raw)
        for x in items:
            s = (x or "").strip()
            key = s.casefold()
            if s and key not in seen:
                seen.add(key)
                out.append(s)
    return out


def place_warnings(data: dict, as_of: date | None = None, stale_months: int = 6):
    """Warn on missing url, stale/missing last_verified, missing or not_ok diet_fit."""
    as_of = as_of or date.today()
    # approximately 6 months
    threshold = as_of - timedelta(days=int(stale_months * 30.4375))
    warnings = []
    for dest_id, kind, i, pl in iter_places(data):
        loc = f"destinations/{dest_id}/{kind}.json places[{i}] ({(pl.get('name') or {}).get('en') or (pl.get('name') or {}).get('he') or pl.get('id')})"
        url = pl.get("url")
        if not url:
            warnings.append(f"{loc}: missing url")
        lv = pl.get("last_verified")
        if not lv:
            warnings.append(f"{loc}: missing last_verified")
        else:
            try:
                d = date.fromisoformat(lv)
                if d < threshold:
                    warnings.append(f"{loc}: last_verified {lv} is older than {stale_months} months (before {threshold.isoformat()})")
            except ValueError:
                warnings.append(f"{loc}: last_verified {lv!r} is not a date")
        hours = pl.get("hours")
        if not hours:
            warnings.append(f"{loc}: missing hours")
        # diet_fit is only required when the party has dietary restrictions.
        if party_dietary(data):
            df = pl.get("diet_fit")
            status = (df or {}).get("status") if isinstance(df, dict) else None
            if not df or not status:
                warnings.append(f"{loc}: diet_fit missing (party has dietary restrictions: {', '.join(party_dietary(data))})")
            elif status == "not_ok":
                note = (df or {}).get("note") or ""
                warnings.append(f"{loc}: diet_fit is not_ok" + (f" ({note})" if note else ""))
    return warnings


def cross_checks(data: dict):
    """Hard errors: booking refs, destination dates, nights, optional excluded from totals."""
    errors = []
    trip = data["trip"]
    dests = trip.get("destinations") or []
    by_id = {d["id"]: d for d in dests}
    bookings = {b["id"]: b for b in data["bookings"].get("bookings") or []}

    # booking refs on transfers
    for t in data["transfers"].get("transfers") or []:
        refs = []
        if t.get("booking_id"):
            refs.append(t["booking_id"])
        refs.extend(t.get("booking_ids") or [])
        for r in refs:
            if r not in bookings:
                errors.append(f"transfer {t.get('id')}: booking_id {r!r} does not exist")
        if t.get("from_id") and t["from_id"] not in by_id and t["from_id"] not in ("home", "tlv", "origin"):
            # from_id may be 'home' for outbound
            if t["from_id"] not in by_id:
                errors.append(f"transfer {t.get('id')}: from_id {t['from_id']!r} is not a destination")
        if t.get("to_id") and t["to_id"] not in by_id and t["to_id"] not in ("home", "tlv", "origin"):
            errors.append(f"transfer {t.get('id')}: to_id {t['to_id']!r} is not a destination")

    # stay booking refs
    for dest_id, dest in data.get("destinations", {}).items():
        info = dest.get("info") or {}
        sid = info.get("stay_booking_id")
        if sid and sid not in bookings:
            errors.append(f"destinations/{dest_id}/info.json: stay_booking_id {sid!r} does not exist")

    # dates: required (non-optional) destinations should not overlap and should
    # be contiguous (checkout day == next checkin). Flexible pairs may share a
    # window — flagged only when both are non-flexible.
    required = [d for d in dests if not d.get("optional")]
    def span(d):
        a = date.fromisoformat(d["dates"]["start"])
        b = date.fromisoformat(d["dates"]["end"])
        return a, b

    trip_start = date.fromisoformat(trip["dates"]["start"])
    trip_end = date.fromisoformat(trip["dates"]["end"])
    if trip_end < trip_start:
        errors.append("trip dates: end is before start")

    for d in dests:
        a, b = span(d)
        if b < a:
            errors.append(f"destination {d['id']}: end is before start")
        nights = d.get("nights")
        computed = (b - a).days
        if nights is not None and not d["dates"].get("flexible") and nights != computed:
            errors.append(
                f"destination {d['id']}: nights={nights} but {a}–{b} is {computed} night(s)"
            )
        if d.get("nights_min") is not None and d.get("nights_max") is not None:
            if d["nights_min"] > d["nights_max"]:
                errors.append(f"destination {d['id']}: nights_min > nights_max")

    # overlap among required non-flexible dests: adjacent sharing a date is OK.
    # A gap is OK when optional destinations fill it (checkout = next checkin).
    optional = [d for d in dests if d.get("optional")]
    ordered = sorted(required, key=lambda d: span(d)[0])
    for i in range(len(ordered) - 1):
        a1, b1 = span(ordered[i])
        a2, b2 = span(ordered[i + 1])
        flex = ordered[i]["dates"].get("flexible") or ordered[i + 1]["dates"].get("flexible")
        if flex:
            continue
        if a2 < b1:
            errors.append(
                f"destinations {ordered[i]['id']} and {ordered[i+1]['id']} overlap ({a1}–{b1} vs {a2}–{b2})"
            )
        elif a2 > b1:
            fillers = [d for d in optional if span(d)[0] >= b1 and span(d)[1] <= a2]
            filled = b1
            for d in sorted(fillers, key=lambda d: span(d)[0]):
                fa, fb = span(d)
                if fa > filled:
                    break
                filled = max(filled, fb)
            if filled < a2:
                errors.append(
                    f"destinations {ordered[i]['id']} and {ordered[i+1]['id']} are not contiguous "
                    f"(gap {b1} → {a2})"
                )

    # optional items must not be in booked total — structural: status optional
    for b in bookings.values():
        if b.get("status") == "optional" and (b.get("price") or {}).get("amount"):
            # not an error, just a reminder stored as warning by caller via budget
            pass

    return errors



INBOX_IGNORE = {".gitkeep", ".ds_store", "readme", "readme.md", "readme.txt"}
RESERVE_KINDS = ("food", "sights", "daytrips")


def inbox_ignore(name: str) -> bool:
    return name.lower() in INBOX_IGNORE or name.startswith(".")


def list_inbox(data_dir: Path):
    """Return (pending, unresolved, missing_folder). Sidecars are unresolved; their source is pending too if present."""
    inbox = Path(data_dir) / "inbox"
    if not inbox.is_dir():
        return [], [], True
    pending, unresolved = [], []
    for p in sorted(inbox.iterdir()):
        if inbox_ignore(p.name):
            continue
        if p.name.endswith(".unresolved.txt"):
            unresolved.append(p)
        elif p.is_file() or p.is_dir():
            pending.append(p)
    return pending, unresolved, False


def sidecar_for(path: Path) -> Path | None:
    a = path.with_name(path.name + ".unresolved.txt")
    b = path.with_name(path.stem + ".unresolved.txt")
    if a.exists():
        return a
    if b.exists() and b != path:
        return b
    return None


def inbox_warnings(data_dir: Path):
    """Warn when inbox/ is missing or not empty (anything other than a README / .gitkeep)."""
    pending, unresolved, missing = list_inbox(data_dir)
    warnings = []
    if missing:
        warnings.append("inbox/ folder is missing — create it (init_trip.py does this) so contributed links and files have a drop box")
        return warnings
    for p in pending:
        side = sidecar_for(p)
        if side:
            hint = ""
            try:
                hint = " — " + side.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0][:160]
            except OSError:
                pass
            warnings.append(f"inbox/{p.name} is still unresolved{hint}")
        else:
            warnings.append(f"inbox/{p.name} is waiting to be ingested")
    for u in unresolved:
        # skip if we already mentioned it as a sidecar of a pending file
        stem_base = u.name[: -len(".unresolved.txt")]
        if any(p.name == stem_base or p.stem == Path(stem_base).stem or p.name == stem_base for p in pending):
            continue
        warnings.append(f"inbox/{u.name} is an unresolved note with no matching inbox item")
    return warnings


def reservation_is_booked(res, data) -> bool:
    if not res:
        return False
    b = res.get("booked")
    if b is True:
        return True
    if isinstance(b, str) and b.strip():
        bk = booking_by_id(data, b.strip())
        return bool(bk and bk.get("status") == "booked")
    return False


def parse_lead_days(text) -> int | None:
    if not text or not isinstance(text, str):
        return None
    m = re.search(r"(\d+)\s*(day|days|week|weeks|month|months)\b", text, re.I)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return n * 30
    return n


def effective_book_by(pl) -> date | None:
    res = pl.get("reservation") or {}
    raw = res.get("book_by")
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    planned = pl.get("planned_day")
    lead = parse_lead_days(res.get("lead_time") or "")
    if planned and lead is not None:
        try:
            return date.fromisoformat(planned) - timedelta(days=lead)
        except ValueError:
            return None
    return None


def reservation_warnings(data: dict, as_of: date | None = None, book_by_days: int = 7):
    """Warn on missing / unknown reservation research, required-and-unbooked, and upcoming book_by dates."""
    as_of = as_of or date.today()
    horizon = as_of + timedelta(days=int(book_by_days))
    warnings = []
    for dest_id, kind, i, pl in iter_places(data):
        if kind not in RESERVE_KINDS:
            continue
        loc = f"destinations/{dest_id}/{kind}.json places[{i}] ({(pl.get('name') or {}).get('en') or (pl.get('name') or {}).get('he') or pl.get('id')})"
        res = pl.get("reservation")
        if not res or not res.get("need"):
            warnings.append(f"{loc}: reservation not yet researched")
            continue
        need = res.get("need")
        if need == "unknown":
            warnings.append(f"{loc}: reservation.need is unknown (not yet researched)")
        booked = reservation_is_booked(res, data)
        if need == "required" and not booked:
            warnings.append(f"{loc}: reservation is required but not booked")
        by = effective_book_by(pl)
        if by and not booked and need in ("required", "recommended", "unknown"):
            if by < as_of:
                warnings.append(f"{loc}: book_by {by.isoformat()} has passed and the place is not booked")
            elif by <= horizon:
                warnings.append(f"{loc}: book_by {by.isoformat()} is within {book_by_days} days and the place is not booked")
        if res.get("book_by"):
            try:
                date.fromisoformat(res["book_by"])
            except ValueError:
                warnings.append(f"{loc}: reservation.book_by {res['book_by']!r} is not a date")
        bid = res.get("booked")
        if isinstance(bid, str) and bid.strip() and not booking_by_id(data, bid.strip()):
            warnings.append(f"{loc}: reservation.booked {bid!r} is not a booking id")
    return warnings



def stay_is_booked(data, dest) -> bool:
    files = (data.get("destinations") or {}).get(dest["id"]) or {}
    info = files.get("info") or {}
    if info.get("stay_status") == "booked":
        return True
    sid = info.get("stay_booking_id")
    if sid:
        b = booking_by_id(data, sid)
        return bool(b and b.get("status") == "booked")
    return False


def transfer_is_booked(data, x) -> bool:
    if x.get("optional"):
        return False
    bid = x.get("booking_id")
    if not bid:
        return False
    b = booking_by_id(data, bid)
    return bool(b and b.get("status") == "booked")


def _xfer_from(x) -> str:
    return (x.get("from_id") or x.get("from") or "").strip()


def _xfer_to(x) -> str:
    return (x.get("to_id") or x.get("to") or "").strip()


def transfer_connects(x, a_id, b_id) -> bool:
    return _xfer_from(x) == a_id and _xfer_to(x) == b_id


def gap_warnings(data: dict):
    """Nights without lodging, unbooked transfers, and missing legs between stops."""
    warnings = []
    dests = data["trip"].get("destinations") or []
    xfers = (data.get("transfers") or {}).get("transfers") or []
    for d in dests:
        if d.get("optional"):
            continue
        if not stay_is_booked(data, d):
            nights = d.get("nights")
            dates = d.get("dates") or {}
            window = f"{dates.get('start') or '?'}–{dates.get('end') or '?'}"
            label = (d.get("name") or {})
            name = (label.get("en") if isinstance(label, dict) else label) or d["id"]
            warnings.append(
                f"gap: {d['id']} ({name}) has no booked stay for {window}"
                + (f" ({nights} nights)" if nights else "")
            )
    for x in xfers:
        if x.get("optional"):
            continue
        if not transfer_is_booked(data, x):
            warnings.append(
                f"gap: transfer {x.get('id')} ({x.get('route_label') or x.get('from','')} → {x.get('to','')}) is not booked"
            )

    ids = [d["id"] for d in dests]
    required = [d["id"] for d in dests if not d.get("optional")]

    def connected(a, b) -> bool:
        return any(transfer_connects(x, a, b) for x in xfers)

    for i, a in enumerate(required):
        if i + 1 >= len(required):
            break
        b = required[i + 1]
        if connected(a, b):
            continue
        # Allow a path through optional stops that sit between a and b.
        try:
            ia, ib = ids.index(a), ids.index(b)
        except ValueError:
            ia = ib = -1
        path_ok = False
        if 0 <= ia < ib:
            path_ok = all(connected(ids[k], ids[k + 1]) for k in range(ia, ib))
        if not path_ok:
            warnings.append(f"gap: no transfer recorded between {a} and {b}")

    trip = data["trip"]
    if (trip.get("home_airport") or trip.get("departure_city")) and required:
        first, last = required[0], required[-1]
        has_out = any(
            _xfer_to(x) == first and (
                _xfer_from(x) in ("home", "origin", "")
                or x.get("boundary")
                or _xfer_from(x) == (trip.get("home_airport") or "")
            )
            for x in xfers
        )
        has_ret = any(
            _xfer_from(x) == last and (
                _xfer_to(x) in ("home", "origin", "")
                or x.get("boundary")
                or _xfer_to(x) == (trip.get("home_airport") or "")
            )
            for x in xfers
        )
        if not has_out:
            warnings.append(f"gap: no outbound transfer recorded from home to {first}")
        if not has_ret:
            warnings.append(f"gap: no return transfer recorded from {last} to home")
    return warnings


def book_first(data: dict, as_of: date | None = None, book_by_days: int = 7) -> list:
    """Urgency-ordered list of things to book. urgency 0 = overdue, then soon, required, stays, transfers, recommended."""
    if not data:
        return []
    as_of = as_of or date.today()
    horizon = as_of + timedelta(days=int(book_by_days))
    items = []

    def add(urgency, title, reason, by=None, kind="", ident=""):
        items.append({
            "urgency": urgency,
            "by": by.isoformat() if isinstance(by, date) else by,
            "kind": kind,
            "id": ident,
            "title": title,
            "reason": reason,
        })

    # Reservations with a book_by (food/sights/daytrips)
    for dest_id, kind, i, pl in iter_places(data):
        if kind not in RESERVE_KINDS:
            continue
        res = pl.get("reservation") or {}
        need = res.get("need")
        if reservation_is_booked(res, data):
            continue
        name = (pl.get("name") or {})
        title = (name.get("en") if isinstance(name, dict) else name) or pl.get("id") or f"{dest_id}/{kind}[{i}]"
        by = effective_book_by(pl)
        if by and by < as_of and need in ("required", "recommended", "unknown", None):
            add(0, title, "book_by has passed and the place is not booked", by, "reservation", pl.get("id"))
        elif by and by <= horizon:
            add(1, title, f"book_by is within {book_by_days} days and the place is not booked", by, "reservation", pl.get("id"))
        elif need == "required":
            add(2, title, "reservation is required but not booked", by, "reservation", pl.get("id"))
        elif need == "recommended" and by:
            add(5, title, "booking is recommended", by, "reservation", pl.get("id"))

    # Stays
    for d in data["trip"].get("destinations") or []:
        if d.get("optional") or stay_is_booked(data, d):
            continue
        name = d.get("name") if isinstance(d.get("name"), str) else (d.get("name") or {}).get("en") or d["id"]
        start = (d.get("dates") or {}).get("start")
        by = None
        try:
            by = date.fromisoformat(start) - timedelta(days=14) if start else None
        except ValueError:
            pass
        urg = 0 if (by and by < as_of) else (1 if (by and by <= horizon) else 4)
        add(urg, f"Stay in {name}", "nights without a booked lodging", by, "stay", d["id"])

    # Transfers
    for x in (data["transfers"].get("transfers") or []):
        if x.get("optional") or transfer_is_booked(data, x):
            continue
        title = x.get("route_label") or f"{x.get('from')} → {x.get('to')}"
        raw = x.get("depart_at") or x.get("date_label")
        by = None
        if raw:
            try:
                by = date.fromisoformat(raw[:10]) - timedelta(days=7)
            except ValueError:
                pass
        urg = 0 if (by and by < as_of) else (1 if (by and by <= horizon) else 3)
        add(urg, f"Transfer {title}", "this leg is not booked", by, "transfer", x.get("id"))

    # Missing legs (no transfer recorded) — also appear as gap warnings.
    for w in gap_warnings(data):
        if not (
            w.startswith("gap: no transfer recorded")
            or w.startswith("gap: no outbound transfer")
            or w.startswith("gap: no return transfer")
        ):
            continue
        title = w[len("gap: "):]
        add(3, title, "record this leg, then book it", None, "missing_transfer", "")

    items.sort(key=lambda it: (it["urgency"], it.get("by") or "9999", it["title"]))
    return items


def validate_trip(data_dir: Path, as_of=None, stale_months=6, book_by_days=7):
    data_dir = Path(data_dir)
    files = discover(data_dir)
    errors, warnings = [], []
    if "trip.json" not in files:
        return {"ok": False, "errors": ["no trip.json"], "warnings": [], "data": None}
    schemas = {p.name: load_json(p) for p in SCHEMA_DIR.glob("*.json")}
    for rel, path in files.items():
        fname = Path(rel).name
        if rel.startswith("countries/"):
            schema = schemas["country.schema.json"]
        else:
            sname = FILE_MAP.get(fname)
            schema = schemas.get(sname) if sname else None
        obj = load_json(path)
        if schema:
            errors.extend(f"{rel}: {e}" for e in validate_schema(obj, schema))
        errors.extend(f"{rel}: {e}" for e in scan_secrets(obj, rel))
    data = load_trip(data_dir)
    errors.extend(cross_checks(data))
    warnings.extend(place_warnings(data, as_of=as_of, stale_months=stale_months))
    warnings.extend(reservation_warnings(data, as_of=as_of, book_by_days=book_by_days))
    warnings.extend(inbox_warnings(data_dir))
    warnings.extend(gap_warnings(data))
    first = book_first(data, as_of=as_of, book_by_days=book_by_days)
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "data": data,
        "budget": derive_budget(data),
        "book_first": first,
    }
