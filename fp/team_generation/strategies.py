"""
Strategy Manager

Manages team building strategies (Trick Room, Tailwind, etc.)
and provides strategy-specific team building logic.

Phase 11 - AI Team Generator
"""

import json
import os
from typing import Dict, List, Optional


class StrategyManager:
    """Manages team building strategies and their requirements."""
    
    def __init__(self, strategies_path: Optional[str] = None):
        """
        Initialize strategy manager.
        
        Args:
            strategies_path: Path to strategy_templates.json, or None for default
        """
        self.strategies = self._load_strategies(strategies_path)
        self.strategy_names = list(self.strategies.keys())
    
    def _load_strategies(self, strategies_path: Optional[str] = None) -> Dict:
        """Load strategy templates from JSON file."""
        if strategies_path is None:
            # Try to find the strategies file
            possible_paths = [
                'fp/data/strategy_templates.json',
                'data/strategy_templates.json',
                '../data/strategy_templates.json',
                os.path.join(os.path.dirname(__file__), '../data/strategy_templates.json')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    strategies_path = path
                    break
        
        if strategies_path is None or not os.path.exists(strategies_path):
            # Return default strategies if file not found
            return self._get_default_strategies()
        
        with open(strategies_path, 'r') as f:
            data = json.load(f)
            return data.get('strategies', {})
    
    def _get_default_strategies(self) -> Dict:
        """Get default strategies if file not found."""
        return {
            'balanced': {
                'name': 'Balanced',
                'description': 'Best Pokemon with good coverage',
                'required_moves': [],
                'required_roles': [],
                'preferred_roles': ['INTIMIDATE'],
                'speed_range': [60, 255],
                'min_bulk': 0,
                'core_size': 2,
                'team_size': 6
            }
        }
    
    def get_strategy(self, name: str) -> Optional[Dict]:
        """Get strategy by name."""
        return self.strategies.get(name.lower().replace(' ', '_'))
    
    def list_strategies(self) -> List[str]:
        """List all available strategies."""
        return [self.strategies[key]['name'] for key in self.strategy_names]
    
    def get_strategy_requirements(self, strategy_name: str) -> Dict:
        """
        Get requirements for a strategy.
        
        Returns:
            Dict with required_moves, required_roles, etc.
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return {}
        
        return {
            'required_moves': strategy.get('required_moves', []),
            'required_roles': strategy.get('required_roles', []),
            'preferred_roles': strategy.get('preferred_roles', []),
            'speed_range': strategy.get('speed_range', [0, 255]),
            'min_bulk': strategy.get('min_bulk', 0),
            'priority_abilities': strategy.get('priority_abilities', []),
            'avoid_abilities': strategy.get('avoid_abilities', [])
        }
    
    def validate_pokemon_for_strategy(self, pokemon: Dict, strategy_name: str) -> bool:
        """
        Check if a Pokemon fits a strategy's requirements.
        
        Args:
            pokemon: Pokemon data dict
            strategy_name: Name of strategy
        
        Returns:
            bool: True if Pokemon fits strategy
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return False
        
        # Check speed range
        speed_range = strategy.get('speed_range', [0, 255])
        pokemon_speed = pokemon.get('base_stats', {}).get('spe', 100)
        if not (speed_range[0] <= pokemon_speed <= speed_range[1]):
            return False
        
        # Check bulk requirement
        min_bulk = strategy.get('min_bulk', 0)
        if min_bulk > 0:
            stats = pokemon.get('base_stats', {})
            bulk = stats.get('hp', 0) + stats.get('def', 0) + stats.get('spd', 0)
            if bulk < min_bulk:
                return False
        
        # Check for avoid abilities
        avoid_abilities = strategy.get('avoid_abilities', [])
        pokemon_abilities = [a.lower().replace(' ', '') for a in pokemon.get('abilities', [])]
        for avoid_ability in avoid_abilities:
            if avoid_ability.lower().replace(' ', '') in pokemon_abilities:
                return False
        
        return True
    
    def get_sample_cores(self, strategy_name: str) -> List[List[str]]:
        """Get sample cores for a strategy."""
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return []
        
        return strategy.get('sample_cores', [])


# Example usage
if __name__ == '__main__':
    manager = StrategyManager()
    
    print("Strategy Manager Test")
    print("=" * 60)
    
    # List all strategies
    strategies = manager.list_strategies()
    print(f"\nAvailable Strategies: {len(strategies)}")
    for strat in strategies:
        print(f"  - {strat}")
    
    # Get Trick Room strategy details
    print("\nTrick Room Strategy:")
    tr_strategy = manager.get_strategy('Trick Room')
    if tr_strategy:
        print(f"  Description: {tr_strategy['description']}")
        print(f"  Required Moves: {tr_strategy.get('required_moves', [])}")
        print(f"  Speed Range: {tr_strategy.get('speed_range', [])}")
        print(f"  Min Bulk: {tr_strategy.get('min_bulk', 0)}")
    
    # Test Pokemon validation
    test_pokemon = {
        'name': 'Ursaluna',
        'base_stats': {'hp': 130, 'atk': 140, 'def': 105, 'spa': 45, 'spd': 80, 'spe': 50},
        'abilities': ['Guts']
    }
    
    print(f"\nValidating Ursaluna for Trick Room:")
    is_valid = manager.validate_pokemon_for_strategy(test_pokemon, 'Trick Room')
    print(f"  Valid: {is_valid}")

