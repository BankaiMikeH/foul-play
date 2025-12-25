"""
Test team preview handling for doubles battles.
"""
import pytest
import json
from fp.battle import Battle, Battler
import constants


class TestDoublesTeamPreview:
    """Test team preview initialization for doubles."""
    
    def test_team_preview_initialization_doubles(self):
        """Test that team preview correctly moves active Pokemon to reserve."""
        battle = Battle("test-battle", is_doubles=True)
        
        # Simulate initial request JSON
        request_json = {
            "active": [{"moves": []}, {"moves": []}],  # Two active slots
            "side": {
                "name": "TestPlayer",
                "id": "p1",
                "pokemon": [
                    {
                        "ident": "p1: Miraidon",
                        "details": "Miraidon, L50",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 100, "def": 100, "spa": 150, "spd": 100, "spe": 130},
                        "moves": ["electrodr

ift", "dracometeor", "voltswitch", "protect"],
                        "baseAbility": "hadronengine",
                        "item": "lifeorb",
                        "pokeball": "pokeball",
                        "ability": "hadronengine"
                    },
                    {
                        "ident": "p1: Incineroar",
                        "details": "Incineroar, L50",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 130, "def": 100, "spa": 80, "spd": 100, "spe": 60},
                        "moves": ["fakeout", "flareblitz", "knockoff", "partingshot"],
                        "baseAbility": "intimidate",
                        "item": "sitrusberry",
                        "pokeball": "pokeball",
                        "ability": "intimidate"
                    },
                    {
                        "ident": "p1: Amoonguss",
                        "details": "Amoonguss, L50",
                        "condition": "220/220",
                        "active": False,
                        "stats": {"atk": 70, "def": 90, "spa": 90, "spd": 100, "spe": 30},
                        "moves": ["spore", "ragepowder", "pollenpuff", "protect"],
                        "baseAbility": "regenerator",
                        "item": "rockyhelmet",
                        "pokeball": "pokeball",
                        "ability": "regenerator"
                    },
                    {
                        "ident": "p1: Landorus",
                        "details": "Landorus-Therian, L50",
                        "condition": "180/180",
                        "active": False,
                        "stats": {"atk": 165, "def": 100, "spa": 115, "spd": 80, "spe": 111},
                        "moves": ["earthquake", "rockslide", "uturn", "protect"],
                        "baseAbility": "intimidate",
                        "item": "choicescarf",
                        "pokeball": "pokeball",
                        "ability": "intimidate"
                    }
                ]
            },
            "rqid": 1
        }
        
        # Initialize user's Pokemon from request
        battle.user.from_json(request_json, battle.user.active_index)
        
        # Verify initial state
        assert battle.user.active == [None, None], "Active should be [None, None] for doubles"
        assert len(battle.user.reserve) == 4, "All 4 Pokemon should be in reserve"
        
        # Simulate team preview selection (player chooses which 4 to bring)
        # In VGC, you see all 6 but can only bring 4
        team_preview_msg = "|teampreview|4"
        
        # After team preview, user selects their lead Pokemon
        # Simulate selecting Pokemon 1 and 2 as leads
        battle.user.active = [battle.user.reserve[0], battle.user.reserve[1]]
        battle.user.reserve = battle.user.reserve[2:]
        
        # Verify final state
        assert len(battle.user.active) == 2, "Should have 2 active Pokemon"
        assert battle.user.active[0] is not None, "Position 0 should have Pokemon"
        assert battle.user.active[1] is not None, "Position 1 should have Pokemon"
        assert len(battle.user.reserve) == 2, "Should have 2 reserve Pokemon"
    
    def test_battler_initialize_first_turn_doubles(self):
        """Test Battler.initialize_first_turn_user_from_json for doubles."""
        battler = Battler(is_doubles=True)
        
        request_json = {
            "active": [
                {"moves": [{"move": "Electro Drift", "id": "electrodrift", "pp": 8, "maxpp": 8, "target": "normal"}]},
                {"moves": [{"move": "Fake Out", "id": "fakeout", "pp": 16, "maxpp": 16, "target": "normal"}]}
            ],
            "side": {
                "name": "TestPlayer",
                "id": "p1",
                "pokemon": [
                    {
                        "ident": "p1: Miraidon",
                        "details": "Miraidon, L50, M",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 100, "def": 100, "spa": 150, "spd": 100, "spe": 130},
                        "moves": ["electrodrift", "dracometeor"],
                        "baseAbility": "hadronengine",
                        "item": "lifeorb",
                        "pokeball": "pokeball",
                        "ability": "hadronengine"
                    },
                    {
                        "ident": "p1: Incineroar",
                        "details": "Incineroar, L50, M",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 130, "def": 100, "spa": 80, "spd": 100, "spe": 60},
                        "moves": ["fakeout", "flareblitz"],
                        "baseAbility": "intimidate",
                        "item": "sitrusberry",
                        "pokeball": "pokeball",
                        "ability": "intimidate"
                    },
                    {
                        "ident": "p1: Amoonguss",
                        "details": "Amoonguss, L50",
                        "condition": "220/220",
                        "active": False,
                        "stats": {"atk": 70, "def": 90, "spa": 90, "spd": 100, "spe": 30},
                        "moves": ["spore", "ragepowder"],
                        "baseAbility": "regenerator",
                        "item": "rockyhelmet",
                        "pokeball": "pokeball",
                        "ability": "regenerator"
                    }
                ]
            }
        }
        
        # This should not raise an error
        battler.initialize_first_turn_user_from_json(request_json)
        
        # Verify doubles state
        assert isinstance(battler.active, list), "Active should be a list for doubles"
        assert len(battler.active) == 2, "Should have 2 active Pokemon"
        assert battler.active[0] is not None, "Position 0 should have Pokemon"
        assert battler.active[1] is not None, "Position 1 should have Pokemon"
        assert battler.active[0].name == "miraidon", "First Pokemon should be Miraidon"
        assert battler.active[1].name == "incineroar", "Second Pokemon should be Incineroar"
        assert len(battler.reserve) == 1, "Should have 1 reserve Pokemon"
    
    def test_battler_update_from_request_json_doubles(self):
        """Test Battler.update_from_request_json for doubles."""
        battler = Battler(is_doubles=True)
        
        # First, initialize
        initial_request = {
            "active": [
                {"moves": [{"move": "Electro Drift", "id": "electrodrift"}]},
                {"moves": [{"move": "Fake Out", "id": "fakeout"}]}
            ],
            "side": {
                "name": "TestPlayer",
                "id": "p1",
                "pokemon": [
                    {
                        "ident": "p1: Miraidon",
                        "details": "Miraidon, L50",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 100, "def": 100, "spa": 150, "spd": 100, "spe": 130},
                        "moves": ["electrodrift"],
                        "baseAbility": "hadronengine",
                        "item": "lifeorb",
                        "ability": "hadronengine"
                    },
                    {
                        "ident": "p1: Incineroar",
                        "details": "Incineroar, L50",
                        "condition": "200/200",
                        "active": True,
                        "stats": {"atk": 130, "def": 100, "spa": 80, "spd": 100, "spe": 60},
                        "moves": ["fakeout"],
                        "baseAbility": "intimidate",
                        "item": "sitrusberry",
                        "ability": "intimidate"
                    }
                ]
            }
        }
        
        battler.initialize_first_turn_user_from_json(initial_request)
        
        # Now update with damage
        update_request = {
            "active": [
                {
                    "moves": [{"move": "Electro Drift", "id": "electrodrift", "disabled": False}]
                },
                {
                    "moves": [{"move": "Fake Out", "id": "fakeout", "disabled": True}]  # Fake Out disabled turn 2
                }
            ],
            "side": {
                "name": "TestPlayer",
                "id": "p1",
                "pokemon": [
                    {
                        "ident": "p1: Miraidon",
                        "details": "Miraidon, L50",
                        "condition": "150/200",  # Took damage
                        "active": True,
                        "stats": {"atk": 100, "def": 100, "spa": 150, "spd": 100, "spe": 130},
                        "moves": ["electrodrift"],
                        "baseAbility": "hadronengine",
                        "item": "lifeorb",
                        "ability": "hadronengine"
                    },
                    {
                        "ident": "p1: Incineroar",
                        "details": "Incineroar, L50",
                        "condition": "180/200",  # Took damage
                        "active": True,
                        "stats": {"atk": 130, "def": 100, "spa": 80, "spd": 100, "spe": 60},
                        "moves": ["fakeout"],
                        "baseAbility": "intimidate",
                        "item": "sitrusberry",
                        "ability": "intimidate"
                    }
                ]
            }
        }
        
        # This should update HP without errors
        battler.update_from_request_json(update_request)
        
        # Verify updates
        assert battler.active[0].hp == 150, "Miraidon HP should be updated"
        assert battler.active[1].hp == 180, "Incineroar HP should be updated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

