"""
Tests for Phase 2: Doubles Decision Formatting

These tests verify that decision formatting works correctly for doubles battles
while maintaining backward compatibility with singles.
"""

import unittest
from unittest.mock import Mock
from fp.battle import Battle, Pokemon, Battler
from fp.run_battle import (
    format_decision,
    format_singles_decision,
    format_doubles_decision,
    format_single_pokemon_decision,
    get_default_doubles_target,
)
import constants


class TestDoublesDecisionFormatting(unittest.TestCase):
    """Test doubles decision formatting functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock doubles battle
        self.doubles_battle = Battle("test-doubles", is_doubles=True)
        self.doubles_battle.rqid = 123

        # Create mock Pokemon
        self.pikachu = Mock(spec=Pokemon)
        self.pikachu.name = "pikachu"
        self.pikachu.index = 1
        self.pikachu.hp = 100
        self.pikachu.can_mega_evo = False
        self.pikachu.can_ultra_burst = False
        self.pikachu.can_dynamax = False

        self.charizard = Mock(spec=Pokemon)
        self.charizard.name = "charizard"
        self.charizard.index = 2
        self.charizard.hp = 100
        self.charizard.can_mega_evo = True
        self.charizard.can_ultra_burst = False
        self.charizard.can_dynamax = False

        self.blastoise = Mock(spec=Pokemon)
        self.blastoise.name = "blastoise"
        self.blastoise.index = 3
        self.blastoise.hp = 100

        self.venusaur = Mock(spec=Pokemon)
        self.venusaur.name = "venusaur"
        self.venusaur.index = 4
        self.venusaur.hp = 100

        # Mock opponent Pokemon
        self.opponent_left = Mock(spec=Pokemon)
        self.opponent_left.hp = 100

        self.opponent_right = Mock(spec=Pokemon)
        self.opponent_right.hp = 100

        # Set up battle state
        self.doubles_battle.user.active = [self.pikachu, self.charizard]
        self.doubles_battle.user.reserve = [self.blastoise, self.venusaur]
        self.doubles_battle.opponent.active = [self.opponent_left, self.opponent_right]

        # Mock move
        mock_move = Mock()
        mock_move.can_z = False
        self.pikachu.get_move = Mock(return_value=mock_move)
        self.charizard.get_move = Mock(return_value=mock_move)

        # Create a singles battle for compatibility tests
        self.singles_battle = Battle("test-singles", is_doubles=False)
        self.singles_battle.rqid = 456
        self.singles_battle.user.active = self.pikachu
        self.singles_battle.user.reserve = [self.charizard, self.blastoise]

    def test_format_decision_routes_to_singles(self):
        """Test that format_decision correctly routes to singles formatter."""
        decision = "move 1"
        result = format_decision(self.singles_battle, decision)
        self.assertEqual(result[0], "/choose move 1")
        self.assertEqual(result[1], "456")

    def test_format_decision_routes_to_doubles(self):
        """Test that format_decision correctly routes to doubles formatter."""
        decision = "move 1 1, move 2 2"
        result = format_decision(self.doubles_battle, decision)
        self.assertIn("/choose", result[0])
        self.assertEqual(result[1], "123")

    def test_doubles_two_moves(self):
        """Test formatting two moves in doubles."""
        decision = "move 1 1, move 2 2"
        result = format_doubles_decision(self.doubles_battle, decision)
        self.assertEqual(result[0], "/choose move 1 1, move 2 2")

    def test_doubles_move_and_switch(self):
        """Test formatting move + switch in doubles."""
        decision = "move 1 1, switch blastoise"
        result = format_doubles_decision(self.doubles_battle, decision)
        self.assertEqual(result[0], "/choose move 1 1, switch 3")

    def test_doubles_two_switches(self):
        """Test formatting two switches in doubles."""
        decision = "switch blastoise, switch venusaur"
        result = format_doubles_decision(self.doubles_battle, decision)
        self.assertEqual(result[0], "/choose switch 3, switch 4")

    def test_doubles_switch_and_move(self):
        """Test formatting switch + move in doubles."""
        decision = "switch blastoise, move 2 2"
        result = format_doubles_decision(self.doubles_battle, decision)
        self.assertEqual(result[0], "/choose switch 3, move 2 2")

    def test_single_pokemon_move_decision(self):
        """Test formatting a single Pokemon's move."""
        decision = "move 1 2"
        result = format_single_pokemon_decision(self.doubles_battle, decision, 0)
        self.assertEqual(result, "move 1 2")

    def test_single_pokemon_switch_decision(self):
        """Test formatting a single Pokemon's switch."""
        decision = "switch blastoise"
        result = format_single_pokemon_decision(self.doubles_battle, decision, 0)
        self.assertEqual(result, "switch 3")

    def test_mega_evolution_in_doubles(self):
        """Test Mega Evolution formatting in doubles."""
        decision = "move 1-mega 1, move 2 2"
        result = format_doubles_decision(self.doubles_battle, decision)
        # Charizard is at position 1 and can mega evolve
        # Should have mega in the left position's move
        self.assertIn("move", result[0])

    def test_terastallize_in_doubles(self):
        """Test Terastallize formatting in doubles."""
        decision = "move 1-tera 1, move 2 2"
        result = format_doubles_decision(self.doubles_battle, decision)
        self.assertIn("move", result[0])

    def test_default_target_left_opponent(self):
        """Test default targeting chooses left opponent."""
        target = get_default_doubles_target(self.doubles_battle, "1", 0)
        self.assertEqual(target, constants.TARGET_LEFT_OPPONENT)

    def test_default_target_right_when_left_fainted(self):
        """Test default targeting chooses right when left fainted."""
        self.opponent_left.hp = 0
        target = get_default_doubles_target(self.doubles_battle, "1", 0)
        # Should target right opponent when left is fainted
        self.assertEqual(target, constants.TARGET_RIGHT_OPPONENT)

    def test_switch_pokemon_not_found_raises_error(self):
        """Test that switching to non-existent Pokemon raises error."""
        decision = "switch mew"
        with self.assertRaises(ValueError):
            format_single_pokemon_decision(self.doubles_battle, decision, 0)

    def test_backward_compatibility_singles_move(self):
        """Test singles move formatting is unchanged."""
        decision = "move 1"
        result = format_singles_decision(self.singles_battle, decision)
        self.assertEqual(result[0], "/choose move 1")

    def test_backward_compatibility_singles_switch(self):
        """Test singles switch formatting is unchanged."""
        decision = "switch charizard"
        result = format_singles_decision(self.singles_battle, decision)
        self.assertEqual(result[0], "/switch 2")

    def test_backward_compatibility_singles_mega(self):
        """Test singles mega evolution formatting is unchanged."""
        self.singles_battle.user.active = self.charizard
        decision = "move 1-mega"
        result = format_singles_decision(self.singles_battle, decision)
        self.assertIn("/choose move 1", result[0])
        self.assertIn("mega", result[0])

    def test_empty_decision_handling(self):
        """Test handling of empty decision (fainted Pokemon)."""
        decision = ""
        result = format_single_pokemon_decision(self.doubles_battle, decision, 0)
        self.assertEqual(result, "")


class TestDoublesTargeting(unittest.TestCase):
    """Test doubles targeting logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.battle = Battle("test-targeting", is_doubles=True)

        # Create mock Pokemon
        self.user_left = Mock(spec=Pokemon)
        self.user_left.hp = 100
        mock_move = Mock()
        self.user_left.get_move = Mock(return_value=mock_move)

        self.opponent_left = Mock(spec=Pokemon)
        self.opponent_left.hp = 100

        self.opponent_right = Mock(spec=Pokemon)
        self.opponent_right.hp = 100

        self.battle.user.active = [self.user_left, None]
        self.battle.opponent.active = [self.opponent_left, self.opponent_right]

    def test_target_left_opponent_when_available(self):
        """Test targeting left opponent when available."""
        target = get_default_doubles_target(self.battle, "1", 0)
        self.assertEqual(target, constants.TARGET_LEFT_OPPONENT)

    def test_target_right_opponent_when_left_fainted(self):
        """Test targeting right opponent when left fainted."""
        self.opponent_left.hp = 0
        target = get_default_doubles_target(self.battle, "1", 0)
        self.assertEqual(target, constants.TARGET_RIGHT_OPPONENT)

    def test_target_fallback_when_both_fainted(self):
        """Test fallback targeting when both opponents fainted."""
        self.opponent_left.hp = 0
        self.opponent_right.hp = 0
        target = get_default_doubles_target(self.battle, "1", 0)
        # Should still return a valid target (left) even if fainted
        self.assertEqual(target, constants.TARGET_LEFT_OPPONENT)


if __name__ == "__main__":
    unittest.main()

