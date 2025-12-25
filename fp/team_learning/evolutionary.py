"""
Evolutionary Team Builder

Uses genetic algorithms to evolve and optimize Pokemon teams.
Teams are evolved over generations to maximize performance.

Phase 12 - Team Learning & Adaptation
"""

import random
import json
from typing import Dict, List, Optional, Tuple, Callable
from ..team_generation.team_generator import TeamGenerator
from ..team_generation.pokemon_database import PokemonDatabase
from ..team_analysis.team_analyzer import TeamAnalyzer


class EvolutionaryTeamBuilder:
    """Evolves Pokemon teams using genetic algorithms."""
    
    def __init__(self, pokemon_db: Optional[PokemonDatabase] = None,
                 fitness_func: Optional[Callable] = None):
        """
        Initialize evolutionary builder.
        
        Args:
            pokemon_db: Pokemon database, or None for default
            fitness_func: Custom fitness function, or None for default
        """
        self.pokemon_db = pokemon_db if pokemon_db else PokemonDatabase()
        self.team_generator = TeamGenerator(self.pokemon_db)
        self.team_analyzer = TeamAnalyzer()
        self.fitness_func = fitness_func if fitness_func else self._default_fitness
    
    def evolve(self, strategy: str = "Balanced",
              population_size: int = 20,
              generations: int = 20,
              mutation_rate: float = 0.2,
              crossover_rate: float = 0.7,
              elitism_count: int = 2,
              verbose: bool = True) -> Dict:
        """
        Evolve teams using genetic algorithm.
        
        Args:
            strategy: Base strategy to use
            population_size: Number of teams in each generation
            generations: Number of generations to evolve
            mutation_rate: Probability of mutation (0.0-1.0)
            crossover_rate: Probability of crossover (0.0-1.0)
            elitism_count: Number of top teams to preserve each generation
            verbose: Print progress
        
        Returns:
            Best team found
        """
        if verbose:
            print(f"🧬 Evolving {strategy} teams...")
            print(f"   Population: {population_size}, Generations: {generations}")
            print(f"   Mutation Rate: {mutation_rate}, Crossover Rate: {crossover_rate}")
            print()
        
        # Initialize population
        population = self._create_initial_population(strategy, population_size)
        
        best_fitness = 0.0
        best_team = None
        
        for gen in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for team in population:
                fitness = self.fitness_func(team)
                fitness_scores.append((team, fitness))
            
            # Sort by fitness (descending)
            fitness_scores.sort(key=lambda x: -x[1])
            
            # Track best
            if fitness_scores[0][1] > best_fitness:
                best_fitness = fitness_scores[0][1]
                best_team = fitness_scores[0][0]
            
            if verbose and gen % 5 == 0:
                avg_fitness = sum(f for _, f in fitness_scores) / len(fitness_scores)
                print(f"   Generation {gen:2}: "
                      f"Best={best_fitness:.2f}, Avg={avg_fitness:.2f}")
            
            # Selection: Keep elite teams
            next_generation = [team for team, _ in fitness_scores[:elitism_count]]
            
            # Create offspring
            while len(next_generation) < population_size:
                # Tournament selection
                parent1 = self._tournament_selection(fitness_scores, k=3)
                parent2 = self._tournament_selection(fitness_scores, k=3)
                
                # Crossover
                if random.random() < crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = random.choice([parent1, parent2])
                
                # Mutation
                if random.random() < mutation_rate:
                    child = self._mutate(child, strategy)
                
                next_generation.append(child)
            
            population = next_generation
        
        # Final evaluation
        fitness_scores = [(team, self.fitness_func(team)) for team in population]
        fitness_scores.sort(key=lambda x: -x[1])
        best_team, best_fitness = fitness_scores[0]
        
        if verbose:
            print(f"\n✅ Evolution complete!")
            print(f"   Best fitness: {best_fitness:.2f}")
            print(f"   Best team: {', '.join([p['name'] for p in best_team])}")
        
        return {
            'team': best_team,
            'fitness': best_fitness,
            'strategy': strategy,
            'final_population': [team for team, _ in fitness_scores[:5]]
        }
    
    def _create_initial_population(self, strategy: str, size: int) -> List[List[Dict]]:
        """Create initial random population."""
        population = []
        
        for _ in range(size):
            team_data = self.team_generator.generate(strategy)
            team = team_data['pokemon']
            population.append(team)
        
        return population
    
    def _tournament_selection(self, fitness_scores: List[Tuple], k: int = 3):
        """Select team using tournament selection."""
        tournament = random.sample(fitness_scores, k)
        winner = max(tournament, key=lambda x: x[1])
        return winner[0]
    
    def _crossover(self, parent1: List[Dict], parent2: List[Dict]) -> List[Dict]:
        """
        Perform crossover between two teams.
        
        Takes some Pokemon from each parent to create a child.
        """
        # Take 3 Pokemon from each parent
        child = []
        
        # Randomly select 3 from parent1
        selected_from_p1 = random.sample(range(len(parent1)), 3)
        for idx in selected_from_p1:
            child.append(parent1[idx].copy())
        
        # Fill remaining spots from parent2 (avoid duplicates)
        used_names = {p['name'] for p in child}
        
        for pokemon in parent2:
            if len(child) >= 6:
                break
            if pokemon['name'] not in used_names:
                child.append(pokemon.copy())
                used_names.add(pokemon['name'])
        
        # If still not full (due to duplicates), add random Pokemon
        while len(child) < 6:
            random_pokemon = random.choice(self.pokemon_db.get_all_pokemon())
            if random_pokemon['name'] not in used_names:
                child.append(random_pokemon)
                used_names.add(random_pokemon['name'])
        
        return child
    
    def _mutate(self, team: List[Dict], strategy: str) -> List[Dict]:
        """
        Mutate a team by replacing 1-2 Pokemon.
        
        Args:
            team: Team to mutate
            strategy: Strategy context for mutation
        
        Returns:
            Mutated team
        """
        mutated = team.copy()
        
        # Number of mutations (1-2)
        num_mutations = random.randint(1, 2)
        
        for _ in range(num_mutations):
            # Select random position to mutate
            position = random.randint(0, len(mutated) - 1)
            
            # Get replacement Pokemon
            # Try to find Pokemon from same role if possible
            original_role = self._guess_role(mutated[position])
            
            # Get candidates
            all_pokemon = self.pokemon_db.get_all_pokemon()
            
            # Filter by role if possible
            candidates = [p for p in all_pokemon 
                         if self._guess_role(p) == original_role]
            
            if not candidates:
                candidates = all_pokemon
            
            # Avoid duplicates
            used_names = {p['name'] for i, p in enumerate(mutated) if i != position}
            candidates = [p for p in candidates if p['name'] not in used_names]
            
            if candidates:
                mutated[position] = random.choice(candidates)
        
        return mutated
    
    def _guess_role(self, pokemon: Dict) -> str:
        """Guess Pokemon role based on stats."""
        stats = pokemon.get('stats', {})
        
        # High attack/special attack -> offensive
        if stats.get('atk', 0) > 120 or stats.get('spa', 0) > 120:
            # Fast -> sweeper
            if stats.get('spe', 0) > 100:
                return 'sweeper'
            # Slow -> attacker
            return 'attacker'
        
        # High defenses -> defensive
        if stats.get('def', 0) > 100 or stats.get('spd', 0) > 100:
            return 'wall'
        
        # Otherwise support
        return 'support'
    
    def _default_fitness(self, team: List[Dict]) -> float:
        """
        Default fitness function using Phase 10 team analysis.
        
        Args:
            team: Team to evaluate
        
        Returns:
            Fitness score (0.0-10.0+)
        """
        try:
            analysis = self.team_analyzer.analyze_team(team)
            
            # Overall score from Phase 10 (0-10)
            base_score = analysis['overall_score']
            
            # Bonus for diversity (number of unique types)
            all_types = set()
            for pokemon in team:
                all_types.update(pokemon.get('types', []))
            
            type_diversity = len(all_types) / 18.0  # 18 types total
            
            # Bonus for balanced roles
            roles = [self._guess_role(p) for p in team]
            role_diversity = len(set(roles)) / 4.0  # 4 roles
            
            # Combined fitness
            fitness = (base_score * 0.7 +  # 70% from synergy
                      type_diversity * 2.0 +  # Up to 2.0 from type diversity
                      role_diversity * 1.0)   # Up to 1.0 from role diversity
            
            return fitness
        except Exception as e:
            # If analysis fails, return low score
            return 0.0


# Example usage
if __name__ == '__main__':
    print("Evolutionary Team Builder Example")
    print("=" * 60)
    
    # Initialize builder
    builder = EvolutionaryTeamBuilder()
    
    # Evolve a Balanced team
    result = builder.evolve(
        strategy="Balanced",
        population_size=10,
        generations=10,
        mutation_rate=0.25,
        crossover_rate=0.7,
        verbose=True
    )
    
    print(f"\n🏆 Best Team Found:")
    for i, pokemon in enumerate(result['team'], 1):
        print(f"   {i}. {pokemon['name']}")
    
    print(f"\n   Fitness Score: {result['fitness']:.2f}")

