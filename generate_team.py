#!/usr/bin/env python
"""
Team Generation CLI Tool

Command-line interface for generating Pokemon VGC teams.

Usage:
    python generate_team.py --strategy "Trick Room"
    python generate_team.py --strategy "Balanced" --count 10 --best
"""

import json
import sys
import argparse
from fp.team_generation import TeamGenerator


def save_team_to_file(team, filepath):
    """Save team to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(team, f, indent=2)
    print(f"✅ Team saved to '{filepath}'")


def save_team_to_showdown_format(team, filepath):
    """Save team in Pokemon Showdown import format."""
    lines = []
    
    for pkmn in team:
        # Pokemon name and item
        name = pkmn.get('name', 'Unknown')
        item = pkmn.get('item', '')
        if item and item != 'None':
            lines.append(f"{name} @ {item}")
        else:
            lines.append(name)
        
        # Ability
        ability = pkmn.get('ability', '')
        if ability:
            lines.append(f"Ability: {ability}")
        
        # EVs (if available)
        # For now, skip EVs since we don't store them in the final format
        
        # Moves
        for move in pkmn.get('moves', []):
            lines.append(f"- {move.get('name', 'Unknown')}")
        
        lines.append("")  # Blank line between Pokemon
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    print(f"✅ Team saved to '{filepath}' (Showdown format)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate Pokemon VGC teams using AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a Trick Room team
  python generate_team.py --strategy "Trick Room"
  
  # Generate multiple teams and pick the best
  python generate_team.py --strategy "Balanced" --count 10 --best
  
  # Generate and save to file
  python generate_team.py --strategy "Tailwind" --output my_team.json
  
  # Save in Pokemon Showdown format
  python generate_team.py --strategy "Balanced" --showdown team.txt
        """
    )
    
    parser.add_argument('--strategy', '-s', default='Balanced',
                       help='Strategy to use (Trick Room, Tailwind, Balanced, etc.)')
    parser.add_argument('--count', '-c', type=int, default=1,
                       help='Number of teams to generate')
    parser.add_argument('--best', action='store_true',
                       help='Generate multiple teams and return the best')
    parser.add_argument('--output', '-o',
                       help='Save team to JSON file')
    parser.add_argument('--showdown',
                       help='Save team in Pokemon Showdown format')
    parser.add_argument('--list-strategies', action='store_true',
                       help='List available strategies and exit')
    parser.add_argument('--size', type=int, default=6,
                       help='Team size (default: 6)')
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = TeamGenerator()
    except Exception as e:
        print(f"❌ Error initializing generator: {e}")
        return 1
    
    # List strategies if requested
    if args.list_strategies:
        strategies = generator.list_strategies()
        print("\nAvailable Strategies:")
        print("=" * 60)
        for strategy in strategies:
            print(f"  • {strategy}")
        print()
        return 0
    
    # Generate team(s)
    print(f"\n🎮 Generating {args.strategy} team...")
    print("=" * 60)
    
    try:
        if args.best:
            print(f"Generating {args.count} teams and selecting the best...\n")
            team = generator.generate_best(args.strategy, args.count, args.size)
        elif args.count > 1:
            print(f"Generating {args.count} teams...\n")
            teams = generator.generate_multiple(args.strategy, args.count, args.size)
            if not teams:
                print("❌ Failed to generate teams")
                return 1
            team = teams[0]  # Use first team
            
            # Show all teams briefly
            for i, t in enumerate(teams, 1):
                pkmn_names = [p['name'] for p in t]
                print(f"Team {i}: {', '.join(pkmn_names)}")
            print()
        else:
            team = generator.generate(args.strategy, args.size)
        
        if not team:
            print("❌ Failed to generate team")
            return 1
        
        # Display team
        print("\n✅ Generated Team:")
        print("=" * 60)
        for i, pkmn in enumerate(team, 1):
            types_str = '/'.join(pkmn['types'])
            print(f"\n{i}. {pkmn['name']} ({types_str})")
            print(f"   Ability: {pkmn.get('ability', 'Unknown')}")
            print(f"   Item: {pkmn.get('item', 'None')}")
            print(f"   Stats: HP {pkmn['stats']['hp']}, " +
                  f"Atk {pkmn['stats']['atk']}, " +
                  f"Def {pkmn['stats']['def']}, " +
                  f"SpA {pkmn['stats']['spa']}, " +
                  f"SpD {pkmn['stats']['spd']}, " +
                  f"Spe {pkmn['stats']['spe']}")
            print(f"   Moves:")
            for move in pkmn.get('moves', []):
                print(f"     • {move['name']} ({move.get('type', 'Unknown')})")
        
        # Evaluate team
        print("\n" + "=" * 60)
        print("📊 Team Analysis:")
        print("=" * 60)
        
        evaluation = generator.evaluate_team(team)
        
        if 'overall_score' in evaluation:
            score = evaluation['overall_score']
            stars = '⭐' * int(score / 2)
            print(f"\nOverall Score: {score}/10 {stars}")
        
        if 'strengths' in evaluation:
            print("\n✅ Strengths:")
            for strength in evaluation.get('strengths', []):
                print(f"  {strength}")
        
        if 'weaknesses' in evaluation:
            print("\n⚠️ Weaknesses:")
            for weakness in evaluation.get('weaknesses', []):
                print(f"  {weakness}")
        
        if 'recommendations' in evaluation:
            recs = evaluation.get('recommendations', [])
            if recs:
                print("\n💡 Recommendations:")
                for rec in recs[:3]:
                    print(f"  • {rec}")
        
        print("\n" + "=" * 60)
        
        # Save to file if requested
        if args.output:
            save_team_to_file(team, args.output)
        
        if args.showdown:
            save_team_to_showdown_format(team, args.showdown)
        
        print("\n✨ Team generation complete!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error generating team: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Generation interrupted by user")
        sys.exit(0)

