import unittest

from fp.doubles_v2 import scoring
from fp.doubles_v2.scoring import AttackInput, score_attack

try:
    from poke_env.battle import DoubleBattle, Move, Pokemon
    from poke_env.player.battle_order import DoubleBattleOrder
    from fp.doubles_v2.player import VGCHeuristicPlayer

    HAVE_POKE_ENV = True
except ImportError:  # poke-env not installed
    HAVE_POKE_ENV = False


class TestScoring(unittest.TestCase):
    def test_super_effective_beats_neutral(self):
        self.assertGreater(
            score_attack(AttackInput(90, effectiveness=2.0)),
            score_attack(AttackInput(90, effectiveness=1.0)),
        )

    def test_spread_hitting_both_beats_single_neutral(self):
        single = score_attack(AttackInput(95, effectiveness=1.0))
        spread = score_attack(
            AttackInput(
                95, effectiveness=1.0, spread=True, second_target_effectiveness=1.0
            )
        )
        self.assertGreater(spread, single)

    def test_earthquake_into_weak_ally_is_bad(self):
        safe = score_attack(
            AttackInput(100, spread=True, second_target_effectiveness=1.0)
        )
        hurts_ally = score_attack(
            AttackInput(
                100,
                spread=True,
                second_target_effectiveness=1.0,
                hits_ally=True,
                ally_effectiveness=2.0,
            )
        )
        self.assertLess(hurts_ally, 0)
        self.assertGreater(safe, hurts_ally)

    def test_ko_bonus(self):
        low = score_attack(AttackInput(80, target_hp=0.3))
        full = score_attack(AttackInput(80, target_hp=1.0))
        self.assertGreater(low - full, 50)

    def test_protect_never_twice(self):
        self.assertLess(scoring.score_protect(0.3, 200, protected_last_turn=True), 0)
        self.assertGreater(
            scoring.score_protect(0.3, 200, False),
            scoring.score_protect(1.0, 50, False),
        )

    def test_priors_shift_choice(self):
        plain = score_attack(AttackInput(80))
        favored = score_attack(AttackInput(80, prior=0.6))
        self.assertGreater(favored, plain)

    def test_protecting_target_taxes_single_target_more(self):
        single_drop = score_attack(AttackInput(90)) - score_attack(
            AttackInput(90, target_protect_rate=0.5)
        )
        spread_drop = score_attack(
            AttackInput(90, spread=True, second_target_effectiveness=1)
        ) - score_attack(
            AttackInput(
                90, spread=True, second_target_effectiveness=1, target_protect_rate=0.5
            )
        )
        self.assertGreater(
            single_drop / score_attack(AttackInput(90)),
            spread_drop
            / score_attack(AttackInput(90, spread=True, second_target_effectiveness=1)),
        )

    def test_joint_double_protect_penalty(self):
        self.assertLess(
            scoring.joint_adjustment(None, None, True, True, False, False), 0
        )
        self.assertLess(scoring.joint_adjustment(-1, -1, False, False, True, True), 0)


class _FakePriors:
    def move_frequencies(self, species, top=10):
        return {"Fake Out": 0.5} if species == "Incineroar" else {}

    def protect_rate(self, species):
        return 0.0

    def best_leads(self, team, min_games=3, top=5):
        return [(("Amoonguss", "Incineroar"), 0.7, 40)]

    def species_win_rate(self, species):
        return ({"Rillaboom": 0.6}.get(species, 0.5), 10)


def _mon(species, hp=1.0):
    mon = Pokemon(gen=9, species=species)
    mon._max_hp = 100
    mon._current_hp = int(100 * hp)
    return mon


@unittest.skipUnless(HAVE_POKE_ENV, "poke-env not installed")
class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = VGCHeuristicPlayer(
            battle_format="gen9vgc2026regi", start_listening=False, priors=_FakePriors()
        )

    def _battle(self, mine, foes, moves):
        battle = DoubleBattle(
            "battle-gen9vgc2026regi-1", "me", self.player.logger, gen=9
        )
        a, b = [_mon(s) for s in mine]
        fa, fb = [_mon(s) for s in foes]
        battle._active = (a, b)

        class _B:
            pass

        fake = _B()
        fake.battle_tag = battle.battle_tag
        fake.active_pokemon = [a, b]
        fake.opponent_active_pokemon = [fa, fb]
        fake.available_moves = [
            [Move(m, 9) for m in moves[0]],
            [Move(m, 9) for m in moves[1]],
        ]
        fake.available_switches = [[], []]
        fake.force_switch = [False, False]
        fake.can_tera = [False, False]
        for k in (
            "POKEMON_1_POSITION",
            "POKEMON_2_POSITION",
            "OPPONENT_1_POSITION",
            "OPPONENT_2_POSITION",
            "EMPTY_TARGET_POSITION",
        ):
            setattr(fake, k, getattr(DoubleBattle, k))

        def targets(move, mon):
            if move.target and move.target.name in ("NORMAL", "ANY", "ADJACENT_FOE"):
                return [1, 2]
            return [0]

        fake.get_possible_showdown_targets = targets
        return fake

    def test_picks_super_effective_target_and_avoids_double_protect(self):
        battle = self._battle(
            ["incineroar", "rillaboom"],
            ["amoonguss", "urshifurapidstrike"],
            [["flareblitz", "protect"], ["woodhammer", "protect"]],
        )
        order = self.player.choose_move(battle)
        self.assertIsInstance(order, DoubleBattleOrder)
        self.assertEqual(order.first_order.order.id, "flareblitz")
        self.assertEqual(order.first_order.move_target, 1)  # Amoonguss is weak to Fire
        self.assertEqual(order.second_order.order.id, "woodhammer")
        self.assertEqual(
            order.second_order.move_target, 2
        )  # Urshifu-Rapid-Strike is weak to Grass

    def test_ground_spread_avoided_when_ally_is_weak(self):
        battle = self._battle(
            ["landorustherian", "incineroar"],
            ["fluttermane", "rillaboom"],
            [["earthquake", "stoneedge"], ["knockoff", "protect"]],
        )
        order = self.player.choose_move(battle)
        self.assertNotEqual(order.first_order.order.id, "earthquake")

    def test_teampreview_uses_lead_prior(self):
        class _TP:
            team = {
                k: _mon(s)
                for k, s in [
                    ("p1: Incineroar", "incineroar"),
                    ("p1: Rillaboom", "rillaboom"),
                    ("p1: Amoonguss", "amoonguss"),
                    ("p1: Flutter", "fluttermane"),
                    ("p1: Urshifu", "urshifurapidstrike"),
                    ("p1: Lando", "landorustherian"),
                ]
            }

        msg = self.player.teampreview(_TP())
        self.assertTrue(msg.startswith("/team 31"))
        self.assertEqual(msg[8], "2")  # Rillaboom has the best win rate of the rest
        self.assertEqual(len(msg) - len("/team "), 4)


if __name__ == "__main__":
    unittest.main()
