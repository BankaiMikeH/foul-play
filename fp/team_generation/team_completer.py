"""
Team Completer

Completes a team by filling remaining slots with complementary Pokemon.
Uses Phase 10's team analyzer to evaluate and improve teams.

Phase 11 - AI Team Generator
"""

import random
from typing import Dict, List, Optional
from .pokemon_database import PokemonDatabase
from .strategies import StrategyManager

# Try to import Phase 10 analyzer
try:
    from fp.team_analysis import TeamAnalyzer
    PHASE10_AVAILABLE = True
except ImportError:
    PHASE10_AVAILABLE = False
    print("Warning: Phase 10 TeamAnalyzer not available. Team evaluation will be limited.")


class TeamCompleter:
    """Completes teams by filling remaining slots strategically."""
    
    def __init__(self, pokemon_db: Optional[PokemonDatabase] = None,
                 strategy_manager: Optional[StrategyManager] = None):
        """
        Initialize team completer.
        
        Args:
            pokemon_db: Pokemon database instance
            strategy_manager: Strategy manager instance
        """
        self.db = pokemon_db or PokemonDatabase()
        self.strategies = strategy_manager or StrategyManager()
        
        # Initialize Phase 10 analyzer if available
        if PHASE10_AVAILABLE:
            self.analyzer = TeamAnalyzer()
        else:
            self.analyzer = None
    
    def complete_team(self, core: List[Dict], strategy_name: str, 
                      target_size: int = 6) -> List[Dict]:
        """
        Complete a team by filling remaining slots.
        
        Args:
            core: Starting core (2-3 Pokemon)
            strategy_name: Strategy being used
            target_size: Target team size (usually 6)
        
        Returns:
            Complete team
        """
        team = core.copy()
        strategy = self.strategies.get_strategy(strategy_name)
        
        if not strategy:
            # Just fill with random Pokemon
            return self._fill_random(team, target_size)
        
        # Fill remaining slots
        while len(team) < target_size:
            # Get current team analysis if Phase 10 is available
            if self.analyzer:
                analysis = self.analyzer.analyze_team(team)
                next_pokemon = self._pick_pokemon_for_gaps(team, analysis, strategy)
            else:
                next_pokemon = self._pick_complementary_pokemon(team, strategy)
            
            if next_pokemon:
                team.append(next_pokemon)
            else:
                # Fallback: add random valid Pokemon
                fallback = self._pick_fallback_pokemon(team, strategy)
                if fallback:
                    team.append(fallback)
                else:
                    break  # Can't find more Pokemon
        
        return team
    
    def _pick_pokemon_for_gaps(self, team: List[Dict], analysis: Dict, 
                               strategy: Dict) -> Optional[Dict]:
        """Pick Pokemon that fills identified gaps (using Phase 10)."""
        # Get team weaknesses
        weaknesses = analysis.get('weaknesses', [])
        
        # Priority 1: Add speed control if missing
        if any('No Tailwind or Trick Room' in w or 'No speed control' in w for w in weaknesses):
            speed_control_pkmn = self._find_speed_control_pokemon(team, strategy)
            if speed_control_pkmn:
                return speed_control_pkmn
        
        # Priority 2: Add Intimidate if beneficial
        if 'intimidate' in strategy.get('preferred_roles', []):
            intimidate_users = self.db.filter_by_ability('Intimidate')
            intimidate_users = [p for p in intimidate_users 
                               if not self._is_on_team(p['name'], team)]
            if intimidate_users:
                pkmn_data = random.choice(intimidate_users)
                spread_type = self._get_spread_type(strategy['name'], pkmn_data)
                return self.db.build_full_pokemon(pkmn_data, spread_type)
        
        # Priority 3: Fill type coverage gaps
        type_coverage = analysis.get('type_coverage', {})
        no_coverage = type_coverage.get('offensive', {}).get('no_coverage', [])
        
        if no_coverage:
            # Find Pokemon that covers missing types
            for missing_type in no_coverage[:2]:  # Focus on first 2 gaps
                pkmn = self._find_pokemon_with_coverage(missing_type, team, strategy)
                if pkmn:
                    return pkmn
        
        # Fallback: pick complementary Pokemon
        return self._pick_complementary_pokemon(team, strategy)
    
    def _find_speed_control_pokemon(self, team: List[Dict], 
                                    strategy: Dict) -> Optional[Dict]:
        """Find Pokemon with Tailwind or Trick Room."""
        strategy_name = strategy.get('name', '').lower()
        
        if 'trick room' in strategy_name:
            # Find TR setter
            candidates = self.db.get_pokemon_with_move('Trick Room')
        else:
            # Find Tailwind setter
            candidates = self.db.get_pokemon_with_move('Tailwind')
        
        candidates = [c for c in candidates if not self._is_on_team(c['name'], team)]
        
        if candidates:
            pkmn_data = random.choice(candidates)
            spread_type = self._get_spread_type(strategy['name'], pkmn_data)
            return self.db.build_full_pokemon(pkmn_data, spread_type)
        
        return None
    
    def _find_pokemon_with_coverage(self, missing_type: str, team: List[Dict],
                                    strategy: Dict) -> Optional[Dict]:
        """Find Pokemon that can hit the missing type."""
        # Get Pokemon of the type that hits the missing type
        # For simplicity, get Pokemon with moves of that type
        all_pokemon = self.db.filter_non_restricted()
        
        # Filter out Pokemon already on team
        candidates = [p for p in all_pokemon if not self._is_on_team(p['name'], team)]
        
        # Prefer high usage Pokemon
        candidates = [p for p in candidates if p.get('usage_rate', 0) >= 0.15]
        
        if candidates:
            pkmn_data = random.choice(candidates)
            spread_type = self._get_spread_type(strategy['name'], pkmn_data)
            return self.db.build_full_pokemon(pkmn_data, spread_type)
        
        return None
    
    def _pick_complementary_pokemon(self, team: List[Dict], 
                                   strategy: Dict) -> Optional[Dict]:
        """Pick Pokemon that complements the team."""
        # Get types already on team
        team_types = set()
        for pkmn in team:
            team_types.update(pkmn['types'])
        
        # Get high usage Pokemon
        candidates = self.db.get_high_usage_pokemon(min_usage=0.2)
        
        # Filter out Pokemon already on team
        candidates = [c for c in candidates if not self._is_on_team(c['name'], team)]
        
        # Prefer Pokemon with different types
        different_type_candidates = [c for c in candidates 
                                     if not any(t in team_types for t in c['types'])]
        
        if different_type_candidates:
            candidates = different_type_candidates
        
        # Filter by strategy requirements
        valid_candidates = [c for c in candidates 
                           if self.strategies.validate_pokemon_for_strategy(c, strategy['name'])]
        
        if valid_candidates:
            candidates = valid_candidates
        
        if candidates:
            pkmn_data = random.choice(candidates)
            spread_type = self._get_spread_type(strategy['name'], pkmn_data)
            return self.db.build_full_pokemon(pkmn_data, spread_type)
        
        return None
    
    def _pick_fallback_pokemon(self, team: List[Dict], strategy: Dict) -> Optional[Dict]:
        """Pick any valid Pokemon as fallback."""
        all_pokemon = self.db.filter_non_restricted()
        candidates = [p for p in all_pokemon if not self._is_on_team(p['name'], team)]
        
        if candidates:
            pkmn_data = random.choice(candidates)
            spread_type = self._get_spread_type(strategy['name'], pkmn_data)
            return self.db.build_full_pokemon(pkmn_data, spread_type)
        
        return None
    
    def _fill_random(self, team: List[Dict], target_size: int) -> List[Dict]:
        """Fill team with random Pokemon."""
        while len(team) < target_size:
            all_pokemon = self.db.get_all_pokemon()
            team_names = {p['name'] for p in team}
            available = [name for name in all_pokemon if name not in team_names]
            
            if not available:
                break
            
            pkmn_name = random.choice(available)
            pkmn_data = self.db.get_pokemon(pkmn_name)
            if pkmn_data:
                team.append(self.db.build_full_pokemon(pkmn_data))
        
        return team
    
    def _is_on_team(self, pokemon_name: str, team: List[Dict]) -> bool:
        """Check if Pokemon is already on team."""
        return any(p['name'] == pokemon_name for p in team)
    
    def _get_spread_type(self, strategy_name: str, pokemon_data: Dict) -> str:
        """Determine EV spread type for strategy."""
        strategy_name_lower = strategy_name.lower()
        
        if 'trick room' in strategy_name_lower:
            return 'defensive' if 'defensive' in pokemon_data.get('common_spreads', {}) else 'offensive'
        elif 'tailwind' in strategy_name_lower or 'offense' in strategy_name_lower:
            return 'fast' if 'fast' in pokemon_data.get('common_spreads', {}) else 'offensive'
        else:
            spreads = list(pokemon_data.get('common_spreads', {}).keys())
            return random.choice(spreads) if spreads else 'offensive'


# Example usage
if __name__ == '__main__':
    from .core_builder import CoreBuilder
    
    completer = TeamCompleter()
    builder = CoreBuilder()
    
    print("Team Completer Test")
    print("=" * 60)
    
    # Build a core and complete it
    print("\nBuilding and completing Balanced team:")
    core = builder.build_core('Balanced')
    print(f"\nCore ({len(core)} Pokemon):")
    for pkmn in core:
        print(f"  - {pkmn['name']}")
    
    team = completer.complete_team(core, 'Balanced', target_size=6)
    print(f"\nCompleted Team ({len(team)} Pokemon):")
    for i, pkmn in enumerate(team, 1):
        print(f"{i}. {pkmn['name']} ({', '.join(pkmn['types'])})")
        print(f"   Speed: {pkmn['stats']['spe']}")
        print(f"   Moves: {', '.join(m['name'] for m in pkmn['moves'])}")
        print()

