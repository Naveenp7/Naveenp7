#!/usr/bin/env python3
"""Generates assets/contrib-stats.svg and assets/contrib-heatmap.svg from GitHub contribution data.

Usage (CI):    GITHUB_TOKEN=... python scripts/contrib.py
Local preview: python scripts/contrib.py --demo   (random data, never commit this)
Stdlib only.
"""
import datetime as dt
import html
import json
import math
import os
import random
import sys
import urllib.request

USER = os.environ.get("GH_USER", "Naveenp7")
OUT = os.environ.get("ASSETS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets"))

W = 900
BG, INK, MUTE = "#F2F2F0", "#111111", "#6B6B66"
BLUE, GREY, LINE = "#2F55FF", "#C8C8C2", "#D9D9D3"
GREEN = "#16A34A"
LEVELS = ["#E2E2DD", "#C7EDD2", "#8ED6A5", "#4CB96F", "#14803E"]
SERIF = "'Instrument Serif','Playfair Display',Georgia,'Times New Roman',serif"
SANS = "Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

STYLE = f"""<style>
.s{{font-family:{SERIF}}} .m{{font-family:{MONO}}} .p{{font-family:{SANS}}} .i{{font-style:italic}}
</style>"""
DEFS = """<defs><filter id="n" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 .25  0 0 0 0 .25  0 0 0 0 .25  0 0 0 .10 0"/></filter></defs>"""


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, cls="p", size=12, fill=INK, anchor="start", ls=None, op=None):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    o = f' opacity="{op}"' if op else ""
    return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}"{a}{l}{o}>{esc(s)}</text>'


def root(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title>{STYLE}{DEFS}'
            f'<clipPath id="c"><rect width="{w}" height="{h}" rx="18"/></clipPath>'
            f'<rect width="{w}" height="{h}" rx="18" fill="{BG}"/>'
            f'<g clip-path="url(#c)"><rect width="{w}" height="{h}" filter="url(#n)"/></g>{body}</svg>')


# ------------------------------------------------------------------ data
def fetch(user, token):
    q = ("query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{"
         "weeks{contributionDays{date contributionCount}}}}}}")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"u": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "contrib-svg"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]


def demo_days():
    random.seed(7)
    end = dt.date.today()
    out = []
    for i in range(365, -1, -1):
        d = end - dt.timedelta(days=i)
        out.append((d, 0 if random.random() < .05 else int(random.expovariate(1 / 22))))
    return out


def empty_days():
    end = dt.date.today()
    return [(end - dt.timedelta(days=i), 0) for i in range(365, -1, -1)]


def stats(days):
    total = sum(c for _, c in days)
    cur = longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    # current streak: allow today to still be empty
    i = len(days) - 1
    if days[i][1] == 0:
        i -= 1
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    active = sum(1 for _, c in days if c > 0)
    busiest = max(c for _, c in days)
    today = days[-1][0]
    months = []
    y, m = today.year, today.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per = {k: 0 for k in months}
    for d, c in days:
        if (d.year, d.month) in per:
            per[(d.year, d.month)] += c
    return dict(total=total, cur=cur, longest=longest, active=active, n=len(days), busiest=busiest, months=months, per=per)


# ------------------------------------------------------------------ svgs
def stats_svg(days):
    s = stats(days)
    H = 282
    b = f'<rect x="28" y="28" width="9" height="9" rx="2" fill="{BLUE}"/>'
    b += text(46, 36, "THE LAST 12 MONTHS ON GITHUB", "m", 11, MUTE, ls=2)
    b += (f'<text x="28" y="86" class="s" font-size="42" fill="{INK}">{s["total"]:,} '
          f'<tspan class="i">contributions</tspan></text>')
    vals = [s["per"][k] for k in s["months"]]
    mx = max(vals) or 1
    x0, x1, base, maxh = 28, 600, 236, 108
    pitch = (x1 - x0) / 12
    bw = pitch - 12
    imax = vals.index(max(vals)) if max(vals) > 0 else -1
    for i, ((yy, mm), v) in enumerate(zip(s["months"], vals)):
        h = max(7, v / mx * maxh)
        x = x0 + i * pitch + 6
        col = BLUE if i == imax else (GREY if i == 11 else INK)
        b += f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="5" fill="{col}"/>'
        if i == imax:
            b += text(f"{x+bw/2:.1f}", f"{base-h-8:.1f}", f"{v:,}", "m", 11, BLUE, anchor="middle")
        b += text(f"{x+bw/2:.1f}", base + 20, dt.date(yy, mm, 1).strftime("%b"), "m", 10.5, MUTE, anchor="middle")
    rows = [
        (f'{s["cur"]} ', "days", "current streak" + (", and the longest" if s["cur"] == s["longest"] and s["cur"] > 0 else f" (longest {s['longest']})")),
        (f'{s["active"]}', f' / {s["n"]}', "days with a commit"),
        (f'{s["busiest"]}', "", "on the busiest day"),
    ]
    rx = 650
    for i, (a, c, cap) in enumerate(rows):
        y = 100 + i * 66
        if c.startswith(" /"):
            b += (f'<text x="{rx}" y="{y}" class="s" font-size="34" fill="{INK}">{esc(a)}'
                  f'<tspan fill="{MUTE}" fill-opacity=".7"> /</tspan><tspan fill="{MUTE}" fill-opacity=".7">{esc(c[2:])}</tspan></text>')
        else:
            b += (f'<text x="{rx}" y="{y}" class="s" font-size="34" fill="{INK}">{esc(a)}'
                  f'<tspan class="i">{esc(c)}</tspan></text>')
        b += text(rx, y + 20, cap, "p", 12, MUTE)
        if i < 2:
            b += f'<line x1="{rx}" y1="{y+36}" x2="872" y2="{y+36}" stroke="{LINE}"/>'
    return root(W, H, b, f'{s["total"]:,} GitHub contributions in the last 12 months, {s["cur"]} day current streak')


def heatmap_svg(days):
    offset = (days[0][0].weekday() + 1) % 7  # Sunday = 0
    cols = math.ceil((offset + len(days)) / 7)
    pad = 28
    pitch = (W - 2 * pad) / cols
    cell = pitch - 3.4
    nz = sorted(c for _, c in days if c > 0)

    def level(c):
        if c == 0 or not nz:
            return 0
        q = lambda p: nz[min(len(nz) - 1, int(len(nz) * p))]
        return 1 if c <= q(.25) else 2 if c <= q(.5) else 3 if c <= q(.75) else 4

    y0 = 78
    H = y0 + 7 * pitch + 36
    b = f'<text x="{pad}" y="46" class="s" font-size="28" fill="{INK}">Contribution <tspan class="i" fill="{GREEN}">activity</tspan></text>'
    b += text(W - pad, 42, "REFRESHED DAILY", "m", 11, MUTE, anchor="end", ls=2)
    last_label = -9
    for i, (d, c) in enumerate(days):
        col, row = (offset + i) // 7, (offset + i) % 7
        x, y = pad + col * pitch, y0 + row * pitch
        b += f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="3.2" fill="{LEVELS[level(c)]}"/>'
    for col in range(cols):
        first = None
        for r in range(7):
            idx = col * 7 + r - offset
            if 0 <= idx < len(days) and days[idx][0].day == 1:
                first = days[idx][0]
        if first is not None and col - last_label >= 4:
            b += text(f"{pad + col*pitch:.1f}", y0 + 7 * pitch + 16, first.strftime("%b"), "m", 10.5, MUTE)
            last_label = col
    lx = W - pad - 5 * pitch - 230
    ly = 31
    b += text(lx, ly + 9, "less", "m", 10.5, MUTE, anchor="end")
    for i, col in enumerate(LEVELS):
        b += f'<rect x="{lx+10+i*pitch:.1f}" y="{ly}" width="{cell:.1f}" height="{cell:.1f}" rx="3.2" fill="{col}"/>'
    b += text(lx + 16 + 5 * pitch, ly + 9, "more", "m", 10.5, MUTE)
    return root(W, round(H), b, "GitHub contribution heatmap for the last year")


def write(days):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "contrib-stats.svg"), "w") as f:
        f.write(stats_svg(days))
    with open(os.path.join(OUT, "contrib-heatmap.svg"), "w") as f:
        f.write(heatmap_svg(days))


if __name__ == "__main__":
    if "--demo" in sys.argv:
        write(demo_days())
    elif "--empty" in sys.argv:
        write(empty_days())
    else:
        token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Set GITHUB_TOKEN (or GH_PAT)")
        write(fetch(USER, token))
    print("contribution svgs written to", os.path.abspath(OUT))
