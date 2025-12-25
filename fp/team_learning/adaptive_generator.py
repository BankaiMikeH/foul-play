"""
Adaptive Team Generator

Generates teams using learned performance data to make better decisions.
Adjusts Pokemon selection and team building based on win rates.

Phase 12 - Team Learning & Adaptation
"""

from typing import Dict, List, Optional
from ..team_generation.team_generator import TeamGenerator
from ..team_generation.pokemon_database import PokemonDatabase
from .performance_db import PerformanceDatabase
import random


class AdaptiveTeamGenerator(TeamGenerator):
    """
    Team generator that learns from battle history.
    
    Adapts generation based on:
    - Pokemon win rates
    - Strategy success rates
    - Synergistic pair performance
    """
    
    def __init__(self, pokemon_db: Optional[PokemonDatabase] = None,
                 perf_db: Optional[PerformanceDatabase] = None,
                 learning_rate: float = 0.5):
        """
        Initialize adaptive generator.
        
        Args:
            pokemon_db: Pokemon database
            perf_db: Performance database for learning
            learning_rate: How much to weight learned data (0.0-1.0)
                          0.0 = ignore learning, 1.0 = fully trust learning
        """
        super().__init__(pokemon_db)
        self.perf_db = perf_db if perf_db else PerformanceDatabase()
        self.learning_rate = learning_rate
        
        # Cache for performance data
        self._pokemon_weights = None
        self._successful_pairs = None
        self._strategy_preferences = None
    
    def generate(self, strategy: str = "Balanced", 
                use_learning: bool = True) -> Dict:
        """
        Generate a team with adaptive learning.
        
        Args:
            strategy: Strategy to use
            use_learning: Whether to use learned data
        
        Returns:
            Generated team with metadata
        """
        if use_learning:
            self._update_learning_cache()
        
        # Get base team from parent generator
        base_team = super().generate(strategy)
        
        if not use_learning or not self._has_sufficient_data():
            return base_team
        
        # Adapt team based on learned data
        adapted_team = self._adapt_team(base_team, strategy)
        
        return adapted_team
    
    def _update_learning_cache(self):
        """Update cached learning data."""
        self._pokemon_weights = self._calculate_pokemon_weights()
        self._successful_pairs = self._get_successful_pairs()
        self._strategy_preferences = self._get_strategy_preferences()
    
    def _has_sufficient_data(self, min_battles: int = 10) -> bool:
        """Check if we have enough data to learn from."""
        stats = self.perf_db.get_statistics()
        return stats['total_battles'] >= min_battles
    
    def _calculate_pokemon_weights(self) -> Dict[str, float]:
        """
        Calculate selection weights for Pokemon based on performance.
        
        Returns:
            Dict mapping Pokemon name to weight (0.0-2.0)
        """
        weights = {}
        
        # Get all Pokemon with performance data
        cursor = self.perf_db.conn.cursor()
        cursor.execute("""
            SELECT pokemon_name, win_rate, total_battles
            FROM pokemon_performance
            WHERE total_battles >= 3
        """)
        
        for row in cursor.fetchall():
            name = row['pokemon_name']
            win_rate = row['win_rate']
            battles = row['total_battles']
            
            # Weight based on win rate
            # 0.5 win rate = 1.0 weight (neutral)
            # 0.7 win rate = 1.4 weight (preferred)
            # 0.3 win rate = 0.6 weight (avoided)
            base_weight = 0.5 + win_rate
            
            # Confidence multiplier (more battles = more confidence)
            confidence = min(battles / 20.0, 1.0)
            
            # Combine with learning rate
            weight = 1.0 + (base_weight - 1.0) * confidence * self.learning_rate
            
            weights[name] = max(0.1, min(2.0, weight))  # Clamp to 0.1-2.0
        
        return weights
    
    def _get_successful_pairs(self, min_battles: int = 3) -> List[tuple]:
        """
        Get Pokemon pairs that have been successful together.
        
        Returns:
            List of (pokemon1, pokemon2, win_rate) tuples
        """
        pairs = []
        
        # Get all successful teams
        cursor = self.perf_db.conn.cursor()
        cursor.execute("""
            SELECT team_json, win_rate
            FROM team_performance
            WHERE total_battles >= ? AND win_rate >= 0.55
        """, (min_battles,))
        
        import json
        from itertools import combinations
        
        pair_stats = {}
        
        for row in cursor.fetchall():
            team_data = json.loads(row['team_json'])
            pokemon_names = [p['name'] for p in team_data]
            win_rate = row['win_rate']
            
            # Record all pairs
            for pair in combinations(sorted(pokemon_names), 2):
                pair_key = tuple(sorted(pair))
                
                if pair_key not in pair_stats:
                    pair_stats[pair_key] = {'total_wr': 0.0, 'count': 0}
                
                pair_stats[pair_key]['total_wr'] += win_rate
                pair_stats[pair_key]['count'] += 1
        
        # Calculate average win rates
        for pair, stats in pair_stats.items():
            avg_wr = stats['total_wr'] / stats['count']
            pairs.append((pair[0], pair[1], avg_wr))
        
        # Sort by win rate
        pairs.sort(key=lambda x: -x[2])
        
        return pairs[:50]  # Top 50 pairs
    
    def _get_strategy_preferences(self) -> Dict[str, float]:
        """
        Get strategy preferences based on performance.
        
        Returns:
            Dict mapping strategy name to weight
        """
        preferences = {}
        
        strategies = self.perf_db.get_top_strategies()
        
        for strat in strategies:
            name = strat['strategy']
            win_rate = strat['win_rate']
            
            # Weight based on win rate
            weight = 0.5 + win_rate
            preferences[name] = weight
        
        return preferences
    
    def _adapt_team(self, base_team: Dict, strategy: str) -> Dict:
        """
        Adapt base team using learned data.
        
        Args:
            base_team: Base team from standard generator
            strategy: Strategy used
        
        Returns:
            Adapted team
        """
        team = base_team['pokemon'].copy()
        
        # Try to improve team by replacing low-performing Pokemon
        improvements_made = 0
        max_improvements = 2  # Don't change too much
        
        for i, pokemon in enumerate(team):
            if improvements_made >= max_improvements:
                break
            
            name = pokemon['name']
            
            # Check if this Pokemon has poor performance
            weight = self._pokemon_weights.get(name, 1.0)
            
            if weight < 0.7:  # Poor performer
                # Try to find a better replacement
                replacement = self._find_better_replacement(
                    pokemon, team, strategy
                )
                
                if replacement:
                    team[i] = replacement
                    improvements_made += 1
        
        # Try to incorporate successful pairs
        if self._successful_pairs and random.random() < 0.3:  # 30% chance
            team = self._incorporate_successful_pair(team)
        
        # Rebuild team dict
        return {
            'pokemon': team,
            'strategy': strategy,
            'adapted': True,
            'improvements_made': improvements_made
        }
    
    def _find_better_replacement(self, pokemon: Dict, current_team: List[Dict],
                                 strategy: str) -> Optional[Dict]:
        """
        Find a better replacement for a Pokemon.
        
        Args:
            pokemon: Pokemon to replace
            current_team: Current team
            strategy: Strategy being used
        
        Returns:
            Replacement Pokemon or None
        """
        # Get Pokemon of same type/role
        candidates = []
        
        for candidate in self.pokemon_db.get_all_pokemon():
            # Skip if already on team
            if any(p['name'] == candidate['name'] for p in current_team):
                continue
            
            # Check if similar (shares a type)
            if not any(t in candidate.get('types', []) for t in pokemon.get('types', [])):
                continue
            
            # Check if better performance
            weight = self._pokemon_weights.get(candidate['name'], 1.0)
            if weight > 1.2:  # Significantly better
                candidates.append((candidate, weight))
        
        if candidates:
            # Select best candidate
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        
        return None
    
    def _incorporate_successful_pair(self, team: List[Dict]) -> List[Dict]:
        """
        Try to incorporate a successful pair into the team.
        
        Args:
            team: Current team
        
        Returns:
            Modified team
        """
        current_names = {p['name'] for p in team}
        
        # Find pairs where one Pokemon is already on team
        for pkmn1, pkmn2, win_rate in self._successful_pairs:
            if win_rate < 0.65:  # Only high-performing pairs
                break
            
            # If one is on team and the other isn't
            if pkmn1 in current_names and pkmn2 not in current_names:
                # Try to add pkmn2
                partner = self.pokemon_db.get_pokemon(pkmn2)
                if partner:
                    # Replace lowest-performing Pokemon
                    worst_idx = self._find_worst_pokemon_index(team)
                    if worst_idx is not None:
                        team[worst_idx] = partner
                        return team
            
            elif pkmn2 in current_names and pkmn1 not in current_names:
                # Try to add pkmn1
                partner = self.pokemon_db.get_pokemon(pkmn1)
                if partner:
                    worst_idx = self._find_worst_pokemon_index(team)
                    if worst_idx is not None:
                        team[worst_idx] = partner
                        return team
        
        return team
    
    def _find_worst_pokemon_index(self, team: List[Dict]) -> Optional[int]:
        """Find index of worst-performing Pokemon on team."""
        worst_weight = 2.0
        worst_idx = None
        
        for i, pokemon in enumerate(team):
            weight = self._pokemon_weights.get(pokemon['name'], 1.0)
            if weight < worst_weight:
                worst_weight = weight
                worst_idx = i
        
        return worst_idx if worst_weight < 0.8 else None
    
    def get_learning_report(self) -> Dict:
        """
        Get a report on what the generator has learned.
        
        Returns:
            Learning report
        """
        if not self._has_sufficient_data():
            return {
                'status': 'insufficient_data',
                'battles_needed': 10 - self.perf_db.get_statistics()['total_battles']
            }
        
        self._update_learning_cache()
        
        # Top Pokemon
        top_pokemon = sorted(
            self._pokemon_weights.items(),
            key=lambda x: -x[1]
        )[:10]
        
        # Worst Pokemon
        worst_pokemon = sorted(
            self._pokemon_weights.items(),
            key=lambda x: x[1]
        )[:10]
        
        # Top pairs
        top_pairs = self._successful_pairs[:10]
        
        # Strategy preferences
        top_strategies = sorted(
            self._strategy_preferences.items(),
            key=lambda x: -x[1]
        )
        
        return {
            'status': 'active',
            'total_battles': self.perf_db.get_statistics()['total_battles'],
            'learning_rate': self.learning_rate,
            'top_pokemon': [{'name': name, 'weight': weight} 
                           for name, weight in top_pokemon],
            'worst_pokemon': [{'name': name, 'weight': weight}
                             for name, weight in worst_pokemon],
            'top_pairs': [{'pokemon_1': p1, 'pokemon_2': p2, 'win_rate': wr}
                         for p1, p2, wr in top_pairs],
            'strategy_preferences': [{'strategy': name, 'weight': weight}
                                    for name, weight in top_strategies]
        }


# Example usage
if __name__ == '__main__':
    print("Adaptive Team Generator Example")
    print("=" * 60)
    
    # Initialize generator
    generator = AdaptiveTeamGenerator(learning_rate=0.7)
    
    # Check if we have enough data
    if not generator._has_sufficient_data():
        print("\n⚠️  Not enough battle data yet.")
        print("   Need at least 10 battles to enable learning.")
        print("\n   Generating standard team instead...")
        team_data = generator.generate("Balanced", use_learning=False)
    else:
        print("\n✅ Sufficient data for adaptive generation!")
        
        # Get learning report
        report = generator.get_learning_report()
        print(f"\n📊 Learning Report:")
        print(f"   Total Battles: {report['total_battles']}")
        print(f"   Learning Rate: {report['learning_rate']}")
        
        if report.get('top_pokemon'):
            print(f"\n   Top Pokemon:")
            for pkmn in report['top_pokemon'][:5]:
                print(f"      {pkmn['name']}: {pkmn['weight']:.2f}x")
        
        # Generate adaptive team
        print(f"\n🧠 Generating adaptive Balanced team...")
        team_data = generator.generate("Balanced", use_learning=True)
    
    print(f"\n🏆 Generated Team:")
    for i, pokemon in enumerate(team_data['pokemon'], 1):
        print(f"   {i}. {pokemon['name']}")
    
    if team_data.get('adapted'):
        print(f"\n   ✨ Team was adapted using learned data!")
        print(f"   Improvements made: {team_data.get('improvements_made', 0)}")

