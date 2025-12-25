#!/usr/bin/env python3
"""
Battle Result Recorder

CLI tool to manually record battle results to the learning database.
Used for tracking performance of custom teams.

Phase 12 - Team Learning & Adaptation

Usage:
    python record_battle.py --team my_team.json --result win --rating 1520
    python record_battle.py --team my_team.json --result loss --rating 1480 --opponent "BankaiMike"
    python record_battle.py --auto  # Auto-detect from last battle log
"""

import argparse
import json
import os
from fp.team_learning import BattleTracker


def load_team(team_file: str) -> list:
    """Load team from JSON file."""
    if not os.path.exists(team_file):
        raise FileNotFoundError(f"Team file not found: {team_file}")
    
    with open(team_file, 'r') as f:
        data = json.load(f)
    
    # Handle different team file formats
    if isinstance(data, dict) and 'pokemon' in data:
        return data['pokemon']
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Invalid team file format")


def record_battle_manual(team_file: str, result: str, rating_after: int,
                         rating_before: int = None, opponent: str = "Unknown",
                         strategy: str = "Unknown", turns: int = 0,
                         format_name: str = "gen9vgc2026regf",
                         db_path: str = None):
    """Record a battle manually."""
    # Load team
    team = load_team(team_file)
    
    # Auto-detect strategy from filename if not provided
    if strategy == "Unknown":
        if "balanced" in team_file.lower():
            strategy = "Balanced"
        elif "trick_room" in team_file.lower() or "tr" in team_file.lower():
            strategy = "Trick Room"
        elif "tailwind" in team_file.lower():
            strategy = "Tailwind"
        elif "rain" in team_file.lower():
            strategy = "Rain"
        elif "sun" in team_file.lower():
            strategy = "Sun"
    
    # Estimate rating before if not provided
    if rating_before is None:
        if result == "win":
            rating_before = rating_after - 20
        elif result == "loss":
            rating_before = rating_after + 20
        else:
            rating_before = rating_after
    
    # Initialize tracker
    tracker = BattleTracker(db_path)
    
    # Record battle
    battle_id = tracker.record_battle(
        team=team,
        strategy=strategy,
        result=result,
        opponent=opponent,
        rating_before=rating_before,
        rating_after=rating_after,
        turns=turns,
        format_name=format_name
    )
    
    print(f"\n✅ Battle recorded successfully!")
    print(f"   Battle ID: {battle_id}")
    print(f"   Result: {result.upper()}")
    print(f"   Rating: {rating_before} → {rating_after} ({rating_after - rating_before:+d})")
    print(f"   Strategy: {strategy}")
    print(f"   Opponent: {opponent}")
    
    # Show updated team stats
    team_stats = tracker.get_team_stats(team)
    if team_stats:
        print(f"\n📊 Updated Team Stats:")
        print(f"   Total Battles: {team_stats['total_battles']}")
        print(f"   Win Rate: {team_stats['win_rate']*100:.1f}%")
        print(f"   Peak Rating: {team_stats['peak_rating']}")


def main():
    parser = argparse.ArgumentParser(
        description='Record a battle result to the learning database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record a win
  python record_battle.py --team my_team.json --result win --rating 1520
  
  # Record a loss with opponent name
  python record_battle.py --team my_team.json --result loss --rating 1480 --opponent "BankaiMike"
  
  # Record with full details
  python record_battle.py --team balanced_team.json --result win \\
      --rating-before 1500 --rating-after 1520 \\
      --opponent "TestPlayer" --turns 15 --strategy "Balanced"
        """
    )
    
    parser.add_argument('--team', type=str, required=True,
                       help='Path to team JSON file')
    parser.add_argument('--result', type=str, required=True,
                       choices=['win', 'loss', 'tie'],
                       help='Battle result')
    parser.add_argument('--rating', '--rating-after', type=int, dest='rating_after',
                       help='Rating after battle')
    parser.add_argument('--rating-before', type=int,
                       help='Rating before battle (auto-estimated if not provided)')
    parser.add_argument('--opponent', type=str, default="Unknown",
                       help='Opponent name')
    parser.add_argument('--strategy', type=str, default="Unknown",
                       help='Strategy used (auto-detected from filename if not provided)')
    parser.add_argument('--turns', type=int, default=0,
                       help='Number of turns')
    parser.add_argument('--format', type=str, default="gen9vgc2026regf",
                       help='Battle format')
    parser.add_argument('--db', type=str,
                       help='Path to custom database file')
    
    args = parser.parse_args()
    
    # Validate rating
    if args.rating_after is None:
        parser.error("--rating (or --rating-after) is required")
    
    # Record battle
    try:
        record_battle_manual(
            team_file=args.team,
            result=args.result,
            rating_after=args.rating_after,
            rating_before=args.rating_before,
            opponent=args.opponent,
            strategy=args.strategy,
            turns=args.turns,
            format_name=args.format,
            db_path=args.db
        )
    except Exception as e:
        print(f"\n❌ Error recording battle: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

