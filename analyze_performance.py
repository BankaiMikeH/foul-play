#!/usr/bin/env python3
"""
Performance Analysis CLI

Command-line tool for analyzing battle performance data and getting
team recommendations based on learned patterns.

Phase 12 - Team Learning & Adaptation

Usage:
    python analyze_performance.py --summary
    python analyze_performance.py --recommend
    python analyze_performance.py --meta
    python analyze_performance.py --pokemon "Incineroar"
    python analyze_performance.py --strategy "Balanced"
    python analyze_performance.py --export report.json
"""

import argparse
import json
from fp.team_learning import BattleTracker, PerformanceDatabase, TeamRecommender
from fp.team_learning.meta_analyzer import MetaAnalyzer


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_summary(tracker: BattleTracker):
    """Print overall performance summary."""
    print_header("📊 OVERALL PERFORMANCE SUMMARY")
    
    stats = tracker.db.get_statistics()
    
    print(f"\n{'Total Battles:':<25} {stats['total_battles']}")
    print(f"{'Wins:':<25} {stats['wins']}")
    print(f"{'Losses:':<25} {stats['losses']}")
    print(f"{'Ties:':<25} {stats['ties']}")
    print(f"{'Win Rate:':<25} {stats['win_rate']*100:.1f}%")
    print(f"{'Unique Teams Used:':<25} {stats['unique_teams']}")
    print(f"{'Average Rating:':<25} {stats['avg_rating']}")
    
    # Recent battles
    print("\n" + "-"*70)
    print("Recent Battles:")
    print("-"*70)
    
    recent = tracker.get_recent_battles(10)
    
    if not recent:
        print("  No battles recorded yet.")
        return
    
    for battle in recent[:5]:
        timestamp = battle['timestamp'][:19].replace('T', ' ')
        result_symbol = "✅" if battle['result'] == 'win' else "❌" if battle['result'] == 'loss' else "➖"
        rating_change = f"{battle['rating_change']:+d}" if battle['rating_change'] else "+0"
        
        print(f"  {result_symbol} {timestamp} | {battle['strategy']:<15} | "
              f"Rating: {battle['rating_after']} ({rating_change}) | "
              f"vs {battle['opponent']}")


def print_meta_analysis(analyzer: MetaAnalyzer, min_battles: int = 5):
    """Print meta analysis."""
    print_header("🎯 META ANALYSIS")
    
    report = analyzer.get_meta_report(min_battles=min_battles)
    
    # Best strategy
    if report['best_strategy']:
        strat = report['best_strategy']
        print(f"\n🥇 Best Strategy: {strat['name']}")
        print(f"   Win Rate: {strat['win_rate']*100:.1f}%")
        print(f"   Battles: {strat['total_battles']}")
    
    # Top Pokemon
    if report['best_pokemon']:
        print(f"\n⭐ Top Pokemon:")
        for i, pkmn in enumerate(report['best_pokemon'][:10], 1):
            stars = "★" * min(5, int(pkmn['win_rate'] * 10))
            print(f"   {i:2}. {pkmn['name']:<20} {stars:<5} "
                  f"WR: {pkmn['win_rate']*100:5.1f}% | "
                  f"Battles: {pkmn['total_battles']:3} | "
                  f"Survival: {pkmn['survival_rate']*100:5.1f}%")
    
    # Worst Pokemon
    if report['worst_pokemon']:
        print(f"\n⚠️  Struggling Pokemon:")
        for i, pkmn in enumerate(report['worst_pokemon'][:5], 1):
            print(f"   {i}. {pkmn['name']:<20} "
                  f"WR: {pkmn['win_rate']*100:5.1f}% | "
                  f"Battles: {pkmn['total_battles']:3}")
    
    # Top teams
    if report['top_teams']:
        print(f"\n🏆 Top Teams:")
        for i, team in enumerate(report['top_teams'][:3], 1):
            print(f"\n   {i}. {team['strategy']} Team:")
            print(f"      Pokemon: {', '.join(team['pokemon'])}")
            print(f"      Win Rate: {team['win_rate']*100:.1f}% ({team['total_battles']} battles)")
            print(f"      Peak Rating: {team['peak_rating']}")
            if team['phase10_score']:
                print(f"      Synergy Score: {team['phase10_score']:.1f}/10")
    
    # Strategy breakdown
    if report['strategy_breakdown']:
        print(f"\n📈 Strategy Breakdown:")
        for strat in report['strategy_breakdown']:
            print(f"   {strat['strategy']:<20} "
                  f"WR: {strat['win_rate']*100:5.1f}% | "
                  f"Battles: {strat['total_battles']:3} | "
                  f"Avg Rating: {strat['avg_rating']}")
    
    # Meta shift detection
    shift = analyzer.detect_meta_shift()
    if shift['shift_detected']:
        print(f"\n🔄 Meta Shift Detected!")
        print(f"   Trend: {shift['trend'].upper()}")
        print(f"   Recent Win Rate: {shift['recent_winrate']*100:.1f}%")
        print(f"   Previous Win Rate: {shift['old_winrate']*100:.1f}%")
        print(f"   Change: {shift['change']*100:+.1f}%")


def print_recommendations(recommender: TeamRecommender, min_battles: int = 5):
    """Print team recommendations."""
    print_header("💡 TEAM RECOMMENDATIONS")
    
    # Best overall
    print("\n🥇 Best Overall Teams:")
    best = recommender.recommend('best_overall', limit=5, min_battles=min_battles)
    
    if not best:
        print("   No teams meet minimum battle requirement yet.")
        print(f"   (Need at least {min_battles} battles)")
    else:
        for i, team in enumerate(best, 1):
            print(f"\n   {i}. {team['strategy']} Team")
            print(f"      {', '.join(team['pokemon'])}")
            print(f"      ✅ Win Rate: {team['win_rate']*100:.1f}% ({team['total_battles']} battles)")
            print(f"      📊 Peak Rating: {team['peak_rating']}")
            if team.get('phase10_score'):
                print(f"      🔗 Synergy: {team['phase10_score']:.1f}/10")
    
    # Trending
    print("\n🔥 Trending Teams (Last 7 Days):")
    trending = recommender.recommend('trending', limit=3, min_battles=min_battles)
    
    if not trending:
        print("   No trending teams found.")
    else:
        for i, team in enumerate(trending, 1):
            print(f"\n   {i}. {', '.join(team['pokemon'])}")
            print(f"      {team['reason']}")
    
    # Underrated
    print("\n💎 Hidden Gems (Underrated Teams):")
    underrated = recommender.recommend('underrated', limit=3, min_battles=min_battles)
    
    if not underrated:
        print("   No underrated teams found.")
    else:
        for i, team in enumerate(underrated, 1):
            print(f"\n   {i}. {', '.join(team['pokemon'])}")
            print(f"      {team['reason']}")


def print_pokemon_stats(tracker: BattleTracker, pokemon_name: str):
    """Print stats for a specific Pokemon."""
    print_header(f"📈 {pokemon_name.upper()} PERFORMANCE")
    
    stats = tracker.db.get_pokemon_performance(pokemon_name)
    
    if not stats:
        print(f"\n  No data found for {pokemon_name}.")
        print(f"  This Pokemon has not been used in any recorded battles.")
        return
    
    print(f"\n{'Total Battles:':<25} {stats['total_battles']}")
    print(f"{'Wins:':<25} {stats['wins']}")
    print(f"{'Losses:':<25} {stats['losses']}")
    print(f"{'Ties:':<25} {stats['ties']}")
    print(f"{'Win Rate:':<25} {stats['win_rate']*100:.1f}%")
    print(f"{'Times Fainted:':<25} {stats['times_fainted']}")
    print(f"{'Survival Rate:':<25} {stats['survival_rate']*100:.1f}%")
    print(f"{'Last Used:':<25} {stats['last_used'][:19].replace('T', ' ')}")
    
    # Performance rating
    if stats['win_rate'] >= 0.6 and stats['survival_rate'] >= 0.7:
        rating = "⭐⭐⭐⭐⭐ EXCELLENT"
    elif stats['win_rate'] >= 0.55 and stats['survival_rate'] >= 0.6:
        rating = "⭐⭐⭐⭐ VERY GOOD"
    elif stats['win_rate'] >= 0.5:
        rating = "⭐⭐⭐ GOOD"
    elif stats['win_rate'] >= 0.45:
        rating = "⭐⭐ FAIR"
    else:
        rating = "⭐ NEEDS IMPROVEMENT"
    
    print(f"\n{'Performance Rating:':<25} {rating}")


def print_strategy_stats(tracker: BattleTracker, strategy: str):
    """Print stats for a specific strategy."""
    print_header(f"📊 {strategy.upper()} STRATEGY PERFORMANCE")
    
    stats = tracker.db.get_strategy_performance(strategy)
    
    if not stats:
        print(f"\n  No data found for {strategy} strategy.")
        print(f"  This strategy has not been used in any recorded battles.")
        return
    
    print(f"\n{'Total Battles:':<25} {stats['total_battles']}")
    print(f"{'Wins:':<25} {stats['wins']}")
    print(f"{'Losses:':<25} {stats['losses']}")
    print(f"{'Ties:':<25} {stats['ties']}")
    print(f"{'Win Rate:':<25} {stats['win_rate']*100:.1f}%")
    print(f"{'Average Rating:':<25} {stats['avg_rating']}")
    
    # Best team for this strategy
    if stats['best_team_hash']:
        print(f"\n🏆 Best Team for this Strategy:")
        team_stats = tracker.db.get_team_performance(stats['best_team_hash'])
        if team_stats:
            team_data = json.loads(team_stats['team_json'])
            pokemon_names = [p['name'] for p in team_data]
            print(f"   {', '.join(pokemon_names)}")
            print(f"   Win Rate: {team_stats['win_rate']*100:.1f}%")
            print(f"   Peak Rating: {team_stats['peak_rating']}")


def export_report(tracker: BattleTracker, analyzer: MetaAnalyzer,
                 recommender: TeamRecommender, filename: str,
                 min_battles: int = 5):
    """Export full report to JSON."""
    report = {
        'summary': tracker.db.get_statistics(),
        'meta_analysis': analyzer.get_meta_report(min_battles=min_battles),
        'recommendations': recommender.get_recommendations_report(min_battles=min_battles),
        'recent_battles': tracker.get_recent_battles(20)
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ Report exported to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Pokemon battle performance data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_performance.py --summary
  python analyze_performance.py --meta --min-battles 3
  python analyze_performance.py --recommend
  python analyze_performance.py --pokemon "Incineroar"
  python analyze_performance.py --strategy "Balanced"
  python analyze_performance.py --export report.json
        """
    )
    
    parser.add_argument('--summary', action='store_true',
                       help='Show overall performance summary')
    parser.add_argument('--meta', action='store_true',
                       help='Show meta analysis')
    parser.add_argument('--recommend', action='store_true',
                       help='Show team recommendations')
    parser.add_argument('--pokemon', type=str,
                       help='Show stats for specific Pokemon')
    parser.add_argument('--strategy', type=str,
                       help='Show stats for specific strategy')
    parser.add_argument('--export', type=str, metavar='FILE',
                       help='Export full report to JSON file')
    parser.add_argument('--min-battles', type=int, default=5,
                       help='Minimum battles for analysis (default: 5)')
    parser.add_argument('--db', type=str,
                       help='Path to custom database file')
    
    args = parser.parse_args()
    
    # Initialize components
    tracker = BattleTracker(args.db)
    analyzer = MetaAnalyzer(tracker.db)
    recommender = TeamRecommender(tracker.db)
    
    # Check if database has data
    stats = tracker.db.get_statistics()
    if stats['total_battles'] == 0:
        print("\n⚠️  No battle data found!")
        print("\nTo get started:")
        print("  1. Generate a team: python generate_team.py")
        print("  2. Battle with it on Pokemon Showdown")
        print("  3. Record results: python record_battle.py --team my_team.json --result win")
        print("\nOr run some test battles to populate the database.")
        return
    
    # Show analysis based on arguments
    if args.summary or not any([args.meta, args.recommend, args.pokemon, args.strategy, args.export]):
        print_summary(tracker)
    
    if args.meta:
        print_meta_analysis(analyzer, args.min_battles)
    
    if args.recommend:
        print_recommendations(recommender, args.min_battles)
    
    if args.pokemon:
        print_pokemon_stats(tracker, args.pokemon)
    
    if args.strategy:
        print_strategy_stats(tracker, args.strategy)
    
    if args.export:
        export_report(tracker, analyzer, recommender, args.export, args.min_battles)
    
    print()  # Final newline


if __name__ == '__main__':
    main()

