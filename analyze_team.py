#!/usr/bin/env python
"""
Team Analysis CLI Tool

Command-line interface for analyzing Pokemon VGC teams.
Provides comprehensive team evaluation using the Phase 10 Team Synergy Engine.

Usage:
    python analyze_team.py <team_file.json>
    python analyze_team.py --example
"""

import json
import sys
import argparse
from fp.team_analysis import TeamAnalyzer


def load_team_from_file(filepath: str):
    """Load team data from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Team file '{filepath}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in team file: {e}")
        sys.exit(1)


def create_example_team():
    """Create an example VGC team for demonstration."""
    return [
        {
            'name': 'Flutter Mane',
            'types': ['Ghost', 'Fairy'],
            'stats': {'hp': 131, 'atk': 54, 'def': 75, 'spa': 187, 'spd': 155, 'spe': 205},
            'ability': 'Protosynthesis',
            'item': 'Booster Energy',
            'moves': [
                {'name': 'Moonblast', 'type': 'Fairy'},
                {'name': 'Shadow Ball', 'type': 'Ghost'},
                {'name': 'Dazzling Gleam', 'type': 'Fairy'},
                {'name': 'Protect', 'type': 'Normal'}
            ]
        },
        {
            'name': 'Iron Hands',
            'types': ['Fighting', 'Electric'],
            'stats': {'hp': 261, 'atk': 211, 'def': 128, 'spa': 49, 'spd': 89, 'spe': 70},
            'ability': 'Quark Drive',
            'item': 'Assault Vest',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Close Combat', 'type': 'Fighting'},
                {'name': 'Wild Charge', 'type': 'Electric'},
                {'name': 'Heavy Slam', 'type': 'Steel'}
            ]
        },
        {
            'name': 'Rillaboom',
            'types': ['Grass'],
            'stats': {'hp': 207, 'atk': 194, 'def': 110, 'spa': 58, 'spd': 91, 'spe': 105},
            'ability': 'Grassy Surge',
            'item': 'Miracle Seed',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Grassy Glide', 'type': 'Grass'},
                {'name': 'Wood Hammer', 'type': 'Grass'},
                {'name': 'U-turn', 'type': 'Bug'}
            ]
        },
        {
            'name': 'Incineroar',
            'types': ['Fire', 'Dark'],
            'stats': {'hp': 202, 'atk': 136, 'def': 110, 'spa': 76, 'spd': 156, 'spe': 80},
            'ability': 'Intimidate',
            'item': 'Sitrus Berry',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Knock Off', 'type': 'Dark'},
                {'name': 'Flare Blitz', 'type': 'Fire'},
                {'name': 'Parting Shot', 'type': 'Dark'}
            ]
        },
        {
            'name': 'Gholdengo',
            'types': ['Steel', 'Ghost'],
            'stats': {'hp': 194, 'atk': 58, 'def': 115, 'spa': 203, 'spd': 112, 'spe': 104},
            'ability': 'Good as Gold',
            'item': 'Leftovers',
            'moves': [
                {'name': 'Make It Rain', 'type': 'Steel'},
                {'name': 'Shadow Ball', 'type': 'Ghost'},
                {'name': 'Protect', 'type': 'Normal'},
                {'name': 'Nasty Plot', 'type': 'Dark'}
            ]
        },
        {
            'name': 'Landorus-Therian',
            'types': ['Ground', 'Flying'],
            'stats': {'hp': 165, 'atk': 197, 'def': 110, 'spa': 99, 'spd': 100, 'spe': 157},
            'ability': 'Intimidate',
            'item': 'Choice Scarf',
            'moves': [
                {'name': 'Earthquake', 'type': 'Ground'},
                {'name': 'Rock Slide', 'type': 'Rock'},
                {'name': 'U-turn', 'type': 'Bug'},
                {'name': 'Stomping Tantrum', 'type': 'Ground'}
            ]
        }
    ]


def save_example_team(filepath: str = 'example_team.json'):
    """Save an example team to a JSON file."""
    team = create_example_team()
    with open(filepath, 'w') as f:
        json.dump(team, f, indent=2)
    print(f"✅ Example team saved to '{filepath}'")
    return filepath


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze Pokemon VGC teams for competitive play',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a team from file
  python analyze_team.py my_team.json
  
  # Generate and analyze example team
  python analyze_team.py --example
  
  # Show brief analysis
  python analyze_team.py my_team.json --brief
  
  # Compare two teams
  python analyze_team.py team1.json team2.json --compare
        """
    )
    
    parser.add_argument('team_file', nargs='?', help='Path to team JSON file')
    parser.add_argument('team_file2', nargs='?', help='Second team file (for comparison)')
    parser.add_argument('--example', action='store_true', help='Analyze example team')
    parser.add_argument('--brief', action='store_true', help='Show brief analysis (scores only)')
    parser.add_argument('--compare', action='store_true', help='Compare two teams')
    parser.add_argument('--save-example', action='store_true', help='Save example team to file and exit')
    parser.add_argument('--output', '-o', help='Save report to file')
    
    args = parser.parse_args()
    
    # Handle save example
    if args.save_example:
        save_example_team()
        return
    
    # Get team data
    if args.example:
        print("📊 Analyzing example VGC team...\n")
        team = create_example_team()
    elif args.team_file:
        print(f"📊 Loading team from '{args.team_file}'...\n")
        team = load_team_from_file(args.team_file)
    else:
        parser.print_help()
        return
    
    # Validate team
    if not team:
        print("❌ Error: Team is empty")
        return
    
    if len(team) < 3:
        print("⚠️ Warning: Team has less than 3 Pokemon")
    
    if len(team) > 6:
        print("⚠️ Warning: Team has more than 6 Pokemon (using first 6)")
        team = team[:6]
    
    # Initialize analyzer
    analyzer = TeamAnalyzer()
    
    # Handle comparison mode
    if args.compare and args.team_file2:
        print(f"📊 Comparing with '{args.team_file2}'...\n")
        team2 = load_team_from_file(args.team_file2)
        comparison = analyzer.compare_teams(team, team2)
        
        print("═" * 65)
        print("   TEAM COMPARISON")
        print("═" * 65)
        print()
        print(f"Team 1: {comparison['team1']['team_name']}")
        print(f"  Overall Score: {comparison['team1']['overall_score']}/10")
        print()
        print(f"Team 2: {comparison['team2']['team_name']}")
        print(f"  Overall Score: {comparison['team2']['overall_score']}/10")
        print()
        print(f"Winner: {comparison['winner']}")
        print()
        print("Score Differences (Team 1 - Team 2):")
        for category, diff in comparison['comparison'].items():
            symbol = "+" if diff > 0 else ""
            print(f"  {category.replace('_', ' ').title()}: {symbol}{diff:.1f}")
        print()
        return
    
    # Generate report
    if args.brief:
        # Brief analysis - just scores
        analysis = analyzer.analyze_team(team)
        print("═" * 65)
        print(f"   TEAM ANALYSIS: {analysis['team_name']}")
        print("═" * 65)
        print()
        print("SCORES:")
        print(f"  Type Coverage:    {analysis['type_coverage']['score']}/10")
        print(f"  Role Balance:     {analysis['roles']['balance_score']}/10")
        print(f"  Team Synergy:     {analysis['synergy']['team_score']}/10")
        print(f"  Overall Score:    {analysis['overall_score']}/10 {'⭐' * int(analysis['overall_score'] / 2)}")
        print()
    else:
        # Full detailed report
        report = analyzer.generate_report(team, detailed=True)
        print(report)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\n✅ Report saved to '{args.output}'")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

