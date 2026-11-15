#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contrast checks for an easy-to-trip page.

Fails if light or dark --muted is under 4.5:1 on --paper, or if a dark-mode
--region-N token is under 4.5:1 on the dark paper. Light region colours are
reported as warnings only (they may be decorative).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from trip_lib import (  # noqa: E402
    DARK_PAPER,
    LIGHT_PAPER,
    contrast_ratio,
    parse_hex_color,
)

MIN = 4.5
# Tokens that sit on paper as body/chrome text (must pass both themes).
TEXT_TOKENS = ("--muted", "--ink", "--ink-2", "--text", "--text-2")


def _blocks(css: str):
    """Yield (selectors, body) for simple CSS rule blocks."""
    for m in re.finditer(r"([^{}@]+)\{([^{}]+)\}", css):
        yield m.group(1).strip(), m.group(2)


def _decls(body: str) -> dict:
    out = {}
    for part in body.split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k, v = k.strip(), v.strip()
        if k.startswith("--"):
            out[k] = v
    return out


def extract_themes(html: str) -> dict:
    """Return {'light': {token: hex}, 'dark': {token: hex}} from style tags."""
    styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)
    css = "\n".join(styles)
    light, dark = {}, {}
    for sel, body in _blocks(css):
        decls = {k: v for k, v in _decls(body).items() if parse_hex_color(v)}
        if not decls:
            continue
        sl = sel.lower()
        if "data-theme" in sl and "dark" in sl:
            dark.update(decls)
        elif "data-theme" in sl and "light" in sl:
            light.update(decls)
        elif ":root" in sl or "html" == sl.strip():
            # :root is the light defaults in this template
            if "dark" not in sl:
                light.update(decls)
    return {"light": light, "dark": dark}


def _paper(tokens: dict, fallback):
    rgb = parse_hex_color(tokens.get("--paper") or tokens.get("--bg") or "")
    return rgb or fallback


def check(html: str) -> tuple[list[str], list[str]]:
    fails, warns = [], []
    themes = extract_themes(html)
    for theme, fallback in (("light", LIGHT_PAPER), ("dark", DARK_PAPER)):
        tokens = themes.get(theme) or {}
        paper = _paper(tokens, fallback)
        # muted is the required check
        for tok in TEXT_TOKENS:
            raw = tokens.get(tok)
            rgb = parse_hex_color(raw or "")
            if not rgb:
                continue
            r = contrast_ratio(rgb, paper)
            msg = f"{theme} {tok} {raw} on {hex_paper(paper)} = {r:.2f}:1"
            if r + 1e-9 < MIN:
                if tok == "--muted" or tok in ("--ink", "--text"):
                    fails.append(msg)
                else:
                    warns.append(msg)
            else:
                warns.append("PASS " + msg)
        if theme == "dark":
            for k, raw in tokens.items():
                if not re.fullmatch(r"--region-\d+", k):
                    continue
                rgb = parse_hex_color(raw)
                if not rgb:
                    continue
                r = contrast_ratio(rgb, paper)
                msg = f"dark {k} {raw} on {hex_paper(paper)} = {r:.2f}:1"
                if r + 1e-9 < MIN:
                    fails.append(msg)
                else:
                    warns.append("PASS " + msg)
    return fails, warns


def hex_paper(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path)
    args = ap.parse_args(argv)
    html = args.html.read_text(encoding="utf-8")
    fails, warns = check(html)
    for w in warns:
        print(w)
    if fails:
        print("CONTRAST FAIL:")
        for f in fails:
            print("  ", f)
        return 1
    print("contrast: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
