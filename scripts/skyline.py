"""Render the last year of GitHub contributions as an animated isometric skyline (SVG).

In GitHub Actions:  python scripts/skyline.py <login> exhibit-c-skyline.svg   (uses GITHUB_TOKEN)
Local preview:      python skyline.py <login> out.svg --json days.json      ([["YYYY-MM-DD", n], ...])
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    cal = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [[d["date"], d["contributionCount"]] for w in cal["weeks"] for d in w["contributionDays"]]


def build_weeks(days):
    """Return list of weeks, each a list of 7 (date, count) Sunday..Saturday, covering the last 53 weeks."""
    counts = {d: c for d, c in days}
    end = max(dt.date.fromisoformat(d) for d, _ in days) if days else dt.date.today()
    end = max(end, dt.date.today())
    last_sun = end - dt.timedelta(days=(end.weekday() + 1) % 7)
    start = last_sun - dt.timedelta(weeks=52)
    weeks = []
    for w in range(53):
        col = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            col.append((day, counts.get(day.isoformat(), 0) if day <= end else None))
        weeks.append(col)
    return weeks


def render(login, days):
    weeks = build_weeks(days)
    total = sum(c for col in weeks for _, c in col if c)
    busiest = max(((c, d) for col in weeks for d, c in col if c), default=(0, None))
    active = sum(1 for col in weeks for _, c in col if c)
    mx = max(busiest[0], 1)

    W, H = 1000, 490
    WX, WY = 15.2, 1.6      # one week step
    DX, DY = -8.0, 5.0      # one day step
    ox, oy = 100.0, 300.0
    g = 0.82                # footprint fraction
    HMAX = 190.0

    def pt(x, y):
        return f"{x:.1f},{y:.1f}"

    parts = []
    month_seen = set()
    for w, col in enumerate(weeks):
        for d, (day, c) in enumerate(col):
            if c is None:
                continue
            px, py = ox + w * WX + d * DX, oy + w * WY + d * DY
            a = (px, py)
            b = (px + WX * g, py + WY * g)
            cc = (px + WX * g + DX * g, py + WY * g + DY * g)
            e = (px + DX * g, py + DY * g)
            if not c:
                parts.append(f'<polygon class="f" points="{pt(*a)} {pt(*b)} {pt(*cc)} {pt(*e)}"/>')
                continue
            h = 5 + (HMAX - 5) * (c / mx) ** 0.75
            up = lambda p: (p[0], p[1] - h)
            shade = int(150 + 105 * math.sqrt(c / mx))
            top = f"#{shade:02x}{shade:02x}{shade:02x}"
            delay = 0.4 + w * 0.035 + d * 0.02
            parts.append(
                f'<g class="b" style="animation-delay:{delay:.2f}s">'
                f'<polygon fill="#5c5c5c" points="{pt(*e)} {pt(*cc)} {pt(*up(cc))} {pt(*up(e))}"/>'
                f'<polygon fill="#3a3a3a" points="{pt(*b)} {pt(*cc)} {pt(*up(cc))} {pt(*up(b))}"/>'
                f'<polygon fill="{top}" points="{pt(*up(a))} {pt(*up(b))} {pt(*up(cc))} {pt(*up(e))}"/>'
                f'<title>{c} on {day.isoformat()}</title></g>'
            )
        first = col[0][0]
        key = (first.year, first.month)
        if key not in month_seen and first.day <= 7:
            month_seen.add(key)
            mx_, my_ = ox + w * WX + 7 * DX + 2, oy + w * WY + 7 * DY + 16
            parts.append(f'<text class="m" x="{mx_:.1f}" y="{my_:.1f}">{first.strftime("%b").upper()}</text>')

    bd = busiest[1].strftime("%b %d").upper() if busiest[1] else "-"
    updated = dt.date.today().strftime("%b %d, %Y").upper()
    style = """<style>
text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;letter-spacing:.02em}
.h{fill:#f2f2f2;font-size:13px}.hd{fill:#8a8a8a;font-size:11px}.n{fill:#fff;font-size:11px;font-weight:700}
.m{fill:#6f6f6f;font-size:9.5px}.f{fill:#161616;stroke:#222;stroke-width:.6}
.b{transform-box:fill-box;transform-origin:50% 100%;transform:scaleY(0);animation:rise .9s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes rise{to{transform:scaleY(1)}}
@media (prefers-reduced-motion:reduce){.b{animation:none;transform:none}}
</style>"""
    head = (
        f'<text class="h" x="40" y="34">EXHIBIT C: CONTRIBUTIONS</text>'
        f'<text class="hd" x="{W-40}" y="34" text-anchor="end">@{login.upper()}</text>'
        f'<text class="hd" x="40" y="54">THE LAST YEAR, ONE BUILDING PER DAY, HEIGHT = COMMITS</text>'
        f'<text class="hd" x="{W-40}" y="54" text-anchor="end">UPDATED {updated}</text>'
        f'<text class="hd" x="40" y="{H-24}">TOTAL</text><text class="n" x="88" y="{H-24}">{total}</text>'
        f'<text class="hd" x="150" y="{H-24}">ACTIVE DAYS</text><text class="n" x="240" y="{H-24}">{active}</text>'
        f'<text class="hd" x="290" y="{H-24}">BUSIEST</text><text class="n" x="352" y="{H-24}">{busiest[0]} ON {bd}</text>'
        f'<text class="hd" x="{W-40}" y="{H-24}" text-anchor="end">READ LEFT TO RIGHT, OLDEST FIRST</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="{total} contributions in the last year, busiest day {busiest[0]} on {bd}">'
        f'{style}<rect width="{W}" height="{H}" fill="#0b0b0b"/>{head}' + "".join(parts) + "</svg>"
    )


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    if "--json" in sys.argv:
        days = json.load(open(sys.argv[sys.argv.index("--json") + 1]))
    else:
        days = fetch(login)
    with open(out, "w") as f:
        f.write(render(login, days))
    print("wrote", out)
