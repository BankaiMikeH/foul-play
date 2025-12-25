"""
Tests for Phase 6: Python-Rust Integration for Doubles Battles

Tests the conversion between Python battle state and Rust poke-engine state,
and the conversion of Rust decisions back to Python/Showdown format.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch, Mock

# Mock the poke_engine module before importing
sys.modules['poke_engine'] = MagicMock()

from fp.battle import Battle, Battler, Pokemon, Move
from fp.search.poke_engine_helpers import (
    parse_rust_decision_for_doubles,
    _parse_single_rust_decision,
)
import constants

# We'll test the functions that don't require poke_engine directly


class TestPokeEngineIntegrationDoubles(unittest.TestCase):
    """Test Python-Rust integration for doubles battles"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.battle = Battle("test-battle", is_doubles=True)
        
        # Create test Pokemon
        self.pikachu = Pokemon("pikachu", 100)
        self.pikachu.hp = 100
        self.pikachu.max_hp = 100
        self.pikachu.moves = [
            Move("thunderbolt"),
            Move("quickattack"),
            Move("irontail"),
            Move("protect"),
        ]
        self.pikachu.ability = "static"
        self.pikachu.item = "leftovers"
        
        self.charizard = Pokemon("charizard", 100)
        self.charizard.hp = 150
        self.charizard.max_hp = 150
        self.charizard.moves = [
            Move("flamethrower"),
            Move("airslash"),
            Move("dragonclaw"),
            Move("roost"),
        ]
        self.charizard.ability = "blaze"
        self.charizard.item = "charcoal"
        
        self.blastoise = Pokemon("blastoise", 100)
        self.blastoise.hp = 140
        self.blastoise.max_hp = 140
        self.blastoise.moves = [
            Move("hydropump"),
            Move("icebeam"),
            Move("earthquake"),
            Move("protect"),
        ]
        
        self.venusaur = Pokemon("venusaur", 100)
        self.venusaur.hp = 130
        self.venusaur.max_hp = 130
        self.venusaur.moves = [
            Move("energyball"),
            Move("sludgebomb"),
            Move("earthquake"),
            Move("synthesis"),
        ]
    
    # NOTE: Tests requiring poke_engine module are commented out
    # They require Rust compilation and are better suited for end-to-end testing
    # when the poke-engine is fully installed
    
    # def test_battler_to_poke_engine_side_doubles_both_active(self):
    #     """Test converting doubles Battler with both Pokemon active"""
    #     # Requires poke_engine module
    #     pass
    
    # def test_battle_to_poke_engine_state_doubles(self):
    #     """Test converting full doubles Battle to poke-engine State"""
    #     # Requires poke_engine module
    #     pass
    
    def test_parse_single_rust_decision_move(self):
        """Test parsing a single Rust move decision"""
        decision = _parse_single_rust_decision("move0")
        self.assertEqual(decision["type"], "move")
        self.assertEqual(decision["index"], 0)
        self.assertNotIn("target", decision)
    
    def test_parse_single_rust_decision_move_with_target(self):
        """Test parsing a single Rust move decision with target"""
        decision = _parse_single_rust_decision("move1target2")
        self.assertEqual(decision["type"], "move")
        self.assertEqual(decision["index"], 1)
        self.assertEqual(decision["target"], 2)
    
    def test_parse_single_rust_decision_switch(self):
        """Test parsing a single Rust switch decision"""
        decision = _parse_single_rust_decision("switch2")
        self.assertEqual(decision["type"], "switch")
        self.assertEqual(decision["index"], 2)
    
    def test_parse_rust_decision_for_doubles_both_moves(self):
        """Test parsing Rust decision with both Pokemon using moves"""
        left_dec, right_dec = parse_rust_decision_for_doubles("move0, move1")
        
        self.assertEqual(left_dec["type"], "move")
        self.assertEqual(left_dec["index"], 0)
        
        self.assertEqual(right_dec["type"], "move")
        self.assertEqual(right_dec["index"], 1)
    
    def test_parse_rust_decision_for_doubles_move_and_switch(self):
        """Test parsing Rust decision with move and switch"""
        left_dec, right_dec = parse_rust_decision_for_doubles("move2target1, switch3")
        
        self.assertEqual(left_dec["type"], "move")
        self.assertEqual(left_dec["index"], 2)
        self.assertEqual(left_dec["target"], 1)
        
        self.assertEqual(right_dec["type"], "switch")
        self.assertEqual(right_dec["index"], 3)
    
    def test_parse_rust_decision_for_doubles_both_switch(self):
        """Test parsing Rust decision with both Pokemon switching"""
        left_dec, right_dec = parse_rust_decision_for_doubles("switch2, switch3")
        
        self.assertEqual(left_dec["type"], "switch")
        self.assertEqual(left_dec["index"], 2)
        
        self.assertEqual(right_dec["type"], "switch")
        self.assertEqual(right_dec["index"], 3)
    
    # NOTE: Tests requiring poke_engine module or format_decision are commented out
    # def test_rust_decision_to_showdown_decision_doubles_moves(self):
    #     """Test converting Rust decision to Showdown format for doubles (both moves)"""
    #     # Requires format_decision which may have circular dependencies
    #     pass
    
    # def test_rust_decision_to_showdown_decision_singles(self):
    #     """Test converting Rust decision to Showdown format for singles"""
    #     # Requires format_decision
    #     pass


class TestRustDecisionParsing(unittest.TestCase):
    """Test Rust decision string parsing"""
    
    def test_parse_move_no_target(self):
        """Test parsing move without explicit target"""
        result = _parse_single_rust_decision("move0")
        self.assertEqual(result, {"type": "move", "index": 0})
    
    def test_parse_move_with_target(self):
        """Test parsing move with explicit target"""
        result = _parse_single_rust_decision("move1target2")
        self.assertEqual(result, {"type": "move", "index": 1, "target": 2})
    
    def test_parse_switch(self):
        """Test parsing switch decision"""
        result = _parse_single_rust_decision("switch3")
        self.assertEqual(result, {"type": "switch", "index": 3})
    
    def test_parse_invalid_decision(self):
        """Test parsing invalid decision string"""
        result = _parse_single_rust_decision("invalid")
        # Should default to move 0
        self.assertEqual(result["type"], "move")
        self.assertEqual(result["index"], 0)
    
    def test_parse_doubles_decision_string(self):
        """Test parsing full doubles decision string"""
        left, right = parse_rust_decision_for_doubles("move0target1,switch2")
        
        self.assertEqual(left["type"], "move")
        self.assertEqual(left["index"], 0)
        self.assertEqual(left["target"], 1)
        
        self.assertEqual(right["type"], "switch")
        self.assertEqual(right["index"], 2)


if __name__ == "__main__":
    unittest.main()

