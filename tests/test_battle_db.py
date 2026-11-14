import os
import tempfile
import unittest

from fp.battle_db import BattlePriors, BattleStore, parse_log
from fp.battle_db.importer import ReplayClient, import_replays
from fp.battle_db.local_logs import import_local_logs

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "vgc_sample_replay.log")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as f:
        return f.read()


class TestParser(unittest.TestCase):
    def setUp(self):
        self.b = parse_log(load_fixture())

    def test_players_and_result(self):
        self.assertEqual(self.b.players, {"p1": "Alpha", "p2": "Bravo"})
        self.assertEqual(self.b.ratings, {"p1": 1510, "p2": 1488})
        self.assertEqual(self.b.winner_side, "p1")
        self.assertEqual(self.b.turns, 4)
        self.assertEqual(self.b.format_id, "[Gen 9] VGC 2026 Reg I")

    def test_team_preview_brought_and_leads(self):
        p1 = self.b.teams["p1"]
        self.assertEqual(len(p1), 6)
        brought = {s for s, m in p1.items() if m.brought}
        self.assertEqual(brought, {"Incineroar", "Flutter Mane", "Urshifu-Rapid-Strike", "Amoonguss"})
        self.assertNotIn("Urshifu", p1)  # wildcard preview forme replaced by the real one
        leads = {s for s, m in p1.items() if m.lead}
        self.assertEqual(leads, {"Incineroar", "Flutter Mane"})
        self.assertEqual(p1["Flutter Mane"].tera_type, "Fairy")
        self.assertTrue(p1["Flutter Mane"].fainted)

    def test_moves_targets_spread_forced(self):
        moves = [a for a in self.b.actions if a.kind == "move"]
        fake_out = next(a for a in moves if a.name == "Fake Out")
        self.assertEqual((fake_out.turn, fake_out.side, fake_out.slot), (1, "p1", "a"))
        self.assertEqual(fake_out.target_species, "Calyrex-Shadow")
        astral = next(a for a in moves if a.name == "Astral Barrage")
        self.assertTrue(astral.spread)
        outrage = next(a for a in moves if a.name == "Outrage")
        self.assertTrue(outrage.forced)
        protect_fail = [a for a in moves if a.name == "Protect" and a.side == "p2"][0]
        self.assertIsNone(protect_fail.target_side)

    def test_switch_kinds(self):
        kinds = [(a.turn, a.side, a.actor, a.kind) for a in self.b.actions if a.kind != "move"]
        self.assertIn((1, "p1", "Urshifu-Rapid-Strike", "replacement"), kinds)
        self.assertIn((3, "p1", "Amoonguss", "switch"), kinds)
        self.assertIn((0, "p2", "Tornadus", "lead"), kinds)
        self.assertIn((1, "p1", "Flutter Mane", "tera"), kinds)

    def test_client_log_prefix_is_stripped(self):
        prefixed = "\n".join(f"[2026-11-14 10:00:00.000] (+1.000s) {l}" for l in load_fixture().splitlines())
        b = parse_log(prefixed)
        self.assertEqual(b.winner_side, "p1")
        self.assertEqual(len(b.actions), len(self.b.actions))


class TestStoreAndPriors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BattleStore(os.path.join(self.tmp.name, "battles.db"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_add_is_deduplicated(self):
        self.assertIsNotNone(self.store.add_battle("x-1", load_fixture(), format_id="gen9vgc2026regi", rating=1500))
        self.assertIsNone(self.store.add_battle("x-1", load_fixture()))
        s = self.store.summary("gen9vgc2026regi")
        self.assertEqual(s["battles"], 1)
        self.assertGreater(s["actions"], 10)

    def test_priors(self):
        for i in range(4):
            self.store.add_battle(f"x-{i}", load_fixture(), format_id="gen9vgc2026regi", rating=1500)
        pri = BattlePriors(self.store, format_id="gen9vgc2026regi", min_rating=1400)
        freqs = pri.move_frequencies("Incineroar")
        self.assertAlmostEqual(sum(freqs.values()), 1.0)
        self.assertEqual(set(freqs), {"Fake Out", "Protect", "Flare Blitz"})
        self.assertAlmostEqual(pri.protect_rate("Incineroar"), 1 / 3)
        # Forced (locked-in) moves are not counted as choices.
        self.assertEqual(pri.move_frequencies("Tornadus").get("Outrage"), None)
        self.assertEqual(pri.tera_types("Flutter Mane"), {"Fairy": 1.0})
        leads = pri.best_leads(["Incineroar", "Flutter Mane", "Amoonguss", "Rillaboom"], min_games=2)
        self.assertEqual(leads[0][0], ("Flutter Mane", "Incineroar"))
        self.assertEqual(leads[0][1], 1.0)
        wr, n = pri.species_win_rate("Calyrex-Shadow")
        self.assertEqual((wr, n), (0.0, 4))
        self.assertIn(("Flutter Mane", 4), pri.common_partners("Incineroar"))
        # Rating filter excludes everything below it.
        self.assertEqual(BattlePriors(self.store, min_rating=1600).move_frequencies("Incineroar"), {})

    def test_reparse(self):
        self.store.add_battle("x-1", load_fixture())
        self.assertEqual(self.store.reparse_all(), 1)
        self.assertEqual(self.store.summary()["battles"], 1)

    def test_local_logs(self):
        logdir = os.path.join(self.tmp.name, "battle_logs")
        os.makedirs(logdir)
        body = "\n".join(f"[2026-11-14 10:00:00.000] (+1.000s) {l}" for l in load_fixture().splitlines())
        name = "BattleBuddy_gen9vgc2026regi-1234_20261114_100000_client_messages.log"
        with open(os.path.join(logdir, name), "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\nheader\n" + body)
        stats = import_local_logs(self.store, logdir)
        self.assertEqual(stats["imported"], 1)
        self.assertTrue(self.store.has_battle("local-gen9vgc2026regi-1234"))
        self.assertEqual(import_local_logs(self.store, logdir)["skipped_existing"], 1)


class _FakeResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data
        self.headers = {}

    def json(self):
        return self._data


class _FakeSession:
    """Serves 2 pages of search results (51 then 10) and replay bodies."""

    def __init__(self):
        self.headers = {}
        self.calls = []
        base = 2_000_000_000
        self.listing = [
            {"id": f"gen9vgc2026regi-{i}", "uploadtime": base - i, "rating": 1200 + i,
             "private": 1 if i == 3 else 0, "password": None}
            for i in range(60)
        ]

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if url.endswith("/search.json"):
            before = (params or {}).get("before")
            items = [e for e in self.listing if before is None or e["uploadtime"] < before]
            return _FakeResp(200, items[:51])
        rid = url.rsplit("/", 1)[1][:-5]
        entry = next(e for e in self.listing if e["id"] == rid)
        return _FakeResp(200, {"id": rid, "formatid": "gen9vgc2026regi", "log": load_fixture(),
                               "uploadtime": entry["uploadtime"], "rating": entry["rating"]})


class TestImporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BattleStore(os.path.join(self.tmp.name, "battles.db"))
        self.session = _FakeSession()
        self.client = ReplayClient(delay=0, session=self.session, sleep=lambda s: None)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_backfill_paginates_and_skips_private(self):
        stats = import_replays(self.store, "gen9vgc2026regi", max_pages=None, client=self.client)
        self.assertEqual(stats["pages"], 2)
        self.assertEqual(stats["listed"], 60)
        self.assertEqual(stats["skipped_private"], 1)
        self.assertEqual(stats["imported"], 59)
        searches = [p for u, p in self.session.calls if u.endswith("search.json")]
        self.assertEqual(searches[1]["before"], 2_000_000_000 - 49)
        self.assertNotIn(("https://replay.pokemonshowdown.com/gen9vgc2026regi-3.json", {}), self.session.calls)
        self.assertEqual(self.session.headers["User-Agent"].split("/")[0], "foul-play-battle-db")

    def test_resume_and_new_mode(self):
        import_replays(self.store, "gen9vgc2026regi", max_pages=1, client=self.client)
        self.assertEqual(self.store.summary()["battles"], 49)
        # Backfill picks up where it stopped instead of re-listing page 1.
        stats = import_replays(self.store, "gen9vgc2026regi", max_pages=None, client=self.client)
        self.assertEqual(stats["imported"], 10)
        # "new" mode stops at the first page once it reaches stored replays.
        stats = import_replays(self.store, "gen9vgc2026regi", mode="new", client=self.client)
        self.assertEqual((stats["imported"], stats["pages"]), (0, 1))

    def test_min_rating(self):
        stats = import_replays(self.store, "gen9vgc2026regi", max_pages=1, min_rating=1240,
                               client=self.client)
        self.assertEqual(stats["imported"], 10)


if __name__ == "__main__":
    unittest.main()
