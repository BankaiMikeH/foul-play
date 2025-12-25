"""
Tests for Phase 1: Python Foundation - Doubles Battle Support

Tests the core Battle and Battler classes with doubles mode enabled,
including helper methods for position management and format detection.
"""

import unittest
from fp.battle import Battle, Battler, Pokemon
from fp.helpers import is_doubles_format, parse_position_from_protocol_identifier, format_position_identifier
import constants


class TestDoublesFormatDetection(unittest.TestCase):
    """Test doubles format detection"""
    
    def test_vgc2024_is_doubles(self):
        """VGC 2024 formats should be detected as doubles"""
        self.assertTrue(is_doubles_format("gen9vgc2024"))
        self.assertTrue(is_doubles_format("gen9vgc2024regg"))
        self.assertTrue(is_doubles_format("gen9vgc2024regf"))
    
    def test_doubles_ou_is_doubles(self):
        """Doubles OU formats should be detected as doubles"""
        self.assertTrue(is_doubles_format("gen9doublesou"))
        self.assertTrue(is_doubles_format("gen8doublesou"))
        self.assertTrue(is_doubles_format("gen7doublesou"))
    
    def test_singles_ou_not_doubles(self):
        """Singles formats should not be detected as doubles"""
        self.assertFalse(is_doubles_format("gen9ou"))
        self.assertFalse(is_doubles_format("gen8ou"))
        self.assertFalse(is_doubles_format("gen9randombattle"))
    
    def test_empty_format_not_doubles(self):
        """Empty or None format should not be detected as doubles"""
        self.assertFalse(is_doubles_format(""))
        self.assertFalse(is_doubles_format(None))


class TestPositionParsing(unittest.TestCase):
    """Test parsing position identifiers from Pokemon Showdown protocol"""
    
    def test_parse_p1a(self):
        """Parse p1a (player 1, left position)"""
        player, position = parse_position_from_protocol_identifier("p1a: Pikachu")
        self.assertEqual(player, "p1")
        self.assertEqual(position, 0)
    
    def test_parse_p1b(self):
        """Parse p1b (player 1, right position)"""
        player, position = parse_position_from_protocol_identifier("p1b: Charizard")
        self.assertEqual(player, "p1")
        self.assertEqual(position, 1)
    
    def test_parse_p2a(self):
        """Parse p2a (player 2, left position)"""
        player, position = parse_position_from_protocol_identifier("p2a: Mewtwo")
        self.assertEqual(player, "p2")
        self.assertEqual(position, 0)
    
    def test_parse_p2b(self):
        """Parse p2b (player 2, right position)"""
        player, position = parse_position_from_protocol_identifier("p2b: Rayquaza")
        self.assertEqual(player, "p2")
        self.assertEqual(position, 1)
    
    def test_parse_singles_p1(self):
        """Parse singles format (just p1)"""
        player, position = parse_position_from_protocol_identifier("p1: Pikachu")
        self.assertEqual(player, "p1")
        self.assertEqual(position, 0)
    
    def test_format_position_identifier_p1a(self):
        """Format position identifier for p1a"""
        identifier = format_position_identifier("p1", 0)
        self.assertEqual(identifier, "p1a")
    
    def test_format_position_identifier_p2b(self):
        """Format position identifier for p2b"""
        identifier = format_position_identifier("p2", 1)
        self.assertEqual(identifier, "p2b")


class TestBattleDoublesInitialization(unittest.TestCase):
    """Test Battle class initialization with doubles support"""
    
    def test_battle_singles_initialization(self):
        """Battle should initialize in singles mode by default"""
        battle = Battle("test-battle")
        self.assertFalse(battle.is_doubles)
        self.assertFalse(battle.user.is_doubles)
        self.assertFalse(battle.opponent.is_doubles)
        self.assertIsNone(battle.user.active)
        self.assertIsNone(battle.opponent.active)
    
    def test_battle_doubles_initialization(self):
        """Battle should initialize in doubles mode when specified"""
        battle = Battle("test-battle", is_doubles=True)
        self.assertTrue(battle.is_doubles)
        self.assertTrue(battle.user.is_doubles)
        self.assertTrue(battle.opponent.is_doubles)
        self.assertEqual(battle.user.active, [None, None])
        self.assertEqual(battle.opponent.active, [None, None])


class TestBattlerDoublesMode(unittest.TestCase):
    """Test Battler class in doubles mode"""
    
    def setUp(self):
        """Set up test battlers"""
        self.singles_battler = Battler(is_doubles=False)
        self.doubles_battler = Battler(is_doubles=True)
        
        # Create test Pokemon
        self.pikachu = Pokemon("pikachu", 100)
        self.charizard = Pokemon("charizard", 100)
        self.blastoise = Pokemon("blastoise", 100)
    
    def test_singles_battler_active_is_none(self):
        """Singles battler should have active as None initially"""
        self.assertIsNone(self.singles_battler.active)
    
    def test_doubles_battler_active_is_list(self):
        """Doubles battler should have active as list of None initially"""
        self.assertEqual(self.doubles_battler.active, [None, None])
    
    def test_get_active_pokemon_singles_position_0(self):
        """Get active Pokemon in singles at position 0"""
        self.singles_battler.active = self.pikachu
        pkmn = self.singles_battler.get_active_pokemon(0)
        self.assertEqual(pkmn, self.pikachu)
    
    def test_get_active_pokemon_singles_position_1_returns_none(self):
        """Get active Pokemon in singles at position 1 should return None"""
        self.singles_battler.active = self.pikachu
        pkmn = self.singles_battler.get_active_pokemon(1)
        self.assertIsNone(pkmn)
    
    def test_get_active_pokemon_doubles_left(self):
        """Get left active Pokemon in doubles"""
        self.doubles_battler.active[0] = self.pikachu
        self.doubles_battler.active[1] = self.charizard
        pkmn = self.doubles_battler.get_active_pokemon(0)
        self.assertEqual(pkmn, self.pikachu)
    
    def test_get_active_pokemon_doubles_right(self):
        """Get right active Pokemon in doubles"""
        self.doubles_battler.active[0] = self.pikachu
        self.doubles_battler.active[1] = self.charizard
        pkmn = self.doubles_battler.get_active_pokemon(1)
        self.assertEqual(pkmn, self.charizard)
    
    def test_set_active_pokemon_singles(self):
        """Set active Pokemon in singles"""
        self.singles_battler.set_active_pokemon(self.pikachu, 0)
        self.assertEqual(self.singles_battler.active, self.pikachu)
    
    def test_set_active_pokemon_doubles_left(self):
        """Set left active Pokemon in doubles"""
        self.doubles_battler.set_active_pokemon(self.pikachu, 0)
        self.assertEqual(self.doubles_battler.active[0], self.pikachu)
        self.assertIsNone(self.doubles_battler.active[1])
    
    def test_set_active_pokemon_doubles_right(self):
        """Set right active Pokemon in doubles"""
        self.doubles_battler.set_active_pokemon(self.charizard, 1)
        self.assertIsNone(self.doubles_battler.active[0])
        self.assertEqual(self.doubles_battler.active[1], self.charizard)
    
    def test_get_all_active_pokemon_singles_with_pokemon(self):
        """Get all active Pokemon in singles mode"""
        self.singles_battler.active = self.pikachu
        all_active = self.singles_battler.get_all_active_pokemon()
        self.assertEqual(len(all_active), 1)
        self.assertEqual(all_active[0], self.pikachu)
    
    def test_get_all_active_pokemon_singles_none(self):
        """Get all active Pokemon in singles mode when None"""
        all_active = self.singles_battler.get_all_active_pokemon()
        self.assertEqual(len(all_active), 0)
    
    def test_get_all_active_pokemon_doubles_both(self):
        """Get all active Pokemon in doubles mode with both positions filled"""
        self.doubles_battler.active[0] = self.pikachu
        self.doubles_battler.active[1] = self.charizard
        all_active = self.doubles_battler.get_all_active_pokemon()
        self.assertEqual(len(all_active), 2)
        self.assertIn(self.pikachu, all_active)
        self.assertIn(self.charizard, all_active)
    
    def test_get_all_active_pokemon_doubles_one(self):
        """Get all active Pokemon in doubles mode with one position filled"""
        self.doubles_battler.active[0] = self.pikachu
        all_active = self.doubles_battler.get_all_active_pokemon()
        self.assertEqual(len(all_active), 1)
        self.assertEqual(all_active[0], self.pikachu)
    
    def test_get_all_active_pokemon_doubles_none(self):
        """Get all active Pokemon in doubles mode with no positions filled"""
        all_active = self.doubles_battler.get_all_active_pokemon()
        self.assertEqual(len(all_active), 0)
    
    def test_get_active_count_singles(self):
        """Count active Pokemon in singles mode"""
        self.singles_battler.active = self.pikachu
        count = self.singles_battler.get_active_count()
        self.assertEqual(count, 1)
    
    def test_get_active_count_singles_none(self):
        """Count active Pokemon in singles mode when None"""
        count = self.singles_battler.get_active_count()
        self.assertEqual(count, 0)
    
    def test_get_active_count_doubles_both(self):
        """Count active Pokemon in doubles mode with both positions"""
        self.doubles_battler.active[0] = self.pikachu
        self.doubles_battler.active[1] = self.charizard
        count = self.doubles_battler.get_active_count()
        self.assertEqual(count, 2)
    
    def test_get_active_count_doubles_one(self):
        """Count active Pokemon in doubles mode with one position"""
        self.doubles_battler.active[0] = self.pikachu
        count = self.doubles_battler.get_active_count()
        self.assertEqual(count, 1)
    
    def test_has_pokemon_at_position_singles_true(self):
        """Check if Pokemon exists at position in singles"""
        self.singles_battler.active = self.pikachu
        self.assertTrue(self.singles_battler.has_pokemon_at_position(0))
    
    def test_has_pokemon_at_position_singles_false(self):
        """Check if Pokemon exists at invalid position in singles"""
        self.singles_battler.active = self.pikachu
        self.assertFalse(self.singles_battler.has_pokemon_at_position(1))
    
    def test_has_pokemon_at_position_doubles_left(self):
        """Check if Pokemon exists at left position in doubles"""
        self.doubles_battler.active[0] = self.pikachu
        self.assertTrue(self.doubles_battler.has_pokemon_at_position(0))
    
    def test_has_pokemon_at_position_doubles_right(self):
        """Check if Pokemon exists at right position in doubles"""
        self.doubles_battler.active[1] = self.charizard
        self.assertTrue(self.doubles_battler.has_pokemon_at_position(1))
    
    def test_has_pokemon_at_position_doubles_empty(self):
        """Check if Pokemon exists at empty position in doubles"""
        self.assertFalse(self.doubles_battler.has_pokemon_at_position(0))
        self.assertFalse(self.doubles_battler.has_pokemon_at_position(1))


class TestDoublesBackwardCompatibility(unittest.TestCase):
    """Test that singles battles still work with the new doubles support"""
    
    def test_existing_battler_methods_work_in_singles(self):
        """Test that existing Battler methods work correctly in singles mode"""
        battler = Battler(is_doubles=False)
        pikachu = Pokemon("pikachu", 100)
        charizard = Pokemon("charizard", 100)
        
        battler.active = pikachu
        battler.reserve = [charizard]
        
        # Test num_fainted_pkmn (uses get_all_active_pokemon internally)
        self.assertEqual(battler.num_fainted_pkmn(), 0)
        
        # Test mega_revealed (uses get_all_active_pokemon internally)
        self.assertFalse(battler.mega_revealed())
    
    def test_battle_initialization_defaults_to_singles(self):
        """Test that Battle defaults to singles mode for backward compatibility"""
        battle = Battle("test-battle")
        self.assertFalse(battle.is_doubles)
        self.assertIsNone(battle.user.active)
        self.assertIsNone(battle.opponent.active)


class TestDoublesConstants(unittest.TestCase):
    """Test that doubles constants are properly defined"""
    
    def test_doubles_formats_defined(self):
        """Test that DOUBLES_FORMATS constant exists and has entries"""
        self.assertTrue(hasattr(constants, 'DOUBLES_FORMATS'))
        self.assertGreater(len(constants.DOUBLES_FORMATS), 0)
        self.assertIn("gen9vgc2024", constants.DOUBLES_FORMATS)
    
    def test_position_constants_defined(self):
        """Test that position constants are defined"""
        self.assertTrue(hasattr(constants, 'POSITION_LEFT'))
        self.assertTrue(hasattr(constants, 'POSITION_RIGHT'))
        self.assertEqual(constants.POSITION_LEFT, 0)
        self.assertEqual(constants.POSITION_RIGHT, 1)
    
    def test_targeting_constants_defined(self):
        """Test that targeting constants are defined"""
        self.assertTrue(hasattr(constants, 'TARGET_RANDOM'))
        self.assertTrue(hasattr(constants, 'TARGET_SELF'))
        self.assertTrue(hasattr(constants, 'TARGET_ALLY'))
        self.assertTrue(hasattr(constants, 'TARGET_LEFT_OPPONENT'))
        self.assertTrue(hasattr(constants, 'TARGET_RIGHT_OPPONENT'))


if __name__ == '__main__':
    unittest.main()











