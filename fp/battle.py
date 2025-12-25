"""
Battle module - Main entry point for battle-related classes.

This module re-exports all battle-related classes for backwards compatibility.
The actual implementations are in separate files:
- Pokemon, Move, LastUsedMove, etc. -> fp/pokemon.py
- SinglesBattler, DoublesBattler -> fp/battler_singles.py, fp/battler_doubles.py
- SinglesBattle, DoublesBattle -> fp/battle_types.py
- Battle (base class) -> fp/battle_base.py

For creating battles, use the factory function from fp/battle_factory.py
"""

# Re-export all classes for backwards compatibility
from fp.pokemon import (
    Pokemon,
    Move,
    LastUsedMove,
    DamageDealt,
    StatRange,
)

from fp.battler_singles import SinglesBattler
from fp.battler_doubles import DoublesBattler

from fp.battle_base import Battle, smart_team_preview, boost_multiplier_lookup
from fp.battle_types import SinglesBattle, DoublesBattle
from fp.battle_factory import create_battle

# Legacy compatibility: Export a generic "Battler" that maps to SinglesBattler
# (most old code expects singles)
Battler = SinglesBattler

__all__ = [
    # Pokemon-related
    "Pokemon",
    "Move",
    "LastUsedMove",
    "DamageDealt",
    "StatRange",
    
    # Battler classes
    "Battler",  # Legacy - maps to SinglesBattler
    "SinglesBattler",
    "DoublesBattler",
    
    # Battle classes
    "Battle",  # Base class
    "SinglesBattle",
    "DoublesBattle",
    "create_battle",  # Factory function
    
    # Utilities
    "smart_team_preview",
    "boost_multiplier_lookup",
]
