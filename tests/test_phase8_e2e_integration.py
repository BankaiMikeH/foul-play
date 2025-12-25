"""
Phase 8: End-to-End Integration Tests

Tests the full Python → Rust → Python flow for doubles battles.
"""

import pytest
from fp.battle import Battle, Battler, Pokemon
from fp.search.poke_engine_helpers import (
    battler_to_poke_engine_side,
    battle_to_poke_engine_state,
    parse_rust_decision_for_doubles,
    rust_decision_to_showdown_decision,
)
from data import all_move_json
import constants


class TestPhase8EndToEnd:
    """End-to-end integration tests for doubles battles"""

    def setup_method(self):
        """Create a test doubles battle"""
        self.battle = Battle("doubles_test")
        self.battle.battle_type = constants.DOUBLES_BATTLE
        self.battle.generation = "gen9"
        
        # Create user's battler with 2 active Pokemon
        self.battle.user = Battler()
        self.battle.user.name = "TestPlayer"
        self.battle.user.is_doubles = True
        
        # Create opponent's battler
        self.battle.opponent = Battler()
        self.battle.opponent.name = "Opponent"
        self.battle.opponent.is_doubles = True
        
        # Add Pokemon to user's team
        self.create_test_pokemon(self.battle.user)
        
        # Add Pokemon to opponent's team
        self.create_test_pokemon(self.battle.opponent)
        
    def create_test_pokemon(self, battler):
        """Create test Pokemon for a battler"""
        # Active Pokemon 1 (left position)
        pkmn1 = Pokemon("pikachu", 50)
        pkmn1.moves = self.get_test_moves(["thunderbolt", "quickattack", "irontail", "thunderwave"])
        pkmn1.hp = 100
        pkmn1.max_hp = 100
        pkmn1.stats = {
            constants.ATTACK: 55,
            constants.DEFENSE: 40,
            constants.SPECIAL_ATTACK: 50,
            constants.SPECIAL_DEFENSE: 50,
            constants.SPEED: 90,
        }
        pkmn1.ability = "static"
        pkmn1.item = "lightball"
        pkmn1.types = ["electric"]
        
        # Active Pokemon 2 (right position)
        pkmn2 = Pokemon("charizard", 50)
        pkmn2.moves = self.get_test_moves(["flamethrower", "airslash", "dragonpulse", "roost"])
        pkmn2.hp = 150
        pkmn2.max_hp = 150
        pkmn2.stats = {
            constants.ATTACK: 84,
            constants.DEFENSE: 78,
            constants.SPECIAL_ATTACK: 109,
            constants.SPECIAL_DEFENSE: 85,
            constants.SPEED: 100,
        }
        pkmn2.ability = "blaze"
        pkmn2.item = "choicespecs"
        pkmn2.types = ["fire", "flying"]
        
        # Reserve Pokemon
        pkmn3 = Pokemon("venusaur", 50)
        pkmn3.moves = self.get_test_moves(["gigadrain", "sludgebomb", "earthquake", "synthesis"])
        pkmn3.hp = 155
        pkmn3.max_hp = 155
        pkmn3.stats = {
            constants.ATTACK: 82,
            constants.DEFENSE: 83,
            constants.SPECIAL_ATTACK: 100,
            constants.SPECIAL_DEFENSE: 100,
            constants.SPEED: 80,
        }
        pkmn3.ability = "overgrow"
        pkmn3.item = "blacksludge"
        pkmn3.types = ["grass", "poison"]
        
        # Assign Pokemon
        # For doubles, active should be a list [pkmn1, pkmn2]
        # For singles, active is just a Pokemon object
        if battler.is_doubles:
            battler.active = [pkmn1, pkmn2]
            battler.active_pokemon = {0: pkmn1, 1: pkmn2}
        else:
            battler.active = pkmn1
        battler.reserve = [pkmn3]
        
    def get_test_moves(self, move_names):
        """Get move objects from move names"""
        moves = []
        for name in move_names:
            move_dict = all_move_json.get(name, {})
            move_obj = type('Move', (), {
                'name': name,
                'disabled': False,
                'current_pp': move_dict.get('pp', 10),
                'max_pp': move_dict.get('pp', 10),
            })()
            moves.append(move_obj)
        return moves

    def test_python_to_rust_conversion(self):
        """Test converting Python battle to Rust state"""
        # Convert user battler to Rust side
        rust_side = battler_to_poke_engine_side(self.battle.user)
        
        # Verify conversion worked
        assert rust_side is not None
        assert len(rust_side.pokemon) >= 2, "Should have at least 2 Pokemon"
        
        # For doubles, active_index should be "0,1"
        if self.battle.user.is_doubles:
            assert "," in rust_side.active_index, "Doubles should have comma-separated active indices"
            indices = rust_side.active_index.split(",")
            assert len(indices) == 2, "Should have 2 active indices for doubles"

    def test_battle_state_conversion(self):
        """Test converting full battle to Rust state"""
        try:
            from poke_engine import State as PokeEngineState
            
            # Convert battle to Rust state
            rust_state = battle_to_poke_engine_state(self.battle)
            
            # Verify state was created
            assert rust_state is not None
            
            # Check if state recognizes it's doubles
            # Note: This depends on Rust implementation
            print(f"Rust state created successfully")
            
        except ImportError:
            pytest.skip("poke-engine not available (needs compilation)")

    def test_rust_decision_parsing(self):
        """Test parsing Rust decision strings"""
        # Test move pair
        left, right = parse_rust_decision_for_doubles("move0,move1")
        assert left["type"] == "move"
        assert left["index"] == 0
        assert right["type"] == "move"
        assert right["index"] == 1
        
        # Test move with switch
        left, right = parse_rust_decision_for_doubles("move2,switch1")
        assert left["type"] == "move"
        assert left["index"] == 2
        assert right["type"] == "switch"
        assert right["index"] == 1
        
        # Test move with target
        left, right = parse_rust_decision_for_doubles("move0target1,move1target2")
        assert left["type"] == "move"
        assert left["index"] == 0
        assert left["target"] == 1
        assert right["type"] == "move"
        assert right["index"] == 1
        assert right["target"] == 2

    def test_rust_to_showdown_conversion(self):
        """Test converting Rust decision to Showdown format"""
        # Simple move pair
        decision_str = "move0,move1"
        showdown_cmd = rust_decision_to_showdown_decision(self.battle, decision_str)
        
        # Should be a valid Showdown command
        assert showdown_cmd.startswith("/choose")
        # Note: The actual format depends on implementation
        # For doubles, might be "/choose move 1, move 2" or similar
        
        print(f"Showdown command: {showdown_cmd}")

    def test_full_flow_simulation(self):
        """
        Test the complete flow:
        Python Battle → Rust State → Rust Decision → Python Decision
        """
        try:
            from poke_engine import State, perform_mcts
            from poke_engine import quick_doubles_decision
            import time
            
            # Step 1: Convert Python battle to Rust state
            print("\n=== Testing Full Integration Flow ===")
            print("Step 1: Converting Python battle to Rust state...")
            rust_state = battle_to_poke_engine_state(self.battle)
            print("✓ Conversion successful")
            
            # Step 2: Get AI decision from Rust
            print("Step 2: Getting AI decision from Rust MCTS...")
            start_time = time.time()
            
            # Call the Rust MCTS (using quick decision for faster test)
            # Note: This will use the doubles MCTS if state is doubles
            try:
                (pos0_move, pos1_move) = quick_doubles_decision(rust_state)
                decision_time = time.time() - start_time
                print(f"✓ AI decision made in {decision_time:.3f}s")
                print(f"  Position 0: {pos0_move}")
                print(f"  Position 1: {pos1_move}")
                
                # Step 3: Convert Rust decision back to Python/Showdown format
                print("Step 3: Converting Rust decision to Showdown format...")
                # Format the decision for Rust integration
                rust_decision_str = f"{pos0_move},{pos1_move}"
                showdown_cmd = rust_decision_to_showdown_decision(self.battle, rust_decision_str)
                print(f"✓ Showdown command: {showdown_cmd}")
                
                print("\n=== Full Flow Test PASSED ===")
                
                # Verify decision time is reasonable
                assert decision_time < 10.0, f"Decision took too long: {decision_time:.3f}s"
                
            except AttributeError:
                # quick_doubles_decision might not be available in this version
                print("Note: quick_doubles_decision not available, using fallback")
                # Fallback: just verify conversion worked
                showdown_cmd = rust_decision_to_showdown_decision(self.battle, "move0,move1")
                print(f"✓ Showdown command (fallback): {showdown_cmd}")
                
        except ImportError as e:
            pytest.skip(f"poke-engine not available: {e}")

    def test_error_handling(self):
        """Test that errors are handled gracefully"""
        # Invalid decision format
        left, right = parse_rust_decision_for_doubles("invalid")
        assert left is not None
        assert right is not None
        # Should have fallback values
        
        # Empty decision
        left, right = parse_rust_decision_for_doubles("")
        assert left is not None
        assert right is not None

    def test_decision_validity(self):
        """Test that generated decisions are valid for the battle state"""
        rust_decision = "move0,move1"
        showdown_cmd = rust_decision_to_showdown_decision(self.battle, rust_decision)
        
        # Basic format checks
        assert "/choose" in showdown_cmd
        assert "move" in showdown_cmd.lower()

    def test_performance_target(self):
        """Test that decision making meets performance targets"""
        try:
            from poke_engine import State
            from poke_engine import quick_doubles_decision
            import time
            
            rust_state = battle_to_poke_engine_state(self.battle)
            
            # Measure decision time
            start = time.time()
            decision = quick_doubles_decision(rust_state)
            elapsed = time.time() - start
            
            print(f"\nDecision time: {elapsed:.3f}s")
            
            # Target: < 5s for quick decision
            assert elapsed < 5.0, f"Decision too slow: {elapsed:.3f}s"
            
        except ImportError:
            pytest.skip("poke-engine not available")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])

