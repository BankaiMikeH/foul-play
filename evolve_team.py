#!/usr/bin/env python3
"""
Evolutionary Team Builder CLI

Uses genetic algorithms to evolve and optimize Pokemon teams.
Iteratively improves teams over multiple generations.

Phase 12 - Team Learning & Adaptation

Usage:
    python evolve_team.py --strategy "Balanced" --generations 20
    python evolve_team.py --strategy "Trick Room" --population 30 --generations 50
    python evolve_team.py --strategy "Balanced" --output evolved_team.json
"""

import argparse
import json
from fp.team_learning import EvolutionaryTeamBuilder


def main():
    parser = argparse.ArgumentParser(
        description='Evolve Pokemon teams using genetic algorithms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evolve a Balanced team
  python evolve_team.py --strategy "Balanced"
  
  # Evolve with custom parameters
  python evolve_team.py --strategy "Trick Room" --population 30 --generations 50
  
  # Save best team to file
  python evolve_team.py --strategy "Balanced" --output evolved_team.json
  
  # Evolve quietly
  python evolve_team.py --strategy "Balanced" --quiet
        """
    )
    
    parser.add_argument('--strategy', type=str, default="Balanced",
                       help='Strategy to evolve (default: Balanced)')
    parser.add_argument('--population', type=int, default=20,
                       help='Population size (default: 20)')
    parser.add_argument('--generations', type=int, default=20,
                       help='Number of generations (default: 20)')
    parser.add_argument('--mutation-rate', type=float, default=0.2,
                       help='Mutation rate 0.0-1.0 (default: 0.2)')
    parser.add_argument('--crossover-rate', type=float, default=0.7,
                       help='Crossover rate 0.0-1.0 (default: 0.7)')
    parser.add_argument('--elitism', type=int, default=2,
                       help='Number of elite teams to preserve (default: 2)')
    parser.add_argument('--output', type=str,
                       help='Save best team to JSON file')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress evolution progress output')
    
    args = parser.parse_args()
    
    # Print header
    if not args.quiet:
        print("\n" + "="*70)
        print("  🧬 EVOLUTIONARY TEAM BUILDER")
        print("="*70)
        print(f"\nStrategy: {args.strategy}")
        print(f"Population Size: {args.population}")
        print(f"Generations: {args.generations}")
        print(f"Mutation Rate: {args.mutation_rate}")
        print(f"Crossover Rate: {args.crossover_rate}")
        print(f"Elitism: {args.elitism}")
        print()
    
    # Initialize builder
    builder = EvolutionaryTeamBuilder()
    
    # Evolve team
    result = builder.evolve(
        strategy=args.strategy,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        elitism_count=args.elitism,
        verbose=not args.quiet
    )
    
    # Display result
    if not args.quiet:
        print("\n" + "="*70)
        print("  🏆 EVOLUTION COMPLETE")
        print("="*70)
    
    print(f"\n✅ Best Team (Fitness: {result['fitness']:.2f}):")
    print()
    
    for i, pokemon in enumerate(result['team'], 1):
        types_str = "/".join(pokemon.get('types', []))
        print(f"  {i}. {pokemon['name']:<20} [{types_str}]")
        
        # Show a sample move
        moves = pokemon.get('common_moves', [])
        if moves:
            print(f"     Sample Move: {moves[0]}")
    
    # Save to file if requested
    if args.output:
        team_export = {
            'pokemon': result['team'],
            'strategy': args.strategy,
            'fitness': result['fitness'],
            'evolved': True,
            'evolution_params': {
                'population': args.population,
                'generations': args.generations,
                'mutation_rate': args.mutation_rate,
                'crossover_rate': args.crossover_rate
            }
        }
        
        with open(args.output, 'w') as f:
            json.dump(team_export, f, indent=2)
        
        print(f"\n💾 Team saved to: {args.output}")
    
    # Show other top teams
    if not args.quiet and len(result['final_population']) > 1:
        print(f"\n📊 Other Top Teams:")
        for i, team in enumerate(result['final_population'][1:4], 2):
            pokemon_names = [p['name'] for p in team]
            print(f"  {i}. {', '.join(pokemon_names[:3])}...")
    
    print()


if __name__ == '__main__':
    main()

