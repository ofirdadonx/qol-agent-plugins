#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a self-contained trip page from loaded trip data. No trip-specific defaults."""
from __future__ import annotations

import html as htmlmod
import json
import re
from datetime import date, datetime
from pathlib import Path

from trip_lib import (
    booking_by_id,
    derive_budget,
    effective_book_by,
    iter_places,
    lighten_for_contrast,
    party_dietary,
    pluralize,
    reservation_is_booked,
)

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = ROOT / "templates" / "default" / "ui"

REGION_COLORS = ["#7a3b4a", "#1f6f68", "#3d4d7a", "#8a5a28", "#4a6b3c", "#6b3d6a"]


def region_color(country, region_i) -> str:
    c = (country or {}).get("color")
    if c:
        return str(c)
    return REGION_COLORS[region_i % len(REGION_COLORS)]


_COLOR_OK = re.compile(
    r"^(#[0-9A-Fa-f]{3,8}|rgba?\([^;{}]+\)|color-mix\([^;{}]+\)|var\([^;{}]+\)|[a-zA-Z][a-zA-Z0-9-]*)$"
)


def safe_css_color(value, fallback=""):
    s = (value or "").strip()
    if s and _COLOR_OK.match(s):
        return s
    return fallback


_HE_WD_SHORT = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
_EN_WD_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_HE_MON_SHORT = {
    1: "ינו׳", 2: "פבר׳", 3: "מרץ", 4: "אפר׳", 5: "מאי", 6: "יונ׳",
    7: "יול׳", 8: "אוג׳", 9: "ספט׳", 10: "אוק׳", 11: "נוב׳", 12: "דצמ׳",
}
_EN_MON_SHORT = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def parse_iso_date(raw):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def date_col(raw, lang, extra="") -> str:
    d = parse_iso_date(raw)
    if not d:
        return f'<div class="date">{extra}</div>'
    he = (lang or "").startswith("he")
    wd = (_HE_WD_SHORT if he else _EN_WD_SHORT)[d.weekday()]
    mon = (_HE_MON_SHORT if he else _EN_MON_SHORT)[d.month]
    return (
        f'<div class="date">{extra}'
        f'<div class="d tnum">{d.day}</div>'
        f'<div class="w">{esc(wd)}</div>'
        f'<div class="mon">{esc(mon)}</div></div>'
    )


def format_span(start, end) -> str:
    a, b = parse_iso_date(start), parse_iso_date(end)
    if not a and not b:
        return ""
    if a and not b:
        return f"{a.day:02d}.{a.month:02d}.{a.year}"
    if b and not a:
        return f"{b.day:02d}.{b.month:02d}.{b.year}"
    if a.year == b.year:
        return f"{a.day:02d}.{a.month:02d}–{b.day:02d}.{b.month:02d}.{b.year}"
    return f"{a.day:02d}.{a.month:02d}.{a.year}–{b.day:02d}.{b.month:02d}.{b.year}"


def dest_nights(d) -> int:
    if d.get("nights") is not None:
        return int(d["nights"])
    a = parse_iso_date((d.get("dates") or {}).get("start"))
    b = parse_iso_date((d.get("dates") or {}).get("end"))
    if a and b:
        return max(0, (b - a).days)
    if d.get("nights_min") is not None:
        return int(d["nights_min"])
    return 0


def mast_dates(trip) -> str:
    dates = trip.get("dates") or {}
    return format_span(dates.get("start"), dates.get("end"))


def party_label(data, lang) -> str:
    names = []
    for t in data["trip"].get("travelers") or []:
        n = (t.get("name") or "").strip()
        if n:
            names.append(n.split()[0])
    if not names:
        return ""
    if (lang or "").startswith("he") and len(names) >= 2:
        return names[0] + " ו" + " ו".join(names[1:])
    return " · ".join(names)


def who_if_needed(brand: str, who: str) -> str:
    """Skip the party line when the wordmark already names the travelers."""
    if not who:
        return ""
    if brand and who in brand:
        return ""
    return who


def diet_phrase(data, ui) -> str:
    """Localized dietary labels from ui[diet_<code>]; codes stay in the data."""
    labels = []
    for code in party_dietary(data):
        label = (ui.get("diet_" + code) or "").strip()
        if not label:
            label = (code or "").replace("-", " ").replace("_", " ").strip()
        if label:
            labels.append(label)
    return " · ".join(labels)


def booking_display_title(b) -> str:
    """Short title, or the full title with a repeated confirmation code stripped."""
    short = (b.get("short_title") or "").strip()
    if short:
        return short
    title = (b.get("title") or "").strip()
    code = (b.get("confirmation_code") or "").strip()
    if code and code in title:
        title = title.replace(code, "")
        title = re.sub(r"[\s·•|,:\-–—]+$", "", title)
        title = re.sub(r"^[\s·•|,:\-–—]+", "", title)
        title = re.sub(r"\s+", " ", title).strip()
    return title or code


def render_flag(country, size="sm") -> str:
    flag = (country or {}).get("flag") or {}
    shapes = flag.get("shapes") or []
    if not shapes:
        return ""
    parts = [
        '<svg viewBox="0 0 900 600" xmlns="http://www.w3.org/2000/svg" '
        'focusable="false" aria-hidden="true">'
    ]
    for s in shapes:
        kind = s.get("type") or "rect"
        fill = safe_css_color(s.get("fill"), "#efece6")
        if kind in ("rect", "stripe"):
            x = s.get("x", 0)
            y = s.get("y", 0)
            w = s.get("width", 900)
            h = s.get("height", 600 if kind == "rect" else 0)
            parts.append(
                f'<rect x="{esc(x)}" y="{esc(y)}" width="{esc(w)}" height="{esc(h)}" fill="{esc(fill)}"/>'
            )
        elif kind == "circle":
            parts.append(
                f'<circle cx="{esc(s.get("cx", 450))}" cy="{esc(s.get("cy", 300))}" '
                f'r="{esc(s.get("r", 180))}" fill="{esc(fill)}"/>'
            )
        elif kind == "path" and s.get("d"):
            parts.append(f'<path d="{esc(s["d"])}" fill="{esc(fill)}"/>')
    parts.append("</svg>")
    label = flag.get("label") or loc((country or {}).get("name"), "en") or (country or {}).get("id") or ""
    cls = "flag lg" if size == "lg" else "flag"
    return (
        f'<span class="{cls}" title="{esc(label)}" aria-label="{esc(label)}">'
        + "".join(parts)
        + "</span>"
    )


def theme_style(data) -> str:
    countries = country_list(data)
    rules = []
    meshes = []
    for i, c in enumerate(countries):
        color = safe_css_color(region_color(c, i), REGION_COLORS[i % len(REGION_COLORS)])
        color2 = safe_css_color(c.get("color_2"), color)
        tint = safe_css_color(c.get("tint"), f"color-mix(in srgb,{color} 10%, transparent)")
        accent = safe_css_color(c.get("accent"), color2)
        rules += [
            f"--region-{i}:{color}",
            f"--region-{i}-2:{color2}",
            f"--region-{i}-tint:{tint}",
            f"--region-{i}-accent:{accent}",
        ]
        mesh = safe_css_color(c.get("mesh"), f"color-mix(in srgb,{color} 16%, transparent)")
        meshes.append(mesh)
    while len(meshes) < 3:
        meshes.append("rgba(80,76,72,.08)")
    for i, m in enumerate(meshes[:3]):
        rules.append(f"--mesh-{i}:{m}")
    css = ":root{" + ";".join(rules) + "}"
    # Dark-mode region tokens: computed from each country's colour (same hue,
    # lighter), emitted AFTER #trip-theme so they win, under html[data-theme="dark"]
    # for specificity. Never hard-code a country's hex here.
    dark_rules = []
    for i, c in enumerate(countries):
        color = safe_css_color(region_color(c, i), REGION_COLORS[i % len(REGION_COLORS)])
        color2 = safe_css_color(c.get("color_2"), color)
        dark = lighten_for_contrast(color)
        dark2 = lighten_for_contrast(color2) or dark
        if dark:
            dark_rules.append(f"--region-{i}:{dark}")
        if dark2:
            dark_rules.append(f"--region-{i}-2:{dark2}")
        tint = f"color-mix(in srgb,{dark or color} 22%, transparent)"
        dark_rules.append(f"--region-{i}-tint:{tint}")
        if dark2:
            dark_rules.append(f"--region-{i}-accent:{dark2}")
    dark_css = "html[data-theme=\"dark\"]{" + ";".join(dark_rules) + "}" if dark_rules else ""
    dark_tag = f'<style id="trip-theme-dark">{dark_css}</style>' if dark_css else ""
    return f'<style id="trip-theme">{css}</style>\n{dark_tag}'


def transfer_date(data, x):
    for key in ("date", "depart_date", "start", "on"):
        if x.get(key):
            return x[key]
    b = booking_by_id(data, x.get("booking_id")) if x.get("booking_id") else None
    if b:
        for key in ("depart_at", "departure_at", "start", "date"):
            if b.get(key):
                return b[key]
    lab = x.get("date_label") or ""
    m = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", lab)
    if m:
        year_s = m.group(3)
        if not year_s:
            year_s = str(((data.get("trip") or {}).get("dates") or {}).get("start") or "2026")[:4]
        try:
            return date(int(year_s), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None


def country_span_and_nights(data, country, lang, ui):
    cid = country["id"]
    dests = [d for d in data["trip"]["destinations"] if d.get("country") == cid]
    starts, ends = [], []
    leading, after, trailing = transfers_in_country(data, cid)
    for x in leading + trailing:
        raw = transfer_date(data, x)
        d = parse_iso_date(raw)
        if d:
            starts.append(d.isoformat())
            ends.append(d.isoformat())
    nights = 0
    opt_nights = 0
    opt_labels = []
    for d in dests:
        dates = d.get("dates") or {}
        if dates.get("start"):
            starts.append(dates["start"])
        if dates.get("end"):
            ends.append(dates["end"])
        n = dest_nights(d)
        if d.get("optional"):
            opt_nights += n
            if d.get("optional_label"):
                opt_labels.append(d["optional_label"])
        else:
            nights += n
    span = format_span(min(starts) if starts else None, max(ends) if ends else None)
    nights_h = pluralize(
        nights,
        ui.get("plural_night") or {"one": "1 night", "other": "{n} nights"},
    )
    if opt_labels:
        opt_h = " · ".join(opt_labels)
    elif opt_nights:
        opt_h = (ui.get("nights_optional") or "{n} optional nights").replace("{n}", str(opt_nights))
    else:
        opt_h = ""
    return span, nights_h, opt_h, dests

MODE_ICON = {
    "flight": "ph-airplane-tilt",
    "train": "ph-train",
    "ferry": "ph-waves",
    "bus": "ph-bus",
    "car": "ph-car",
    "path": "ph-path",
}

# Official Phosphor fill paths (MIT, viewBox 0 0 256 256). Regular solid
# weight, used as 18px glyphs inside the 32px transfer-mode chip so the
# page stays self-contained offline. Not the duotone webfont.
_CHIP_PATHS = {
    "airplane-tilt": "M215.52,197.26a8,8,0,0,1-1.86,8.39l-24,24A8,8,0,0,1,184,232a7.09,7.09,0,0,1-.79,0,8,8,0,0,1-5.87-3.52l-44.07-66.12L112,183.59V208a8,8,0,0,1-2.34,5.65s-14,14.06-15.88,15.88A7.91,7.91,0,0,1,91,231.41a8,8,0,0,1-10.41-4.35l-.06-.15-14.7-36.76L29,175.42a8,8,0,0,1-2.69-13.08l16-16A8,8,0,0,1,48,144H72.4l21.27-21.27L27.56,78.65a8,8,0,0,1-1.22-12.32l24-24a8,8,0,0,1,8.39-1.86l85.94,31.25L176.2,40.19a28,28,0,0,1,39.6,39.6l-31.53,31.53Z",
    "train": "M184,24H72A32,32,0,0,0,40,56V184a32,32,0,0,0,32,32h8L65.6,235.2a8,8,0,1,0,12.8,9.6L100,216h56l21.6,28.8a8,8,0,1,0,12.8-9.6L176,216h8a32,32,0,0,0,32-32V56A32,32,0,0,0,184,24ZM84,184a12,12,0,1,1,12-12A12,12,0,0,1,84,184Zm36-64H56V80h64Zm52,64a12,12,0,1,1,12-12A12,12,0,0,1,172,184Zm28-64H136V80h64Z",
    "path": "M228,200a28,28,0,0,1-54.83,8H72a48,48,0,0,1,0-96h96a24,24,0,0,0,0-48H72a8,8,0,0,1,0-16h96a40,40,0,0,1,0,80H72a32,32,0,0,0,0,64H173.17A28,28,0,0,1,228,200Z",
    "boat": "M221.06,110.59,208,106.23V56a16,16,0,0,0-16-16H136V24a8,8,0,0,0-16,0V40H64A16,16,0,0,0,48,56v50.23l-13.06,4.36A16,16,0,0,0,24,125.77V152c0,61.54,97.89,86.72,102.06,87.76a8,8,0,0,0,3.88,0C134.11,238.72,232,213.54,232,152V125.77A16,16,0,0,0,221.06,110.59ZM136,168a8,8,0,0,1-16,0V104.87a8,8,0,0,1,16,0Zm56-67.1L130.53,80.41a8,8,0,0,0-5.06,0L64,100.9V56H192Z",
    "bus": "M248,80v24a8,8,0,0,1-16,0V80a8,8,0,0,1,16,0ZM16,72a8,8,0,0,0-8,8v24a8,8,0,0,0,16,0V80A8,8,0,0,0,16,72Zm200-8V208a16,16,0,0,1-16,16H184a16,16,0,0,1-16-16v-8H88v8a16,16,0,0,1-16,16H56a16,16,0,0,1-16-16V64A32,32,0,0,1,72,32H184A32,32,0,0,1,216,64ZM104,148a12,12,0,1,0-12,12A12,12,0,0,0,104,148Zm72,0a12,12,0,1,0-12,12A12,12,0,0,0,176,148Zm24-76H56v40H200Z",
    "car": "M240,104H229.2L201.42,41.5A16,16,0,0,0,186.8,32H69.2a16,16,0,0,0-14.62,9.5L26.8,104H16a8,8,0,0,0,0,16h8v80a16,16,0,0,0,16,16H64a16,16,0,0,0,16-16v-8h96v8a16,16,0,0,0,16,16h24a16,16,0,0,0,16-16V120h8a8,8,0,0,0,0-16ZM80,152H56a8,8,0,0,1,0-16H80a8,8,0,0,1,0,16Zm120,0H176a8,8,0,0,1,0-16h24a8,8,0,0,1,0,16ZM44.31,104,69.2,48H186.8l24.89,56Z",
    "taxi": "M240,104H228.64L201.25,56.06A16,16,0,0,0,187.36,48H165.42l-12-29.94A15.93,15.93,0,0,0,138.58,8H117.42a15.93,15.93,0,0,0-14.86,10.06L90.58,48H68.64a16,16,0,0,0-13.89,8.06L27.36,104H16a8,8,0,0,0,0,16h8v80a16,16,0,0,0,16,16H64a16,16,0,0,0,16-16v-8h96v8a16,16,0,0,0,16,16h24a16,16,0,0,0,16-16V120h8a8,8,0,0,0,0-16ZM80,152H56a8,8,0,0,1,0-16H80a8,8,0,0,1,0,16Zm120,0H176a8,8,0,0,1,0-16h24a8,8,0,0,1,0,16ZM45.79,104,68.64,64H187.36l22.85,40Z",
}

_CHIP_FROM = {
    "flight": "airplane-tilt",
    "airplane": "airplane-tilt",
    "airplane-tilt": "airplane-tilt",
    "ph-airplane-tilt": "airplane-tilt",
    "train": "train",
    "ph-train": "train",
    "ferry": "boat",
    "boat": "boat",
    "ph-boat": "boat",
    "ph-waves": "boat",
    "waves": "boat",
    "bus": "bus",
    "ph-bus": "bus",
    "car": "car",
    "ph-car": "car",
    "taxi": "taxi",
    "ph-taxi": "taxi",
    "path": "path",
    "ph-path": "path",
}


def xfer_chip(mode_or_icon: str) -> str:
    """32px regular-weight mode chip (inline SVG, works offline)."""
    raw = (mode_or_icon or "").strip()
    key = _CHIP_FROM.get(raw) or _CHIP_FROM.get(raw.replace("ph-", "")) or "path"
    d = _CHIP_PATHS.get(key) or _CHIP_PATHS["path"]
    return (
        f'<span class="xfer-chip" aria-hidden="true">'
        f'<svg class="xfer-ico" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        f'fill="currentColor" width="18" height="18" focusable="false" aria-hidden="true">'
        f'<path d="{d}"/></svg></span>'
    )


SYMBOLS = {"ILS": "₪", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "THB": "฿"}
HOME_IDS = {"home", "tlv", "origin", "start", None, ""}


def esc(s) -> str:
    return htmlmod.escape("" if s is None else str(s), quote=True)


class HTML(str):
    """A string that is already safe HTML and must not be escaped again."""


def loc(obj, lang: str, fallback: str = "en") -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return str(obj)
    return (
        obj.get(lang)
        or obj.get(fallback)
        or obj.get("local")
        or next((v for v in obj.values() if v), "")
        or ""
    )


# Whole LTR numeric atoms (amounts, times, dates, and their units).
# The thousands comma sits inside the first character class so "1,124.75"
# is one match, never "1," + "124.75". Units and currency symbols stay in
# the same match ("12.5°C", "20 °C", "30 min", "¥1,200") so RTL cannot
# render "C°12.5". Longer unit names come first in the unit group.
_UNIT = (
    r"(?:"
    r"°[CFK]|℃|℉|°|"
    r"km(?:/h)?|kph|mph|"
    r"min(?:ute)?s?|hours?|hrs?|sec(?:ond)?s?|"
    r"cm|mm|kg|lbs?|"
    r"USD|EUR|ILS|JPY|THB|GBP|CHF|"
    r"[%$€£¥₪฿]|"
    r"דקות|דק[\'׳]|שעות|"
    r"ק[\"״]מ|מ[\"״]מ|מעלות"
    r")"
)
_NUM_RE = re.compile(
    r"("
    r"[$€£¥₪฿]\s?\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|[$€£¥₪฿]\s?\d+(?:[.,]\d+)?"
    r"|¥[\d,.\-–]+"
    r"|฿[\d,.\-–]+"
    r"|\$[\d,.\-–]+"
    r"|₪[\d,.\-–]+"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*" + _UNIT +
    r"|\d+[.,]\d+\s*" + _UNIT +
    r"|\d+\s*" + _UNIT +
    r"|\d{1,2}\.\d{2}(?:\.\d{2,4})?[–-]\d{1,2}\.\d{2}(?:\.\d{2,4})?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\d+[.,]\d+"
    r"|\d{1,2}:\d{2}(?::\d{2})?"
    r"|\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?"
    r"|\+?\d[\d,./:–-]{1,}\d"
    r")"
)


def bdi(inner_escaped: str) -> str:
    """Wrap a complete LTR atom. Never split a number across spans."""
    if not inner_escaped:
        return ""
    return f'<bdi class="tnum" dir="ltr">{inner_escaped}</bdi>'


def ltr(s: str) -> str:
    if not s:
        return s
    return _NUM_RE.sub(lambda m: bdi(m.group(0)), s)


def raw_ltr(s) -> str:
    return ltr(esc(s))


# A cluster of numeric LTR atoms joined by middots: "21.11 · 21:45".
_LEG_CLUSTER = re.compile(
    r"((?:\d[\d./:–-]*)(?:\s*[·•]\s*\d[\d./:–-]*)+)"
)


def xfer_leg_html(*parts: str) -> str:
    """One nowrap date·time group. The middot is a .sep, never a bare flex text node."""
    atoms = [p for p in parts if p]
    if not atoms:
        return ""
    inner = []
    for i, p in enumerate(atoms):
        if i:
            inner.append('<span class="sep" aria-hidden="true">·</span>')
        inner.append(raw_ltr(p))
    return f'<span class="xfer-leg">{"".join(inner)}</span>'


def wrap_xfer_legs(text: str) -> str:
    """Turn '21.11 · 21:45 landing 22.11 · 16:15' into two .xfer-leg groups.

    Hebrew (or any non-numeric) words stay outside the nowrap group; each
    date·time cluster becomes one flex item so a middot cannot wrap alone.
    """
    if not text:
        return ""
    if not _LEG_CLUSTER.search(text):
        return xfer_leg_html(text)
    out = []
    last = 0
    for m in _LEG_CLUSTER.finditer(text):
        out.append(esc(text[last:m.start()]))
        chunks = [c for c in re.split(r"\s*[·•]\s*", m.group(1)) if c]
        out.append(xfer_leg_html(*chunks))
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


def parse_iso_dt(raw):
    """Parse an ISO date or datetime. None if empty or unparseable."""
    if not raw:
        return None
    s = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        d = parse_iso_date(raw)
        if d:
            return datetime(d.year, d.month, d.day)
        return None


def _short_dmy(dt) -> str:
    return f"{dt.day:02d}.{dt.month:02d}"


def _short_hm(dt, raw) -> str:
    if not dt or not raw:
        return ""
    s = str(raw)
    if "T" in s or " " in s.strip():
        return f"{dt.hour:02d}:{dt.minute:02d}"
    return ""


def xfer_when_bits(x) -> list:
    """Flex-safe date·time groups for a transfer's meta row."""
    bits = []
    dl = (x.get("date_label") or "").strip()
    tl = (x.get("time_label") or "").strip()
    if dl or tl:
        if dl and tl:
            if re.search(r"[·•]", dl):
                bits.append(wrap_xfer_legs(dl))
                if tl not in dl:
                    bits.append(wrap_xfer_legs(tl) if re.search(r"[·•]", tl) else xfer_leg_html(tl))
            else:
                bits.append(xfer_leg_html(dl, tl))
        elif dl:
            bits.append(wrap_xfer_legs(dl) if re.search(r"[·•]", dl) else xfer_leg_html(dl))
        else:
            bits.append(wrap_xfer_legs(tl) if re.search(r"[·•]", tl) else xfer_leg_html(tl))
        return bits
    dep = parse_iso_dt(x.get("depart_at") or x.get("date"))
    arr = parse_iso_dt(x.get("arrive_at"))
    if dep:
        bits.append(xfer_leg_html(*filter(None, [_short_dmy(dep), _short_hm(dep, x.get("depart_at") or x.get("date"))])))
    if arr:
        bits.append(xfer_leg_html(*filter(None, [_short_dmy(arr), _short_hm(arr, x.get("arrive_at"))])))
    return bits



def countdown_caption(trip, ui) -> str:
    cd = trip.get("countdown") or {}
    if cd.get("caption"):
        return raw_ltr(cd["caption"])
    raw = trip.get("departure_at") or ""
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return bdi(esc(dt.strftime("%Y-%m-%d %H:%M")))
    except ValueError:
        return esc(raw)


def load_ui(lang: str) -> dict:

    base = json.loads((UI_DIR / "en.json").read_text(encoding="utf-8"))
    p = UI_DIR / f"{lang}.json"
    if p.exists() and lang != "en":
        base.update(json.loads(p.read_text(encoding="utf-8")))
    return base


def icon(name: str, extra: str = "") -> str:
    name = name or "ph-map-pin"
    if not name.startswith("ph-"):
        name = "ph-" + name
    return f'<i class="ph-duotone {esc(name)} ph {extra}" aria-hidden="true"></i>'


def ext(href: str, label: str, cls: str = "ext") -> str:
    if not href:
        return esc(label)
    return (
        f'<a class="{cls}" href="{esc(href)}" target="_blank" rel="noopener noreferrer">'
        f"{raw_ltr(label)}{icon('ph-arrow-square-out')}</a>"
    )


def copybtn(text: str, ui: dict) -> str:
    if not text:
        return ""
    return (
        f'<button type="button" class="copybtn press" data-copy="{esc(text)}" '
        f'aria-label="{esc(ui["copy"] + " " + text)}">{icon("ph-copy")} {esc(ui["copy"])}</button>'
    )


def badge(status: str, ui: dict, optional: bool = False) -> str:
    if optional or status == "optional":
        return f'<span class="badge opt">{esc(ui["optional"])}</span>'
    if status == "booked":
        return f'<span class="badge closed">{esc(ui["booked"])}</span>'
    if status in ("open", "wait", "estimate"):
        return f'<span class="badge wait">{esc(ui["open"])}</span>'
    return ""


def tel_link(number: str, tel: str | None = None) -> str:
    if not number:
        return ""
    href = tel or re.sub(r"[^\d+]", "", number)
    return f'<a class="call" href="tel:{esc(href)}">{icon("ph-phone")} {bdi(esc(number))}</a>'


def _emer_link(e: dict) -> str:
    """One emergency number: nowrap LTR isolate; long numbers span a full row."""
    number = e.get("number") or e.get("tel") or ""
    tel = e.get("tel") or re.sub(r"[^\d+]", "", number)
    compact = re.sub(r"\s+", "", number)
    wide = " emer-wide" if len(compact) >= 11 else ""
    return (
        f'<a class="call{wide}" href="tel:{esc(tel)}">'
        f'<div class="n">{bdi(esc(number))}</div>'
        f'<div class="w">{esc(e.get("label") or "")}</div></a>'
    )


def fold(inner: str, detail_id: str) -> str:
    return (
        f'<div class="fold"><div class="fold-inner" inert aria-hidden="true">'
        f'<div class="xfer-detail" id="{esc(detail_id)}">{inner}</div>'
        f"</div></div>"
    )


def money(amount, currency) -> str:
    if amount is None:
        return ""
    if isinstance(amount, float) and amount == int(amount):
        amount = int(amount)
    if isinstance(amount, float):
        txt = f"{amount:,.2f} {currency or ''}".strip()
    else:
        txt = f"{amount:,} {currency or ''}".strip()
    return bdi(esc(txt))


def country_list(data) -> list:
    seen, out = [], []
    cmap = data.get("countries") or {}
    for d in data["trip"].get("destinations") or []:
        cid = d.get("country")
        if cid and cid not in seen:
            seen.append(cid)
            out.append(cmap.get(cid) or {"id": cid, "name": {"en": cid}})
    for cid, c in cmap.items():
        if cid not in seen:
            out.append(c)
    return out


def dest_by_id(data, did):
    for d in data["trip"].get("destinations") or []:
        if d["id"] == did:
            return d
    return None


def country_index(data) -> dict:
    return {c["id"]: i for i, c in enumerate(country_list(data))}


def transfers_in_country(data, cid):
    """Leading arrivals, legs after each dest, trailing boundary legs leaving the country.

    A boundary arriving from another country is shown only on the departing country's timeline.
    """
    ids = {d["id"] for d in data["trip"]["destinations"] if d.get("country") == cid}
    xfers = data["transfers"].get("transfers") or []
    leading, trailing, after = [], [], {i: [] for i in ids}
    for x in xfers:
        frm, to = x.get("from_id"), x.get("to_id")
        if frm in ids and to in ids:
            after.setdefault(frm, []).append(x)
        elif frm in ids and to not in ids:
            if x.get("boundary") or to in HOME_IDS:
                trailing.append(x)
            else:
                after.setdefault(frm, []).append(x)
        elif to in ids and frm not in ids:
            if x.get("boundary") and frm not in HOME_IDS:
                continue
            leading.append(x)
    return leading, after, trailing


def status_of_xfer(data, x) -> str:
    if x.get("optional"):
        return "optional"
    bid = x.get("booking_id")
    b = booking_by_id(data, bid) if bid else None
    if b:
        return b.get("status") or "open"
    return "open"


def symbol(code: str) -> str:
    return SYMBOLS.get(code or "", code or "")


HOW_KEYS = {
    "website": "how_website",
    "app": "how_app",
    "phone": "how_phone",
    "hotel_concierge": "how_hotel_concierge",
    "at_door": "how_at_door",
    "ticket_online": "how_ticket_online",
}


def reservation_html(pl, ui, data) -> str:
    res = pl.get("reservation")
    if not res:
        return ""
    need = res.get("need")
    bits = []
    cls = {
        "required": ("res-required", "res_required"),
        "recommended": ("res-recommended", "res_recommended"),
        "walk_in": ("res-walkin", "res_walk_in"),
        "unknown": ("res-unknown", "res_unknown"),
    }
    if need in cls:
        c, k = cls[need]
        bits.append(f'<span class="badge {c}">{esc(ui[k])}</span>')
    if reservation_is_booked(res, data):
        bits.append(f'<span class="badge res-booked">{esc(ui["res_booked"])}</span>')
    how = res.get("how") or {}
    method = how.get("method") if isinstance(how, dict) else how
    how_label = ui.get(HOW_KEYS.get(method or ""), method or "")
    if how_label:
        label = ui["res_how"].replace("{how}", how_label)
        if isinstance(how, dict) and how.get("app_name"):
            label += f" ({how['app_name']})"
        href = (how.get("url") if isinstance(how, dict) else None) or None
        if href:
            bits.append(f'<span class="res-how">{ext(href, label)}</span>')
        else:
            bits.append(f'<span class="res-how">{esc(label)}</span>')
    if res.get("lead_time"):
        bits.append(f'<span>{esc(ui["res_lead"].replace("{lead}", res["lead_time"]))}</span>')
    by = effective_book_by(pl)
    if by:
        bits.append(f'<span>{esc(ui["res_book_by"].replace("{date}", by.isoformat()))}</span>')
    if res.get("notes"):
        bits.append(f'<span>{raw_ltr(res["notes"])}</span>')
    if not bits:
        return ""
    return f'<div class="rec-res">{"".join(bits)}</div>'

def render_header(data, ui, lang) -> str:
    trip = data["trip"]
    chips = []
    for n in trip.get("nav") or []:
        chips.append(f'<a href="{esc(n["href"])}">{esc(n["label"])}</a>')
    if not chips:
        chips = [
            f'<a href="#overview">{esc(ui.get("at_a_glance") or "Overview")}</a>',
            f'<a href="#itinerary">{esc(ui.get("axis") or "Itinerary")}</a>',
        ]
    chips[0] = chips[0].replace("<a ", '<a class="on" ', 1)
    brand = trip.get("brand") or trip.get("title") or ""
    flags = "".join(render_flag(c, "sm") for c in country_list(data))
    flags_h = f'<span class="flags">{flags}</span>' if flags else ""
    dates = mast_dates(trip)
    dates_h = f'<div class="dates tnum" dir="ltr">{esc(dates)}</div>' if dates else ""
    who = who_if_needed(brand, party_label(data, lang))
    who_h = f'<div class="who">{esc(who)}</div>' if who else ""
    return (
        '<header class="top glass g-thick">\n'
        '  <div class="mast">\n'
        '    <div class="mast-lead">\n'
        f'      <div class="wordmark">{esc(brand)}{flags_h}</div>\n'
        f'      {dates_h}\n'
        f'      {who_h}\n'
        '    </div>\n'
        '    <div class="mast-actions">\n'
        f'      <button type="button" class="jump-today press" id="jumpSearch" aria-label="{esc(ui["search_places"])}">{icon("ph-magnifying-glass")}<span> {esc(ui["search"])}</span></button>\n'
        f'      <button type="button" class="jump-today press" id="jumpToday" aria-label="{esc(ui["today"])}">{icon("ph-calendar-check")}<span> {esc(ui["today"])}</span></button>\n'
        f'      <button type="button" class="jump-today press" id="locateBtn" hidden aria-label="{esc(ui["locate_title"])}">{icon("ph-compass")}<span> {esc(ui["locate"])}</span></button>\n'
        f'      <button class="iconbtn press" id="themeBtn" aria-label="{esc(ui["theme"])}">{icon("ph-moon-stars")}</button>\n'
        "    </div>\n"
        "  </div>\n"
        f'  <div class="nav-wrap"><nav class="nav-bar" aria-label="{esc(ui.get("sections") or ui["contents"])}">{"".join(chips)}</nav></div>\n'
        '  <div class="progress" aria-hidden="true"><b id="prog"></b></div>\n'
        "</header>"
    )


_HE_WEEKDAYS = ["יום ב׳", "יום ג׳", "יום ד׳", "יום ה׳", "יום ו׳", "שבת", "יום א׳"]


def format_deadline_date(dt, lang: str) -> str:
    """A readable local date: 'יום ה׳ 19.11.2026' or 'Thu 19.11.2026'."""
    stamp = f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
    if (lang or "").startswith("he"):
        wd = _HE_WEEKDAYS[dt.weekday()]
        return f'{wd} {bdi(esc(stamp))}'
    wd = dt.strftime("%a")
    return f'{esc(wd)} {bdi(esc(stamp))}'


def deadline_cards(data, ui, lang: str = "en") -> str:
    """Short action title + short what/where detail + a readable date line."""
    detail_key = {
        "charge_at": "charge_detail",
        "cancel_deadline": "cancel_detail",
        "checkin_at": "checkin_detail",
    }
    cards = []
    for b in data["bookings"].get("bookings") or []:
        for field, label_key in (
            ("charge_at", "charge"),
            ("cancel_deadline", "cancel_by"),
            ("checkin_at", "checkin_by"),
        ):
            raw = b.get(field)
            if not raw:
                continue
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                sort_key = dt
                date_h = format_deadline_date(dt, lang)
            except ValueError:
                sort_key = datetime.max
                date_h = bdi(esc(raw))
            title = ui.get(label_key) or field
            short = b.get("short_title") or ""
            custom = b.get(detail_key[field])
            if custom:
                when = raw_ltr(custom)
            else:
                when = date_h
            if field == "checkin_at" and b.get("checkin_url"):
                label = ui.get("checkin_on_site") or ui.get("checkin") or "Check-in"
                carrier = b.get("carrier") or short or ""
                link_lbl = f"{label} {carrier}".strip()
                when = when + " · " + ext(b["checkin_url"], link_lbl, cls="inline-ext")
            detail_h = f'<p class="dead-detail">{esc(short)}</p>' if short else ""
            cards.append((sort_key, (
                f'<article class="dead glass g-reg" data-end="{esc(raw)}" id="dl-{esc(b["id"])}-{esc(field)}">'
                f'<span class="st" data-st></span>'
                f"<h3>{esc(title)}</h3>"
                f"{detail_h}"
                f'<p class="when">{when}</p>'
                f"</article>"
            )))
    cards = [html for _, html in sorted(cards, key=lambda x: x[0])]
    if not cards:
        return ""
    return f'<div class="dead-strip" id="deadlines" aria-label="{esc(ui["deadlines"])}">{"".join(cards)}</div>'


def render_overview(data, ui, lang) -> str:
    countries = country_list(data)
    blocks = []
    for i, c in enumerate(countries):
        span, nights_h, _opt_h, dests = country_span_and_nights(data, c, lang, ui)
        color = safe_css_color(region_color(c, i), REGION_COLORS[i % len(REGION_COLORS)])
        flag = render_flag(c, "lg")
        name = loc(c.get("name"), lang) or c["id"]
        stops = []
        for d in dests:
            nm = loc(d.get("name"), lang) or d["id"]
            short = re.split(r"\s[—–-]\s", nm)[0]
            info = ((data.get("destinations") or {}).get(d["id"]) or {}).get("info") or {}
            stay_st = info.get("stay_status") or ("booked" if info.get("stay_booking_id") else "open")
            if d.get("optional"):
                stops.append(f'<span class="stop-opt">{esc(short)}</span>')
            elif stay_st == "booked":
                stops.append(f'<span class="ok">{esc(short)} ✓</span>')
            else:
                stops.append(f'<span>{esc(short)}</span>')
        blocks.append(
            f'<div class="folio-block" style="--block-color:var(--region-{i})">'
            f'<p class="kicker"><bdi class="tnum" dir="ltr">{esc(span)}</bdi></p>'
            f'<div class="h-flag">{flag}<p class="display">{esc(name)}</p></div>'
            f'<p class="nights-line">{esc(nights_h)}</p>'
            f'<p class="stops-line">{" · ".join(stops)}</p>'
            "</div>"
        )
    booked = [b for b in data["bookings"].get("bookings") or [] if b.get("status") == "booked"]
    closed = ""
    if booked:
        titles = ", ".join(booking_display_title(b) for b in booked)
        closed = f'<p class="closed-line">{esc(ui.get("closed_booked") or "")}: {esc(titles)}.</p>'
    diet_html = ""
    phrase = diet_phrase(data, ui)
    note = data["trip"].get("dietary_note") or ""
    if phrase or note:
        body = esc(phrase)
        if note:
            body = (body + " — " if body else "") + esc(note)
        diet_html = (
            f'<p class="closed-line"><strong>{esc(ui["dietary"])}:</strong> {body}</p>'
        )
    legend_items = data["trip"].get("status_legend") or []

    def _legend_caption(item, kind, fallback):
        """The checkmark phrase ('סגור ✓' / 'Booked ✓') lives only on the badge."""
        badge_html = badge(kind, ui)
        text = item if item else fallback
        if not text:
            return badge_html

        def _norm(s):
            return re.sub(r"[\s✓✔✔︎]+", "", re.sub(r"<[^>]+>", "", str(s))).casefold()

        phrases = [
            ui.get("booked") if kind == "booked" else "",
            ui.get("open") if kind == "open" else "",
            ui.get("optional") if kind == "optional" else "",
            ui.get("closed_booked") if kind == "booked" else "",
            ui.get("legend_booked") if kind == "booked" else "",
            ui.get("legend_open") if kind == "open" else "",
            ui.get("legend_optional") if kind == "optional" else "",
            badge_html,
        ]
        ntext = _norm(text)
        if any(p and ntext == _norm(p) for p in phrases):
            return badge_html
        return f"{badge_html} {esc(text)}"

    legend = (
        '<div class="status-legend" style="margin-top:12px">'
        f'<span>{_legend_caption(legend_items[0] if legend_items else None, "booked", ui.get("legend_booked"))}</span> '
        f'<span>{_legend_caption(legend_items[1] if len(legend_items) > 1 else None, "open", ui.get("legend_open"))}</span> '
        f'<span>{_legend_caption(legend_items[2] if len(legend_items) > 2 else None, "optional", ui.get("legend_optional"))}</span>'
        "</div>"
    )
    map_html = render_map_figure(data, ui, lang)
    return (
        f'<section class="spread" id="overview" aria-label="{esc(ui.get("at_a_glance") or "")}">'
        f'<div class="folio">{"".join(blocks)}{closed}{diet_html}{legend}'
        '<div class="today-banner" id="todayBanner" hidden></div>'
        '<div class="today-card card glass g-thick" id="todayCard" hidden></div>'
        '<p class="locate-msg" id="locateMsg" hidden></p>'
        f"</div>{map_html}</section>"
    )


def render_map_figure(data, ui, lang) -> str:
    trip = data["trip"]
    info = trip.get("map") or {}
    fallback = ""
    rel = info.get("fallback_svg")
    if rel:
        p = Path(data["dir"]) / rel
        if p.exists():
            fallback = p.read_text(encoding="utf-8")
    if not fallback:
        fallback = f'<p class="src-note">{esc(ui["map_offline"])}</p>'
    cap = info.get("lede") or info.get("headline") or ""
    attr = info.get("attribution") or ""
    cap_h = ""
    if cap or attr:
        cap_h = f'<figcaption>{raw_ltr(cap)}{" · " if cap and attr else ""}<span class="src">{raw_ltr(attr)}</span></figcaption>'
    return (
        f'<figure class="map" id="map">'
        f'<div class="map-tools">'
        f'<button type="button" class="stop-toggle press" id="btnLiveMap" aria-pressed="true">{icon("ph-map-trifold")} {esc(ui["live_map"])}</button>'
        f'<button type="button" class="stop-toggle press" id="btnSvgMap" aria-pressed="false">{icon("ph-path")} {esc(ui["overview_map"])}</button>'
        f'<p class="map-offline-note" id="mapOfflineNote" hidden></p>'
        f"</div>"
        f'<div id="mapLive" class="map-live" dir="ltr" role="region" aria-label="{esc(ui["live_map"])}"></div>'
        f'<div id="mapFallback" class="map-fallback" hidden>{fallback}</div>'
        f"{cap_h}</figure>"
    )


def render_nights(data, ui, lang) -> str:
    trip = data["trip"]
    cap = trip.get("nights_chart_caption") or ""
    cap_html = f'<p class="caption">{icon("ph-info")}<span>{raw_ltr(cap)}</span></p>' if cap else ""
    nights_h = (trip.get("nights_chart") or {}).get("headline") or ui.get("nights_chart") or ui["nights"]
    groups = (trip.get("nights_chart") or {}).get("groups")
    if groups is None:
        groups = nights_payload(data, lang).get("groups") or []
    if not groups:
        body = f'<p class="empty"><strong>{esc(ui.get("nights_chart_empty") or ui.get("no_amount") or "")}</strong></p>'
    else:
        body = '<div class="chart" style="height:280px"><canvas id="nightsChart"></canvas></div>'
    return (
        f'<section id="nights" class="sec glass g-reg">'
        f'<p class="kicker">{esc(ui.get("nights") or "")}</p>'
        f"<h2>{esc(nights_h)}</h2>"
        f"{body}{cap_html}</section>"
    )


def render_map(data, ui, lang) -> str:
    """Kept for callers; the live map now lives in the opening spread."""
    return render_nights(data, ui, lang)


def as_item(it) -> str:
    if isinstance(it, HTML):
        return it
    return raw_ltr(it)


def blk(heading, items, status="", source="", ui=None, extra_class="") -> str:
    if not heading and not items:
        return ""
    bdg = badge(status, ui) if ui and status else ""
    src = f'<p class="src-note">{raw_ltr(source)}</p>' if source else ""
    lis = "".join(f"<li>{as_item(it)}</li>" for it in (items or []))
    ul = f'<ul class="blk-list">{lis}</ul>' if lis else ""
    return f'<div class="blk {extra_class}"><h4 class="blk-h">{raw_ltr(heading)} {bdg}</h4>{src}{ul}</div>'


def render_places(dest_id, dest_files, ui, lang, data, exclude_not_ok=False) -> str:
    groups = []
    for kind in ("food", "sights", "shopping", "daytrips"):
        blob = (dest_files or {}).get(kind) or {}
        places = list(blob.get("places") or [])
        if exclude_not_ok:
            places = [p for p in places if ((p.get("diet_fit") or {}).get("status") != "not_ok")]
        if not places:
            continue
        buckets = {}
        for pl in places:
            label = pl.get("type_label") or blob.get("group_heading") or pl.get("type") or kind
            buckets.setdefault(label, []).append(pl)
        for label, items in buckets.items():
            lis = [render_place(pl, dest_id, ui, lang, data) for pl in items]
            groups.append(
                f'<details class="recs-g"><summary><span>{esc(label)}</span>'
                f'<span class="n ltr tnum">{len(items)}</span></summary>'
                f'<ul class="rec-list">{"".join(lis)}</ul></details>'
            )
    if not groups:
        return ""
    intro = (dest_files.get("info") or {}).get("recs_intro") or ui["places_note"]
    return (
        f'<div class="recs glass g-thin"><h4>{icon("ph-star")} {esc(ui["places"])}</h4>'
        f'<p class="recs-note">{raw_ltr(intro)}</p>{"".join(groups)}</div>'
    )


def render_place(pl, dest_id, ui, lang, data) -> str:
    pid = pl.get("id") or ""
    name = loc(pl.get("name"), lang)
    price = pl.get("price_range") or ""
    price_h = f'<span class="price">{esc(price)}</span>' if price else ""
    df = pl.get("diet_fit") or {}
    caut = ""
    note = df.get("note") or pl.get("caution") or ""
    if df.get("status") == "caution" or pl.get("caution"):
        caut = f'<span class="caution" title="{esc(note)}">{icon("ph-warning")} {esc(note)}</span>' if note else ""
    opt = f' {badge("optional", ui)}' if pl.get("optional") else ""
    blurb = f'<p class="rec-blurb">{raw_ltr(pl.get("note") or "")}</p>' if pl.get("note") else ""
    order = f'<p class="rec-order">{raw_ltr(pl.get("order") or "")}</p>' if pl.get("order") else ""
    rec_caut = f'<p class="rec-caut">{raw_ltr(pl.get("caution") or "")}</p>' if pl.get("caution") else ""
    links = []
    for m in pl.get("maps") or []:
        href = m.get("href") if isinstance(m, dict) else (m[1] if len(m) > 1 else "")
        label = (m.get("label") if isinstance(m, dict) else (m[0] if m else "")) or ui["maps"]
        if href:
            links.append(
                f'<a class="maps" href="{esc(href)}" target="_blank" rel="noopener noreferrer">'
                f'{icon("ph-map-pin")} {esc(label)}</a>'
            )
    if not pl.get("maps") and pl.get("maps_url"):
        links.append(
            f'<a class="maps" href="{esc(pl["maps_url"])}" target="_blank" rel="noopener noreferrer">'
            f'{icon("ph-map-pin")} {esc(ui["maps"])}</a>'
        )
    if pl.get("url"):
        links.append(ext(pl["url"], "link"))
    for s in pl.get("sources") or []:
        href = s.get("href") if isinstance(s, dict) else (s[1] if len(s) > 1 else "")
        label = (s.get("label") if isinstance(s, dict) else (s[0] if s else "")) or ""
        if href and href != pl.get("url"):
            links.append(ext(href, label or "source"))
    hours = f'<p class="rec-hours">{raw_ltr(pl["hours"])}</p>' if pl.get("hours") else ""
    res = reservation_html(pl, ui, data)
    return (
        f'<li class="rec" id="{esc(pid)}"><div class="rec-top"><b>{esc(name)}</b>{price_h}{caut}{opt}</div>'
        f"{blurb}{order}{rec_caut}{hours}{res}"
        f'<div class="rec-links">{"".join(links)}</div></li>'
    )

def render_xfer(data, x, ui, lang) -> str:
    st = status_of_xfer(data, x)
    cls = "item ticket xfer rv"
    if st == "booked":
        cls += " is-closed"
    if x.get("optional") or st == "optional":
        cls += " is-optional"
    if x.get("boundary"):
        cls += " xfer-boundary"
    ic = x.get("icon") or MODE_ICON.get(x.get("mode") or "", "ph-path")
    route = x.get("route_label") or f'{x.get("from", "")} -> {x.get("to", "")}'
    meta_bits = []
    meta_bits.extend(xfer_when_bits(x))
    carrier = " ".join(filter(None, [x.get("carrier") or "", x.get("number") or ""]))
    if carrier:
        meta_bits.append(f"<span>{raw_ltr(carrier)}</span>")
    meta_bits.append(badge(st, ui, optional=x.get("optional")))
    b = booking_by_id(data, x.get("booking_id")) if x.get("booking_id") else None
    rows = []
    heading = " ".join(filter(None, [x.get("carrier") or "", x.get("number") or ""]))
    if not heading.strip():
        heading = ui.get("transfer") or "Transfer"
    items = []
    if b:
        if b.get("confirmation_code"):
            extras = ""
            if b.get("confirmation_link"):
                extras += " " + ext(b["confirmation_link"], ui["email"])
            if b.get("manage_url"):
                extras += " " + ext(b.get("manage_url"), ui["manage"])
            if b.get("checkin_url"):
                extras += " " + ext(b.get("checkin_url"), ui["checkin"])
            items.append(HTML(
                f'{esc(ui["code"])}: <strong><bdi class="tnum">{esc(b["confirmation_code"])}</bdi></strong> '
                + copybtn(b["confirmation_code"], ui)
                + extras
            ))
        if b.get("cabin"):
            items.append(b["cabin"])
        if b.get("seats"):
            items.append(b["seats"])
        if b.get("notes"):
            items.append(b["notes"])
        price = b.get("price") or {}
        if price.get("amount") is not None:
            items.append(HTML(money(price["amount"], price.get("currency"))))
        for d in b.get("details") or []:
            if isinstance(d, dict):
                items.append(HTML(f'{esc(d.get("label") or "")}: {raw_ltr(d.get("value") or "")}'))
            else:
                items.append(str(d))
    if x.get("notes"):
        items.append(x["notes"])
    for tip in x.get("tips") or []:
        items.append(tip)
    for block in x.get("details_blocks") or []:
        rows.append(blk(block.get("heading") or "", block.get("items") or [], ui=ui))
    if items:
        rows.insert(0, blk(heading, items, status=st, ui=ui))
    inner = "".join(rows)
    xid = x.get("id") or "xfer"
    return (
        f'<article class="{cls}" id="xfer-{esc(xid)}">'
        f'{date_col(transfer_date(data, x), lang)}'
        f'<div class="node" aria-hidden="true"><i class="dot"></i></div>'
        f'<div class="col">'
        f'<span class="pin" aria-hidden="true"></span>'
        f'<button type="button" class="xfer-sum" aria-expanded="false" aria-controls="xfer-{esc(xid)}-d">'
        f'<span class="xfer-head">{xfer_chip(x.get("mode") or ic)}<span class="xfer-route">{raw_ltr(route)}</span></span>'
        f'<span class="xfer-meta">{"".join(meta_bits)}</span>'
        f'{icon("ph-caret-down")}</button>'
        f'{fold(inner, "xfer-" + str(xid) + "-d")}</div></article>'
    )


def render_stop(data, dest, index, ui, lang, exclude_not_ok=False) -> str:
    did = dest["id"]
    files = (data.get("destinations") or {}).get(did) or {}
    info = files.get("info") or {"id": did}
    optional = bool(dest.get("optional"))
    stay_st = info.get("stay_status") or ("booked" if info.get("stay_booking_id") else "open")
    stay_st_badge = "optional" if optional else ("booked" if stay_st == "booked" else "open")
    cls = "item stay stop rv"
    if stay_st == "booked":
        cls += " is-closed"
    if optional:
        cls += " is-optional"
    name = loc(dest.get("name"), lang) or did
    ic = dest.get("icon") or "ph-map-pin"
    dates = dest.get("dates") or {}
    date_lbl = ""
    if dates.get("start") and dates.get("end"):
        def fmt(s):
            d = date.fromisoformat(s)
            return f"{d.day:02d}.{d.month:02d}"
        date_lbl = f"{fmt(dates['start'])}–{fmt(dates['end'])}"
    nights = dest.get("nights")
    nights_undecided = nights is None and dest.get("nights_min") is not None
    if nights_undecided:
        tmpl = ui.get("nights_range_undecided") or "{min}–{max} nights"
        nights_lbl = tmpl.replace("{min}", str(dest["nights_min"])).replace(
            "{max}", str(dest.get("nights_max") if dest.get("nights_max") is not None else dest["nights_min"])
        )
    elif nights is not None:
        nights_lbl = f"{nights} {ui['nights'] if nights != 1 else ui['night']}"
    else:
        nights_lbl = ""
    stay_label = info.get("stay_label") or ""
    meta_bits = []
    if date_lbl:
        meta_bits.append(bdi(esc(date_lbl)))
    if nights_undecided:
        meta_bits.append(f'<span class="badge pick">{esc(nights_lbl)}</span>')
    elif nights_lbl:
        meta_bits.append(f"<span>{esc(nights_lbl)}</span>")
    if optional:
        opt_lbl = dest.get("optional_label") or (
            ui.get("optional_undecided") if dest.get("certainty") != "sure" else ui.get("optional")
        ) or ui["optional"]
        meta_bits.append(f'<span class="badge opt">{esc(opt_lbl)}</span>')
    elif stay_st == "booked":
        meta_bits.append(badge("booked", ui))
    if stay_st == "booked" and stay_label:
        _bn = re.sub(r"[\s✓✔]+", "", ui.get("booked") or "")
        _ln = re.sub(r"[\s✓✔]+", "", stay_label)
        if _ln.casefold() != _bn.casefold():
            meta_bits.append(f"<span>{esc(stay_label)}</span>")
    elif stay_st != "booked" and not nights_undecided:
        meta_bits.append(f'<span class="badge wait">{esc(stay_label or ui["stay_open"])}</span>')
    meta = "".join(meta_bits)
    xfer_line = f'<p class="stop-xfer">{raw_ltr(info["summary_transfer"])}</p>' if info.get("summary_transfer") else ""
    summary_note = dest.get("summary_note") or info.get("summary_note")
    note_line = f'<p class="opt-note">{raw_ltr(summary_note)}</p>' if summary_note else ""
    if info.get("local_address"):
        addr = info["local_address"]
        taxi = (
            f'<div class="taxi-card glass g-thick" id="taxi-{esc(did)}">'
            f'<div class="taxi-lbl">{esc(ui["taxi_title"])}</div>'
            f'<div class="taxi-name">{esc(name)}</div>'
            f'<div class="taxi-addr">{esc(addr).replace(chr(10), "<br>")}</div>'
            f'<div class="today-actions">'
            + (tel_link(info["phone"]) if info.get("phone") else "")
            + (f'<a class="navbtn" href="{esc(info["nav_url"])}" target="_blank" rel="noopener noreferrer">{icon("ph-navigation-arrow")} {esc(ui.get("navigate_stay") or ui["navigate"])}</a>' if info.get("nav_url") else "")
            + copybtn(addr.replace("\n", " "), ui)
            + "</div></div>"
        )
    else:
        taxi = (
            f'<div class="taxi-card glass g-thin is-empty" hidden>'
            f'<div class="taxi-lbl">{esc(ui["taxi_title"])}</div>'
            f'<p class="recs-empty">{esc(ui["taxi_empty"])}</p></div>'
        )
    season = (
        f'<div class="season-note glass g-thin">{icon("ph-warning-circle")} {raw_ltr(info["season_note"])}</div>'
        if info.get("season_note") else ""
    )
    blocks = []
    arr = info.get("arrival") or {}
    if arr.get("items") or arr.get("title"):
        blocks.append(blk(arr.get("title") or ui["arrival"], arr.get("items") or [], status=arr.get("status") or "", ui=ui))
    for b in info.get("blocks") or []:
        blocks.append(blk(b.get("heading") or "", b.get("items") or [], status=b.get("status") or "", ui=ui))
    wx = info.get("weather") or {}
    if wx.get("items"):
        blocks.append(blk(wx.get("title") or ui["weather"], wx["items"], source=wx.get("source") or "", ui=ui, extra_class="wx"))
    food = info.get("food_notes") or {}
    if food.get("items"):
        blocks.append(blk(food.get("title") or ui["food"], food["items"], source=food.get("source") or "", ui=ui, extra_class="food"))
    recs = render_places(did, files, ui, lang, data, exclude_not_ok=exclude_not_ok)
    nav_btn = ""
    if info.get("nav_url"):
        nav_btn = (
            f'<a class="navbtn press" href="{esc(info["nav_url"])}" target="_blank" rel="noopener noreferrer">'
            f'{icon("ph-navigation-arrow")} {esc(ui.get("navigate_stay") or ui["navigate"])}</a>'
        )
    opt_attr = ' data-optional="true"' if optional else ""
    return (
        f'<article class="{cls}" id="stop-{esc(did)}" data-id="{esc(did)}"{opt_attr}>'
        f'{date_col(dates.get("start"), lang)}'
        f'<div class="node" aria-hidden="true"><i class="dot"></i></div>'
        f'<div class="col">'
        f'<span class="pin">{index}</span>'
        f'<div class="stop-sum">'
        f'<div class="stop-sum-top"><h3>{icon(ic)} {esc(name)}</h3></div>'
        f'<div class="stop-meta">{meta}</div>{xfer_line}{note_line}'
        f'<div class="stop-actions">'
        f'<button type="button" class="stop-toggle press" aria-expanded="false" aria-controls="{esc(did)}-detail">{esc(ui["more"])} {icon("ph-caret-down")}</button>'
        f'{nav_btn}</div></div>'
        f'<div class="fold"><div class="fold-inner" inert aria-hidden="true">'
        f'<div class="stop-detail" id="{esc(did)}-detail">'
        f'<button type="button" class="sheet-close press" aria-label="{esc(ui["close"])}">{icon("ph-x")} {esc(ui["close"])}</button>'
        f'{season}{taxi}<div class="rows">{"".join(blocks)}</div>{recs}'
        f'</div></div></div></div></article>'
    )


def render_country_axis(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    cid = country["id"]
    dests = [d for d in data["trip"]["destinations"] if d.get("country") == cid]
    leading, after, trailing = transfers_in_country(data, cid)
    color = safe_css_color(region_color(country, region_i), REGION_COLORS[region_i % len(REGION_COLORS)])
    parts = []
    for x in leading:
        parts.append(render_xfer(data, x, ui, lang))
    all_dests = data["trip"]["destinations"]
    trailing_ids = {x.get("id") for x in trailing}
    for d in dests:
        idx = next(i for i, x in enumerate(all_dests, 1) if x["id"] == d["id"])
        parts.append(render_stop(data, d, idx, ui, lang, exclude_not_ok=exclude_not_ok))
        for x in after.get(d["id"], []):
            if x.get("id") in trailing_ids:
                continue
            parts.append(render_xfer(data, x, ui, lang))
    for x in trailing:
        parts.append(render_xfer(data, x, ui, lang))
    span, nights_h, opt_h, _dests = country_span_and_nights(data, country, lang, ui)
    name = loc(country.get("name"), lang) or cid
    meta = f'<bdi class="tnum" dir="ltr">{esc(span)}</bdi> · {esc(nights_h)}'
    if opt_h:
        meta += f' <span class="stop-opt">{esc(opt_h)}</span>'
    flag = render_flag(country, "sm")
    return (
        f'<section id="{esc(cid)}" class="country-block" data-region="{region_i}" style="--block-color:var(--region-{region_i});--region:var(--region-{region_i})">'
        f'<div class="country-head"><span class="nm">{esc(name)}</span>'
        f'<span class="meta">{meta}</span><span class="rule"></span>{flag}</div>'
        f'<div class="tline" data-region="{region_i}" style="--block-color:var(--region-{region_i});--region:var(--region-{region_i})">{"".join(parts)}</div>'
        "</section>"
    )


def render_country_rest(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    color = safe_css_color(region_color(country, region_i), REGION_COLORS[region_i % len(REGION_COLORS)])
    chunks = [
        render_practical(country, ui, lang, region_i, color),
        render_phrases(country, ui, lang),
        render_entry(country, ui, lang),
        render_packing_country(country, ui, lang),
        render_decisions(data, country["id"], ui, lang),
        render_days(data, country["id"], country, ui, lang, first=(region_i == 0)),
    ]
    return "\n".join(c for c in chunks if c)


def render_country(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    return (
        render_country_axis(data, country, region_i, ui, lang, exclude_not_ok=exclude_not_ok)
        + render_country_rest(data, country, region_i, ui, lang, exclude_not_ok=exclude_not_ok)
    )


def kv_row(label, body) -> str:
    return f'<div class="row glass g-thin"><span class="k">{raw_ltr(label)}</span><span class="v">{body}</span></div>'


def render_practical(country, ui, lang, region_i, color) -> str:
    rows = [kv_row(p.get("label") or "", raw_ltr(p.get("body") or "")) for p in (country.get("practical") or [])]
    em = country.get("emergency") or []
    if em:
        bits = ", ".join(
            f'{esc(e.get("label") or "")} {tel_link(e.get("number") or "", e.get("tel"))}'
            for e in em
        )
        rows.append(
            f'<div class="row glass g-thin"><span class="k">{esc(ui["emergency"])}</span><span class="v">{bits}</span></div>'
        )
    emb = country.get("embassy") or {}
    if emb.get("name") or emb.get("phone"):
        body = "<br>".join(filter(None, [
            f'<bdi class="ltr">{esc(emb.get("address") or "")}</bdi>' if emb.get("address") else "",
            tel_link(emb.get("phone") or "") if emb.get("phone") else "",
            (ui["emergency"] + " " + tel_link(emb.get("phone_emergency") or "")) if emb.get("phone_emergency") else "",
            f'<bdi class="ltr">{esc(emb.get("email") or "")}</bdi>' if emb.get("email") else "",
            ext(emb.get("url"), emb.get("source") or emb.get("url") or "") if emb.get("url") else "",
        ]))
        name = emb.get("name") or ui["embassy"]
        name_h = ext(emb.get("url"), name) if emb.get("url") else esc(name)
        rows.append(f'<div class="row glass g-thin"><span class="k">{name_h}</span><span class="v">{body}</span></div>')
    if not rows:
        return ""
    cid = country["id"]
    h = country.get("practical_headline") or ui["practical"]
    lede = country.get("practical_lede") or ""
    return (
        f'<section id="{esc(cid)}-practical" class="sec country-chunk" data-region="{region_i}" style="--region:var(--region-{region_i})">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-compass")} {esc(ui["practical"])} · {esc(loc(country.get("name"), lang))}</div>'
        f'<h2>{raw_ltr(h)}</h2><p>{raw_ltr(lede)}</p></div>'
        f'<div class="card glass g-reg rv"><h3 style="font-size:18px;font-weight:700;margin-bottom:12px">{esc(loc(country.get("name"), lang))}</h3>'
        f'<div class="kv-stack">{"".join(rows)}</div></div></section>'
    )


def render_phrases(country, ui, lang) -> str:
    ph = country.get("phrases") or {}
    groups = ph.get("groups") or []
    if not groups and not ph.get("headline"):
        return ""
    intro = "".join(f'<p class="note">{raw_ltr(x)}</p>' for x in (ph.get("intro") or []))
    cols = []
    for g in groups:
        items = []
        for it in g.get("items") or []:
            items.append(f'<p class="phrase local-script" lang="{esc(it.get("lang") or "")}">{esc(it.get("text") or "")}</p>')
            if it.get("romanization") or it.get("meaning"):
                roma = it.get("romanization") or ""
                mean = it.get("meaning") or ""
                items.append(f'<p class="roma"><bdi>{esc(roma)}</bdi>{" - " + esc(mean) if mean else ""}</p>')
            if it.get("text"):
                items.append(copybtn(it["text"], ui))
        cols.append(
            f'<div class="waiter-col"><h4>{esc(g.get("language_label") or g.get("label") or "")}</h4>{"".join(items)}</div>'
        )
    cid = country["id"]
    return (
        f'<aside class="waiter phrases card glass g-thick rv" id="phrases-{esc(cid)}">'
        f'<h3>{icon("ph-identification-card")} {esc(ph.get("headline") or ui.get("dietary") or "")}</h3>'
        f'{intro}{"".join(cols)}</aside>'
    )


def render_entry(country, ui, lang) -> str:
    ed = country.get("entry_docs") or {}
    items = ed.get("items") or []
    if not items and not ed.get("headline"):
        return ""
    lis = "".join(f"<li><span>{raw_ltr(i)}</span></li>" for i in items)
    cid = country["id"]
    return (
        f'<section id="{esc(cid)}-docs" class="sec country-chunk">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-identification-card")} {esc(ui["docs"])} · {esc(loc(country.get("name"), lang))}</div>'
        f'<h2>{raw_ltr(ed.get("headline") or "")}</h2><p>{raw_ltr(ed.get("lede") or "")}</p></div>'
        f'<div class="card glass g-reg rv"><ul class="bul">{lis}</ul></div></section>'
    )


def render_packing_country(country, ui, lang) -> str:
    pk = country.get("packing") or {}
    items = pk.get("items") or []
    if not items and not pk.get("headline") and not pk.get("callout"):
        return ""
    callout = ""
    if pk.get("callout"):
        callout = (
            f'<div class="card glass g-thick rv" style="margin-bottom:var(--s4);padding:16px 20px">'
            f'{icon("ph-truck")} {raw_ltr(pk["callout"])}</div>'
        )
    lis = "".join(f"<li><span>{raw_ltr(i)}</span></li>" for i in items)
    cid = country["id"]
    return (
        f'<section id="{esc(cid)}-pack" class="sec country-chunk">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-suitcase-rolling")} {esc(ui["packing"])} · {esc(loc(country.get("name"), lang))}</div>'
        f'<h2>{raw_ltr(pk.get("headline") or "")}</h2><p>{raw_ltr(pk.get("lede") or "")}</p></div>'
        f'{callout}<div class="card glass g-reg rv"><ul class="bul">{lis}</ul></div></section>'
    )

def render_decisions(data, cid, ui, lang) -> str:
    decs = data.get("decisions") or {}
    all_dec = list(decs.get("decisions") if isinstance(decs, dict) else [])
    items = [d for d in all_dec if d.get("country") == cid]
    if not items:
        return ""
    out = []
    for n, d in enumerate(items):
        opts = d.get("options") or []
        cards = []
        rec = set(d.get("recommended") or [])
        for i, o in enumerate(opts):
            tag = o.get("tag") or (ui["recommended"] if i in rec else "")
            tag_h = f'<span class="tag">{icon("ph-star")} {esc(tag)}</span>' if tag else ""
            best = " best" if i in rec else ""
            sel = " sel" if i == 0 else ""
            cards.append(
                f'<div class="opt glass g-reg{best} rv press{sel}" data-opt="{i}" data-decision="{esc(d["id"])}" role="button" tabindex="0">'
                f"{tag_h}<h4>{esc(o.get('name') or '')}</h4>"
                f'<div class="sub">{esc(o.get("sub") or "")}</div>'
                f'<p>{esc(o.get("card") or "")}</p></div>'
            )
        seg = "".join(
            f'<button type="button" aria-pressed="{"true" if i == 0 else "false"}" data-s="{i}">{esc(o.get("name") or "")}</button>'
            for i, o in enumerate(opts)
        )
        chart = ""
        if opts and any("k" in o or "o" in o for o in opts):
            chart = (
                '<div class="viz glass g-reg rv" style="margin-top:var(--s4)">'
                f'<div class="viz-head"><h3>{esc(d.get("chart_caption") or "")}</h3></div>'
                f'<div class="chart" style="height:240px"><canvas id="optChart-{esc(d["id"])}"></canvas></div>'
                f'<p class="caption">{icon("ph-info")}<span>{raw_ltr(d.get("chart_caption") or "")}</span></p></div>'
            )
        steps = ""
        if opts:
            steps = (
                '<div class="viz glass g-reg rv" style="margin-top:var(--s4)">'
                f'<div class="viz-head"><h3></h3><div class="seg glass g-thin seg-choice" id="optSeg-{esc(d["id"])}" role="group">{seg}</div></div>'
                f'<div class="split" id="optBar-{esc(d["id"])}" style="margin-bottom:var(--s4)" aria-hidden="true"></div>'
                f'<ol class="steps" id="optSteps-{esc(d["id"])}"></ol>'
                f'<p class="caption" id="optCap-{esc(d["id"])}">{icon("ph-info")}<span></span></p>'
                f'<p class="choice-flag" id="choiceFlag-{esc(d["id"])}" hidden></p></div>'
            )
        note = ""
        if d.get("card_html_note") and not opts:
            note = (
                f'<div class="card glass g-reg rv is-optional" style="margin-top:var(--s6);padding:16px 20px">'
                f'<h3>{raw_ltr(d.get("card_html_note") or "")}</h3>'
                f'<p>{raw_ltr(d.get("lede") or "")}</p></div>'
            )
        sid = "choose" if all_dec and d is all_dec[0] else f'choose-{d["id"]}'
        out.append(
            f'<section id="{esc(sid)}" class="sec">'
            f'<div class="sec-head rv"><div class="act">{icon("ph-path")} {esc(ui["choose"])}</div>'
            f'<h2>{raw_ltr(d.get("headline") or d.get("title") or "")}</h2>'
            f'<p>{raw_ltr(d.get("lede") or "")}</p></div>'
            f'<div class="opts" id="optCards-{esc(d["id"])}">{"".join(cards)}</div>'
            f'{steps}{chart}{note}</section>'
        )
    return "\n".join(out)


def render_days(data, cid, country, ui, lang, first=False) -> str:
    days = []
    for d in data["trip"]["destinations"]:
        if d.get("country") != cid:
            continue
        blob = ((data.get("destinations") or {}).get(d["id"]) or {}).get("days") or {}
        days.extend(blob.get("days") or [])
    days.sort(key=lambda x: x.get("date") or "")
    if not days:
        return ""
    rows = []
    for day in days:
        cls = "day glass g-thin"
        if day.get("optional"):
            cls += " is-optional"
        if day.get("status") == "booked":
            cls += " is-closed"
        if day.get("undecided") or day.get("status") == "open":
            cls += " open"
        dt = day.get("date") or ""
        try:
            dobj = date.fromisoformat(dt)
            short = dobj.strftime("%d.%m")
            key = dobj.strftime("%d.%m.%Y")
        except ValueError:
            short = dt
            key = dt
        opt = badge("optional", ui) if day.get("optional") else ""
        st = badge(day.get("status") or "", ui) if day.get("status") in ("booked", "open") else ""
        rows.append(
            f'<div class="{cls}" data-day="{esc(key)}" data-iso="{esc(dt)}">'
            f'<div><span class="d ltr tnum">{esc(short)}</span> <span class="w">{esc(day.get("weekday") or "")}</span></div>'
            f'<div><strong>{raw_ltr(day.get("title") or "")}</strong> {opt}{st}</div>'
            f'<div>{raw_ltr(day.get("body") or "")}</div></div>'
        )
    act = country.get("journal_act") or ui["journal"]
    head = country.get("journal_headline") or ""
    lede = country.get("journal_lede") or ""
    sid = "days" if first else f"days-{cid}"
    return (
        f'<section id="{esc(sid)}" class="sec country-chunk">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-calendar-blank")} {esc(act)}</div>'
        f'<h2>{raw_ltr(head)}</h2><p>{raw_ltr(lede)}</p></div>'
        f'<details class="more glass g-thin rv" open>'
        f'<summary>{icon("ph-calendar-blank")} {esc(loc(country.get("name"), lang))} {icon("ph-caret-down","chev")}</summary>'
        f'<div class="body"><div class="days">{"".join(rows)}</div></div></details></section>'
    )


def render_search(data, ui, lang) -> str:
    countries = country_list(data)
    segs = "".join(
        f'<button type="button" class="press" aria-pressed="{"true" if i == 0 else "false"}" data-c="{esc(c["id"])}">{esc(loc(c.get("name"), lang))}</button>'
        for i, c in enumerate(countries)
    )
    types, seen = [], set()
    for dest in (data.get("destinations") or {}).values():
        for kind in ("food", "sights", "shopping", "daytrips"):
            for pl in ((dest.get(kind) or {}).get("places") or []):
                t = pl.get("type") or kind
                if t not in seen:
                    seen.add(t)
                    types.append((t, pl.get("type_label") or t))
    chips = "".join(
        f'<button type="button" class="press" aria-pressed="false" data-t="{esc(t)}">{esc(lab)}</button>'
        for t, lab in types
    )
    return (
        f'<section id="recs-search" class="sec">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-magnifying-glass")} {esc(ui["search_places"])}</div>'
        f'<h2>{esc(ui["search_places"])}</h2><p>{esc(ui["search_lede"])}</p></div>'
        f'<div class="rsearch card glass g-reg rv" role="search">'
        f'<div class="seg rseg" id="rsCountry" role="group">{segs}</div>'
        f'<div class="rs-field"><label for="rsq">{esc(ui["search_places"])}</label>'
        f'<input id="rsq" type="search" placeholder="{esc(ui["search_placeholder"])}" autocomplete="off" enterkeyhint="search" spellcheck="false"></div>'
        f'<div class="rs-chips" id="rsTypes" role="group">{chips}</div>'
        f'<div class="rs-chips" id="rsCities" role="group"></div>'
        f'<p class="rs-count" id="rsCount" aria-live="polite"></p>'
        f'<ul class="rs-list" id="rsList"></ul>'
        f'<p class="rs-empty" id="rsEmpty" hidden>{esc(ui["search_empty"])}</p></div></section>'
    )


def fmt_home(n, home):
    if n is None:
        return ""
    sym = symbol(home)
    if abs(n - round(n)) < 0.05:
        n = int(round(n))
        return f"≈ {sym}{n:,}" if sym and len(sym) <= 2 else f"≈ {home} {n:,}"
    return f"≈ {sym}{n:,.2f}" if sym and len(sym) <= 2 else f"≈ {home} {n:,.2f}"


def render_budget(data, ui, lang) -> str:
    bud = derive_budget(data)
    home = bud["home"] or data["trip"].get("currency") or ""
    total = bud["booked_total_home"]
    total_disp = int(round(total)) if total else 0
    fx = data["trip"].get("fx") or {}
    hero_orig, booked_cards = [], []
    for r in bud["booked_rows"]:
        amt = money(r["amount"], r["currency"])
        home_amt = fmt_home(r["home_amount"], home)
        hero_orig.append(
            f'<span class="bud-pair"><span class="bud-lab">{esc(r["title"] or "")}</span>{amt}</span>'
        )
        code = r.get("confirmation_code")
        booked_cards.append(
            f'<div class="book glass g-thin"><div class="k">{esc(r["title"] or "")} '
            f'{badge("booked", ui)}</div><div class="d">{amt}'
            f'{" (" + raw_ltr(home_amt) + ")" if home_amt else ""}'
            f'{" · " + raw_ltr(r.get("notes") or "") if r.get("notes") else ""}'
            + (copybtn(code, ui) if code else "")
            + "</div></div>"
        )
    open_cards = []
    for e in bud["estimates"]:
        rng = ""
        if e.get("amount_min") is not None:
            rng = money(e["amount_min"], e.get("currency")) + "-" + money(e.get("amount_max"), e.get("currency"))
        elif e.get("amount") is not None:
            rng = money(e["amount"], e.get("currency"))
        open_cards.append(
            f'<div class="book glass g-thin"><div class="k">{esc(e.get("title") or "")} '
            f'<span class="badge wait">{esc(e.get("label") or ui["open"])}</span></div>'
            f'<div class="d">{rng} {raw_ltr(e.get("notes") or "")}</div></div>'
        )
    for r in bud["open_rows"]:
        if any(e.get("id") == r["id"] or e.get("booking_id") == r["id"] for e in bud["estimates"]):
            continue
        open_cards.append(
            f'<div class="book glass g-thin"><div class="k">{esc(r.get("title") or "")} {badge("open", ui)}</div>'
            f'<div class="d">{raw_ltr(r.get("notes") or "")}</div></div>'
        )
    est_chart = ""
    if any(e.get("chart_series") for e in bud["estimates"]):
        est_chart = (
            '<div class="viz glass g-reg rv" style="margin-top:var(--s4)">'
            f'<div class="viz-head"><h3>{esc(ui["budget_open"])}</h3></div>'
            f'<div class="chart" style="height:260px"><canvas id="xferChart"></canvas></div></div>'
        )
    fx_date = fx.get("date") or ""
    sym = symbol(home)
    empty_booked = "".join(booked_cards) or ('<p class="src-note">' + esc(ui["open"]) + "</p>")
    total_txt = f"≈ {sym}{total_disp:,}" if sym and len(sym) <= 2 else f"≈ {home} {total_disp:,}"
    return (
        f'<section id="budget" class="sec">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-wallet")} {esc(ui["budget"])}</div>'
        f'<h2>{esc(ui["budget"])}</h2>'
        f'<p>{raw_ltr(fx.get("label") or ui["fx"])}{(" · " + raw_ltr(fx_date)) if fx_date else ""}</p></div>'
        f'<div class="bud-hero card glass g-thick rv"><div class="lab">{esc(ui["budget_hero"])}</div>'
        f'<div class="n num">{bdi(esc(total_txt))}</div>'
        f'<p class="orig bud-pairs">{"".join(hero_orig)}</p></div>'
        f'<div class="bud-break"><div class="viz glass g-reg rv">'
        f'<div class="viz-head"><h3>{esc(ui["budget_booked"])}</h3><span class="src">{esc(fx.get("label") or "")}</span></div>'
        + (f'<div class="chart" style="height:220px"><canvas id="bookedChart"></canvas></div>' if booked_cards and total else f'<p class="empty"><strong>{esc(ui.get("no_amount") or "")}</strong></p>')
        + '</div>'
        f'<div class="grid2" style="margin-top:var(--s4)">'
        f'<div class="card glass g-reg rv"><h3 style="font-size:16px;font-weight:700;margin-bottom:12px">{icon("ph-check-circle")} {esc(ui["budget_booked"])}</h3>'
        f'{empty_booked}</div>'
        f'<div class="card glass g-reg rv bud-open"><h3 style="font-size:16px;font-weight:700;margin-bottom:12px">{icon("ph-hourglass")} {esc(ui["budget_open"])}</h3>'
        f'{"".join(open_cards)}</div></div></div>{est_chart}</section>'
    )


def render_fx(data, ui) -> str:
    fx = data["trip"].get("fx") or {}
    rates = fx.get("rates_to_home") or {}
    if not rates:
        return ""
    home = fx.get("home") or data["trip"].get("currency") or ""
    opts = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in rates)
    return (
        f'<section id="fx" class="sec">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-currency-circle-dollar")} {esc(ui["fx"])}</div>'
        f'<h2>{esc(ui["fx"])}{(" · " + raw_ltr(fx.get("date") or "")) if fx.get("date") else ""}</h2>'
        f'<p>{raw_ltr(fx.get("label") or "")}</p></div>'
        f'<div class="card glass g-reg rv" style="margin-top:var(--s4)"><div class="convert">'
        f'<input id="fxAmt" type="number" inputmode="decimal" value="100" min="0" aria-label="{esc(ui["fx_amount"])}">'
        f'<select id="fxFrom" aria-label="{esc(ui["fx_currency"])}">{opts}</select>'
        f'<span class="muted">~</span>'
        f'<output id="fxOut" for="fxAmt fxFrom">{esc(symbol(home) or home)}</output>'
        f'</div></div></section>'
    )


def render_shared(data, ui, lang) -> str:
    trip = data["trip"]
    out = []
    docs = trip.get("shared_docs") or {}
    if docs.get("items") or docs.get("headline"):
        lis = "".join(f"<li><span>{raw_ltr(i)}</span></li>" for i in (docs.get("items") or []))
        out.append(
            f'<section id="docs" class="sec"><div class="sec-head rv">'
            f'<div class="act">{icon("ph-identification-card")} {esc(ui["docs"])}</div>'
            f'<h2>{raw_ltr(docs.get("headline") or "")}</h2><p>{raw_ltr(docs.get("lede") or "")}</p></div>'
            f'<div class="card glass g-reg rv"><ul class="bul">{lis}</ul></div></section>'
        )
    pk = trip.get("shared_packing") or {}
    if pk.get("items") or pk.get("headline"):
        lis = "".join(f"<li><span>{raw_ltr(i)}</span></li>" for i in (pk.get("items") or []))
        note = f'<p class="src-note">{raw_ltr(pk.get("note") or "")}</p>' if pk.get("note") else ""
        out.append(
            f'<section id="pack" class="sec"><div class="sec-head rv">'
            f'<div class="act">{icon("ph-suitcase-rolling")} {esc(ui["packing"])}</div>'
            f'<h2>{raw_ltr(pk.get("headline") or "")}</h2><p>{raw_ltr(pk.get("lede") or "")}</p></div>'
            f'<div class="card glass g-reg rv" style="margin-top:var(--s4)"><ul class="bul">{lis}</ul>{note}</div></section>'
        )
    tasks = data.get("tasks") or {}
    if tasks and (tasks.get("done") or tasks.get("open")):
        def lis_t(items, done=False):
            bits = []
            for it in items or []:
                text = it.get("text") if isinstance(it, dict) else str(it)
                opt = it.get("optional") if isinstance(it, dict) else False
                cls = ' class="is-optional"' if opt else ""
                b = badge("optional", ui) if opt else (badge("booked", ui) if done else "")
                bits.append(f"<li{cls}><span>{b} {raw_ltr(text)}</span></li>")
            return "".join(bits)
        out.append(
            f'<section id="tasks" class="sec"><div class="sec-head rv">'
            f'<div class="act">{icon("ph-list-checks")} {esc(ui["tasks_open"])}</div>'
            f'<h2>{raw_ltr(tasks.get("headline") or "")}</h2><p>{raw_ltr(tasks.get("lede") or "")}</p></div>'
            f'<div class="grid2"><div class="card glass g-reg rv">'
            f'<h3 style="font-size:16px;font-weight:700;margin-bottom:10px;color:var(--pos)">{icon("ph-check-circle")} {esc(ui["tasks_done"])}</h3>'
            f'<ul class="bul">{lis_t(tasks.get("done"), done=True)}</ul></div>'
            f'<div class="card glass g-reg rv">'
            f'<h3 style="font-size:16px;font-weight:700;margin-bottom:10px;color:var(--warn)">{icon("ph-circle-dashed")} {esc(ui["tasks_open"])}</h3>'
            f'<ul class="bul">{lis_t(tasks.get("open"))}</ul></div></div></section>'
        )
    pack_i = next((i for i, s in enumerate(out) if 'id="pack"' in s), None)
    task_i = next((i for i, s in enumerate(out) if 'id="tasks"' in s), None)
    if pack_i is not None and task_i is not None:
        wrapped = f'<div class="duo">{out[pack_i]}{out[task_i]}</div>'
        kept, done = [], False
        for k, s in enumerate(out):
            if k in (pack_i, task_i):
                if not done:
                    kept.append(wrapped)
                    done = True
                continue
            kept.append(s)
        out = kept
    return "\n".join(out)


def render_pocket(data, ui, lang) -> str:
    countries = country_list(data)
    tabs = [f'<button type="button" data-tab="trip" aria-pressed="true">{esc(ui["general"])}</button>']
    for c in countries:
        tabs.append(
            f'<button type="button" data-tab="{esc(c["id"])}" aria-pressed="false">{esc(loc(c.get("name"), lang))}</button>'
        )
    booked = [b for b in data["bookings"].get("bookings") or [] if b.get("status") == "booked"]

    def booking_row(b):
        code = b.get("confirmation_code") or ""
        return (
            f'<div class="pk-row"><span>{esc(b.get("title") or "")} {badge("booked", ui)}</span>'
            + (f'<span class="code">{esc(code)}</span>{copybtn(code, ui)}' if code else "")
            + (ext(b.get("confirmation_link"), ui["email"]) if b.get("confirmation_link") else "")
            + (ext(b.get("manage_url"), ui["manage"]) if b.get("manage_url") else "")
            + "</div>"
        )

    trip_booked = [b for b in booked if not b.get("destination_id")]
    dest_booked = [b for b in booked if b.get("destination_id")]
    trip_pane = (
        f'<div data-pane="trip" class="on"><div class="p-inner"><div class="block"><h4>{esc(ui["bookings"])}</h4>'
        + "".join(booking_row(b) for b in trip_booked)
        + "</div></div></div>"
    )
    panes = [trip_pane]
    dest_of = {d["id"]: d.get("country") for d in data["trip"]["destinations"]}
    for c in countries:
        cid = c["id"]
        blocks = []
        local_b = [b for b in dest_booked if dest_of.get(b.get("destination_id")) == cid]
        if local_b:
            blocks.append(f'<div class="block"><h4>{esc(ui["bookings"])}</h4>' + "".join(booking_row(b) for b in local_b) + "</div>")
        em = c.get("emergency") or []
        if em:
            rows = "".join(
                f'<div class="pk-row"><span>{esc(e.get("label") or "")}</span> {tel_link(e.get("number") or "", e.get("tel"))}</div>'
                for e in em
            )
            blocks.append(f'<div class="block"><h4>{esc(ui["emergency"])} - {esc(loc(c.get("name"), lang))}</h4>{rows}</div>')
        emb = c.get("embassy") or {}
        if emb.get("phone") or emb.get("name"):
            blocks.append(
                f'<div class="block"><h4>{esc(ui["embassy"])}</h4><div class="pk-row"><span>{esc(emb.get("name") or "")}</span> '
                + (tel_link(emb.get("phone") or "") if emb.get("phone") else "")
                + (" · " + tel_link(emb.get("phone_emergency") or "") if emb.get("phone_emergency") else "")
                + (ext(emb.get("url"), ui["embassy"]) if emb.get("url") else "")
                + "</div></div>"
            )
        groups = (c.get("phrases") or {}).get("groups") or []
        if groups:
            texts = []
            for g in groups:
                for it in (g.get("items") or [])[:2]:
                    if it.get("text"):
                        texts.append(f'<p class="phrase" style="font-size:22px">{esc(it["text"])}</p>')
            if texts:
                blocks.append(
                    f'<div class="block"><h4>{esc((c.get("phrases") or {}).get("headline") or "")}</h4>'
                    + "".join(texts)
                    + f'<a class="ext" href="#phrases-{esc(cid)}">{esc(ui["phrases_link"])}</a></div>'
                )
        panes.append(f'<div data-pane="{esc(cid)}"><div class="p-inner">{"".join(blocks)}</div></div>')
    return (
        f'<button type="button" class="pocket-toggle press" id="pocketBtn" aria-controls="pocket" aria-expanded="false" aria-label="{esc(ui["pocket"])}">{icon("ph-identification-card")} {esc(ui["pocket"])}</button>'
        f'<aside class="pocket glass g-thick" id="pocket" role="dialog" aria-label="{esc(ui["pocket"])}" aria-hidden="true" inert>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
        f'<h3>{icon("ph-identification-card")} {esc(ui["pocket_title"])}</h3>'
        f'<button type="button" class="sheet-close press" id="pocketClose" aria-label="{esc(ui["close"])}">{icon("ph-x")}</button></div>'
        f'<div class="block"><h4>{esc(ui["search"])}</h4>'
        f'<div class="pk-row"><a class="ext" href="#recs-search" id="pocketSearch">{icon("ph-magnifying-glass")} {esc(ui["pocket_search"])}</a></div></div>'
        f'<div class="pseg" id="pocketSeg" role="tablist">{"".join(tabs)}</div>'
        f'{"".join(panes)}</aside>'
        f'<div class="scrim" id="sheetScrim" hidden></div><div class="scrim" id="scrim" hidden></div>'
    )


def render_instruments(data, ui, lang) -> str:
    trip = data["trip"]
    dep_h = countdown_caption(trip, ui)
    deadlines = deadline_cards(data, ui, lang)
    codes = []
    for b in data["bookings"].get("bookings") or []:
        if b.get("status") != "booked" or not b.get("confirmation_code"):
            continue
        title = booking_display_title(b)
        code = b["confirmation_code"]
        codes.append(
            f'<div class="code-row"><div class="code-meta"><span class="who">{esc(title)}</span>'
            f'<span class="code tnum">{esc(code)}</span></div>'
            f'<div class="code-actions">{badge("booked", ui)}{copybtn(code, ui)}</div></div>'
        )
    emer_blocks = []
    for c in country_list(data):
        em = c.get("emergency") or []
        if not em:
            continue
        name = loc(c.get("name"), lang)
        links = "".join(_emer_link(e) for e in em)
        emer_blocks.append(
            f'<h2>{esc(ui["emergency"])}'
            + (f", {esc(name)}" if name else "")
            + f'</h2><div class="emer">{links}</div>'
        )
    fx = trip.get("fx") or {}
    rates = fx.get("rates_to_home") or {}
    home = fx.get("home") or trip.get("currency") or ""
    snap = []
    for cur, rate in list(rates.items())[:3]:
        try:
            r = float(rate)
        except (TypeError, ValueError):
            continue
        amt = 1000 if r < 0.05 else (100 if r < 1 else 1)
        home_amt = amt * r
        home_txt = f"{home_amt:.2f}".rstrip("0").rstrip(".")
        snap.append(
            f'<div class="cell"><span class="a">{esc(symbol(cur))}{amt:,}</span>'
            f'<span class="b">{esc(symbol(home))}{esc(home_txt)}</span></div>'
        )
    fx_html = ""
    if snap:
        fx_date = fx.get("date") or ""
        fx_html = (
            f'<hr class="hr"><h2>{esc(ui["fx"])}</h2>'
            f'<div class="fx-snap">{"".join(snap)}</div>'
            f'<div class="src">{raw_ltr(fx.get("label") or "")}'
            + (f' · <bdi class="tnum" dir="ltr">{esc(fx_date)}</bdi>' if fx_date else "")
            + "</div>"
        )
    codes_h = (
        f'<hr class="hr"><h2>{esc(ui["bookings"])}</h2>{"".join(codes)}' if codes else ""
    )
    emer_h = "".join(f'<hr class="hr">{e}' for e in emer_blocks)
    return (
        f'<aside class="instruments glass g-thick" id="instruments" aria-label="{esc(ui.get("instruments") or "")}">'
        f'<h2>{esc(ui.get("before_depart") or "")}</h2>'
        f'<div class="lead"><span class="tnum" id="countN">-</span></div>'
        f'<div class="sub" id="countL">{esc(ui["countdown_label"])}</div>'
        f'<div class="stack"><div class="k">{dep_h}</div></div>'
        f'<hr class="hr"><h2>{esc(ui["deadlines"])}</h2>'
        f"{deadlines}{codes_h}{emer_h}{fx_html}"
        "</aside>"
    )


def render_dock(data, ui, lang) -> str:
    return (
        f'<nav class="dock" aria-label="{esc(ui.get("contents") or "")}">'
        f'<button type="button" id="dockToday">{icon("ph-calendar-check")}<span>{esc(ui["today"])}</span></button>'
        f'<a href="#itinerary" id="dockItin">{icon("ph-path")}<span>{esc(ui.get("dock_itinerary") or ui.get("axis") or "")}</span></a>'
        f'<a href="#map" id="dockMap">{icon("ph-map-trifold")}<span>{esc(ui.get("dock_map") or ui["live_map"])}</span></a>'
        f'<button type="button" id="dockPocket" aria-controls="pocket" aria-expanded="false">{icon("ph-identification-card")}<span>{esc(ui.get("dock_access") or ui["pocket"])}</span></button>'
        "</nav>"
    )


def render_panel(data, ui, lang) -> str:
    links = []
    for n in data["trip"].get("nav") or []:
        links.append(f'<a href="{esc(n["href"])}">{esc(n["label"])}</a>')
    return (
        f'<button class="panel-toggle press" id="panelBtn" aria-controls="panel" aria-expanded="false">{icon("ph-list")} {esc(ui["contents"])}</button>'
        f'<aside class="toc-panel glass g-thick" id="panel" role="dialog" aria-label="{esc(ui["contents"])}">'
        f'<h3>{esc(ui["contents"])}</h3>{"".join(links)}'
        f'<button class="close press" id="panelClose">{esc(ui["close"])}</button></aside>'
    )


def render_body(data, ui, lang, exclude_not_ok=False) -> str:
    countries = country_list(data)
    axis, rest_c = [], []
    for i, c in enumerate(countries):
        axis.append(render_country_axis(data, c, i, ui, lang, exclude_not_ok=exclude_not_ok))
        rest_c.append(render_country_rest(data, c, i, ui, lang, exclude_not_ok=exclude_not_ok))
    footer = data["trip"].get("footer") or ui["footer_default"]
    sections = [
        theme_style(data),
        '<div class="mesh" aria-hidden="true"></div>',
        '<div class="grain" aria-hidden="true"></div>',
        render_header(data, ui, lang),
        '<div class="shell">',
        '<div class="shell-main">',
        render_overview(data, ui, lang),
        f'<section class="itinerary" id="itinerary" aria-label="{esc(ui.get("axis") or "")}">'
        f'<h2>{esc(ui.get("axis") or "")}</h2>{"".join(axis)}</section>',
        "</div>",
        render_instruments(data, ui, lang),
        "</div>",
        '<div class="rest">',
        render_nights(data, ui, lang),
        "\n".join(s for s in rest_c if s),
        render_search(data, ui, lang),
        render_budget(data, ui, lang),
        render_fx(data, ui),
        render_shared(data, ui, lang),
        f'<p class="foot rv">{raw_ltr(footer)}</p>',
        "</div>",
        render_panel(data, ui, lang),
        render_pocket(data, ui, lang),
        render_dock(data, ui, lang),
    ]
    return "\n".join(s for s in sections if s)


def nights_payload(data, lang):
    trip = data["trip"]
    chart = trip.get("nights_chart") or {}
    groups = chart.get("groups")
    if not groups:
        groups = []
        cidx = country_index(data)
        for d in trip.get("destinations") or []:
            n = d.get("nights")
            if n is None and d.get("nights_min") is not None:
                n = d.get("nights_max") or d["nights_min"]
            groups.append({
                "id": d["id"],
                "label": loc(d.get("name"), lang) or d["id"],
                "nights": n or 0,
                "optional": bool(d.get("optional")),
                "region": cidx.get(d.get("country"), 0),
                "undecided": bool((d.get("dates") or {}).get("flexible")),
            })
    return {
        "headline": chart.get("headline") or "",
        "source": chart.get("source") or "",
        "y_max": chart.get("y_max"),
        "groups": groups,
    }


def runtime_payload(data, ui, lang, exclude_not_ok=False) -> dict:
    trip = data["trip"]
    fx = trip.get("fx") or {}
    bud = derive_budget(data)
    cidx = country_index(data)
    places = []
    for dest in trip.get("destinations") or []:
        coords = dest.get("coords") or {}
        if coords.get("lat") is None:
            continue
        dates = dest.get("dates") or {}
        nights = dest.get("nights")
        nights_s = (
            f"{dest['nights_min']}-{dest.get('nights_max')}"
            if nights is None and dest.get("nights_min") is not None
            else (str(nights) if nights is not None else "")
        )
        info = ((data.get("destinations") or {}).get(dest["id"]) or {}).get("info") or {}
        places.append({
            "id": dest["id"],
            "name": loc(dest.get("name"), lang) or dest["id"],
            "lat": coords["lat"],
            "lng": coords["lng"],
            "region": dest.get("country"),
            "region_i": cidx.get(dest.get("country"), 0),
            "optional": bool(dest.get("optional")),
            "dates": f"{dates.get('start') or ''}-{dates.get('end') or ''}",
            "nights": nights_s,
            "exact": bool(coords.get("exact")),
            "note": info.get("stay_label") or "",
            "href": f"#stop-{dest['id']}",
        })
    recs = []
    for dest_id, kind, i, pl in iter_places(data):
        if exclude_not_ok and (pl.get("diet_fit") or {}).get("status") == "not_ok":
            continue
        dest = dest_by_id(data, dest_id)
        recs.append({
            "id": pl.get("id"),
            "dest": dest_id,
            "stop": f"stop-{dest_id}",
            "country": dest.get("country") if dest else "",
            "city": loc(dest.get("name"), lang) if dest else dest_id,
            "name": loc(pl.get("name"), lang),
            "type": pl.get("type") or kind,
            "type_label": pl.get("type_label") or pl.get("type") or kind,
            "blurb": pl.get("note") or "",
            "order": pl.get("order") or "",
            "dish": pl.get("dish") or pl.get("order") or "",
            "aliases": [a for a in (pl.get("aliases") or []) if a],
            "caution": pl.get("caution") or "",
            "price": pl.get("price_range") or "",
            "maps": pl.get("maps") or ([{"label": ui["maps"], "href": pl["maps_url"]}] if pl.get("maps_url") else []),
            "sources": pl.get("sources") or [],
            "optional": bool(pl.get("optional")),
            "reservation": (pl.get("reservation") or {}).get("need"),
        })
    today = []
    for s in (data.get("today") or {}).get("segments") or []:
        today.append({
            "from": s.get("from"), "to": s.get("to"), "title": s.get("title"),
            "sleep": s.get("sleep"), "plan": s.get("plan"), "day": s.get("day"),
            "stop": s.get("stop"), "nav": s.get("nav"), "optional": bool(s.get("optional")),
        })
    decisions = []
    for d in (data.get("decisions") or {}).get("decisions") or []:
        decisions.append({
            "id": d["id"],
            "recommended": d.get("recommended") or [],
            "chart_caption": d.get("chart_caption") or "",
            "options": [
                {"name": o.get("name"), "k": o.get("k"), "o": o.get("o"),
                 "bar": o.get("bar") or [], "steps": o.get("steps") or [], "cap": o.get("cap") or ""}
                for o in (d.get("options") or [])
            ],
        })
    estimates_chart = []
    for e in bud["estimates"]:
        estimates_chart.extend(e.get("chart_series") or [])
    home = bud["home"]
    return {
        "id": trip.get("id") or trip.get("storage_key") or "trip",
        "lang": lang,
        "dir": trip.get("dir") or "ltr",
        "locale": trip.get("locale") or lang,
        "departure": trip.get("departure_at"),
        "return": trip.get("return_at"),
        "home_tz": trip.get("home_tz") or "UTC",
        "countdown": trip.get("countdown") or {},
        "storage_key": trip.get("storage_key") or ("trip-" + (trip.get("id") or "page")),
        "fx": {
            "home": home, "symbol": symbol(home),
            "rates": fx.get("rates_to_home") or {},
            "date": fx.get("date"), "label": fx.get("label") or ui["fx"],
        },
        "budget": {
            "booked": [
                {"title": r["title"], "home": r["home_amount"], "amount": r["amount"], "currency": r["currency"]}
                for r in bud["booked_rows"]
            ],
            "total": bud["booked_total_home"],
            "estimates_chart": estimates_chart,
        },
        "nights": nights_payload(data, lang),
        "places": places,
        "recs": recs,
        "today": today,
        "decisions": decisions,
        "countries": [{"id": c["id"], "name": loc(c.get("name"), lang), "region_i": i} for i, c in enumerate(country_list(data))],
        "map": {
            "tile_url": (trip.get("map") or {}).get("tile_url") or "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            "attribution": (trip.get("map") or {}).get("attribution") or "&copy; OpenStreetMap",
        },
        "ui": ui,
    }


def render_page(data, exclude_not_ok=False):
    trip = data["trip"]
    lang = trip.get("language") or "en"
    direction = trip.get("dir") or "ltr"
    ui = load_ui(lang)
    body = render_body(data, ui, lang, exclude_not_ok=exclude_not_ok)
    title = trip.get("title") or "Trip"
    desc = trip.get("lede") or trip.get("subtitle") or title
    payload = runtime_payload(data, ui, lang, exclude_not_ok=exclude_not_ok)
    return body, {
        "lang": lang,
        "dir": direction,
        "title": title,
        "description": desc,
        "ui": ui,
        "payload": payload,
    }
