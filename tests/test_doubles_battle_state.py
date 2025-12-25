"""
Test battle state management for doubles battles.
"""
import pytest
from fp.battle import Battle, Battler, Pokemon
import constants


class TestDoublesBattleState:
    """Test battle state tracking for doubles."""
    
    def test_get_active_pokemon_by_position(self):
        """Test getting active Pokemon by position in doubles."""
        battler = Battler(is_doubles=True)
        
        # Create test Pokemon
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.hp = 200
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.hp = 200
        
        # Set active Pokemon
        battler.active = [pkmn1, pkmn2]
        
        # Test getting by position
        assert battler.get_active_pokemon(0) == pkmn1
        assert battler.get_active_pokemon(1) == pkmn2
        
        # Test invalid position
        assert battler.get_active_pokemon(2) is None
        assert battler.get_active_pokemon(-1) is None
    
    def test_set_active_pokemon_by_position(self):
        """Test setting active Pokemon by position in doubles."""
        battler = Battler(is_doubles=True)
        battler.active = [None, None]
        
        # Create test Pokemon
        pkmn1 = Pokemon("miraidon", 50)
        pkmn2 = Pokemon("incineroar", 50)
        
        # Set by position
        battler.set_active_pokemon(pkmn1, 0)
        battler.set_active_pokemon(pkmn2, 1)
        
        # Verify
        assert battler.active[0] == pkmn1
        assert battler.active[1] == pkmn2
    
    def test_get_all_active_pokemon(self):
        """Test getting all active Pokemon in doubles."""
        battler = Battler(is_doubles=True)
        
        pkmn1 = Pokemon("miraidon", 50)
        pkmn2 = Pokemon("incineroar", 50)
        battler.active = [pkmn1, pkmn2]
        
        all_active = battler.get_all_active_pokemon()
        
        assert len(all_active) == 2
        assert pkmn1 in all_active
        assert pkmn2 in all_active
    
    def test_get_all_active_pokemon_with_faint(self):
        """Test getting active Pokemon when one has fainted."""
        battler = Battler(is_doubles=True)
        
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.hp = 0  # Fainted
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.hp = 200
        
        battler.active = [pkmn1, pkmn2]
        
        all_active = battler.get_all_active_pokemon()
        
        # Should still return both, even if one is fainted
        assert len(all_active) == 2
    
    def test_battle_has_both_battlers_doubles(self):
        """Test that Battle has both user and opponent as Battler instances."""
        battle = Battle("test-battle", is_doubles=True)
        
        assert isinstance(battle.user, Battler)
        assert isinstance(battle.opponent, Battler)
        assert battle.user.is_doubles == True
        assert battle.opponent.is_doubles == True
    
    def test_find_pokemon_in_reserves(self):
        """Test finding Pokemon in reserve by name."""
        battler = Battler(is_doubles=True)
        
        pkmn1 = Pokemon("amoonguss", 50)
        pkmn1.identifier = "p1: Amoonguss"
        pkmn2 = Pokemon("landorustherian", 50)
        pkmn2.identifier = "p1: Landorus"
        
        battler.reserve = [pkmn1, pkmn2]
        
        # Find by name
        found = battler.find_pokemon_in_reserves("amoonguss")
        assert found == pkmn1
        
        found2 = battler.find_pokemon_in_reserves("landorustherian")
        assert found2 == pkmn2
        
        # Not found
        not_found = battler.find_pokemon_in_reserves("nonexistent")
        assert not_found is None
    
    def test_switch_pokemon_in_doubles(self):
        """Test switching Pokemon in doubles."""
        battler = Battler(is_doubles=True)
        
        # Active Pokemon
        active1 = Pokemon("miraidon", 50)
        active1.hp = 150
        active2 = Pokemon("incineroar", 50)
        active2.hp = 200
        
        # Reserve Pokemon
        reserve1 = Pokemon("amoonguss", 50)
        reserve1.hp = 220
        reserve2 = Pokemon("landorustherian", 50)
        reserve2.hp = 180
        
        battler.active = [active1, active2]
        battler.reserve = [reserve1, reserve2]
        
        # Switch position 0: Miraidon -> Amoonguss
        # This simulates what would happen during a switch
        switched_out = battler.active[0]
        switched_in = battler.reserve[0]
        
        battler.active[0] = switched_in
        battler.reserve[0] = switched_out
        
        # Verify switch
        assert battler.active[0] == reserve1  # Amoonguss now active
        assert battler.active[1] == active2   # Incineroar still active
        assert battler.reserve[0] == active1  # Miraidon now in reserve
    
    def test_simultaneous_faint_doubles(self):
        """Test handling when both active Pokemon faint."""
        battler = Battler(is_doubles=True)
        
        # Both active Pokemon faint
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.hp = 0
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.hp = 0
        
        battler.active = [pkmn1, pkmn2]
        
        # Should have 2 active Pokemon (even if fainted)
        assert len(battler.active) == 2
        
        # Both should be fainted
        all_active = battler.get_all_active_pokemon()
        assert all(p.hp == 0 for p in all_active)
    
    def test_position_tracking(self):
        """Test that Pokemon positions are tracked correctly."""
        battler = Battler(is_doubles=True)
        
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.position_index = 0
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.position_index = 1
        
        battler.active = [pkmn1, pkmn2]
        
        # Verify positions
        assert battler.get_active_pokemon(0).position_index == 0
        assert battler.get_active_pokemon(1).position_index == 1


class TestDoublesIdentifierParsing:
    """Test parsing of Pokemon identifiers in doubles (p1a, p1b, p2a, p2b)."""
    
    def test_identifier_format_doubles(self):
        """Test that doubles identifiers are parsed correctly."""
        # In doubles, identifiers are like "p1a: Miraidon" or "p1b: Incineroar"
        # p1a = Player 1, position a (left)
        # p1b = Player 1, position b (right)
        
        pkmn = Pokemon("miraidon", 50)
        pkmn.identifier = "p1a: Miraidon"
        
        assert "p1a" in pkmn.identifier
        
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.identifier = "p1b: Incineroar"
        
        assert "p1b" in pkmn2.identifier
    
    def test_extract_position_from_identifier(self):
        """Test extracting position (a or b) from identifier."""
        # Position 'a' = left = index 0
        # Position 'b' = right = index 1
        
        identifier_a = "p1a: Miraidon"
        identifier_b = "p1b: Incineroar"
        
        # Extract position letter
        position_a = identifier_a.split(":")[0][-1]  # Get last char before ':'
        position_b = identifier_b.split(":")[0][-1]
        
        assert position_a == 'a'
        assert position_b == 'b'
        
        # Convert to index
        index_a = 0 if position_a == 'a' else 1
        index_b = 0 if position_b == 'a' else 1
        
        assert index_a == 0
        assert index_b == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

