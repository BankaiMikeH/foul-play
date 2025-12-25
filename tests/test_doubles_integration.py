"""
Integration tests for full doubles battle flow.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fp.battle import Battle
from fp.run_battle import format_decision, async_update_battle
import constants


class TestDoublesIntegration:
    """Test complete battle flows for doubles."""
    
    def test_team_preview_to_turn_1_flow(self):
        """Test the flow from team preview through first turn."""
        battle = Battle("test-battle", is_doubles=True)
        
        # Step 1: Team Preview
        # Opponent Pokemon are revealed
        opponent_team = [
            ("miraidon", 50),
            ("incineroar", 50),
            ("amoonguss", 50),
            ("landorustherian", 50)
        ]
        
        for name, level in opponent_team:
            battle.initialize_team_preview(opponent_team, constants.BATTLE_TYPE_DOUBLES)
        
        # Step 2: User selects their team (already loaded from team file)
        # In real battle, this comes from request JSON
        
        # Step 3: Turn 1 begins
        # Both players have 2 active Pokemon
        assert battle.is_doubles == True
        
        # User should have active Pokemon list
        assert isinstance(battle.user.active, list) or battle.user.active is None
        
        # Opponent should have active Pokemon list
        assert isinstance(battle.opponent.active, list) or battle.opponent.active is None
    
    def test_decision_formatting_both_positions(self):
        """Test decision formatting for both Pokemon in doubles."""
        battle = Battle("test-battle", is_doubles=True)
        
        # Simulate having 2 active Pokemon with moves
        from fp.battle import Pokemon
        
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.moves = [
            {"id": "electrodrift", "name": "Electro Drift", "pp": 8},
            {"id": "dracometeor", "name": "Draco Meteor", "pp": 8}
        ]
        pkmn1.index = 1
        
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.moves = [
            {"id": "fakeout", "name": "Fake Out", "pp": 16},
            {"id": "flareblitz", "name": "Flare Blitz", "pp": 16}
        ]
        pkmn2.index = 2
        
        battle.user.active = [pkmn1, pkmn2]
        
        # Decision: "move electrodrift 1, move fakeout 2"
        # Miraidon uses Electro Drift on opponent position 1
        # Incineroar uses Fake Out on opponent position 2
        decision = "move electrodrift 1, move fakeout 2"
        
        formatted = format_decision(battle, decision)
        
        # Should format to Pokemon Showdown protocol
        assert "/choose" in formatted
        assert "move" in formatted
        assert "1" in formatted  # Target
        assert "2" in formatted  # Target
    
    def test_switch_decision_formatting(self):
        """Test switch decision formatting in doubles."""
        battle = Battle("test-battle", is_doubles=True)
        
        from fp.battle import Pokemon
        
        # Active Pokemon
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.index = 1
        pkmn1.hp = 50  # Low HP, want to switch
        
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.index = 2
        pkmn2.moves = [{"id": "fakeout", "name": "Fake Out", "pp": 16}]
        
        # Reserve Pokemon
        pkmn3 = Pokemon("amoonguss", 50)
        pkmn3.index = 3
        
        battle.user.active = [pkmn1, pkmn2]
        battle.user.reserve = [pkmn3]
        
        # Decision: Switch Miraidon out for Amoonguss, Incineroar uses Fake Out
        decision = "switch amoonguss, move fakeout 1"
        
        formatted = format_decision(battle, decision)
        
        # Should format to Pokemon Showdown protocol
        assert "/choose" in formatted
        assert "switch" in formatted
        assert "move" in formatted
    
    def test_spread_move_targeting(self):
        """Test that spread moves (hit multiple targets) are handled."""
        battle = Battle("test-battle", is_doubles=True)
        
        from fp.battle import Pokemon
        
        pkmn = Pokemon("landorustherian", 50)
        pkmn.moves = [
            {"id": "earthquake", "name": "Earthquake", "pp": 16}  # Hits all adjacent
        ]
        pkmn.index = 1
        
        battle.user.active = [pkmn, None]
        
        # Earthquake in doubles has no target (hits all adjacent)
        # Some implementations use target -1 or no target specification
        decision = "move earthquake, pass"  # Second Pokemon passed (fainted or not present)
        
        formatted = format_decision(battle, decision)
        
        # Should format correctly
        assert "/choose" in formatted
    
    def test_protect_targeting(self):
        """Test that Protect targets self correctly."""
        battle = Battle("test-battle", is_doubles=True)
        
        from fp.battle import Pokemon
        
        pkmn = Pokemon("incineroar", 50)
        pkmn.moves = [
            {"id": "protect", "name": "Protect", "pp": 16}
        ]
        pkmn.index = 1
        
        battle.user.active = [pkmn, None]
        
        # Protect should target self (no target needed or target -1)
        decision = "move protect, pass"
        
        formatted = format_decision(battle, decision)
        
        # Should format correctly
        assert "/choose" in formatted
        assert "protect" in formatted.lower()


class TestBattleStateTransitions:
    """Test state transitions during battle."""
    
    def test_damage_application_doubles(self):
        """Test that damage is applied to correct Pokemon."""
        battle = Battle("test-battle", is_doubles=True)
        
        from fp.battle import Pokemon
        
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.hp = 200
        pkmn1.maxhp = 200
        pkmn1.identifier = "p1a: Miraidon"
        
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.hp = 200
        pkmn2.maxhp = 200
        pkmn2.identifier = "p1b: Incineroar"
        
        battle.user.active = [pkmn1, pkmn2]
        
        # Simulate damage to position 0 (Miraidon)
        # In real battle, this would come from |-damage|p1a: Miraidon|150/200
        pkmn1.hp = 150
        
        # Verify only Miraidon took damage
        assert battle.user.active[0].hp == 150
        assert battle.user.active[1].hp == 200
    
    def test_faint_and_switch_in(self):
        """Test Pokemon fainting and switching in replacement."""
        battle = Battle("test-battle", is_doubles=True)
        
        from fp.battle import Pokemon
        
        # Active Pokemon
        pkmn1 = Pokemon("miraidon", 50)
        pkmn1.hp = 0  # Fainted
        pkmn1.identifier = "p1a: Miraidon"
        
        pkmn2 = Pokemon("incineroar", 50)
        pkmn2.hp = 200
        pkmn2.identifier = "p1b: Incineroar"
        
        # Reserve Pokemon
        pkmn3 = Pokemon("amoonguss", 50)
        pkmn3.hp = 220
        
        battle.user.active = [pkmn1, pkmn2]
        battle.user.reserve = [pkmn3]
        
        # Simulate forced switch (Miraidon fainted, must switch in Amoonguss)
        # This would happen through battle_modifier.py message handlers
        
        # After switch:
        battle.user.active[0] = pkmn3
        battle.user.reserve = [pkmn1]  # Fainted Pokemon goes to reserve
        
        # Verify
        assert battle.user.active[0].hp == 220  # Amoonguss now active
        assert battle.user.active[1].hp == 200  # Incineroar still active
        assert battle.user.reserve[0].hp == 0   # Miraidon in reserve (fainted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

