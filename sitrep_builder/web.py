"""The offline web app."""
from datetime import date, timedelta

from . import core
from .fieldkit import App, Fail, Raw, bar_chart, card, form, h, redirect, stats, table

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY, day TEXT NOT NULL, org TEXT NOT NULL, sector TEXT NOT NULL, area TEXT NOT NULL, activity TEXT NOT NULL, people INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS indicators (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, target REAL NOT NULL, achieved REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def create_app(db="sitrep.db", today=date.today):
    a = App("SitRep Builder", db, SCHEMA, [("Report", "/"), ("Add activity", "/add"), ("Indicators", "/indicators")])

    def rows():
        return [core.Activity(date.fromisoformat(r["day"]), r["org"], r["sector"], r["area"], r["activity"], r["people"]) for r in a.rows("SELECT * FROM activities ORDER BY day")]

    def period():
        s = a.one("SELECT value FROM settings WHERE key = 'start'")
        e = a.one("SELECT value FROM settings WHERE key = 'end'")
        now = today()
        return date.fromisoformat(s) if s else now - timedelta(days=30), date.fromisoformat(e) if e else now + timedelta(days=60)

    @a.route("/")
    def home(req):
        rs = rows()
        now = today()
        start, end = period()
        ind = core.progress([dict(r) for r in a.rows("SELECT * FROM indicators ORDER BY id")], now, start, end)
        sectors = sorted({r.sector for r in rs})
        areas = sorted({r.area for r in rs})
        missing = core.uncovered(rs, sectors, areas)
        m = core.matrix(rs)
        body = stats([("People reached (at least)", f"{core.reached(rs):,}"), ("Organisations", len({r.org for r in rs})), ("Areas", len(areas)), ("Activities", len(rs))])
        body += card("Summary (a draft to edit)", f"<p>{h(core.narrative(rs, ind, now, missing))}</p>")
        grid = [{"s": s, "c": [", ".join(m.get(s, {}).get(x, [])) for x in areas]} for s in sectors]
        body += card("Who does what where", table(grid, [("Sector", "s")] + [(x, (lambda i: lambda r: r["c"][i])(i)) for i, x in enumerate(areas)], "No activities yet."))
        body += card("People reached by sector", bar_chart(sorted(core.reached(rs, "sector").items(), key=lambda t: -t[1])) if rs else "")
        change = core.week_change(rs, now)
        body += card("This week against last", table(list(change.items()), [("Sector", lambda r: r[0]), ("This week", lambda r: r[1][0]), ("Last week", lambda r: r[1][1]), ("Change", lambda r: "new" if r[1][2] is None else f"{r[1][2]:+.0%}")], "No activity in the last two weeks."))
        body += card("Indicators", table(ind, [("Indicator", "name"), ("Achieved", lambda r: f"{r['achieved']:g} of {r['target']:g}"), ("Progress", lambda r: "" if r["share"] is None else f"{r['share']:.0%}"), ("Time used", lambda r: f"{r['expected']:.0%}"), ("State", lambda r: Raw(f'<span class="{"bad" if r["state"] == "behind" else "warn" if r["state"] == "slightly behind" else "good"}">{r["state"]}</span>'))], "No indicators yet."))
        over = core.overlap(rs)
        if over:
            body += card("Possible overlap to discuss", table(over, [("Sector", lambda r: r[0][0]), ("Area", lambda r: r[0][1]), ("Activity", lambda r: r[0][2]), ("Organisations", lambda r: ", ".join(r[1]))]))
        if missing:
            body += card("No activity reported", table(missing, [("Sector", lambda r: r[0]), ("Area", lambda r: r[1])]))
        return a.page(f"Situation report, {now.isoformat()}", body)

    @a.route("/add", ("GET", "POST"))
    def add(req):
        if req.method == "POST":
            d = req.date("day")
            if date.fromisoformat(d) > today():
                raise Fail("The date cannot be in the future")
            a.run("INSERT INTO activities (day, org, sector, area, activity, people) VALUES (?, ?, ?, ?, ?, ?)", d, req.text("org"), req.text("sector"), req.text("area"), req.text("activity"), int(req.number("people", 0, 0, 10_000_000)))
            return redirect("/")
        return a.page("Add activity", card("Activity", form(a, "/add", [("day", "Date", "date", today().isoformat()), ("org", "Organisation"), ("sector", "Sector"), ("area", "Area"), ("activity", "Activity"), ("people", "People reached", "number", 0)], "Add")))

    @a.route("/indicators", ("GET", "POST"))
    def indicators(req):
        if req.method == "POST":
            if req.get("start"):
                a.run("INSERT OR REPLACE INTO settings (key, value) VALUES ('start', ?)", req.date("start"))
                a.run("INSERT OR REPLACE INTO settings (key, value) VALUES ('end', ?)", req.date("end"))
                if req.date("end") <= req.date("start"):
                    raise Fail("The end must be after the start")
            else:
                a.run("INSERT INTO indicators (name, target, achieved) VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET target = excluded.target, achieved = excluded.achieved", req.text("name"), req.number("target", low=0), req.number("achieved", 0, 0))
            return redirect("/indicators")
        start, end = period()
        return a.page("Indicators", card("Response period", form(a, "/indicators", [("start", "Start", "date", start.isoformat()), ("end", "End", "date", end.isoformat())], "Save")) + card("Add or update", form(a, "/indicators", [("name", "Indicator"), ("target", "Target", "number"), ("achieved", "Achieved", "number", 0)], "Save")))

    return a
