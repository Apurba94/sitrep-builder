import unittest
from datetime import date, timedelta

from sitrep_builder import core, create_app
from sitrep_builder.core import Activity, matrix, narrative, overlap, progress, reached, uncovered, week_change, week_start

D = date(2026, 11, 4)    # a Wednesday


def act(org, sector, area, activity, people, day=D):
    return Activity(day, org, sector, area, activity, people)


class TestReached(unittest.TestCase):
    def test_partners_doing_the_same_thing_are_not_added(self):
        rows = [act("A", "WASH", "North", "Hygiene kits", 500), act("B", "WASH", "North", "Hygiene kits", 300)]
        self.assertEqual(reached(rows), 500)

    def test_different_areas_add_up(self):
        self.assertEqual(reached([act("A", "WASH", "North", "Kits", 500), act("A", "WASH", "South", "Kits", 300)]), 800)

    def test_one_organisation_across_visits_adds_up(self):
        self.assertEqual(reached([act("A", "WASH", "N", "Kits", 100), act("A", "WASH", "N", "Kits", 50)]), 150)

    def test_by_sector(self):
        rows = [act("A", "WASH", "N", "Kits", 5), act("A", "Food", "N", "Rice", 7)]
        self.assertEqual(reached(rows, "sector"), {"WASH": 5, "Food": 7})

    def test_never_exceeds_the_plain_sum(self):
        import random
        rng = random.Random(1)
        for _ in range(100):
            rows = [act(rng.choice("ABC"), rng.choice("XY"), rng.choice("NS"), rng.choice("PQ"), rng.randint(0, 99)) for _ in range(20)]
            self.assertLessEqual(reached(rows), sum(r.people for r in rows))
            self.assertGreaterEqual(reached(rows), max(r.people for r in rows))


class TestMatrix(unittest.TestCase):
    R = [act("A", "WASH", "N", "Kits", 1), act("B", "WASH", "N", "Kits", 1), act("A", "Food", "S", "Rice", 1)]

    def test_matrix(self):
        self.assertEqual(matrix(self.R), {"WASH": {"N": ["A", "B"]}, "Food": {"S": ["A"]}})

    def test_overlap(self):
        self.assertEqual(overlap(self.R), [(("WASH", "N", "Kits"), ["A", "B"])])

    def test_uncovered(self):
        self.assertEqual(uncovered(self.R, ["WASH", "Food"], ["N", "S"]), [("WASH", "S"), ("Food", "N")])


class TestTime(unittest.TestCase):
    def test_week_start(self):
        self.assertEqual(week_start(D), date(2026, 11, 2))

    def test_week_change(self):
        rows = [act("A", "WASH", "N", "K", 150), act("A", "WASH", "N", "K", 100, D - timedelta(days=7)), act("A", "Food", "N", "R", 5)]
        c = week_change(rows, D)
        self.assertEqual(c["WASH"], (150, 100, 0.5))
        self.assertEqual(c["Food"], (5, 0, None))

    def test_progress_compares_with_time(self):
        s, e = date(2026, 1, 1), date(2026, 12, 31)
        mid = date(2026, 7, 1)
        rows = progress([dict(name="a", target=100, achieved=60), dict(name="b", target=100, achieved=45), dict(name="c", target=100, achieved=20), dict(name="d", target=0, achieved=5)], mid, s, e)
        self.assertEqual([r["state"] for r in rows], ["on track", "slightly behind", "behind", "no target"])


class TestNarrative(unittest.TestCase):
    def test_says_at_least(self):
        text = narrative([act("A", "WASH", "N", "K", 1200)], [], D, [])
        self.assertIn("at least 1,200", text)
        self.assertIn("lower bound", text)

    def test_mentions_trouble(self):
        text = narrative([act("A", "WASH", "N", "K", 1)], [{"name": "Latrines built", "state": "behind"}], D, [("Food", "N")])
        self.assertIn("Latrines built", text)
        self.assertIn("1 sector and area", text)

    def test_nothing(self):
        self.assertIn("No activities", narrative([], [], D, []))


class TestApp(unittest.TestCase):
    def setUp(self):
        self.a = create_app(":memory:", lambda: D)

    def add(self, **kw):
        base = dict(day=D.isoformat(), org="Org A", sector="WASH", area="North", activity="Kits", people=100)
        return self.a.post("/add", **{**base, **kw})

    def text(self):
        return self.a.get("/").body.decode()

    def test_report(self):
        self.add()
        self.add(org="Org B", people=70)
        self.add(sector="Food", area="South", activity="Rice", people=30)
        page = self.text()
        self.assertIn("reaching at least 130 people", page)
        self.assertIn("Possible overlap", page)
        self.assertIn("No activity reported", page)

    def test_indicators(self):
        self.add()
        self.a.post("/indicators", start="2026-01-01", end="2026-12-31")
        self.a.post("/indicators", name="Kits", target=1000, achieved=100)
        self.assertIn("behind", self.text())
        self.a.post("/indicators", name="Kits", target=1000, achieved=900)
        self.assertIn("on track", self.text())

    def test_refusals(self):
        self.assertEqual(self.add(day="2030-01-01").status, 400)
        self.assertEqual(self.add(people=-1).status, 400)
        self.assertEqual(self.a.post("/indicators", start="2026-12-31", end="2026-01-01").status, 400)
        self.assertIsNone(self.a.one("SELECT value FROM settings WHERE key = 'start'"))

    def test_empty_report(self):
        self.assertIn("No activities", self.text())


if __name__ == "__main__":
    unittest.main()
