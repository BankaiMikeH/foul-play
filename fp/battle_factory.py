"""
Factory function for creating the correct Battle type
"""
from fp.battle_types import SinglesBattle, DoublesBattle
from fp.helpers import is_doubles_format


def create_battle(battle_tag, pokemon_format=None, is_doubles=None):
    """
    Create the correct Battle subclass based on format.
    
    Args:
        battle_tag: The battle room identifier
        pokemon_format: The Pokemon Showdown format name (e.g. "gen9vgc2026regf")
        is_doubles: Explicit doubles flag (overrides format detection)
    
    Returns:
        SinglesBattle or DoublesBattle instance
    """
    # Determine if this is a doubles battle
    if is_doubles is not None:
        # Explicit flag provided
        doubles = is_doubles
    elif pokemon_format is not None:
        # Detect from format name
        doubles = is_doubles_format(pokemon_format)
    else:
        # Default to singles
        doubles = False
    
    # Create the appropriate Battle subclass
    if doubles:
        return DoublesBattle(battle_tag)
    else:
        return SinglesBattle(battle_tag)

