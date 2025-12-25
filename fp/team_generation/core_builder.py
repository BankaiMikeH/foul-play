"""
Core Builder

Builds 2-3 Pokemon synergistic cores for team generation.
Uses Phase 10's synergy scorer to find Pokemon that work well together.

Phase 11 - AI Team Generator
"""

import random
from typing import Dict, List, Optional, Tuple
from .pokemon_database import PokemonDatabase
from .strategies import StrategyManager


class CoreBuilder:
    """Builds synergistic Pokemon cores for team generation."""
    
    def __init__(self, pokemon_db: Optional[PokemonDatabase] = None,
                 strategy_manager: Optional[StrategyManager] = None):
        """
        Initialize core builder.
        
        Args:
            pokemon_db: Pokemon database instance
            strategy_manager: Strategy manager instance
        """
        self.db = pokemon_db or PokemonDatabase()
        self.strategies = strategy_manager or StrategyManager()
    
    def build_core(self, strategy_name: str, max_attempts: int = 20) -> List[Dict]:
        """
        Build a 2-3 Pokemon core for a strategy.
        
        Args:
            strategy_name: Name of strategy to build for
            max_attempts: Maximum attempts to find good core
        
        Returns:
            List of 2-3 Pokemon forming a core
        """
        strategy = self.strategies.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # Try sample cores first
        sample_cores = strategy.get('sample_cores', [])
        if sample_cores:
            core_names = random.choice(sample_cores)
            core = []
            for name in core_names:
                pkmn_data = self.db.get_pokemon(name)
                if pkmn_data:
                    # Determine spread type based on strategy
                    spread_type = self._get_spread_for_strategy(strategy_name, pkmn_data)
                    core.append(self.db.build_full_pokemon(pkmn_data, spread_type))
            
            if len(core) >= 2:
                return core
        
        # Build core from scratch
        for attempt in range(max_attempts):
            core = self._build_core_from_scratch(strategy)
            if core and len(core) >= 2:
                return core
        
        # Fallback: return best Pokemon for strategy
        return self._build_fallback_core(strategy)
    
    def _build_core_from_scratch(self, strategy: Dict) -> List[Dict]:
        """Build a core from scratch based on strategy requirements."""
        core = []
        
        # 1. Pick main Pokemon (often a restricted or key Pokemon)
        main_pokemon = self._pick_main_pokemon(strategy)
        if main_pokemon:
            spread_type = self._get_spread_for_strategy(strategy['name'], main_pokemon)
            core.append(self.db.build_full_pokemon(main_pokemon, spread_type))
        
        # 2. Pick support/synergy Pokemon
        if core:
            support_pokemon = self._pick_support_for_core(core, strategy)
            if support_pokemon:
                spread_type = self._get_spread_for_strategy(strategy['name'], support_pokemon)
                core.append(self.db.build_full_pokemon(support_pokemon, spread_type))
        
        return core
    
    def _pick_main_pokemon(self, strategy: Dict) -> Optional[Dict]:
        """Pick the main Pokemon for a core."""
        strategy_name = strategy['name'].lower()
        
        # Strategy-specific main Pokemon selection
        if 'trick room' in strategy_name:
            # Pick a TR setter or slow attacker
            candidates = self.db.get_pokemon_with_move('Trick Room')
            if not candidates:
                candidates = self.db.filter_by_speed(min_speed=0, max_speed=70)
        
        elif 'tailwind' in strategy_name:
            # Pick a Tailwind setter
            candidates = self.db.get_pokemon_with_move('Tailwind')
        
        elif 'grassy' in strategy_name:
            # Pick Grassy Surge user
            candidates = self.db.filter_by_ability('Grassy Surge')
        
        elif 'hyper offense' in strategy_name:
            # Pick fastest restricted
            restricted = self.db.filter_restricted()
            candidates = sorted(restricted, 
                              key=lambda p: p['base_stats']['spe'], 
                              reverse=True)[:3]
        
        else:
            # Pick high usage Pokemon
            candidates = self.db.get_high_usage_pokemon(min_usage=0.4)
        
        # Return random candidate
        if candidates:
            return random.choice(candidates)
        
        return None
    
    def _pick_support_for_core(self, core: List[Dict], strategy: Dict) -> Optional[Dict]:
        """Pick a support Pokemon that synergizes with the core."""
        if not core:
            return None
        
        main_pokemon_name = core[0]['name']
        strategy_name = strategy['name'].lower()
        
        # Strategy-specific support selection
        if 'trick room' in strategy_name:
            # Pick slow attacker for TR team
            candidates = self.db.filter_by_speed(min_speed=0, max_speed=70)
            candidates = [c for c in candidates 
                         if c['name'] != main_pokemon_name and
                         c['base_stats']['atk'] >= 120 or c['base_stats']['spa'] >= 120]
        
        elif 'tailwind' in strategy_name:
            # Pick fast sweeper
            candidates = self.db.filter_by_speed(min_speed=100, max_speed=255)
            candidates = [c for c in candidates if c['name'] != main_pokemon_name]
        
        elif 'grassy' in strategy_name:
            # Pick Pokemon with Grassy Glide
            candidates = self.db.get_pokemon_with_move('Grassy Glide')
            candidates = [c for c in candidates if c['name'] != main_pokemon_name]
        
        elif 'intimidate' in strategy_name:
            # Pick another Intimidate user
            candidates = self.db.filter_by_ability('Intimidate')
            candidates = [c for c in candidates if c['name'] != main_pokemon_name]
        
        else:
            # Pick complementary type
            main_types = core[0]['types']
            candidates = self.db.get_high_usage_pokemon(min_usage=0.3)
            # Filter out Pokemon with same types
            candidates = [c for c in candidates 
                         if c['name'] != main_pokemon_name and
                         not any(t in main_types for t in c['types'])]
        
        if candidates:
            return random.choice(candidates)
        
        return None
    
    def _build_fallback_core(self, strategy: Dict) -> List[Dict]:
        """Build a fallback core if other methods fail."""
        # Get top 2 Pokemon for the strategy
        all_pokemon = self.db.get_high_usage_pokemon(min_usage=0.3)
        
        # Filter by strategy
        valid_pokemon = [p for p in all_pokemon 
                        if self.strategies.validate_pokemon_for_strategy(p, strategy['name'])]
        
        if not valid_pokemon:
            valid_pokemon = all_pokemon
        
        # Pick 2 random
        core_data = random.sample(valid_pokemon, min(2, len(valid_pokemon)))
        
        # Build full Pokemon
        core = []
        for pkmn_data in core_data:
            spread_type = self._get_spread_for_strategy(strategy['name'], pkmn_data)
            core.append(self.db.build_full_pokemon(pkmn_data, spread_type))
        
        return core
    
    def _get_spread_for_strategy(self, strategy_name: str, pokemon_data: Dict) -> str:
        """Determine which EV spread to use based on strategy."""
        strategy_name_lower = strategy_name.lower()
        
        if 'trick room' in strategy_name_lower:
            # Prefer defensive or offensive spreads (not fast)
            if 'defensive' in pokemon_data.get('common_spreads', {}):
                return 'defensive'
            return 'offensive'
        
        elif 'tailwind' in strategy_name_lower or 'hyper offense' in strategy_name_lower:
            # Prefer fast/offensive spreads
            if 'fast' in pokemon_data.get('common_spreads', {}):
                return 'fast'
            return 'offensive'
        
        elif 'balanced' in strategy_name_lower:
            # Mix of spreads
            spreads = list(pokemon_data.get('common_spreads', {}).keys())
            return random.choice(spreads) if spreads else 'offensive'
        
        else:
            # Default to offensive
            return 'offensive'
    
    def find_best_cores(self, strategy_name: str, count: int = 5) -> List[List[Dict]]:
        """
        Generate multiple cores and return the best ones.
        
        Args:
            strategy_name: Strategy to build for
            count: Number of cores to generate
        
        Returns:
            List of cores, sorted by quality
        """
        cores = []
        
        for _ in range(count):
            try:
                core = self.build_core(strategy_name)
                if core and len(core) >= 2:
                    cores.append(core)
            except Exception as e:
                print(f"Error building core: {e}")
                continue
        
        # TODO: Score cores using Phase 10's synergy scorer
        # For now, just return them
        return cores


# Example usage
if __name__ == '__main__':
    builder = CoreBuilder()
    
    print("Core Builder Test")
    print("=" * 60)
    
    # Build a Trick Room core
    print("\nBuilding Trick Room Core:")
    tr_core = builder.build_core('Trick Room')
    for i, pkmn in enumerate(tr_core, 1):
        print(f"\n{i}. {pkmn['name']}")
        print(f"   Types: {', '.join(pkmn['types'])}")
        print(f"   Speed: {pkmn['stats']['spe']}")
        print(f"   Moves: {', '.join(m['name'] for m in pkmn['moves'])}")
    
    # Build a Tailwind core
    print("\n" + "=" * 60)
    print("\nBuilding Tailwind Core:")
    tw_core = builder.build_core('Tailwind')
    for i, pkmn in enumerate(tw_core, 1):
        print(f"\n{i}. {pkmn['name']}")
        print(f"   Types: {', '.join(pkmn['types'])}")
        print(f"   Speed: {pkmn['stats']['spe']}")
        print(f"   Moves: {', '.join(m['name'] for m in pkmn['moves'])}")
    
    # Build a Grassy Terrain core
    print("\n" + "=" * 60)
    print("\nBuilding Grassy Terrain Core:")
    grassy_core = builder.build_core('Grassy Terrain')
    for i, pkmn in enumerate(grassy_core, 1):
        print(f"\n{i}. {pkmn['name']}")
        print(f"   Types: {', '.join(pkmn['types'])}")
        print(f"   Ability: {pkmn['ability']}")
        print(f"   Moves: {', '.join(m['name'] for m in pkmn['moves'])}")

