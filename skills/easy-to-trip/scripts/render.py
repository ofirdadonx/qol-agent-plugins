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
    r"|\d{1,2}\.\d{1,2}\.\d{4}(?!\d)"
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
                # "ferry 10:30, flight 14:05" is two legs: each can wrap as a unit
                segs = [t for t in re.split(r",\s+", tl) if t]
                bits.append(xfer_leg_html(dl, segs[0] if segs else tl))
                bits.extend(xfer_leg_html(t) for t in segs[1:])
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


# ---- v13 building blocks: SVG sprite icons, isolated tokens, definition grids ----
SPRITE_FILE = ROOT / "templates" / "default" / "vendor" / "icons-sprite.svg"
_SPRITE_IDS = None


def sprite_ids() -> set:
    global _SPRITE_IDS
    if _SPRITE_IDS is None:
        txt = SPRITE_FILE.read_text(encoding="utf-8") if SPRITE_FILE.exists() else ""
        _SPRITE_IDS = set(re.findall(r'<symbol id="i-([a-z0-9-]+)"', txt))
    return _SPRITE_IDS


def sprite_html() -> str:
    if not SPRITE_FILE.exists():
        return ""
    txt = SPRITE_FILE.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->\s*", "", txt, flags=re.S).strip()


def ic(name: str, cls: str = "ic") -> str:
    """An icon from the inline SVG sprite (Phosphor regular subset)."""
    name = (name or "").replace("ph-", "", 1) if (name or "").startswith("ph-") else (name or "")
    if name not in sprite_ids():
        name = "info"
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{esc(name)}"></use></svg>'


def tchip(inner_escaped: str) -> str:
    """A number/time/amount token that never wraps or reorders."""
    return f'<bdi dir="ltr" class="tnum tchip">{inner_escaped}</bdi>'


def tn(inner_escaped: str) -> str:
    return f'<bdi dir="ltr" class="tnum">{inner_escaped}</bdi>'


def chips_ltr(s) -> str:
    """Escape prose and isolate each numeric atom as a tchip (definition-grid values)."""
    if s is None or s == "":
        return ""
    return _NUM_RE.sub(lambda m: tchip(m.group(0)), esc(s))


def dl_row(icon_name: str, label: str, value_html: str) -> str:
    return (
        f'<div class="dl-row"><span class="dl-ic">{ic(icon_name)}</span>'
        f'<span class="dl-k">{esc(label)}</span><span class="dl-v">{value_html}</span></div>'
    )


def dl_grid(rows) -> str:
    """Rows are (icon, label, value_html). Empty values and repeated values are dropped."""
    seen, out = set(), []
    for icon_name, label, value in rows:
        if not value:
            continue
        key = re.sub(r"<[^>]+>", "", value).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(dl_row(icon_name, label, value))
    return f'<div class="dl">{"".join(out)}</div>' if out else ""


_LABELED = re.compile(r"^\s*([^:：]{1,22})[:：]\s*(.+)$", re.S)


def split_label(text: str):
    """'Tip: ask for chicken broth' -> ('Tip', 'ask for chicken broth'); else (None, text)."""
    m = _LABELED.match(text or "")
    if m and not re.search(r"\d{1,2}$", m.group(1)):
        return m.group(1).strip(), m.group(2).strip()
    return None, text


def item_rows(items, icon_name: str, label: str, ui: dict) -> list:
    """Prose list items as definition rows. 'Label: value' items keep their own label."""
    rows = []
    for it in items or []:
        if isinstance(it, dict):
            rows.append((it.get("icon") or icon_name, it.get("label") or label, chips_ltr(it.get("value") or it.get("text") or "")))
            continue
        lab, val = split_label(str(it))
        ic_name = icon_name
        if lab and re.search(ui.get("tip_rx") or r"(?i)^tip", lab):
            ic_name = "lightbulb"
        rows.append((ic_name, lab or label, chips_ltr(val)))
    return rows


def act_btn(icon_name: str, label: str, href: str = "", copy: str = "", aria: str = "") -> str:
    if copy:
        return (
            f'<button type="button" class="act-btn copybtn press" data-copy="{esc(copy)}" aria-label="{esc(aria or label)}">'
            f'{ic(icon_name)}<span>{esc(label)}</span></button>'
        )
    return (
        f'<a class="act-btn press" href="{esc(href)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(aria or label)}">'
        f'{ic(icon_name)}<span>{esc(label)}</span></a>'
    )


def booking_block(b: dict, ui: dict) -> str:
    """Code line, then one row of 36px actions (copy, email, manage, check-in)."""
    code = (b or {}).get("confirmation_code")
    if not code:
        return ""
    acts = [act_btn("copy", ui["copy"], copy=code, aria=f'{ui["copy"]} {code}')]
    if b.get("confirmation_link"):
        acts.append(act_btn("envelope", ui["email"], href=b["confirmation_link"], aria=f'{ui["email"]} {code}'))
    if b.get("manage_url"):
        acts.append(act_btn("arrow-square-out", ui["manage"], href=b["manage_url"], aria=f'{ui["manage"]} {code}'))
    if b.get("checkin_url"):
        acts.append(act_btn("sign-in", ui["checkin"], href=b["checkin_url"], aria=f'{ui["checkin"]} {code}'))
    return (
        f'<div class="bk"><div class="bk-code"><span class="bk-k">{esc(ui.get("booking_code") or ui["code"])}</span>'
        f'<bdi dir="ltr" class="tnum code">{esc(code)}</bdi></div>'
        f'<div class="bk-actions">{"".join(acts)}</div></div>'
    )


def pill(href: str, inner_html: str, icon_name: str = "", cls: str = "pill", ext_link: bool = False, title: str = "") -> str:
    tgt = ' target="_blank" rel="noopener noreferrer"' if ext_link else ""
    ttl = f' title="{esc(title)}"' if title else ""
    return f'<a class="{cls}" href="{esc(href)}"{tgt}{ttl}>{ic(icon_name) if icon_name else ""}{inner_html}</a>'


def tel_pill(number: str, icon_name: str = "") -> str:
    if not number:
        return ""
    href = re.sub(r"[^\d+]", "", number)
    return pill("tel:" + href, f'<bdi dir="ltr" class="tnum">{esc(number)}</bdi>', icon_name)


def mail_pill(addr: str, icon_name: str = "") -> str:
    if not addr:
        return ""
    return pill("mailto:" + addr, f'<bdi dir="ltr">{esc(addr)}</bdi>', icon_name)


def latin_or_text(s: str) -> str:
    """A name with no RTL letters is isolated as LTR so it never reorders."""
    if not s:
        return ""
    if re.search(r"[\u0590-\u08ff]", s):
        return raw_ltr(s)
    return f'<bdi dir="ltr">{esc(s)}</bdi>'


def home_amount(price: dict, rates: dict):
    if not price:
        return None
    amt = price.get("amount")
    if amt is None:
        return None
    cur = price.get("currency")
    r = rates.get(cur) if cur else 1
    if r is None:
        return None
    return amt * float(r)


def fmt_money_sym(n, code: str, decimals=None) -> str:
    sym = symbol(code)
    if n is None:
        return ""
    if decimals is None:
        decimals = 0 if abs(n - round(n)) < 0.005 else 2
    num = f"{n:,.{decimals}f}"
    return f"{sym}{num}" if sym and len(sym) <= 2 else f"{num} {code}"


_TAG_SPLIT = re.compile(r"(<[^>]+>)")
_LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9'’+./-]{1,}(?:[ \u00a0]+[A-Za-z][A-Za-z0-9'’+./-]{1,})*")
_SKIP_TAGS = {"bdi", "code", "script", "style", "a"}


def wrap_latin(html: str) -> str:
    """Isolate Latin runs inside RTL prose so a multi-word Latin name never reorders on wrap.

    Text inside bdi/code/a stays as is. Only runs when the page text holds RTL letters."""
    if not html or not re.search(r"[\u0590-\u08ff]", html):
        return html
    out, depth = [], []
    for part in _TAG_SPLIT.split(html):
        if not part:
            continue
        if part.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
            if m:
                name = m.group(2).lower()
                if name in _SKIP_TAGS and not part.endswith("/>"):
                    if m.group(1):
                        if name in depth:
                            depth.remove(name)
                    else:
                        depth.append(name)
            out.append(part)
            continue
        if depth or not _LATIN_RUN.search(part):
            out.append(part)
            continue
        out.append(_LATIN_RUN.sub(lambda mm: f'<bdi dir="ltr">{mm.group(0)}</bdi>', part))
    return "".join(out)


_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]")
_THAI = re.compile(r"[\u0e00-\u0e7f]")


def quote_iso(html: str) -> str:
    """«local script» inside RTL text: isolate and keep the quote on one line."""
    def one(m):
        inner = m.group(1)
        if _CJK.search(inner):
            lang = ' lang="ja"' if re.search(r"[\u3040-\u30ff]", inner) else ""
        elif _THAI.search(inner):
            lang = ' lang="th"'
        else:
            return m.group(0)
        return f'<span class="nw q-iso">«<bdi dir="ltr"{lang}>{inner}</bdi>»</span>'
    return re.sub(r"«([^»<]*)»", one, html)


def status_rx(ui: dict) -> list:
    """Status words that data text sometimes repeats next to the real badge."""
    booked = re.escape((ui.get("booked") or "").strip())
    openw = re.escape((ui.get("open") or "").strip())
    undecided = re.escape((ui.get("optional_undecided") or "").strip())
    nouns = "|".join(re.escape(n) for n in (ui.get("status_nouns") or []) if n)
    rx = []
    if booked:
        if nouns:
            rx.append((re.compile(r"\s*" + booked + r"\s+(?:" + nouns + r")(?=[\s.,]|$)"), ""))
        rx.append((re.compile(r"\s*[—–-]?\s*" + booked), ""))
    if openw:
        rx.append((re.compile(r"(\S+) " + openw + r" (?=\1)"), ""))
        rx.append((re.compile(r"\s+" + openw + r"(?=\s*$|\s*[.,])"), ""))
    if undecided:
        rx.append((re.compile(r"\s*" + undecided), ""))
    rx.append((re.compile(r"\s*\u2713"), ""))
    return rx


def clean_status(text: str, ui: dict) -> str:
    for rx, rp in status_rx(ui):
        text = rx.sub(rp, text)
    return text


_RTL_CH = re.compile(r"[\u0590-\u08ff]")


def fix_rtl_in_ltr(html: str) -> str:
    """An LTR isolate that holds RTL words ('4 שעות') renders reversed: let it follow its text."""
    def one(m):
        tag, attrs, txt = m.group(1), m.group(2), m.group(3)
        if not _RTL_CH.search(txt):
            return m.group(0)
        attrs = re.sub(r'\sdir="ltr"', ' dir="auto"', attrs)
        attrs = re.sub(r'class="([^"]*)"', lambda c: 'class="' + " ".join(x for x in c.group(1).split() if x != "ltr") + '"', attrs)
        if "dir=" not in attrs:
            attrs += ' dir="auto"'
        return f"<{tag}{attrs}>{txt}</{tag}>"
    return re.sub(r'<(bdi|span)((?:\s[^>]*)?(?:dir="ltr"|class="[^"]*\bltr\b[^"]*")[^>]*)>([^<]*)</\1>', one, html)


def clock_tile(tz: str, name: str, flag_html: str, where: str, region_i, ui) -> str:
    style = f' style="--region-c:var(--region-{region_i})"' if region_i is not None else ""
    return (
        f'<div class="clk" data-tz="{esc(tz)}" data-where="{esc(where)}"{style}>'
        f'<div class="clk-top">{flag_html}<span class="clk-name">{esc(name)}</span>'
        f'<span class="clk-here" aria-hidden="true">{esc(ui.get("here_now") or "")}</span></div>'
        f'<div class="clk-time" dir="ltr"><span class="tnum">--:--</span></div>'
        f'<div class="clk-meta"><span class="clk-date"></span><span class="clk-off" dir="auto"></span></div></div>'
    )


def home_flag(data, ui) -> str:
    """Home flag from trip.home.flag (same shape format as a country), else a neutral house icon."""
    home = data["trip"].get("home") or {}
    if (home.get("flag") or {}).get("shapes"):
        return render_flag({"flag": home["flag"], "name": home.get("name")}, "sm")
    return f'<span class="flag flag-home" role="img" aria-label="{esc(ui.get("home_clock") or "")}">{ic("house")}</span>'


def glance_units(data, ui):
    """One unit per booking (a code shared by two transfers counts once), else per timeline item."""
    units = {}
    for i, c in enumerate(country_list(data)):
        leading, after, trailing = transfers_in_country(data, c["id"])
        items = []
        for x in leading:
            items.append(("x", x))
        trailing_ids = {x.get("id") for x in trailing}
        for d in [d for d in data["trip"]["destinations"] if d.get("country") == c["id"]]:
            items.append(("s", d))
            for x in after.get(d["id"], []):
                if x.get("id") not in trailing_ids:
                    items.append(("x", x))
        for x in trailing:
            items.append(("x", x))
        for kind, it in items:
            if kind == "x":
                st = status_of_xfer(data, it)
                if it.get("optional") or st == "optional":
                    continue
                b = booking_by_id(data, it.get("booking_id")) if it.get("booking_id") else None
                key = (b or {}).get("confirmation_code") or ("xfer-" + str(it.get("id")))
                closed = st == "booked"
            else:
                if it.get("optional"):
                    continue
                info = ((data.get("destinations") or {}).get(it["id"]) or {}).get("info") or {}
                closed = (info.get("stay_status") or ("booked" if info.get("stay_booking_id") else "open")) == "booked"
                key = "stop-" + it["id"]
            if key in units:
                units[key]["closed"] = units[key]["closed"] or closed
            else:
                units[key] = {"closed": closed, "region": i}
    return list(units.values())


def render_glance(data, ui, lang) -> str:
    bud = derive_budget(data)
    home = bud["home"] or data["trip"].get("currency") or ""
    total = bud["booked_total_home"] or 0
    sym = symbol(home)
    budget_txt = f"≈ {sym}{round(total):,}" if sym and len(sym) <= 2 else f"≈ {home} {round(total):,}"
    dests = [d for d in data["trip"]["destinations"] if not d.get("optional")]
    nights = sum(int(g.get("nights") or 0) for g in nights_payload(data, lang)["groups"] if not g.get("optional"))
    xfers = 0
    for c in country_list(data):
        leading, after, trailing = transfers_in_country(data, c["id"])
        seen = set()
        for x in leading + [y for v in after.values() for y in v] + trailing:
            if x.get("id") in seen:
                continue
            seen.add(x.get("id"))
            if not (x.get("optional") or status_of_xfer(data, x) == "optional"):
                xfers += 1
    units = glance_units(data, ui)
    closed = sum(1 for u in units if u["closed"])
    cells = [f'<i class="on r{u["region"]}"></i>' for u in units if u["closed"]] + ["<i></i>" for u in units if not u["closed"]]
    aria = (ui.get("glance_budget_aria") or "{amount}").replace("{amount}", budget_txt)

    def tile(icon_name, key, value, label, extra_cls="", ltr_v=False, tail=""):
        d = ' dir="ltr"' if ltr_v else ""
        return (
            f'<div class="gl{extra_cls}" role="listitem"><span class="gl-ic">{ic(icon_name)}</span>'
            f'<span class="gl-v"{d}><span class="tnum" data-gl="{key}">{esc(value)}</span></span>'
            f'<span class="gl-k">{esc(label)}</span>{tail}</div>'
        )
    opt_names = [re.split(r"\s[—–-]\s", loc(d.get("name"), lang) or d["id"])[0]
                 for d in data["trip"]["destinations"] if d.get("optional")]
    note = ""
    if opt_names:
        note = f'<p class="glance-note">{esc((ui.get("glance_excludes") or "{names}").replace("{names}", ", ".join(opt_names)))}</p>'
    return (
        f'<div class="glance" role="list" aria-label="{esc(ui.get("at_a_glance") or "")}">'
        f'<a class="gl gl-budget" role="listitem" href="#budget" aria-label="{esc(aria)}">'
        f'<span class="gl-ic">{ic("wallet")}</span><span class="gl-v" dir="ltr"><span class="tnum" data-gl="budget">{esc(budget_txt)}</span></span>'
        f'<span class="gl-k">{esc(ui.get("glance_budget") or "")}</span></a>'
        + tile("moon", "nights", str(nights), ui.get("glance_nights") or "")
        + tile("map-pin-area", "dests", str(len(dests)), ui.get("glance_dests") or "")
        + tile("airplane-tilt", "xfers", str(xfers), ui.get("glance_xfers") or "")
        + tile("check-circle", "booked", f"{closed}/{len(units)}", ui.get("glance_booked") or "", " gl-book", True,
               f'<span class="gl-bar" aria-hidden="true">{"".join(cells)}</span>')
        + "</div>" + note
    )


def _ymd(raw):
    d = parse_iso_date(raw) if raw else None
    return d.isoformat() if d else ""


def price_value(price: dict, fx: dict, home: str) -> str:
    """'$1,124.75 ≈ ₪3,599' (original first, home amount as a sub-line), or a range."""
    if not price:
        return ""
    cur = price.get("currency") or home
    rates = fx.get("rates_to_home") or {}
    if price.get("amount") is not None:
        main = tchip(esc(fmt_money_sym(price["amount"], cur)))
        sub = ""
        if cur != home:
            h = home_amount(price, rates)
            if h is not None:
                sub = f'≈ {tn(esc(fmt_money_sym(h, home, 0)))}'
        note = price.get("note") or ""
        bits = " · ".join(x for x in [sub, raw_ltr(note) if note else ""] if x)
        return main + (f' <span class="dl-sub">{bits}</span>' if bits else "")
    lo, hi = price.get("amount_min"), price.get("amount_max")
    if lo is not None:
        rng = fmt_money_sym(lo, cur) + ("" if hi in (None, lo) else "–" + fmt_money_sym(hi, cur).lstrip(symbol(cur)))
        note = price.get("note") or ""
        return tchip(esc(rng)) + (f' <span class="dl-sub">{raw_ltr(note)}</span>' if note else "")
    return ""


def xfer_rows(data, x, b, ui) -> list:
    fx = data["trip"].get("fx") or {}
    home = fx.get("home") or data["trip"].get("currency") or ""
    mode = x.get("mode") or ""
    dep_ic = "airplane-takeoff" if mode == "flight" else ("boat" if mode in ("ferry", "boat") else "train")
    rows = []
    when = " ".join(filter(None, [x.get("date_label") or "", x.get("time_label") or ""]))
    if when:
        rows.append((dep_ic, ui.get("dl_when") or "", chips_ltr(when)))
    if x.get("duration_label") and x.get("duration_label") not in when:
        rows.append(("timer", ui.get("dl_duration") or "", chips_ltr(x["duration_label"])))
    if b:
        for d in b.get("details") or []:
            if isinstance(d, dict) and d.get("value"):
                rows.append((d.get("icon") or "path", d.get("label") or "", chips_ltr(d["value"])))
        if b.get("cabin"):
            rows.append(("seat", ui.get("dl_cabin") or "", chips_ltr(b["cabin"])))
        if b.get("seats"):
            rows.append(("seat", ui.get("dl_seats") or "", chips_ltr(b["seats"])))
        pv = price_value(b.get("price") or {}, fx, home)
        if pv:
            rows.append(("wallet", ui.get("dl_price") or "", pv))
        if b.get("checkin_at"):
            dt = parse_iso_dt(b["checkin_at"])
            if dt:
                rows.append(("sign-in", ui.get("checkin") or "", tchip(esc(_short_dmy(dt)))))
        if b.get("notes"):
            rows.append(("note", ui.get("dl_notes") or "", note_value(clean_status(b["notes"], ui), ui)))
    if x.get("notes"):
        rows.append(("info", ui.get("dl_notes") or "", note_value(clean_status(x["notes"], ui), ui)))
    for tip in x.get("tips") or []:
        rows.append(("lightbulb", ui.get("dl_tip") or "", chips_ltr(tip)))
    return rows


def stay_rows(data, dest, info, b, ui, lang) -> list:
    """The stay as a definition grid: name, check-in/out, nights, address, contacts, price, terms, code."""
    fx = data["trip"].get("fx") or {}
    home = fx.get("home") or data["trip"].get("currency") or ""
    rows = []
    name = info.get("stay_label") or (b or {}).get("title") or ""
    if name:
        rows.append(("bed", ui.get("dl_name") or "", latin_or_text(name)))
    dates = dest.get("dates") or {}
    ci = parse_iso_dt((b or {}).get("checkin_at")) if b else None
    d_in = parse_iso_date(dates.get("start"))
    d_out = parse_iso_date(dates.get("end"))
    if d_in or info.get("checkin"):
        bits = []
        if d_in:
            bits.append(tchip(esc(_short_dmy(d_in))))
        t_in = info.get("checkin") or (f"{ci.hour:02d}:{ci.minute:02d}" if ci else "")
        if t_in:
            bits.append(tchip(esc(t_in)))
        rows.append(("sign-in", ui.get("checkin") or "", "".join(bits)))
    if d_out or info.get("checkout"):
        bits = []
        if d_out:
            bits.append(tchip(esc(_short_dmy(d_out))))
        if info.get("checkout"):
            bits.append(tchip(esc(info["checkout"])))
        rows.append(("sign-out", ui.get("checkout") or "", "".join(bits)))
    if dest.get("nights") is not None:
        n = int(dest["nights"])
        rows.append(("moon", ui.get("nights") or "", esc(pluralize(n, ui.get("plural_night") or {"one": "1 night", "other": "{n} nights"})).replace(str(n), tn(str(n)), 1)))
    if info.get("room"):
        rows.append(("armchair", ui.get("dl_room") or "", latin_or_text(info["room"])))
    addr = info.get("local_address_latin") or info.get("address") or ""
    if addr:
        rows.append(("map-pin", ui.get("dl_address") or "", latin_or_text(addr)))
    if info.get("phone"):
        rows.append(("phone", ui.get("dl_phone") or "", tel_pill(info["phone"])))
    mail = info.get("email") or (b or {}).get("email")
    if mail:
        rows.append(("envelope", ui.get("email") or "", mail_pill(mail)))
    if b:
        pv = price_value(b.get("price") or {}, fx, home)
        if pv:
            rows.append(("wallet", ui.get("dl_price") or "", pv))
        if b.get("charge_detail") or b.get("charge_at"):
            txt = b.get("charge_detail")
            if txt:
                rows.append(("credit-card", ui.get("charge") or "", chips_ltr(txt)))
            else:
                dt = parse_iso_dt(b["charge_at"])
                rows.append(("credit-card", ui.get("charge") or "", tchip(esc(_short_dmy(dt))) if dt else chips_ltr(b["charge_at"])))
        if b.get("cancel_detail") or b.get("cancel_deadline"):
            txt = b.get("cancel_detail")
            if txt:
                lab = ui.get("cancel_by") or ""
                if lab and txt.startswith(lab):
                    txt = txt[len(lab):].strip()  # the label already says it
                rows.append(("calendar-x", lab, chips_ltr(txt)))
            else:
                dt = parse_iso_dt(b["cancel_deadline"])
                rows.append(("calendar-x", ui.get("cancel_by") or "", tchip(esc(_short_dmy(dt))) if dt else chips_ltr(b["cancel_deadline"])))
        for d in b.get("details") or []:
            if isinstance(d, dict) and d.get("value"):
                rows.append((d.get("icon") or "info", d.get("label") or "", chips_ltr(d["value"])))
        if b.get("notes"):
            rows.append(("note", ui.get("dl_notes") or "", note_value(clean_status(b["notes"], ui), ui)))
        code = b.get("confirmation_code")
        if code:
            rows.append(("ticket", b.get("carrier") or ui.get("code") or "", tchip(esc(code))))
    return rows


def _tz_offset_label(tz: str, on) -> str:
    """'UTC+9' for a zone on a given date (zoneinfo), '' when the zone is unknown."""
    try:
        from zoneinfo import ZoneInfo
        off = datetime(on.year, on.month, on.day, 12, tzinfo=ZoneInfo(tz)).utcoffset()
    except Exception:
        return ""
    mins = int(off.total_seconds() // 60)
    sign = "+" if mins >= 0 else "−"
    h, m = divmod(abs(mins), 60)
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


def _offset_text(ui, mins: int) -> str:
    if mins == 0:
        return ui.get("offset_same") or ""
    sign = "+" if mins > 0 else "−"
    h, m = divmod(abs(mins), 60)
    if m:
        return (ui.get("offset_hm") or "{sign}{h}:{m}").replace("{sign}", sign).replace("{h}", str(h)).replace("{m}", f"{m:02d}")
    if h == 1:
        return (ui.get("offset_one") or "{sign}1").replace("{sign}", sign)
    return (ui.get("offset_n") or "{sign}{n}").replace("{sign}", sign).replace("{n}", str(h))


def ptile(icon_name: str, label: str, value_html: str, line_html: str, more_html: str = "", ui=None) -> str:
    m = ""
    if more_html:
        m = (f'<details class="p-more"><summary>{esc((ui or {}).get("more_short") or "")}{ic("caret-down", "ic car")}</summary>'
             f'<div class="p-more-b">{more_html}</div></details>')
    return (f'<div class="ptile"><div class="ptile-top"><span class="ptile-ic">{ic(icon_name)}</span>'
            f'<span class="ptile-k">{esc(label)}</span></div>'
            f'<div class="ptile-v">{value_html}</div><p class="ptile-l">{line_html}</p>{m}</div>')


_PRACT_ICONS = [
    (r"(?i)time|clock|שעון|שעות|zone", "clock"),
    (r"(?i)curr|money|cash|מטבע|כסף", "currency-circle-dollar"),
    (r"(?i)plug|power|socket|volt|תקע|חשמל", "plug"),
    (r"(?i)transport|train|metro|bus|taxi|תחבורה|רכבת", "train"),
    (r"(?i)phone|sim|esim|internet|טלפון", "phone"),
    (r"(?i)tip|טיפ", "lightbulb"),
    (r"(?i)water|מים", "info"),
]


def _pract_icon(item) -> str:
    if item.get("icon"):
        return item["icon"]
    lab = item.get("label") or ""
    for rx, name in _PRACT_ICONS:
        if re.search(rx, lab):
            return name
    return "info"


def _clauses(body: str):
    first = re.split(r"(?<=[.!?])\s+", (body or "").strip(), maxsplit=1)[0].rstrip(".")
    bits = [b.strip() for b in re.split(r"\s[—–]\s|,\s|;\s", first) if b.strip()]
    return bits


def practical_tiles(data, country, ui, lang) -> str:
    trip = data["trip"]
    fx = trip.get("fx") or {}
    home = fx.get("home") or trip.get("currency") or ""
    rates = fx.get("rates_to_home") or {}
    tz = country.get("timezone")
    home_tz = trip.get("home_tz")
    start = parse_iso_date(((trip.get("dates") or {}).get("start"))) or date.today()
    cname = loc(country.get("name"), lang) or country["id"]
    hname = (trip.get("home") or {}).get("name") or ui.get("home_clock") or ""
    time_rx = ui.get("pract_time_rx") or r"(?i)time"
    cur_rx = ui.get("pract_currency_rx") or r"(?i)currenc"
    tiles, time_done, cur_done = [], False, False
    for it in country.get("practical") or []:
        lab = it.get("label") or ""
        kind = it.get("kind") or ("time" if re.search(time_rx, lab) else ("currency" if re.search(cur_rx, lab) else ""))
        if kind == "time" and tz and home_tz and not time_done:
            time_done = True
            a, b = _tz_offset_label(tz, start), _tz_offset_label(home_tz, start)
            try:
                from zoneinfo import ZoneInfo
                d0 = datetime(start.year, start.month, start.day, 12)
                mins = int((d0.replace(tzinfo=ZoneInfo(tz)).utcoffset() - d0.replace(tzinfo=ZoneInfo(home_tz)).utcoffset()).total_seconds() // 60)
                init = _offset_text(ui, mins)
            except Exception:
                init = ""
            line = it.get("line") and raw_ltr(it["line"]) or f'{esc(cname)} {tn(esc(a))} · {esc(hname)} {tn(esc(b))}'
            tiles.append(ptile("clock", ui.get("pract_time") or lab, f'<span data-offset-tz="{esc(tz)}">{esc(init)}</span>', line, ui=ui))
            continue
        cur = country.get("currency")
        if kind == "currency" and cur and rates.get(cur) is not None and not cur_done:
            cur_done = True
            r = float(rates[cur])
            amt = 1000 if r < 0.05 else (100 if r < 1 else 1)
            hv = amt * r
            hv_txt = f"{hv:,.2f}" if hv < 10 else f"{hv:,.1f}" if hv < 100 else f"{hv:,.0f}"
            value = f'{tn(esc(symbol(cur) + f"{amt:,}"))} ≈ {tn(esc(symbol(home) + hv_txt))}'
            line = raw_ltr(it.get("line") or (ui.get("fx_line") or "{date}").replace("{date}", fx.get("date_label") or _dmy(fx.get("date")) or ""))
            rows = []
            srcs = fx.get("sources") or {}
            for pair, val in (fx.get("cross_rates") or {}).items():
                if cur in pair:
                    sub = srcs.get(pair) or ""
                    sub = re.sub(r",?\s*\d{1,2}\.\d{1,2}\.\d{4}$", "", sub)
                    rows.append(("currency-circle-dollar", f"{pair[:3]}/{pair[3:]}", tchip(esc(f"{val:.2f}")) + (f' <span class="dl-sub">{esc(sub)}</span>' if sub else "")))
            if "USD" in rates and home != "USD":
                sub = re.sub(r",?\s*\d{1,2}\.\d{1,2}\.\d{4}$", "", srcs.get("USD" + home) or "")
                rows.append(("currency-circle-dollar", f"USD/{home}", tchip(esc(f"{float(rates['USD']):.2f}")) + (f' <span class="dl-sub">{esc(sub)}</span>' if sub else "")))
            tiles.append(ptile("currency-circle-dollar", ui.get("pract_currency") or lab, value, line, dl_grid(rows), ui=ui))
            continue
        bits = _clauses(it.get("body") or "")
        value = it.get("value") or (bits[0] if bits else "")
        line = it.get("line") or (bits[1] if len(bits) > 1 else "")
        more = ""
        if it.get("more"):
            more = dl_grid([(m.get("icon") or _pract_icon(it), m.get("label") or "", chips_ltr(m.get("value") or "")) for m in it["more"]])
        elif it.get("body"):
            more = dl_grid([(_pract_icon(it), ui.get("dl_details") or "", chips_ltr(it["body"]))])
        tiles.append(ptile(_pract_icon(it), lab, wrap_latin(raw_ltr(value)), wrap_latin(raw_ltr(line)), more, ui=ui))
    return f'<div class="ptiles">{"".join(tiles)}</div>' if tiles else ""


def _dmy(raw) -> str:
    d = parse_iso_date(raw) if raw else None
    return f"{d.day}.{d.month}.{d.year}" if d else (raw or "")


def callpill(e: dict) -> str:
    number = e.get("number") or e.get("tel") or ""
    tel = e.get("tel") or re.sub(r"[^\d+]", "", number)
    return (f'<a class="callpill" href="tel:{esc(tel)}">{ic("phone")}'
            f'<bdi dir="ltr" class="tnum n">{esc(number)}</bdi><span class="w">{esc(e.get("label") or "")}</span></a>')


def embassy_card(emb: dict, ui) -> str:
    rows = []
    if emb.get("url"):
        rows.append(("globe", ui.get("dl_site") or "", pill(emb["url"], f'<bdi dir="ltr">{esc(emb.get("source") or emb["url"])}</bdi>', "arrow-square-out", ext_link=True)))
    if emb.get("address"):
        parts = [p.strip() for p in emb["address"].split(",")]
        inner = ", ".join(f'<span class="nw">{esc(p)}</span>' for p in parts)
        href = emb.get("map_url") or ""
        if href:
            addr = pill(href, f'<bdi dir="auto">{inner}</bdi>', "map-pin", "pill pill-addr", ext_link=True, title=emb["address"])
        else:
            addr = (f'<button type="button" class="pill pill-addr copybtn press" data-copy="{esc(emb["address"])}" title="{esc(emb["address"])}" '
                    f'aria-label="{esc(ui["copy"] + " " + emb["address"])}">{ic("map-pin")}<bdi dir="auto">{inner}</bdi></button>')
        rows.append(("map-pin", ui.get("dl_address") or "", addr))
    if emb.get("phone"):
        rows.append(("phone", ui.get("dl_phone") or "", tel_pill(emb["phone"], "phone")))
    if emb.get("phone_emergency"):
        rows.append(("siren", ui.get("emergency") or "", tel_pill(emb["phone_emergency"], "phone")))
    if emb.get("email"):
        rows.append(("envelope", ui.get("email") or "", mail_pill(emb["email"], "envelope")))
    body = "".join(f'<div class="emb-row"><span class="emb-k">{ic(i)}{esc(k)}</span><span class="emb-v">{v}</span></div>' for i, k, v in rows)
    return f'<div class="emb"><h3 class="emb-h">{esc(emb.get("name") or ui["embassy"])}</h3><div class="emb-grid">{body}</div></div>'


def _fmt_home_plain(n, home) -> str:
    sym = symbol(home)
    n = int(round(n))
    return f"{sym}{n:,}" if sym and len(sym) <= 2 else f"{home} {n:,}"


def _range_txt(lo, hi, cur) -> str:
    sym = symbol(cur or "")
    pre = sym if sym and len(sym) <= 2 else f"{cur} "
    if lo is None:
        return ""
    if hi is None or int(round(hi)) == int(round(lo)):
        return f"{pre}{int(round(lo)):,}"
    return f"{pre}{int(round(lo)):,}–{int(round(hi)):,}"


def nav_label(data, ui, key, country=None, lang=None) -> str:
    """Short label for a section in the nav. Per-country chunks use a ui template with the
    country name; singletons use trip.nav when it names the same href, else a ui default."""
    lang = lang or (data["trip"].get("language") or "en")
    if country is not None:
        cname = loc(country.get("name"), lang) or country["id"]
        kind = "practical" if key.endswith("-practical") else ("days" if key.startswith("days") else key)
        tpl = ui.get("nav_" + kind) or "{country}"
        return tpl.replace("{country}", cname)
    for n in data["trip"].get("nav") or []:
        if (n.get("href") or "") == "#" + key:
            return n.get("label") or ""
    return ui.get("nav_" + key.replace("-", "_")) or ""


def _chk_list(list_id, items, ui, done=False) -> str:
    lis = []
    for k, it in enumerate(items or []):
        if isinstance(it, dict):
            text = it.get("text") or ""
            val = it.get("id") or it.get("booking_id") or f"{list_id}-{k}"
            opt = bool(it.get("optional"))
        else:
            text, val, opt = str(it), f"{list_id}-{k}", False
        cls = ' class="is-optional"' if opt else ""
        tag = badge("optional", ui) if opt else ""
        dd = ' data-done="1"' if done else ""
        lis.append(
            f'<li{cls}><label><input type="checkbox" value="{esc(val)}"{dd}>'
            f'<span class="chk-txt">{raw_ltr(clean_status(text, ui))}{(" " + tag) if tag else ""}</span></label></li>'
        )
    return f'<ul class="chk-list" id="{esc(list_id)}">{"".join(lis)}</ul>'


def render_shared_pack(data, ui, lang) -> str:
    pk = data["trip"].get("shared_packing") or {}
    if not (pk.get("items") or pk.get("headline")):
        return ""
    items = pk.get("items") or []
    note = f'<p class="src-note">{raw_ltr(pk.get("note") or "")}</p>' if pk.get("note") else ""
    status = (f'<p class="pack-status"><bdi dir="ltr" class="tnum" id="packCount">0/{len(items)}</bdi>'
              f'<span id="packEmpty">{esc(ui.get("pack_empty") or "")}</span></p>') if items else ""
    lst = _chk_list("packList", [{"text": t, "id": f"pack-{i}"} if isinstance(t, str) else t for i, t in enumerate(items)], ui)
    return (
        f'<section id="pack" class="sec" data-nav="{esc(nav_label(data, ui, "pack"))}"><div class="sec-head rv">'
        f'<div class="act">{icon("ph-suitcase-rolling")}{esc(ui["packing"])}</div>'
        f'<h2>{raw_ltr(pk.get("headline") or "")}</h2>{status}<p>{raw_ltr(pk.get("lede") or "")}</p></div>'
        f'<div class="card glass g-reg rv" style="margin-top:var(--s4)">{lst}{note}</div></section>'
    )


def render_shared_docs(data, ui, lang) -> str:
    docs = data["trip"].get("shared_docs") or {}
    if not (docs.get("items") or docs.get("headline")):
        return ""
    lis = "".join(f"<li><span>{raw_ltr(i)}</span></li>" for i in (docs.get("items") or []))
    return (
        f'<section id="docs" class="sec"><div class="sec-head rv">'
        f'<div class="act">{icon("ph-identification-card")}{esc(ui["docs"])}</div>'
        f'<h2>{raw_ltr(docs.get("headline") or "")}</h2><p>{raw_ltr(docs.get("lede") or "")}</p></div>'
        f'<div class="card glass g-reg rv"><ul class="bul">{lis}</ul></div></section>'
    )


def render_tasks(data, ui, lang) -> str:
    tasks = data.get("tasks") or {}
    if not (tasks.get("done") or tasks.get("open")):
        return ""
    done, opn = tasks.get("done") or [], tasks.get("open") or []
    n_all = len(done) + len(opn)
    return (
        f'<section id="tasks" class="sec" data-nav="{esc(nav_label(data, ui, "tasks"))}"><div class="sec-head rv">'
        f'<div class="act">{icon("ph-list-checks")}{esc(ui.get("tasks") or ui["tasks_open"])}</div>'
        f'<h2>{raw_ltr(tasks.get("headline") or "")}</h2>'
        f'<p class="pack-status"><bdi dir="ltr" class="tnum" id="taskCount">{len(done)}/{n_all}</bdi></p>'
        f'<p>{raw_ltr(tasks.get("lede") or "")}</p></div>'
        f'<div class="grid2"><div class="card glass g-reg rv">'
        f'<h3 style="font-size:16px;font-weight:700;margin-bottom:10px;color:var(--pos)">{icon("ph-check-circle")}{esc(ui["tasks_done"])}</h3>'
        f'{_chk_list("taskListDone", done, ui, done=True)}</div>'
        f'<div class="card glass g-reg rv">'
        f'<h3 style="font-size:16px;font-weight:700;margin-bottom:10px;color:var(--ink-2)">{icon("ph-circle-dashed")}{esc(ui["tasks_open"])}</h3>'
        f'{_chk_list("taskListOpen", opn, ui)}</div></div></section>'
    )


def pair(a: str, b: str) -> str:
    if a and b:
        return f'<div class="pair">{a}{b}</div>'
    return a or b or ""


_NAV_RX = re.compile(r'<(?:section|figure|div|article)\b[^>]*?\bid="([^"]+)"[^>]*?\bdata-nav="([^"]*)"|<(?:section|figure|div|article)\b[^>]*?\bdata-nav="([^"]*)"[^>]*?\bid="([^"]+)"')


def nav_from_html(html: str) -> list:
    out, seen = [], set()
    for m in _NAV_RX.finditer(html):
        i, lab = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        if lab and i not in seen:
            seen.add(i)
            out.append((i, htmlmod.unescape(lab)))
    return out


def note_value(text: str, ui: dict, limit: int = 160) -> str:
    """A long free-text note shows its first sentence; the rest folds under 'more'."""
    text = (text or "").strip()
    if len(text) <= limit:
        return chips_ltr(text)
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    if len(parts) < 2:
        return chips_ltr(text)
    return (f'{chips_ltr(parts[0])}<details class="p-more"><summary>{esc(ui.get("more_short") or "")}'
            f'{ic("caret-down", "ic car")}</summary><div class="p-more-b">{chips_ltr(parts[1])}</div></details>')


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


def render_header(data, ui, lang, nav=None) -> str:
    trip = data["trip"]
    chips = [f'<a href="#{esc(sid)}">{esc(label)}</a>' for sid, label in (nav or [])]
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
        f'      <button type="button" class="jump-today press" id="jumpSearch" aria-label="{esc(ui["search_places"])}">{icon("ph-magnifying-glass")}<span>{esc(ui["search"])}</span></button>\n'
        f'      <button type="button" class="jump-today press" id="jumpToday" aria-label="{esc(ui["today"])}">{icon("ph-calendar-check")}<span>{esc(ui["today"])}</span></button>\n'
        f'      <button type="button" class="jump-today press" id="locateBtn" hidden aria-label="{esc(ui["locate_title"])}">{icon("ph-compass")}<span>{esc(ui["locate"])}</span></button>\n'
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


_FOOD_KINDS = {"food"}
_FOOD_PLACE_TYPES = {
    "food", "restaurant", "restaurants", "cafe", "cafes", "bar", "bars",
    "izakaya", "bakery", "dessert",
}


def _place_reservation_booking_id(pl) -> str:
    res = pl.get("reservation") or {}
    if isinstance(res, dict):
        bid = res.get("booked")
        return bid if isinstance(bid, str) and bid else ""
    return ""


def places_linking_booking(data) -> dict:
    """booking_id -> list of (dest_id, kind, place) for places whose reservation.booked points here."""
    out = {}
    for dest_id, kind, _i, pl in iter_places(data):
        bid = _place_reservation_booking_id(pl)
        if bid:
            out.setdefault(bid, []).append((dest_id, kind, pl))
    return out


def _is_restaurant_like(linked) -> bool:
    for _dest_id, kind, pl in linked or []:
        ptype = (pl.get("type") or "").lower()
        if kind in _FOOD_KINDS or ptype in _FOOD_PLACE_TYPES:
            return True
    return False


def _booking_sort_dt(b):
    return parse_iso_dt(b.get("checkin_at")) or parse_iso_dt(b.get("cancel_deadline")) or datetime.max


def booked_activities_for_dest(data, dest_id, links=None) -> list:
    """Booked activity bookings for this destination, plus restaurant-like bookings linked from its places.

    Returns a list of (booking, linked_here) sorted by date/time.
    """
    links = places_linking_booking(data) if links is None else links
    rows = []
    for b in data["bookings"].get("bookings") or []:
        if b.get("status") != "booked":
            continue
        linked_here = [t for t in links.get(b.get("id") or "", []) if t[0] == dest_id]
        if b.get("type") == "activity" and b.get("destination_id") == dest_id:
            rows.append((b, linked_here))
        elif linked_here:
            rows.append((b, linked_here))
    rows.sort(key=lambda x: (_booking_sort_dt(x[0]), x[0].get("id") or ""))
    return rows


def format_booked_when(dt, raw, lang: str) -> str:
    """Weekday + D.M + optional time, compact, for the destination 'what's booked' list."""
    if not dt:
        return ""
    stamp = _short_dmy(dt)
    hm = _short_hm(dt, raw)
    if (lang or "").startswith("he"):
        wd = _HE_WEEKDAYS[dt.weekday()]
        date_h = f"{esc(wd)} {tchip(esc(stamp))}"
    else:
        wd = dt.strftime("%a")
        date_h = f"{esc(wd)} {tchip(esc(stamp))}"
    if hm:
        date_h += f'<span class="sep" aria-hidden="true">·</span>{tchip(esc(hm))}'
    return date_h


def checkin_deadline_label(b, linked, ui) -> str:
    """Short label for a booking's checkin_at: meal / reservation / check-in, by type."""
    if _is_restaurant_like(linked):
        return ui.get("meal_at") or ui.get("booking_at") or ui.get("checkin_by") or "Meal"
    if b.get("type") == "activity":
        return ui.get("booking_at") or ui.get("checkin_by") or "Reservation"
    return ui.get("checkin_by") or "Check-in"


def render_dest_booked_plan(data, dest_id, ui, lang, links=None) -> str:
    """'What's booked' list inside a destination card. Hidden when empty.

    A name with data-jump opens the search dialog on that place (`jumpToRec`).
    """
    rows = booked_activities_for_dest(data, dest_id, links=links)
    if not rows:
        return ""
    items = []
    for b, linked in rows:
        dt = parse_iso_dt(b.get("checkin_at"))
        when = format_booked_when(dt, b.get("checkin_at"), lang)
        when_h = f'<div class="dbk-when">{when}</div>' if when else ""
        restaurant = _is_restaurant_like(linked)
        icon_name = "fork-knife" if restaurant else "ticket"
        title = (b.get("short_title") or b.get("title") or "").strip()
        rec_id = ""
        if linked:
            rec_id = (linked[0][2].get("id") or "") if linked[0][2] else ""
        if rec_id:
            name_h = (
                f'<button type="button" class="dbk-name" data-jump="{esc(rec_id)}">'
                f'<bdi dir="auto">{esc(title)}</bdi></button>'
            )
        else:
            name_h = f'<span class="dbk-name is-static"><bdi dir="auto">{esc(title)}</bdi></span>'
        code = (b.get("confirmation_code") or "").strip()
        code_h = ""
        if code:
            label = f'#{code}' if not code.startswith("#") else code
            aria = f'{(ui.get("manage") or ui.get("code") or "Code")} {code}'
            if b.get("manage_url"):
                code_h = (
                    f'<a class="dbk-code" href="{esc(b["manage_url"])}" target="_blank" '
                    f'rel="noopener noreferrer" aria-label="{esc(aria)}">'
                    f'<bdi dir="ltr" class="tnum">{esc(label)}</bdi></a>'
                )
            else:
                code_h = f'<span class="dbk-code"><bdi dir="ltr" class="tnum">{esc(label)}</bdi></span>'
        sort = (dt.isoformat() if dt else "")
        items.append(
            f'<li class="dbk-row" data-booking="{esc(b.get("id") or "")}" data-sort="{esc(sort)}">'
            f'<span class="dbk-ic" aria-hidden="true">{ic(icon_name)}</span>'
            f'<div class="dbk-body">{when_h}'
            f'<div class="dbk-main">{name_h}{code_h}</div></div></li>'
        )
    heading = ui.get("dest_booked") or "What's booked"
    return (
        f'<div class="blk dest-booked" id="{esc(dest_id)}-booked">'
        f'<h4 class="blk-h">{ic("check-circle")}{esc(heading)}</h4>'
        f'<ul class="dbk-list">{"".join(items)}</ul></div>'
    )


def deadline_cards(data, ui, lang: str = "en") -> str:
    """Short action title + short what/where detail + a readable date line."""
    detail_key = {
        "charge_at": "charge_detail",
        "cancel_deadline": "cancel_detail",
        "checkin_at": "checkin_detail",
    }
    cards = []
    links = places_linking_booking(data)
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
            if field == "checkin_at":
                title = checkin_deadline_label(b, links.get(b.get("id") or "", []), ui)
            else:
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
    trip = data["trip"]
    home = trip.get("home") or {}
    home_tz = trip.get("home_tz") or "UTC"
    clocks = [clock_tile(home_tz, home.get("name") or ui.get("home_clock") or "", home_flag(data, ui), "home", None, ui)]
    blocks = []
    for i, c in enumerate(countries):
        if c.get("timezone"):
            clocks.append(clock_tile(c["timezone"], loc(c.get("name"), lang) or c["id"], render_flag(c, "lg"), c["id"], i, ui))
        span, nights_h, _opt_h, dests = country_span_and_nights(data, c, lang, ui)
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
            f'<div class="folio-block ov-card" style="--block-color:var(--region-{i})">'
            f'<p class="kicker"><bdi class="tnum" dir="ltr">{esc(span)}</bdi></p>'
            f'<div class="h-flag"><p class="display">{esc(name)}</p>{flag}</div>'
            f'<p class="nights-line">{esc(nights_h)}</p>'
            f'<p class="stops-line">{wrap_latin("·".join(stops))}</p>'
            "</div>"
        )
    return (
        f'<section class="ov13" id="overview" data-nav="{esc(nav_label(data, ui, "overview"))}" aria-label="{esc(ui.get("at_a_glance") or "")}">'
        f'<div class="clocks" role="group" aria-label="{esc(ui.get("clocks_label") or "")}">{"".join(clocks)}</div>'
        f'{render_glance(data, ui, lang)}'
        f'<div class="ov-cards">{"".join(blocks)}</div>'
        '<div class="today-banner" id="todayBanner" hidden></div>'
        '<div class="today-card card glass g-thick" id="todayCard" hidden></div>'
        '<p class="locate-msg" id="locateMsg" hidden></p>'
        "</section>"
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
        f'<figure class="map map-band" id="map" data-nav="{esc(nav_label(data, ui, "map"))}">'
        f'<div class="map-tools">'
        f'<button type="button" class="stop-toggle press" id="btnLiveMap" aria-pressed="true">{icon("ph-map-trifold")}{esc(ui["live_map"])}</button>'
        f'<button type="button" class="stop-toggle press" id="btnSvgMap" aria-pressed="false">{icon("ph-path")}{esc(ui["overview_map"])}</button>'
        f'<p class="map-offline-note" id="mapOfflineNote" hidden></p>'
        f"</div>"
        f'<div id="mapLive" class="map-live" dir="ltr" role="region" aria-label="{esc(ui["live_map"])}"></div>'
        f'<div id="mapFallback" class="map-fallback" hidden>{fallback}</div>'
        f"{cap_h}</figure>"
    )


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
    """Build the grouped place list. The default template no longer embeds this
    in destination cards; recommendations are reached through the search dialog
    (`T.recs` in the runtime payload). Kept for the classic template's twin and
    for any caller that still wants the markup.
    """
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
        f'<li class="rec" id="{esc(pid)}"><div class="rec-top"><b><bdi dir="auto">{esc(name)}</bdi></b>{price_h}{caut}{opt}</div>'
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
    icn = x.get("icon") or MODE_ICON.get(x.get("mode") or "", "ph-path")
    route = x.get("route_label") or f'{x.get("from", "")} -> {x.get("to", "")}'
    meta_bits = []
    meta_bits.extend(xfer_when_bits(x))
    carrier = " ".join(filter(None, [x.get("carrier") or "", x.get("number") or ""]))
    if carrier:
        meta_bits.append(f"<span>{raw_ltr(carrier)}</span>")
    meta_bits.append(badge(st, ui, optional=x.get("optional")))
    b = booking_by_id(data, x.get("booking_id")) if x.get("booking_id") else None
    parts = []
    if b:
        parts.append(booking_block(b, ui))
    parts.append(dl_grid(xfer_rows(data, x, b, ui)))
    for block in x.get("details_blocks") or []:
        rows = item_rows(block.get("items") or [], "info", "", ui)
        parts.append(f'<div class="blk"><h4 class="blk-h">{esc(block.get("heading") or "")}</h4>{dl_grid(rows)}</div>')
    inner = "".join(p for p in parts if p)
    xid = x.get("id") or "xfer"
    when = _ymd(transfer_date(data, x))
    arr = parse_iso_dt(x.get("arrive_at"))
    dates_attr = f' data-from="{esc(when)}" data-to="{esc(when)}"' if when else ""
    return (
        f'<article class="{cls}" id="xfer-{esc(xid)}"{dates_attr}>'
        f'{date_col(transfer_date(data, x), lang)}'
        f'<div class="node" aria-hidden="true"><i class="dot"></i></div>'
        f'<div class="col">'
        f'<span class="pin" aria-hidden="true"></span>'
        f'<button type="button" class="xfer-sum" aria-expanded="false" aria-controls="xfer-{esc(xid)}-d">'
        f'<span class="xfer-head">{xfer_chip(x.get("mode") or icn)}<span class="xfer-route">{raw_ltr(route)}</span></span>'
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
    cls = "item stay stop rv"
    if stay_st == "booked":
        cls += " is-closed"
    if optional:
        cls += " is-optional"
    cls += " card-toggle"
    name = loc(dest.get("name"), lang) or did
    icn = dest.get("icon") or "ph-map-pin"
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
            meta_bits.append(f"<span>{latin_or_text(stay_label)}</span>")
    elif stay_st != "booked" and not nights_undecided:
        meta_bits.append(f'<span class="badge wait">{esc(stay_label or ui["stay_open"])}</span>')
    meta = "".join(meta_bits)
    xfer_line = f'<p class="stop-xfer">{wrap_latin(raw_ltr(info["summary_transfer"]))}</p>' if info.get("summary_transfer") else ""
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
        f'<div class="season-note glass g-thin">{icon("ph-warning-circle")}{wrap_latin(raw_ltr(info["season_note"]))}</div>'
        if info.get("season_note") else ""
    )

    def block(title, status, rows, extra_class="", source=""):
        grid = dl_grid(rows)
        if not grid:
            return ""
        src = f'<p class="src-note">{raw_ltr(source)}</p>' if source else ""
        cls_ = f"blk {extra_class}".strip()
        return f'<div class="{cls_}"><h4 class="blk-h">{esc(title)}{badge(status, ui) if status else ""}</h4>{grid}{src}</div>'

    blocks = []
    b = booking_by_id(data, info.get("stay_booking_id")) if info.get("stay_booking_id") else None
    if stay_st == "booked" or b:
        blocks.append(block(ui.get("dl_stay") or "", "booked" if stay_st == "booked" else "", stay_rows(data, dest, info, b, ui, lang)))
    elif not optional and dest.get("nights") is not None:
        n = int(dest["nights"])
        span = tchip(esc(date_lbl)) if date_lbl else ""
        rows = [
            ("moon", ui.get("nights") or "", esc(pluralize(n, ui.get("plural_night") or {"one": "1 night", "other": "{n} nights"})).replace(str(n), tn(str(n)), 1) + (", " + span if span else "")),
            ("bed", ui.get("dl_hotel") or "", esc(stay_label or ui["stay_open"])),
        ]
        blocks.append(block(ui.get("dl_lodging") or "", "", rows))
    arr = info.get("arrival") or {}
    if arr.get("items"):
        blocks.append(block(arr.get("title") or ui["arrival"], "", item_rows(arr.get("items"), "path", ui.get("dl_step") or "", ui)))
    for bl in info.get("blocks") or []:
        blocks.append(block(bl.get("heading") or "", "", item_rows(bl.get("items") or [], bl.get("icon") or "info", ui.get("dl_note") or "", ui)))
    wx = info.get("weather") or {}
    if wx.get("items"):
        blocks.append(block(wx.get("title") or ui["weather"], "", item_rows(wx["items"], "thermometer", ui.get("dl_climate") or "", ui), "wx", wx.get("source") or ""))
    food = info.get("food_notes") or {}
    if food.get("items"):
        blocks.append(block(food.get("title") or ui["food"], "", item_rows(food["items"], "fork-knife", ui.get("dl_dishes") or "", ui), "food", food.get("source") or ""))
    booked_plan = render_dest_booked_plan(data, did, ui, lang)
    nav_btn = ""
    if info.get("nav_url"):
        nav_btn = (
            f'<div class="stop-actions"><a class="navbtn press" href="{esc(info["nav_url"])}" target="_blank" rel="noopener noreferrer">'
            f'{icon("ph-navigation-arrow")}{esc(ui.get("navigate_stay") or ui["navigate"])}</a></div>'
        )
    opt_attr = ' data-optional="true"' if optional else ""
    d_from, d_to = dates.get("start") or "", dates.get("end") or ""
    dates_attr = (f' data-from="{esc(d_from)}"' if d_from else "") + (f' data-to="{esc(d_to)}"' if d_to else "")
    hid = f"stop-{did}-title"
    return (
        f'<article class="{cls}" id="stop-{esc(did)}" data-id="{esc(did)}"{opt_attr}{dates_attr}>'
        f'{date_col(dates.get("start"), lang)}'
        f'<div class="node" aria-hidden="true"><i class="dot"></i></div>'
        f'<div class="col">'
        f'<span class="pin">{index}</span>'
        f'<div class="stop-sum">'
        f'<span class="stop-ic" aria-hidden="true">{icon(icn)}</span>'
        f'<div class="stop-sum-top"><h3 id="{esc(hid)}">{esc(name)}</h3></div>'
        f'<div class="stop-meta">{meta}</div>{xfer_line}{note_line}'
        f'{nav_btn}'
        f'<button type="button" class="stop-toggle stop-caret" aria-expanded="false" aria-controls="{esc(did)}-detail" aria-labelledby="{esc(hid)}">{icon("ph-caret-down")}</button>'
        f'</div>'
        f'<div class="fold"><div class="fold-inner" inert aria-hidden="true">'
        f'<div class="stop-detail" id="{esc(did)}-detail">'
        f'<button type="button" class="sheet-close press" aria-label="{esc(ui["close"])}">{icon("ph-x")}{esc(ui["close"])}</button>'
        f'{season}{taxi}<div class="rows">{"".join(x for x in blocks if x)}</div>{booked_plan}'
        f'</div></div></div></div></article>'
    )


def render_country_axis(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    cid = country["id"]
    dests = [d for d in data["trip"]["destinations"] if d.get("country") == cid]
    leading, after, trailing = transfers_in_country(data, cid)
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
    meta = f'<bdi class="tnum" dir="ltr">{esc(span)}</bdi>· {esc(nights_h)}'
    opt_line = f'<p class="ch-opt"><span class="stop-opt">{esc(opt_h)}</span></p>' if opt_h else ""
    flag = render_flag(country, "sm")
    return (
        f'<section id="{esc(cid)}" class="country-block" data-nav="{esc(nav_label(data, ui, cid, country, lang))}" data-region="{region_i}" style="--block-color:var(--region-{region_i});--region:var(--region-{region_i})">'
        f'<div class="country-head"><span class="nm">{esc(name)}</span>'
        f'<span class="meta">{meta}</span><span class="rule"></span>{flag}</div>{opt_line}'
        f'<div class="tline" data-region="{region_i}" style="--block-color:var(--region-{region_i});--region:var(--region-{region_i})">{"".join(parts)}</div>'
        "</section>"
    )


def render_country_rest(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    color = safe_css_color(region_color(country, region_i), REGION_COLORS[region_i % len(REGION_COLORS)])
    cid = country["id"]
    head = (
        f'<div class="rest-country" data-region="{region_i}" style="--region:var(--region-{region_i})">'
        f'<span class="rc-name">{esc(loc(country.get("name"), lang))}</span>{render_flag(country, "lg")}<span class="rc-rule"></span></div>'
    )
    chunks = [
        head,
        render_days(data, cid, country, ui, lang, first=(region_i == 0)),
        pair(render_practical(country, ui, lang, region_i, color, data=data), render_phrases(country, ui, lang, data=data)),
        pair(render_packing_country(country, ui, lang), render_entry(country, ui, lang)),
        render_decisions(data, cid, ui, lang),
    ]
    return "\n".join(c for c in chunks if c)


def render_country(data, country, region_i, ui, lang, exclude_not_ok=False) -> str:
    return (
        render_country_axis(data, country, region_i, ui, lang, exclude_not_ok=exclude_not_ok)
        + render_country_rest(data, country, region_i, ui, lang, exclude_not_ok=exclude_not_ok)
    )


def kv_row(label, body) -> str:
    return f'<div class="row glass g-thin"><span class="k">{raw_ltr(label)}</span><span class="v">{body}</span></div>'


def render_practical(country, ui, lang, region_i, color, data=None) -> str:
    tiles = practical_tiles(data, country, ui, lang) if data else ""
    em = country.get("emergency") or []
    emer = ""
    if em:
        four = " four" if len(em) == 4 else ""
        emer = (f'<div class="emer-row"><h3 class="emer-h">{ic("siren")}{esc(ui["emergency"])}</h3>'
                f'<div class="callpills{four}">{"".join(callpill(e) for e in em)}</div></div>')
    emb = country.get("embassy") or {}
    emb_h = embassy_card(emb, ui) if (emb.get("name") or emb.get("phone")) else ""
    if not (tiles or emer or emb_h):
        return ""
    cid = country["id"]
    h = country.get("practical_headline") or ui["practical"]
    fx = ((data or {}).get("trip") or {}).get("fx") or {}
    lede = country.get("practical_lede") or ""
    if tiles and fx.get("date") and ui.get("practical_note"):
        lede_h = esc(ui["practical_note"]).replace("{date}", tn(esc(_dmy(fx.get("date")))))
    else:
        lede_h = raw_ltr(lede)
    nav = nav_label(data, ui, f"{cid}-practical", country, lang) if data else ""
    return (
        f'<section id="{esc(cid)}-practical" class="sec country-chunk pract" data-nav="{esc(nav)}" data-region="{region_i}" style="--region:var(--region-{region_i})">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-compass")}{esc(ui["practical"])} · {esc(loc(country.get("name"), lang))}</div>'
        f'<h2>{raw_ltr(h)}</h2><p>{lede_h}</p></div>'
        f'{tiles}{emer}{emb_h}</section>'
    )


def render_phrases(country, ui, lang, data=None) -> str:
    ph = country.get("phrases") or {}
    groups = ph.get("groups") or []
    if not groups and not ph.get("headline"):
        return ""
    trip = (data or {}).get("trip") or {}
    note = (trip.get("dietary_note") or "").strip()
    diet_codes = party_dietary(data) if data else []
    ok_items = trip.get("dietary_ok") or []
    diet = ""
    if diet_codes:
        lis = [f'<li class="no">{ic("prohibit")}{esc(ui.get("diet_" + c) or c.replace("-", " "))}</li>' for c in diet_codes]
        lis += [f'<li class="ok">{ic("check")}{esc(x)}</li>' for x in ok_items]
        diet = f'<ul class="diet" aria-label="{esc(ui.get("diet_aria") or ui.get("dietary") or "")}">{"".join(lis)}</ul>'
    intro_items = ph.get("intro") or []
    if diet and ok_items and note:
        # the chips now say it; drop the intro line that only repeats the party's dietary note
        intro_items = [x for x in intro_items if note not in x]
    intro = "".join(f'<p class="note">{quote_iso(raw_ltr(x))}</p>' for x in intro_items)
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
        f'<aside class="waiter phrases glass sec" id="phrases-{esc(cid)}">'
        f'<h3>{icon("ph-identification-card")}{esc(ph.get("headline") or ui.get("dietary") or "")}</h3>'
        f'{diet}{intro}{"".join(cols)}</aside>'
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
        bars = ""
        if opts and any(o.get("k") is not None or o.get("o") is not None for o in opts):
            mx = max(max(o.get("k") or 0, o.get("o") or 0) for o in opts) or 1
            cols = "".join(
                f'<div class="ob"><div class="ob-bars"><span class="r0" style="--h:{(o.get("k") or 0) / mx:.3f}"><b class="tnum">{esc(o.get("k") or 0)}</b></span>'
                f'<span class="r1" style="--h:{(o.get("o") or 0) / mx:.3f}"><b class="tnum">{esc(o.get("o") or 0)}</b></span></div>'
                f'<div class="ob-l">{esc(o.get("name") or "")}</div></div>'
                for o in opts
            )
            labels = d.get("series_labels") or [ui.get("series_a") or "A", ui.get("series_b") or "B"]
            legend = (f'<div class="ob-legend"><span class="r0">{esc(labels[0])}</span>'
                      f'<span class="r1">{esc(labels[1] if len(labels) > 1 else "")}</span></div>')
            bars = (
                '<div class="viz glass g-reg rv" style="margin-top:var(--s4)">'
                f'<div class="viz-head"><h3>{esc(d.get("chart_caption") or "")}</h3></div>'
                f'<div class="optbars" role="img" aria-label="{esc(d.get("chart_caption") or "")}">{cols}</div>{legend}</div>'
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
        first = bool(all_dec) and d is all_dec[0]
        sid = "choose" if first else f'choose-{d["id"]}'
        nav = f' data-nav="{esc(nav_label(data, ui, "choose"))}"' if first else ""
        out.append(
            f'<section id="{esc(sid)}" class="sec"{nav}>'
            f'<div class="sec-head rv"><div class="act">{icon("ph-path")}{esc(ui["choose"])}</div>'
            f'<h2>{raw_ltr(d.get("headline") or d.get("title") or "")}</h2>'
            f'<p>{raw_ltr(d.get("lede") or "")}</p></div>'
            f'<div class="opts" id="optCards-{esc(d["id"])}">{"".join(cards)}</div>'
            f'{steps}{bars}{note}</section>'
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
        title = clean_status(day.get("title") or "", ui)
        body = clean_status(day.get("body") or "", ui)
        rows.append(
            f'<div class="{cls}" data-day="{esc(key)}" data-iso="{esc(dt)}">'
            f'<div><span class="d ltr tnum">{esc(short)}</span> <span class="w">{esc(day.get("weekday") or "")}</span></div>'
            f'<div><strong>{wrap_latin(raw_ltr(title))}</strong> {opt}{st}</div>'
            f'<div>{wrap_latin(raw_ltr(body))}</div></div>'
        )
    act = country.get("journal_act") or ui["journal"]
    head = country.get("journal_headline") or ""
    lede = country.get("journal_lede") or ""
    sid = "days" if first else f"days-{cid}"
    nav = nav_label(data, ui, "days", country, lang)
    return (
        f'<section id="{esc(sid)}" class="sec country-chunk" data-nav="{esc(nav)}">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-calendar-blank")}{esc(act)}</div>'
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
    icons = {"restaurants": "fork-knife", "food": "fork-knife", "cafes": "coffee", "attractions": "camera",
             "sights": "camera", "shopping": "shopping-bag", "daytrip": "mountains", "daytrips": "mountains"}
    icons.update(ui.get("type_icons") or {})
    chips = "".join(
        f'<button type="button" class="press rs-t t-{esc(t)}" aria-pressed="false" data-t="{esc(t)}">{ic(icons.get(t, "map-pin"))}{esc(lab)}</button>'
        for t, lab in types
    )
    return (
        f'<section id="recs-search" class="sec" data-nav="{esc(nav_label(data, ui, "recs-search"))}">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-magnifying-glass")}{esc(ui.get("recs") or ui["search_places"])}</div>'
        f'<h2>{esc(ui["search_places"])}</h2><p>{esc(ui["search_lede"])}</p></div>'
        f'<div class="rsearch rv rs13" role="search"><div class="rs-main">'
        f'<div class="seg rseg" id="rsCountry" role="group">{segs}</div>'
        f'<div class="rs-field">'
        f'<input id="rsq" type="search" aria-label="{esc(ui.get("search_in_recs") or ui["search_places"])}" placeholder="{esc(ui["search_placeholder"])}" autocomplete="off" enterkeyhint="search" spellcheck="false"></div>'
        f'<div class="rs-chips" id="rsTypes" role="group">{chips}</div>'
        f'<div class="rs-chips" id="rsCities" role="group"></div>'
        f'<p class="rs-count" id="rsCount" aria-live="polite"></p>'
        f'<ul class="rs-list" id="rsList"></ul>'
        f'<p class="rs-empty" id="rsEmpty" hidden>{esc(ui["search_empty"])}</p></div></div></section>'
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
    total = bud["booked_total_home"] or 0
    fx = data["trip"].get("fx") or {}
    total_txt = "≈ " + _fmt_home_plain(total, home)
    # open estimate range in home currency
    lo = hi = 0.0
    have_open = False
    for e in bud["estimates"]:
        a = e.get("home_min") if e.get("home_min") is not None else e.get("home_amount")
        b = e.get("home_max") if e.get("home_max") is not None else e.get("home_amount")
        if a is None:
            continue
        have_open = True
        lo += a
        hi += b if b is not None else a
    circ = 2 * 3.14159265 * 34
    frac = total / (total + (lo + hi) / 2) if (total + (lo + hi) / 2) > 0 else 0
    pct = int(round(frac * 100))
    open_txt = _range_txt(lo, hi, home) if have_open else ""
    aria = (ui.get("budget_ring_aria") or "{closed} / {open}").replace("{closed}", _fmt_home_plain(total, home)).replace(
        "{open}", open_txt or "0")
    donut = (
        f'<svg class="donut" viewBox="0 0 84 84" role="img" aria-label="{esc(aria)}">'
        '<circle class="d-open" cx="42" cy="42" r="34"></circle>'
        f'<circle class="d-closed" cx="42" cy="42" r="34" stroke-dasharray="{frac * circ:.2f} {circ:.2f}" transform="rotate(-90 42 42)"></circle>'
        f'<text class="d-pct" x="42" y="47" text-anchor="middle">{pct}%</text></svg>'
    )
    key = f'<ul class="ring-key"><li class="k-closed">{esc(ui.get("closed_short") or ui["booked"])}</li>'
    if open_txt:
        key += f'<li class="k-open">{esc(ui.get("open_estimate") or ui["open"])} {tn(esc(open_txt))}</li>'
    key += "</ul>"
    fx_date = _dmy(fx.get("date")) if fx.get("date") else ""
    sub = f'<div class="sub">{raw_ltr(fx.get("label") or ui["fx"])}{(" · " + tn(esc(fx_date))) if fx_date else ""}</div>'
    budget_titles = {b.get("id"): b.get("budget_title") for b in data["bookings"].get("bookings") or [] if b.get("budget_title")}
    rows = []
    def _priced(r):
        return r.get("home_amount") is not None or r.get("amount") is not None

    for r in bud["booked_rows"]:
        if not _priced(r):
            continue
        code = r.get("confirmation_code") or ""
        name = (r.get("title") or "").replace(code, "").strip(" ·—-()") if code else (r.get("title") or "")
        name = budget_titles.get(r["id"]) or name
        amt = _fmt_home_plain(r["home_amount"], home) if r.get("home_amount") is not None else ""
        rows.append(
            f'<li><span class="br-n">{latin_or_text(name)}</span>'
            + (f'<bdi dir="ltr" class="tnum br-c">{esc(code)}</bdi>' if code else "")
            + (f'<bdi dir="ltr" class="tnum br-a">{esc(amt)}</bdi>' if amt else "")
            + "</li>"
        )
    note = data["trip"].get("budget_note") or ui.get("budget_note") or ""
    card = (
        f'<div class="bud13 rv"><div class="bud13-top"><div class="bud13-sum">'
        f'<div class="lab">{esc(ui.get("budget_card_lab") or ui["budget_hero"])}</div>'
        f'<div class="bud-total" dir="ltr"><span class="tnum" data-budget-total>{esc(total_txt)}</span></div>{sub}</div>'
        f'<div class="bud13-ring">{donut}{key}</div></div>'
        f'<ul class="bud13-rows">{"".join(rows)}</ul>'
        + (f'<p class="bud13-note">{raw_ltr(note)}</p>' if note else "")
        + '<div id="budgetExtra" data-budget-hook="expenses" hidden></div></div>'
    )

    btitle = budget_titles
    bmap = {b.get("id"): b for b in data["bookings"].get("bookings") or []}

    def lr(name_html, badge_html, amt_txt, detail_html, code=""):
        act = ""
        if code:
            act = f'<div class="bk-actions">{act_btn("copy", ui["copy"], copy=code, aria=ui["copy"] + " " + code)}</div>'
        return (
            f'<li class="lr"><details><summary><span class="lr-n">{name_html}</span>{badge_html}'
            + (f'<bdi dir="ltr" class="tnum lr-a">{esc(amt_txt)}</bdi>' if amt_txt else "")
            + f'{ic("caret-down", "ic car")}</summary><div class="lr-d">{detail_html}{act}</div></details></li>'
        )

    closed = []
    for r in bud["booked_rows"]:
        if not _priced(r):
            continue
        code = r.get("confirmation_code") or ""
        amt = _fmt_home_plain(r["home_amount"], home) if r.get("home_amount") is not None else ""
        orig = money(r["amount"], r["currency"]) if r.get("amount") is not None else ""
        bk = bmap.get(r["id"]) or {}
        facts = [bk.get("charge_detail"), bk.get("cancel_detail")]
        if any(facts):
            # structured facts read better than the free-text note in a one-line list
            body = [chips_ltr(clean_status(f, ui)) for f in facts if f]
        else:
            body = [note_value(clean_status(r.get("notes") or "", ui), ui)] if r.get("notes") else []
        det = " · ".join(x for x in [orig] + body if x)
        closed.append(lr(latin_or_text(btitle.get(r["id"]) or r.get("title") or ""), badge("booked", ui), amt, det, code))
    opened = []
    for e in bud["estimates"]:
        rng = _range_txt(e.get("amount_min") if e.get("amount_min") is not None else e.get("amount"),
                         e.get("amount_max"), e.get("currency"))
        opened.append(lr(latin_or_text(e.get("title") or ""), f'<span class="badge wait">{esc(e.get("label") or ui["open"])}</span>',
                         rng, raw_ltr(e.get("notes") or "")))
    for r in bud["open_rows"]:
        if any(e.get("id") == r["id"] or e.get("booking_id") == r["id"] for e in bud["estimates"]):
            continue
        amt = _range_txt(r.get("amount"), None, r.get("currency")) if r.get("amount") is not None else "—"
        opened.append(lr(latin_or_text(r.get("title") or ""), badge("open", ui), amt, raw_ltr(clean_status(r.get("notes") or "", ui))))
    lists = (
        '<div class="bud-lists">'
        f'<div class="blist"><h3>{ic("check-circle")}{esc(ui["budget_booked"])}</h3><ul>{"".join(closed)}</ul></div>'
        f'<div class="blist"><h3>{ic("hourglass")}{esc(ui["budget_open"])}</h3><ul>{"".join(opened)}</ul></div></div>'
    )
    return (
        f'<section id="budget" class="sec" data-nav="{esc(nav_label(data, ui, "budget"))}">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-wallet")}{esc(ui["budget"])}</div>'
        f'<h2>{esc(ui.get("budget_h2") or ui["budget"])}</h2></div>'
        f'{card}{lists}</section>'
    )


def render_fx(data, ui) -> str:
    fx = data["trip"].get("fx") or {}
    rates = fx.get("rates_to_home") or {}
    if not rates:
        return ""
    home = fx.get("home") or data["trip"].get("currency") or ""
    opts = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in rates)
    return (
        f'<section id="fx" class="sec" data-nav="{esc(nav_label(data, ui, "fx"))}">'
        f'<div class="sec-head rv"><div class="act">{icon("ph-currency-circle-dollar")}{esc(ui["fx"])}</div>'
        f'<h2>{esc(ui["fx"])}{(" · " + tn(esc(_dmy(fx.get("date"))))) if fx.get("date") else ""}</h2>'
        f'<p>{raw_ltr(fx.get("label") or "")}</p></div>'
        f'<div class="card glass g-reg rv" style="margin-top:var(--s4)"><div class="convert">'
        f'<input id="fxAmt" type="number" inputmode="decimal" value="100" min="0" aria-label="{esc(ui["fx_amount"])}">'
        f'<select id="fxFrom" aria-label="{esc(ui["fx_currency"])}">{opts}</select>'
        f'<span class="muted">~</span>'
        f'<output id="fxOut" for="fxAmt fxFrom">{esc(symbol(home) or home)}</output>'
        f'</div></div></section>'
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
            f'<div class="code-row ins-dup"><div class="code-meta"><span class="who">{esc(title)}</span>'
            f'<bdi dir="ltr" class="code tnum">{esc(code)}</bdi></div>'
            f'<div class="code-actions">{badge("booked", ui)}{copybtn(code, ui)}</div></div>'
        )
    fx = trip.get("fx") or {}
    rates = fx.get("rates_to_home") or {}
    home = fx.get("home") or trip.get("currency") or ""
    snap = []
    for cur, rate in [(c, r) for c, r in rates.items() if c != home][:3]:
        try:
            r = float(rate)
        except (TypeError, ValueError):
            continue
        amt = 1000 if r < 0.05 else (100 if r < 1 else 1)
        home_txt = f"{amt * r:.2f}".rstrip("0").rstrip(".")
        snap.append(
            f'<div class="cell"><span class="a">{esc(symbol(cur))}{amt:,}</span>'
            f'<span class="b">{esc(symbol(home))}{esc(home_txt)}</span></div>'
        )
    fx_html = ""
    if snap:
        fx_date = _dmy(fx.get("date")) if fx.get("date") else ""
        fx_html = (
            f'<hr class="hr ins-dup"><h2 class="ins-dup">{esc(ui["fx"])}</h2>'
            f'<div class="fx-snap ins-dup">{"".join(snap)}</div>'
            f'<div class="src ins-dup">{raw_ltr(fx.get("label") or "")}'
            + (f' · <bdi class="tnum" dir="ltr">{esc(fx_date)}</bdi>' if fx_date else "")
            + "</div>"
        )
    codes_h = f'<hr class="hr ins-dup"><h2 class="ins-dup">{esc(ui["bookings"])}</h2>{"".join(codes)}' if codes else ""
    return (
        f'<aside class="instruments glass g-thick" id="instruments" aria-label="{esc(ui.get("instruments") or "")}">'
        f'<h2>{esc(ui.get("before_depart") or "")}</h2>'
        f'<div class="lead"><span class="tnum" id="countN">-</span></div>'
        f'<div class="sub" id="countL">{esc(ui["countdown_label"])}</div>'
        f'<div class="stack"><div class="k">{dep_h}</div></div>'
        f'<hr class="hr"><h2>{esc(ui["deadlines"])}</h2>'
        f"{deadlines}{codes_h}{fx_html}"
        "</aside>"
    )


def render_dock(data, ui, lang) -> str:
    return (
        f'<nav class="dock" aria-label="{esc(ui.get("contents") or "")}">'
        f'<button type="button" id="dockToday">{icon("ph-calendar-check")}<span>{esc(ui["today"])}</span></button>'
        f'<a href="#itinerary" id="dockItin">{icon("ph-path")}<span>{esc(ui.get("dock_itinerary") or ui.get("axis") or "")}</span></a>'
        f'<a href="#map" id="dockMap">{icon("ph-map-trifold")}<span>{esc(ui.get("dock_map") or ui["live_map"])}</span></a>'
        "</nav>"
    )


def render_panel(data, ui, lang, nav=None) -> str:
    links = "".join(f'<a href="#{esc(i)}">{esc(lab)}</a>' for i, lab in (nav or []))
    return (
        f'<button class="panel-toggle press" id="panelBtn" aria-controls="panel" aria-expanded="false">{icon("ph-list")} {esc(ui["contents"])}</button>'
        f'<aside class="toc-panel glass g-thick" id="panel" role="dialog" aria-label="{esc(ui["contents"])}">'
        f'<h3>{esc(ui["contents"])}</h3>{links}'
        f'<button class="close press" id="panelClose">{esc(ui["close"])}</button></aside>'
    )


def render_body(data, ui, lang, exclude_not_ok=False) -> str:
    countries = country_list(data)
    axis, rest = [], []
    for i, c in enumerate(countries):
        axis.append(render_country_axis(data, c, i, ui, lang, exclude_not_ok=exclude_not_ok))
        rest.append(render_country_rest(data, c, i, ui, lang, exclude_not_ok=exclude_not_ok))
    footer = data["trip"].get("footer") or ui["footer_default"]
    main = [
        render_overview(data, ui, lang),
        render_map_figure(data, ui, lang),
        f'<section class="itinerary" id="itinerary" data-nav="{esc(nav_label(data, ui, "itinerary"))}" aria-label="{esc(ui.get("axis") or "")}">'
        f'<h2>{esc(ui.get("axis") or "")}</h2>{"".join(axis)}</section>',
    ]
    rest_html = [
        "\n".join(s for s in rest if s),
        render_search(data, ui, lang),
        render_budget(data, ui, lang),
        render_fx(data, ui),
        pair(render_shared_pack(data, ui, lang), render_shared_docs(data, ui, lang)),
        render_tasks(data, ui, lang),
        f'<p class="foot rv">{raw_ltr(footer)}</p>',
    ]
    page = "\n".join(s for s in main + rest_html if s)
    nav = nav_from_html(page)
    sections = [
        sprite_html(),
        theme_style(data),
        '<div class="mesh" aria-hidden="true"></div>',
        '<div class="grain" aria-hidden="true"></div>',
        render_header(data, ui, lang, nav=nav),
        '<div class="shell">',
        '<div class="shell-main">',
        "\n".join(s for s in main if s),
        "</div>",
        render_instruments(data, ui, lang),
        "</div>",
        '<div class="rest">',
        "\n".join(s for s in rest_html if s),
        "</div>",
        render_panel(data, ui, lang, nav=nav),
        render_dock(data, ui, lang),
        f'<div class="today-pop glass g-thick" id="todayPop" role="dialog" aria-modal="false" aria-labelledby="todayPopT" hidden>'
        f'<span class="tp-ic">{ic("calendar-check")}</span><p id="todayPopT"></p>'
        f'<button type="button" class="tp-go press" id="todayPopGo">{esc(ui.get("today_go_first") or "")}</button>'
        f'<button type="button" class="tp-x press" id="todayPopX" aria-label="{esc(ui["close"])}">{ic("x")}</button></div>',
        '<dialog class="rs-dlg" id="rsDialog" aria-labelledby="rsdTitle"><div class="rs-detail" id="rsDetail" tabindex="-1"></div></dialog>',
    ]
    return fix_rtl_in_ltr("\n".join(s for s in sections if s))


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
                if r.get("home_amount") is not None or r.get("amount") is not None
            ],
            "total": bud["booked_total_home"],
            "estimates_chart": estimates_chart,
        },
        "nights": nights_payload(data, lang),
        "places": places,
        "recs": recs,
        "today": today,
        "decisions": decisions,
        "countries": [{"id": c["id"], "name": loc(c.get("name"), lang), "region_i": i, "tz": c.get("timezone")} for i, c in enumerate(country_list(data))],
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
