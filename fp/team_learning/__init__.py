"""
Team Learning Module for Pokemon VGC

This module provides learning and adaptation from battle results:
- Battle result tracking
- Performance database
- Meta analysis
- Machine learning predictions
- Evolutionary algorithms
- Team recommendations
- Adaptive generation

Phase 12 of the Pokemon Battle AI project.
"""

from .battle_tracker import BattleTracker
from .performance_db import PerformanceDatabase
from .recommender import TeamRecommender
from .meta_analyzer import MetaAnalyzer
from .learning_engine import LearningEngine
from .evolutionary import EvolutionaryTeamBuilder
from .adaptive_generator import AdaptiveTeamGenerator

__all__ = [
    'BattleTracker',
    'PerformanceDatabase',
    'TeamRecommender',
    'MetaAnalyzer',
    'LearningEngine',
    'EvolutionaryTeamBuilder',
    'AdaptiveTeamGenerator'
]

__version__ = '1.0.0'
__author__ = 'Pokemon Battle AI Team'

