"""
Team Generation Module for Pokemon VGC

This module provides AI-powered team generation including:
- Strategy-based team building (Trick Room, Tailwind, etc.)
- Pokemon core building
- Moveset optimization
- EV spread calculation
- Genetic algorithm improvement

Phase 11 of the Pokemon Battle AI project.
"""

from .team_generator import TeamGenerator
from .strategies import StrategyManager
from .pokemon_database import PokemonDatabase

__all__ = [
    'TeamGenerator',
    'StrategyManager',
    'PokemonDatabase'
]

__version__ = '1.0.0'
__author__ = 'Pokemon Battle AI Team'

