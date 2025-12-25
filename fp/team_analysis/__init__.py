"""
Team Analysis Module for Pokemon VGC

This module provides comprehensive team analysis tools including:
- Type coverage analysis
- Speed tier evaluation
- Role identification
- Synergy scoring
- Meta threat coverage

Phase 10 of the Pokemon Battle AI project.
"""

from .team_analyzer import TeamAnalyzer
from .type_coverage import TypeCoverageAnalyzer
from .speed_analysis import SpeedTierAnalyzer
from .role_system import RoleIdentifier
from .synergy_scorer import SynergyScorer

__all__ = [
    'TeamAnalyzer',
    'TypeCoverageAnalyzer',
    'SpeedTierAnalyzer',
    'RoleIdentifier',
    'SynergyScorer'
]

__version__ = '1.0.0'
__author__ = 'Pokemon Battle AI Team'

