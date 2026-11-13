#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layout QA for the easy-to-trip default template.

Optional dependency: Playwright (and a Chromium/Chrome binary). If Playwright
is not installed, this script exits 2 and prints how to install it.

Asserts, at 390 and 1440 × light/dark (and optionally folds closed/open):
  - rail x within ±1px of every node's centre (after entrance animations settle)
  - rail x outside every card (.col) by ≥8px
  - transfer-mode chips: no icon/title overlap; optical centre (getBBox +
    getScreenCTM) within 1px of the 32px chip centre
  - scrollWidth == clientWidth
  - no element overflows its parent (skips display:contents parents and real
    scroll containers: map, nav chips, tables)
  - nav/dock jumps with scroll-behavior:auto land at one header height, not two;
    the scrollspy highlights the target (threshold --header-h + 2, last match)
  - phones, booking codes, prices and times render on a single line (nowrap)
  - accordion 'open all' reproduces setFold (class + inert) or clicks one at a time
  - 0 console / page errors
  - pocket FAB hidden below 900px, kept on desktop

Usage:
  python3 qa_layout.py http://127.0.0.1:8766/japan-tokyo-kyoto.html
  python3 qa_layout.py --shots /tmp/shots http://host/page.html http://host/other.html

Pages are opened with ?static=1 and prefers-reduced-motion, so entrance
animations (.rv scale/translateY) cannot skew getBoundingClientRect.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(
        "qa_layout.py needs Playwright (optional skill dependency).\n"
        "  pip install playwright && python3 -m playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(2)

CHROME = Path("/usr/bin/google-chrome")
WIDTHS = [(390, 844), (1440, 900)]
THEMES = ("light", "dark")
FOLD_STATES = ("closed", "open")

SETTLE = """() => {
  document.documentElement.style.scrollBehavior = 'auto';
  document.documentElement.setAttribute('data-static','');
  document.querySelectorAll('.rv').forEach(el => {
    el.classList.add('in');
    el.style.transition = 'none';
    el.style.transform = 'none';
    el.style.opacity = '1';
  });
}"""

# Reproduce setFold (class + inert). The real helper lives inside an IIFE.
FORCE_FOLDS = """(open) => {
  const units = [...document.querySelectorAll('.tline > .item.stop, .tline > .item.xfer, .tl > .item.stop, .tl > .item.xfer, article.stay, article.xfer')];
  const seen = new Set();
  units.forEach(el => {
    if (seen.has(el)) return;
    seen.add(el);
    const fold = el.querySelector(':scope > .fold, :scope > .col > .fold');
    const inner = fold && fold.querySelector(':scope > .fold-inner');
    const btn = el.querySelector('.stop-toggle, .xfer-sum');
    if (open) {
      if (inner) { inner.removeAttribute('inert'); inner.removeAttribute('aria-hidden'); }
      el.classList.add('is-open');
      if (btn) btn.setAttribute('aria-expanded', 'true');
    } else {
      el.classList.remove('is-open');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      if (inner) { inner.setAttribute('inert', ''); inner.setAttribute('aria-hidden', 'true'); }
    }
  });
}"""

MEASURE = r"""() => {
  const rtl = document.documentElement.dir === 'rtl';
  const tlines = [...document.querySelectorAll('.tline, .tl')];
  const out = {tlines: [], overflows: [], overflowAllowed: [], icons: [], scroll: {}};

  function railCenter(tline) {
    const cs = getComputedStyle(tline, '::before');
    const tr = tline.getBoundingClientRect();
    const inset = parseFloat(cs.insetInlineStart);
    const w = parseFloat(cs.width) || 2;
    const center = rtl ? (tr.right - inset - w/2) : (tr.left + inset + w/2);
    return {center, inset, w,
            tline: {left:tr.left, right:tr.right, width:tr.width},
            content: cs.content, pos: cs.position,
            ring: null};
  }

  tlines.forEach((tline, ti) => {
    const rail = railCenter(tline);
    const items = [...tline.querySelectorAll(':scope > .item')];
    const rows = items.map(item => {
      const dot = item.querySelector(':scope > .node .dot, :scope > .node > i') || item.querySelector(':scope > .node .dot') || item.querySelector('.dot');
      const dr = dot.getBoundingClientRect();
      const col = item.querySelector(':scope > .col');
      const cr = col ? col.getBoundingClientRect() : null;
      const nodeCx = (dr.left + dr.right) / 2;
      const dx = nodeCx - rail.center;
      let inside = false, gapCard = null, okCard = true;
      if (cr && cr.width > 1) {
        inside = rail.center >= cr.left - 0.5 && rail.center <= cr.right + 0.5;
        gapCard = rtl ? (rail.center - cr.right) : (cr.left - rail.center);
        okCard = !inside && gapCard >= 8;
      }
      const dcs = getComputedStyle(dot);
      return {
        id: item.id,
        kind: item.classList.contains('xfer') ? 'xfer' : 'stay',
        open: item.classList.contains('is-open'),
        transform: getComputedStyle(item).transform,
        nodeCx, rail: rail.center, dx,
        gapCard, inside,
        okNode: Math.abs(dx) <= 1,
        okCard,
        ring: dcs.boxShadow,
        paper: getComputedStyle(document.documentElement).getPropertyValue('--paper').trim(),
        bg: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()
      };
    });
    out.tlines.push({
      index: ti, rail, rows,
      failNode: rows.filter(r => !r.okNode).map(r => ({id:r.id, dx:+r.dx.toFixed(2), tf:r.transform})),
      failCard: rows.filter(r => !r.okCard).map(r => ({id:r.id, gap:r.gapCard, inside:r.inside}))
    });
  });

  document.querySelectorAll('.xfer-chip').forEach(chip => {
    const cr = chip.getBoundingClientRect();
    const chipCx = (cr.left+cr.right)/2, chipCy = (cr.top+cr.bottom)/2;
    const svg = chip.querySelector('svg');
    const path = svg && svg.querySelector('path');
    let iconCx = chipCx, iconCy = chipCy, optical = null;
    if (svg) {
      const sr = svg.getBoundingClientRect();
      iconCx = (sr.left+sr.right)/2;
      iconCy = (sr.top+sr.bottom)/2;
      if (path && typeof path.getBBox === 'function') {
        try {
          const bb = path.getBBox();
          const pt = svg.createSVGPoint();
          pt.x = bb.x + bb.width/2;
          pt.y = bb.y + bb.height/2;
          const ctm = path.getScreenCTM();
          if (ctm) {
            const s = pt.matrixTransform(ctm);
            optical = {dx:s.x-chipCx, dy:s.y-chipCy};
          }
        } catch (e) {}
      }
    }
    const title = chip.closest('.xfer-head')?.querySelector('.xfer-route');
    let intersects = false, gap = null;
    if (title) {
      const tr = title.getBoundingClientRect();
      intersects = !(cr.right <= tr.left + 0.5 || cr.left >= tr.right - 0.5
                  || cr.bottom <= tr.top + 0.5 || cr.top >= tr.bottom - 0.5);
      gap = rtl ? (cr.left - tr.right) : (tr.left - cr.right);
    }
    const odx = optical ? optical.dx : (iconCx-chipCx);
    const ody = optical ? optical.dy : (iconCy-chipCy);
    out.icons.push({
      id: chip.closest('article')?.id,
      chip: {w:cr.width, h:cr.height, radius: getComputedStyle(chip).borderRadius},
      opticalDx: odx, opticalDy: ody,
      okCentre: Math.abs(odx) <= 1 && Math.abs(ody) <= 1,
      intersects, gap
    });
  });

  out.scroll = {
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    innerW: window.innerWidth,
    htmlOX: getComputedStyle(document.documentElement).overflowX,
    bodyOX: getComputedStyle(document.body).overflowX
  };

  const allowRe = /(leaflet|map-live|map-tools|nav-bar|chips|table-wrap|pocket|dock|instruments|folio|sr-only|visually-hidden|ol-overlay|ol-tmp)/i;
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.leaflet-container, .leaflet-pane, .leaflet-control-container, #mapLive, figure.map, .nav-bar, .chips, .table-wrap, .pocket, .dock, .sr-only')) {
      continue;
    }
    const p = el.parentElement;
    if (!p) continue;
    const pcs = getComputedStyle(p);
    if (pcs.display === 'contents' || pcs.display === 'none') continue;
    if (/(auto|scroll|hidden|clip)/.test(pcs.overflowX)) continue;
    const er = el.getBoundingClientRect();
    const pr = p.getBoundingClientRect();
    if (pr.width < 1 || er.width < 1 || er.height < 1) continue;
    const overR = er.right - pr.right;
    const overL = pr.left - er.left;
    if (overR > 2 || overL > 2) {
      const cls = (typeof el.className === 'string' ? el.className : '');
      const pcls = (typeof p.className === 'string' ? p.className : '');
      const tag = (el.id && '#'+el.id) || (cls.trim().split(/\s+/)[0]) || el.tagName;
      const rec = {
        tag, class: cls.slice(0, 60),
        overR: Math.round(overR*10)/10, overL: Math.round(overL*10)/10,
        elW: Math.round(er.width), parentW: Math.round(pr.width),
        parent: (p.id && '#'+p.id) || (pcls.trim().split(/\s+/)[0]) || p.tagName
      };
      if (allowRe.test(tag) || allowRe.test(cls) || allowRe.test(pcls) || allowRe.test(p.id||'')) {
        if (out.overflowAllowed.length < 8) out.overflowAllowed.push(rec);
        continue;
      }
      if (out.overflows.length < 20) out.overflows.push(rec);
    }
  }

  const header = document.querySelector('header.top');
  out.header = header ? {
    h: header.getBoundingClientRect().height,
    bottom: header.getBoundingClientRect().bottom,
    pos: getComputedStyle(header).position,
    var: getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim(),
    pad: getComputedStyle(document.documentElement).scrollPaddingTop,
    marginItin: (document.querySelector('#itinerary') && getComputedStyle(document.querySelector('#itinerary')).scrollMarginTop) || null
  } : null;

  const on = document.querySelector('.nav-bar a.on');
  out.nav = {on: on && on.getAttribute('href'), text: on && on.textContent.trim()};
  out.colors = {
    paper: getComputedStyle(document.documentElement).getPropertyValue('--paper').trim(),
    bg: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()
  };
  return out;
}"""

WRAP_JS = r"""() => {
  function lineInfo(el){
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()].filter(r => r.width > 0.5 && r.height > 0.5);
    const tops = [];
    rects.forEach(r => { if (!tops.some(t => Math.abs(t - r.top) < 1.5)) tops.push(r.top); });
    const text = (el.innerText || el.textContent || '').replace(/\s+/g,' ').trim();
    return {
      text, n: tops.length,
      h: +el.getBoundingClientRect().height.toFixed(1),
      w: +el.getBoundingClientRect().width.toFixed(1),
      ws: getComputedStyle(el).whiteSpace,
      wrap: getComputedStyle(el).overflowWrap
    };
  }
  function visible(el){
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  }
  const seen = new Set();
  const out = {phone:[], code:[], price:[], time:[]};
  function add(kind, el){
    if (!el || !visible(el)) return;
    const text = (el.innerText||'').replace(/\s+/g,' ').trim();
    if (!text) return;
    const r = el.getBoundingClientRect();
    const key = kind+'|'+text+'|'+el.tagName+'|'+Math.round(r.top*10)+'|'+Math.round(r.left);
    if (seen.has(key)) return;
    seen.add(key);
    const info = lineInfo(el);
    info.kind = kind;
    out[kind].push(info);
  }
  document.querySelectorAll('.emer .n .tnum, .emer .n, a[href^="tel:"] .tnum, a.call .tnum').forEach(el => {
    if (el.classList.contains('n') && el.querySelector('.tnum, bdi')) return;
    add('phone', el);
  });
  document.querySelectorAll('.code, .code.tnum, bdi.code').forEach(el => {
    const tx = (el.innerText||'').trim();
    if (/^[A-Z0-9]{4,12}$/.test(tx) || /^\d{8,12}$/.test(tx)) add('code', el);
  });
  document.querySelectorAll('.tnum, bdi, [dir="ltr"]').forEach(el => {
    if (el.querySelector('.tnum, bdi, [dir="ltr"]')) return;
    const tx = (el.innerText||'').trim();
    if (tx.length > 28) return;
    if (/[₪$€¥฿£]|USD|EUR|ILS|JPY|THB/.test(tx) && /\d/.test(tx)) add('price', el);
  });
  document.querySelectorAll('.tnum, bdi, [dir="ltr"], .xfer-leg').forEach(el => {
    if (el.querySelector('.tnum, bdi')) return;
    const tx = (el.innerText||'').trim();
    if (/^\d{1,2}:\d{2}(\s*[·–-]\s*\d{1,2}\.\d{2})?$/.test(tx)) add('time', el);
  });
  const fail = [];
  for (const kind of Object.keys(out)){
    for (const tok of out[kind]){
      if (tok.n > 1) fail.push(tok);
    }
  }
  return {
    fail,
    counts: {phone: out.phone.length, code: out.code.length, price: out.price.length, time: out.time.length}
  };
}"""


def with_static(url: str) -> str:
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.setdefault("static", "1")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def slug(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    name = path.split("/")[-1] or "page"
    if name == "index.html":
        parent = path.split("/")[-2] if "/" in path else "site"
        return parent
    return name.replace(".html", "")


def is_noise(text: str) -> bool:
    t = (text or "").lower()
    return any(s in t for s in (
        "favicon", "net::err_failed", "net::err_aborted",
        "404 (not found)", "404 (file not found)", "failed to load resource",
    ))


class Runner:
    def __init__(self, shots: Path | None):
        self.results = []
        self.shots = shots
        if shots:
            shots.mkdir(parents=True, exist_ok=True)

    def add(self, check, status, detail, width=None, theme=None, folds=None, page=None):
        rec = dict(check=check, status=status, detail=detail,
                   width=width, theme=theme, folds=folds, page=page)
        self.results.append(rec)
        loc = " ".join(str(x) for x in (page, width, theme, folds) if x is not None)
        short = str(detail)
        if len(short) > 240:
            short = short[:240] + "…"
        print(f"  [{status}] {check} {loc}: {short}")

    def open_page(self, browser, url, w, h, theme):
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.emulate_media(reduced_motion="reduce", color_scheme=theme)
        console, pageerrs = [], []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: pageerrs.append(str(e)))
        sep = "&" if "?" in url else "?"
        # theme is also a query so the page's own theme boot matches
        dest = url
        if "theme=" not in dest:
            dest = dest + sep + "theme=" + theme
        page.goto(dest, wait_until="load", timeout=60000)
        page.evaluate(
            """(theme) => {
              document.documentElement.dataset.theme = theme;
              document.documentElement.setAttribute('data-static','');
              document.documentElement.style.scrollBehavior = 'auto';
              try {
                const k = (window.TRIP && TRIP.storage_key) || 'easy-to-trip';
                localStorage.setItem(k+'-theme', theme);
              } catch(e) {}
            }""",
            theme,
        )
        page.evaluate(SETTLE)
        page.wait_for_timeout(150)
        return page, console, pageerrs

    def app_errors(self, console, pageerrs):
        bad = [e for e in pageerrs if not is_noise(e)]
        for c in console:
            if not is_noise(c):
                bad.append(c)
        return bad

    def nav_jumps(self, page):
        hrefs = page.evaluate(
            """() => [...document.querySelectorAll(".nav-bar a[href^='#'], .dock a[href^='#']")]
              .map(a => a.getAttribute('href'))
              .filter((v,i,arr) => v && v.length > 1 && arr.indexOf(v) === i)"""
        )
        fails = []
        lands = []
        for href in hrefs or []:
            page.evaluate(
                """(href) => {
                  document.documentElement.style.scrollBehavior = 'auto';
                  const vis = [...document.querySelectorAll(`.nav-bar a[href="${href}"], .dock a[href="${href}"]`)]
                    .find(el => {
                      const cs = getComputedStyle(el);
                      const r = el.getBoundingClientRect();
                      return cs.display !== 'none' && r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
                    });
                  if (vis) vis.click();
                  else {
                    const el = document.getElementById(href.slice(1));
                    if (el) el.scrollIntoView({block:'start', behavior:'auto'});
                  }
                }""",
                href,
            )
            page.wait_for_timeout(160)
            info = page.evaluate(
                """(href) => {
                  const header = document.querySelector('header.top');
                  const hr = header.getBoundingClientRect();
                  const raw = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'));
                  const el = document.getElementById(href.slice(1));
                  if (!el) return {err: 'no target', href};
                  const r = el.getBoundingClientRect();
                  const pad = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop);
                  const expected = Number.isFinite(pad) && pad>0 ? pad : hr.bottom;
                  // At the top of the page the first section may sit lower than
                  // expected without a jump; at the bottom we may not be able
                  // to scroll the last section all the way to the header.
                  const atEnd = (window.scrollY + window.innerHeight) >= (document.documentElement.scrollHeight - 4);
                  const atStart = window.scrollY <= 4;
                  const clear = r.top >= hr.bottom - 2 || (r.top < hr.bottom && r.bottom > hr.bottom);
                  const near = r.top <= expected + 48 || atEnd || atStart;
                  const double = !atEnd && !atStart && r.top > expected + (Number.isFinite(raw)?raw:hr.height) * 0.85;
                  return {
                    href,
                    headerH: +hr.height.toFixed(1), headerBottom: +hr.bottom.toFixed(1),
                    sectionTop: +r.top.toFixed(1),
                    expected: +expected.toFixed(1),
                    pad: getComputedStyle(document.documentElement).scrollPaddingTop,
                    margin: getComputedStyle(el).scrollMarginTop,
                    clear, near, atEnd, atStart,
                    notDouble: !double,
                    ok: clear && near && !double
                  };
                }""",
                href,
            )
            lands.append(info)
            if info.get("err") or not info.get("ok"):
                fails.append(info)
        return fails, hrefs, lands

    def section_spy(self, page):
        href = page.evaluate(
            """() => {
              const prefer = ['#budget','#itinerary','#map','#tasks','#nights'];
              const links = [...document.querySelectorAll('.nav-bar a[href^="#"]')].map(a => a.getAttribute('href'));
              return prefer.find(h => links.includes(h)) || links[links.length-1] || null;
            }"""
        )
        if not href:
            return {"ok": False, "why": "no nav targets"}
        page.evaluate(
            """(href) => {
              document.documentElement.style.scrollBehavior = 'auto';
              const a = document.querySelector(`.nav-bar a[href="${href}"]`);
              if (a) a.click();
              else {
                const el = document.getElementById(href.slice(1));
                if (el) el.scrollIntoView({block:'start', behavior:'auto'});
              }
            }""",
            href,
        )
        page.wait_for_timeout(280)
        return page.evaluate(
            """(href) => {
              const header = document.querySelector('header.top');
              const hr = header.getBoundingClientRect();
              const el = document.getElementById(href.slice(1));
              const on = document.querySelector('.nav-bar a.on');
              const raw = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'));
              const r = el ? el.getBoundingClientRect() : {top:0,bottom:0};
              return {
                target: href,
                href: on && on.getAttribute('href'),
                text: on && on.textContent.trim(),
                sectionTop: +r.top.toFixed(1),
                headerBottom: +hr.bottom.toFixed(1),
                headerVar: raw,
                scrollMargin: el && getComputedStyle(el).scrollMarginTop,
                scrollPad: getComputedStyle(document.documentElement).scrollPaddingTop,
                ok: !!(on && on.getAttribute('href') === href)
              };
            }""",
            href,
        )

    def click_fold_works(self, page):
        return page.evaluate(
            """() => {
              const stay = document.querySelector('article.stay, .tline > .item.stay, .tline > .item.stop');
              const xfer = document.querySelector('article.xfer, .tline > .item.xfer');
              function openOne(el){
                if (!el) return {ok:false, why:'missing'};
                const btn = el.querySelector('.stop-toggle, .xfer-sum, button[aria-expanded]');
                if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                const fold = el.querySelector(':scope > .fold, :scope > .col > .fold');
                const h = fold ? fold.getBoundingClientRect().height : 0;
                const ok = el.classList.contains('is-open') && h > 20;
                if (ok && btn) btn.click();
                return {ok, h, id: el.id, open: el.classList.contains('is-open')};
              }
              const s = openOne(stay);
              const x = openOne(xfer);
              return {stay:s, xfer:x, ok: !!(s.ok || (s.why==='missing' && x.ok)) && (x.ok || x.why==='missing')};
            }"""
        )

    def run_combo(self, browser, url, name, w, h, theme, folds, shot=False):
        page, cons, errs = self.open_page(browser, url, w, h, theme)
        try:
            page.evaluate(FORCE_FOLDS, folds == "open")
            page.evaluate(SETTLE)
            page.wait_for_timeout(80)
            m = page.evaluate(MEASURE)

            node_fails, card_fails, n_rows, unsettled, rings = [], [], 0, [], []
            for tl in m["tlines"]:
                n_rows += len(tl["rows"])
                node_fails += tl["failNode"]
                card_fails += tl["failCard"]
                unsettled += [
                    r["id"]
                    for r in tl["rows"]
                    if r.get("transform") not in ("none", "matrix(1, 0, 0, 1, 0, 0)")
                ]
                for r in tl["rows"]:
                    rings.append(r.get("ring") or "")
            self.add(
                "rail-node",
                "PASS" if not node_fails and not unsettled and n_rows >= 1 else "FAIL",
                f"rows={n_rows} fails={node_fails[:6]} unsettled={unsettled[:4]}",
                w, theme, folds, name,
            )
            self.add(
                "rail-card",
                "PASS" if not card_fails and n_rows >= 1 else "FAIL",
                f"fails={card_fails[:6]}",
                w, theme, folds, name,
            )
            # --paper ring (not a --bg halo). Look for 'rgb' of paper already in box-shadow.
            def _hex_rgb(h):
                h = (h or "").strip().lstrip("#")
                if len(h) == 6 and all(c in "0123456789abcdefABCDEF" for c in h):
                    return f"rgb({int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)})"
                return ""
            ring_fails = []
            for tl in m["tlines"]:
                for r in tl["rows"]:
                    ring = r.get("ring") or ""
                    paper = (r.get("paper") or "").strip()
                    paper_rgb = _hex_rgb(paper)
                    ok = (
                        "0px 0px 0px 3px" in ring
                        and (not paper_rgb or paper_rgb in ring)
                    )
                    if not ok:
                        ring_fails.append({
                            "id": r.get("id"), "ring": ring,
                            "paper": paper, "bg": r.get("bg"),
                        })
            self.add(
                "rail-ring",
                "PASS" if not ring_fails and n_rows >= 1 else "FAIL",
                f"fails={ring_fails[:4]} sample={rings[:1]}",
                w, theme, folds, name,
            )

            ic = m["icons"]
            if ic:
                bad_isect = [i for i in ic if i["intersects"]]
                bad_ctr = [i for i in ic if not i["okCentre"]]
                self.add(
                    "icon-text",
                    "PASS" if not bad_isect else "FAIL",
                    f"n={len(ic)} intersects={bad_isect}",
                    w, theme, folds, name,
                )
                self.add(
                    "icon-centre",
                    "PASS" if not bad_ctr else "FAIL",
                    f"n={len(ic)} off={[{k:i[k] for k in ('id','opticalDx','opticalDy')} for i in bad_ctr[:6]]} sample={ic[:1]}",
                    w, theme, folds, name,
                )
            else:
                self.add("icon-text", "SKIP", "no transfer chips on this page", w, theme, folds, name)
                self.add("icon-centre", "SKIP", "no transfer chips on this page", w, theme, folds, name)

            sc = m["scroll"]
            self.add(
                "scrollWidth",
                "PASS" if sc["scrollW"] <= sc["clientW"] + 1 else "FAIL",
                f"{sc}",
                w, theme, folds, name,
            )
            self.add(
                "overflow-parent",
                "PASS" if not m["overflows"] else "FAIL",
                f"real={m['overflows'][:8]} allowed={m.get('overflowAllowed', [])[:4]}",
                w, theme, folds, name,
            )

            if folds == "closed":
                jf, hrefs, lands = self.nav_jumps(page)
                self.add(
                    "nav-jump",
                    "PASS" if hrefs and not jf else "FAIL",
                    f"n_links={len(hrefs or [])} fails={jf[:5]} lands={lands[:3]}",
                    w, theme, folds, name,
                )
                page.evaluate(SETTLE)
                spy = self.section_spy(page)
                self.add(
                    "scrollspy",
                    "PASS" if spy.get("ok") else "FAIL",
                    f"{spy}",
                    w, theme, folds, name,
                )

            st = page.evaluate(
                """() => {
                  const h = document.querySelector('header.top');
                  const r = h.getBoundingClientRect();
                  return {pos:getComputedStyle(h).position, top:r.top, var:getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim(), h:r.height, margin: (document.querySelector('#itinerary')&&getComputedStyle(document.querySelector('#itinerary')).scrollMarginTop), pad:getComputedStyle(document.documentElement).scrollPaddingTop};
                }"""
            )
            self.add(
                "sticky",
                "PASS" if st["pos"] == "sticky" and abs(st["top"]) < 2 else "FAIL",
                f"{st}",
                w, theme, folds, name,
            )

            if folds == "open":
                fo = page.evaluate(
                    """() => {
                      const arts = [...document.querySelectorAll('article.stay.is-open, article.xfer.is-open, .item.is-open')];
                      const hs = arts.map(a => {
                        const f = a.querySelector(':scope > .fold, :scope > .col > .fold');
                        return {id:a.id, h: f ? f.getBoundingClientRect().height : 0};
                      });
                      return {n: arts.length, tall: hs.filter(x => x.h>20).length, sample: hs.slice(0,3)};
                    }"""
                )
                self.add(
                    "folds-open-all",
                    "PASS" if fo.get("tall", 0) >= 1 else "FAIL",
                    f"{fo}",
                    w, theme, folds, name,
                )
            elif w in (390, 1440) and theme == "light":
                cw = self.click_fold_works(page)
                self.add(
                    "folds-click",
                    "PASS" if cw.get("ok") else "FAIL",
                    f"{cw}",
                    w, theme, folds, name,
                )

            if folds == "closed" and theme == "light":
                fab = page.evaluate(
                    """() => {
                      const el = document.querySelector('.pocket-toggle, #pocketBtn');
                      if (!el) return {ok: true, missing: true};
                      const s = getComputedStyle(el);
                      const r = el.getBoundingClientRect();
                      const hidden = s.display==='none' || s.visibility==='hidden' || r.width<1 || r.height<1;
                      return {ok: (innerWidth<=899) ? hidden : !hidden, hidden, w: innerWidth, display:s.display};
                    }"""
                )
                self.add("pocket-fab", "PASS" if fab.get("ok") else "FAIL", f"{fab}", w, theme, folds, name)

            if folds == "closed" and (w == 390 or theme == "light"):
                wrap = page.evaluate(WRAP_JS)
                self.add(
                    "nowrap-tokens",
                    "PASS" if not wrap["fail"] else "FAIL",
                    f"fail={wrap['fail'][:6]} counts={wrap['counts']}",
                    w, theme, folds, name,
                )

            # html overflow-x clip, not hidden
            ox = m["scroll"]
            self.add(
                "overflow-x",
                "PASS" if ox["htmlOX"] != "hidden" and ox["bodyOX"] != "hidden" else "FAIL",
                f"html={ox['htmlOX']} body={ox['bodyOX']}",
                w, theme, folds, name,
            )

            bad = self.app_errors(cons, errs)
            self.add(
                "console",
                "PASS" if not bad else "FAIL",
                f"{bad}",
                w, theme, folds, name,
            )

            if shot and self.shots and folds == "closed":
                prefix = self.shots / f"{name}_{theme}_{w}"
                page.screenshot(path=str(prefix) + "_top.png", full_page=False)
                el = page.locator("#itinerary, .itinerary").first
                if el.count():
                    el.scroll_into_view_if_needed()
                    page.wait_for_timeout(80)
                    page.screenshot(path=str(prefix) + "_itinerary.png", full_page=False)
                xfer = page.locator("article.xfer, .xfer").first
                if xfer.count():
                    xfer.scroll_into_view_if_needed()
                    page.wait_for_timeout(40)
                    try:
                        xfer.screenshot(path=str(prefix) + "_xfer.png")
                    except Exception:
                        pass
        finally:
            page.close()

    def summary(self, out: Path | None):
        fails = [r for r in self.results if r["status"] == "FAIL"]
        passes = [r for r in self.results if r["status"] == "PASS"]
        skips = [r for r in self.results if r["status"] == "SKIP"]
        print("\n======== QA LAYOUT SUMMARY ========")
        by = defaultdict(Counter)
        for r in self.results:
            by[r["check"]][r["status"]] += 1
        for k, c in by.items():
            print(f"  {k}: PASS {c['PASS']}  FAIL {c['FAIL']}  SKIP {c['SKIP']}")
        print(f"\nTOTAL  PASS {len(passes)}  FAIL {len(fails)}  SKIP {len(skips)}  of {len(self.results)}")
        if fails:
            print("\nFAILURES:")
            for r in fails:
                print(f"  - {r['check']} {r.get('page')} {r['width']} {r['theme']} {r['folds']}: {str(r['detail'])[:500]}")
        if out:
            out.write_text(
                json.dumps(
                    {
                        "total": {"PASS": len(passes), "FAIL": len(fails), "SKIP": len(skips), "n": len(self.results)},
                        "per_check": {k: dict(c) for k, c in by.items()},
                        "results": self.results,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            print(f"Wrote {out}")
        return 1 if fails else 0


def parse_args(argv):
    ap = argparse.ArgumentParser(description="Layout QA for an easy-to-trip page.")
    ap.add_argument("urls", nargs="+", help="Page URL(s). ?static=1 is added if missing.")
    ap.add_argument("--shots", type=Path, default=None, help="Directory for screenshots.")
    ap.add_argument("--report", type=Path, default=None, help="Write JSON report here.")
    ap.add_argument("--chrome", default=str(CHROME) if CHROME.exists() else None)
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    urls = [with_static(u) for u in args.urls]
    print("QA", urls)
    run = Runner(args.shots)
    launch = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    if args.chrome:
        launch["executable_path"] = args.chrome
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        for url in urls:
            name = slug(url)
            for w, h in WIDTHS:
                for theme in THEMES:
                    for folds in FOLD_STATES:
                        print(f"\n=== {name} {w} {theme} {folds} ===")
                        shot = folds == "closed"
                        run.run_combo(browser, url, name, w, h, theme, folds, shot=shot)
        browser.close()
    report = args.report
    if report is None and args.shots:
        report = args.shots / "report.json"
    return run.summary(report)


if __name__ == "__main__":
    sys.exit(main())
