"""Turn activity records into a situation report: a 4W matrix, indicators and a draft narrative.

4W means who does what, where and when. Beneficiary numbers from partners overlap, so the most
common mistake in a report is adding them up. Here the sum of partner numbers is never called
"people reached": for each activity and place, the largest figure is used as a lower bound.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class Activity:
    day: date
    org: str
    sector: str
    area: str
    activity: str
    people: int = 0


def week_start(d):
    return d - timedelta(days=d.weekday())


def matrix(rows):
    """{sector: {area: sorted list of organisations}}"""
    out = defaultdict(lambda: defaultdict(set))
    for r in rows:
        out[r.sector][r.area].add(r.org)
    return {s: {a: sorted(v) for a, v in areas.items()} for s, areas in out.items()}


def reached(rows, by=None):
    """Lower bound of people reached: the largest figure for each activity and area, added across them.
    Records from the same organisation in a period are summed first, as they may be new people."""
    best = defaultdict(int)
    orgs = defaultdict(int)
    for r in rows:
        orgs[(r.sector, r.area, r.activity, r.org)] += r.people
    for (sector, area, activity, _), n in orgs.items():
        key = (sector, area, activity)
        best[key] = max(best[key], n)
    if by is None:
        return sum(best.values())
    idx = {"sector": 0, "area": 1, "activity": 2}[by]
    out = defaultdict(int)
    for k, v in best.items():
        out[k[idx]] += v
    return dict(out)


def overlap(rows, sectors=None):
    """Areas where several organisations do the same activity: worth a coordination talk."""
    seen = defaultdict(set)
    for r in rows:
        seen[(r.sector, r.area, r.activity)].add(r.org)
    return sorted((k, sorted(v)) for k, v in seen.items() if len(v) > 1)


def uncovered(rows, sectors, areas):
    """Sector and area pairs with no reported activity."""
    have = {(r.sector, r.area) for r in rows}
    return [(s, a) for s in sectors for a in areas if (s, a) not in have]


def week_change(rows, today):
    """People reached this week against last, per sector."""
    this, last = week_start(today), week_start(today) - timedelta(days=7)
    a = reached([r for r in rows if week_start(r.day) == this], "sector")
    b = reached([r for r in rows if week_start(r.day) == last], "sector")
    out = {}
    for s in sorted(set(a) | set(b)):
        x, y = a.get(s, 0), b.get(s, 0)
        out[s] = (x, y, None if y == 0 else (x - y) / y)
    return out


def progress(indicators, today, start, end):
    """indicators: list of dicts with name, target, achieved. Compares progress with time elapsed."""
    span = max((end - start).days, 1)
    elapsed = min(max((today - start).days, 0), span) / span
    rows = []
    for i in indicators:
        target = i["target"]
        share = i["achieved"] / target if target else None
        if share is None:
            state = "no target"
        elif share >= elapsed:
            state = "on track"
        elif share >= elapsed - 0.1:
            state = "slightly behind"
        else:
            state = "behind"
        rows.append({**i, "share": share, "expected": elapsed, "state": state})
    return rows


def narrative(rows, indicators, today, gaps_found):
    """A plain first draft. A person must add context, which numbers cannot supply."""
    if not rows:
        return "No activities were reported for this period."
    orgs = sorted({r.org for r in rows})
    sectors = reached(rows, "sector")
    top = sorted(sectors.items(), key=lambda t: -t[1])
    lines = [f"In the period to {today.isoformat()}, {len(orgs)} organisations reported activities in {len({r.area for r in rows})} areas, reaching at least {reached(rows):,} people."]
    lines.append("By sector: " + "; ".join(f"{s} at least {n:,}" for s, n in top) + ".")
    behind = [i["name"] for i in indicators if i["state"] == "behind"]
    if behind:
        lines.append("Indicators behind schedule: " + ", ".join(behind) + ".")
    if gaps_found:
        lines.append(f"{len(gaps_found)} sector and area combinations reported no activity.")
    lines.append("Figures are a lower bound, because people may be reached by more than one activity.")
    return " ".join(lines)
