#!/usr/bin/env python3
"""Static QA for topic-to-html pages.
usage: qa_check.py page.html
Checks: no white / near-white colors, no 'story' wording, WCAG contrast of
text tokens over glass surfaces composited on the bg + every mesh color (both
themes), Phosphor 2.1.1 icon names, no global :empty{display:none}, and
file size (Drive HTML upload cap of 1,000,000 characters, plus 3 MB)."""
import re, sys
from pathlib import Path
src = open(sys.argv[1], encoding='utf-8').read()
path = Path(sys.argv[1])
fail = 0
warns = 0
def bad(msg):
    global fail; fail += 1; print('FAIL', msg)
def warn(msg):
    global warns; warns += 1; print('WARN', msg)

# 1. no white
css = re.sub(r'white-space', '', src)
for m in re.finditer(r'#(?:fff\b|ffffff\b)|\bwhite\b|rgba?\(\s*255\s*,\s*255\s*,\s*255', css, re.I):
    bad(f'white color: {m.group(0)!r} at {m.start()}')
for m in re.finditer(r'#([0-9a-f]{6})\b', css, re.I):
    r, g, b = (int(m.group(1)[i:i+2], 16) for i in (0, 2, 4))
    if min(r, g, b) >= 0xF2: bad(f'near-white #{m.group(1)}')
# 2. no story wording
for w in ['סיפור', r'(?<![a-z])[Ss]tory']:
    for m in re.finditer(w, src): bad(f'"{w}" wording at {m.start()}')

# 3. contrast
def tok(theme):
    blk = re.search(r'\[data-theme="%s"\]\{(.*?)\n\}' % theme, src, re.S).group(1)
    return dict(re.findall(r'--([\w-]+):\s*([^;]+);', blk))
def rgba(v):
    v = v.strip()
    if v.startswith('#'):
        h = v[1:]; return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (1.0,)
    n = re.findall(r'[\d.]+', v); return tuple(float(x) for x in n[:3]) + (float(n[3]) if len(n) > 3 else 1.0,)
def over(top, bottom):
    a = top[3]; return tuple(top[i]*a + bottom[i]*(1-a) for i in range(3)) + (1.0,)
def lum(c):
    def ch(x):
        x /= 255; return x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4
    return .2126*ch(c[0]) + .7152*ch(c[1]) + .0722*ch(c[2])
def ratio(a, b):
    l1, l2 = sorted([lum(a), lum(b)], reverse=True); return (l1+.05)/(l2+.05)
TEXT = {'text': 4.5, 'text-2': 4.5, 'muted': 4.5, 'accent-ink': 4.5, 'pos': 4.5, 'neg': 4.5, 'warn': 4.5, 'accent': 3.0}
for theme in ('light', 'dark'):
    t = tok(theme); bg = rgba(t['bg'])
    # mesh blobs are blurred at ~85% opacity over bg -> composite
    backs = [bg] + [over(rgba(t[f'mesh-{i}'])[:3] + (.85,), bg) for i in range(1, 5)]
    worst = {}
    for surf in ('g-thin', 'g-reg', 'g-thick'):
        for back in backs:
            s = over(rgba(t[surf]), back)
            for k, need in TEXT.items():
                if k not in t: continue
                r = ratio(rgba(t[k]), s)
                key = (k, surf)
                worst[key] = min(worst.get(key, 99), r)
    for (k, surf), r in sorted(worst.items()):
        need = TEXT[k]
        # rule: body text may sit on thin glass only for chips/labels (>=3:1 allowed for 'muted' on thin)
        status = 'ok' if r >= need else 'FAIL'
        if status == 'FAIL': bad(f'{theme}: --{k} on .{surf} = {r:.2f} (< {need})')
        else: print(f'ok   {theme}: --{k} on .{surf} = {r:.2f}')

# 4. file size: Drive HTML upload cap (characters) and 3 MB byte cap
CHARS_CAP = 1_000_000
BYTES_CAP = 3 * 1024 * 1024
nchars = len(src)
nbytes = path.stat().st_size
if nchars > CHARS_CAP:
    bad(f'{nchars:,} characters (Drive HTML upload cap is {CHARS_CAP:,})')
else:
    print(f'ok   size: {nchars:,} characters (Drive cap {CHARS_CAP:,})')
if nbytes > BYTES_CAP:
    bad(f'{nbytes:,} bytes (limit 3 MB / {BYTES_CAP:,})')
else:
    print(f'ok   size: {nbytes:,} bytes (limit 3 MB)')

# 5. Phosphor 2.1.1 icon names
HINTS = {
    'ph-palm-tree': 'ph-tree-palm',
    'ph-hot-springs': 'no icon of that name in 2.1.1 (a common stand-in is ph-bathtub)',
    'ph-passport': 'ph-identification-card',
    'ph-skyscraper': 'ph-city',
}
SKIP = {'ph-duotone'}
names_file = Path(__file__).resolve().parent.parent / 'assets' / 'phosphor-2.1.1-names.txt'
if not names_file.is_file():
    bad(f'missing Phosphor name list: {names_file}')
    valid = set()
else:
    valid = {'ph-' + line.strip() for line in names_file.read_text(encoding='utf-8').splitlines()
             if line.strip() and not line.lstrip().startswith('#')}
    found = {m.lower() for m in re.findall(r'(?<![\w-])(ph-[a-z0-9-]+)', src)}
    icons = sorted(found - SKIP)
    unknown = [i for i in icons if i not in valid]
    if unknown:
        for name in unknown:
            hint = HINTS.get(name)
            extra = f' (did you mean {hint}?)' if hint and hint.startswith('ph-') else (f' ({hint})' if hint else '')
            bad(f'unknown Phosphor 2.1.1 icon: {name}{extra}')
    else:
        print(f'ok   icons: {len(icons)} Phosphor 2.1.1 name(s)')

# 6. no global :empty{display:none} (hides empty <i> icons that paint via ::before/::after)
def is_global_empty(selector):
    for part in selector.split(','):
        p = re.sub(r'/\*.*?\*/', '', part).strip()
        if re.fullmatch(r'\*?:empty', p):
            return True
    return False
for m in re.finditer(r'([^{}]+)\{([^}]+)\}', src):
    sel, body = m.group(1), m.group(2)
    if not re.search(r':empty', sel): continue
    if not re.search(r'display\s*:\s*none', body, re.I): continue
    # only the last line / last chunk is the actual selector list (ignore trailing CSS before it)
    sel = sel.strip()
    if '{' in sel: sel = sel.split('{')[-1]
    # drop a leading @media ... leftover by taking from the last ; or } already excluded
    sel = re.split(r'[\n;]', sel)[-1].strip()
    if is_global_empty(sel):
        warn('global :empty{display:none} hides Phosphor <i> icons and other empty elements that paint via ::before/::after; hide with [hidden] only'
             f' (at {m.start()})')

print('\nRESULT:', 'PASS' if not fail else f'{fail} problem(s)', end='')
if warns:
    print(f' ({warns} warning{"s" if warns != 1 else ""})')
else:
    print()
sys.exit(1 if fail else 0)
