"""
Battle Result Tracker

Tracks battle results and records them to the performance database.
Integrates with the bot to automatically log battles.

Phase 12 - Team Learning & Adaptation
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional
from .performance_db import PerformanceDatabase


class BattleTracker:
    """Tracks and records battle results for learning."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize battle tracker.
        
        Args:
            db_path: Path to SQLite database, or None for default
        """
        self.db = PerformanceDatabase(db_path)
    
    def record_battle(self, team: List[Dict], strategy: str,
                     result: str, opponent: str = "Unknown",
                     rating_before: int = 1500, rating_after: int = 1500,
                     turns: int = 0, duration_seconds: int = 0,
                     format_name: str = "gen9vgc2026regf",
                     pokemon_used: Optional[List[str]] = None,
                     pokemon_fainted: Optional[List[str]] = None,
                     phase10_score: Optional[float] = None) -> int:
        """
        Record a battle result.
        
        Args:
            team: Team used in battle
            strategy: Strategy used
            result: 'win', 'loss', or 'tie'
            opponent: Opponent name
            rating_before: Rating before battle
            rating_after: Rating after battle
            turns: Number of turns
            duration_seconds: Battle duration
            format_name: Battle format
            pokemon_used: List of Pokemon that battled
            pokemon_fainted: List of Pokemon that fainted
            phase10_score: Team's Phase 10 score
        
        Returns:
            Battle ID
        """
        # Generate team hash
        team_hash = self.hash_team(team)
        
        # Record battle
        battle_id = self.db.record_battle(
            team_hash=team_hash,
            strategy=strategy,
            format_name=format_name,
            opponent=opponent,
            result=result,
            rating_before=rating_before,
            rating_after=rating_after,
            turns=turns,
            duration_seconds=duration_seconds
        )
        
        # Update team performance
        self.db.update_team_performance(
            team_hash=team_hash,
            team_json=json.dumps(team),
            strategy=strategy,
            result=result,
            rating_after=rating_after,
            turns=turns,
            phase10_score=phase10_score
        )
        
        # Update Pokemon performance
        if pokemon_used is None:
            pokemon_used = [p['name'] for p in team]
        
        if pokemon_fainted is None:
            pokemon_fainted = []
        
        for pokemon_name in set(pokemon_used):
            fainted = pokemon_name in pokemon_fainted
            self.db.update_pokemon_performance(
                pokemon_name=pokemon_name,
                result=result,
                fainted=fainted
            )
        
        # Update strategy performance
        self.db.update_strategy_performance(
            strategy=strategy,
            result=result,
            rating_after=rating_after,
            team_hash=team_hash
        )
        
        return battle_id
    
    def hash_team(self, team: List[Dict]) -> str:
        """
        Generate a hash for a team.
        
        Args:
            team: Team to hash
        
        Returns:
            MD5 hash of team composition
        """
        # Create stable team representation
        team_names = sorted([p['name'] for p in team])
        team_str = ','.join(team_names)
        
        # Generate hash
        return hashlib.md5(team_str.encode()).hexdigest()
    
    def get_team_stats(self, team: List[Dict]) -> Optional[Dict]:
        """
        Get performance stats for a specific team.
        
        Args:
            team: Team to look up
        
        Returns:
            Performance stats or None if not found
        """
        team_hash = self.hash_team(team)
        return self.db.get_team_performance(team_hash)
    
    def get_recent_battles(self, limit: int = 10) -> List[Dict]:
        """
        Get recent battles.
        
        Args:
            limit: Number of battles to return
        
        Returns:
            List of battle records
        """
        return self.db.get_recent_battles(limit)
    
    def get_win_rate(self, team: Optional[List[Dict]] = None,
                     strategy: Optional[str] = None,
                     pokemon: Optional[str] = None) -> float:
        """
        Get win rate for team/strategy/Pokemon.
        
        Args:
            team: Specific team (optional)
            strategy: Strategy name (optional)
            pokemon: Pokemon name (optional)
        
        Returns:
            Win rate (0.0 - 1.0)
        """
        if team is not None:
            stats = self.get_team_stats(team)
            if stats:
                return stats.get('win_rate', 0.0)
            return 0.0
        
        elif strategy is not None:
            stats = self.db.get_strategy_performance(strategy)
            if stats:
                return stats.get('win_rate', 0.0)
            return 0.0
        
        elif pokemon is not None:
            stats = self.db.get_pokemon_performance(pokemon)
            if stats:
                return stats.get('win_rate', 0.0)
            return 0.0
        
        else:
            # Overall win rate
            return self.db.get_overall_win_rate()
    
    def clear_data(self):
        """Clear all battle data (use with caution!)."""
        self.db.clear_all_data()


# Example usage
if __name__ == '__main__':
    tracker = BattleTracker()
    
    # Example team
    example_team = [
        {'name': 'Incineroar', 'types': ['Fire', 'Dark']},
        {'name': 'Landorus-Therian', 'types': ['Ground', 'Flying']},
        {'name': 'Rillaboom', 'types': ['Grass']},
        {'name': 'Iron Hands', 'types': ['Fighting', 'Electric']},
        {'name': 'Flutter Mane', 'types': ['Ghost', 'Fairy']},
        {'name': 'Gholdengo', 'types': ['Steel', 'Ghost']}
    ]
    
    # Record a win
    battle_id = tracker.record_battle(
        team=example_team,
        strategy="Balanced",
        result="win",
        opponent="TestOpponent",
        rating_before=1500,
        rating_after=1520,
        turns=15,
        phase10_score=8.2
    )
    
    print(f"Recorded battle {battle_id}")
    
    # Get team stats
    stats = tracker.get_team_stats(example_team)
    if stats:
        print(f"\nTeam Performance:")
        print(f"  Battles: {stats['total_battles']}")
        print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"  Peak Rating: {stats['peak_rating']}")
    
    # Get win rates
    print(f"\nWin Rates:")
    print(f"  Team: {tracker.get_win_rate(team=example_team)*100:.1f}%")
    print(f"  Strategy (Balanced): {tracker.get_win_rate(strategy='Balanced')*100:.1f}%")
    print(f"  Pokemon (Incineroar): {tracker.get_win_rate(pokemon='Incineroar')*100:.1f}%")

