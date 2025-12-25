"""
Team Generator - Main Class

Main team generation system that coordinates all components
to generate competitive VGC teams.

Phase 11 - AI Team Generator
"""

import random
from typing import Dict, List, Optional
from .pokemon_database import PokemonDatabase
from .strategies import StrategyManager
from .core_builder import CoreBuilder
from .team_completer import TeamCompleter

# Try to import Phase 10 analyzer
try:
    from fp.team_analysis import TeamAnalyzer
    PHASE10_AVAILABLE = True
except ImportError:
    PHASE10_AVAILABLE = False


class TeamGenerator:
    """Main team generation system."""
    
    def __init__(self):
        """Initialize team generator with all components."""
        self.db = PokemonDatabase()
        self.strategies = StrategyManager()
        self.core_builder = CoreBuilder(self.db, self.strategies)
        self.team_completer = TeamCompleter(self.db, self.strategies)
        
        if PHASE10_AVAILABLE:
            self.analyzer = TeamAnalyzer()
        else:
            self.analyzer = None
    
    def generate(self, strategy_name: str = 'Balanced', 
                 team_size: int = 6) -> List[Dict]:
        """
        Generate a complete team for a strategy.
        
        Args:
            strategy_name: Strategy to build (Trick Room, Tailwind, etc.)
            team_size: Target team size (usually 6)
        
        Returns:
            Complete team as list of Pokemon dicts
        """
        # Build core
        core = self.core_builder.build_core(strategy_name)
        
        # Complete team
        team = self.team_completer.complete_team(core, strategy_name, team_size)
        
        return team
    
    def generate_multiple(self, strategy_name: str = 'Balanced',
                          count: int = 5, team_size: int = 6) -> List[List[Dict]]:
        """
        Generate multiple teams and return them.
        
        Args:
            strategy_name: Strategy to build
            count: Number of teams to generate
            team_size: Target team size
        
        Returns:
            List of teams
        """
        teams = []
        
        for _ in range(count):
            try:
                team = self.generate(strategy_name, team_size)
                if team and len(team) >= 4:  # At least 4 Pokemon
                    teams.append(team)
            except Exception as e:
                print(f"Error generating team: {e}")
                continue
        
        return teams
    
    def generate_best(self, strategy_name: str = 'Balanced',
                      count: int = 10, team_size: int = 6) -> List[Dict]:
        """
        Generate multiple teams and return the best one.
        
        Args:
            strategy_name: Strategy to build
            count: Number of teams to try
            team_size: Target team size
        
        Returns:
            Best team
        """
        teams = self.generate_multiple(strategy_name, count, team_size)
        
        if not teams:
            # Fallback: generate one team
            return self.generate(strategy_name, team_size)
        
        # Score teams using Phase 10 if available
        if self.analyzer:
            team_scores = []
            for team in teams:
                analysis = self.analyzer.analyze_team(team)
                score = analysis.get('overall_score', 0)
                team_scores.append((team, score))
            
            # Return best team
            team_scores.sort(key=lambda x: -x[1])
            return team_scores[0][0]
        else:
            # Return random team if no analyzer
            return random.choice(teams)
    
    def evaluate_team(self, team: List[Dict]) -> Dict:
        """
        Evaluate a team using Phase 10 analyzer.
        
        Args:
            team: Team to evaluate
        
        Returns:
            Analysis dict or simple evaluation
        """
        if self.analyzer:
            return self.analyzer.analyze_team(team)
        else:
            # Simple evaluation without Phase 10
            return {
                'overall_score': 5.0,
                'note': 'Phase 10 analyzer not available'
            }
    
    def get_team_report(self, team: List[Dict]) -> str:
        """
        Get a detailed report for a team.
        
        Args:
            team: Team to analyze
        
        Returns:
            Report string
        """
        if self.analyzer:
            return self.analyzer.generate_report(team, detailed=True)
        else:
            # Simple report
            lines = []
            lines.append("=" * 60)
            lines.append("GENERATED TEAM")
            lines.append("=" * 60)
            for i, pkmn in enumerate(team, 1):
                lines.append(f"\n{i}. {pkmn['name']} ({', '.join(pkmn['types'])})")
                lines.append(f"   Ability: {pkmn.get('ability', 'Unknown')}")
                lines.append(f"   Item: {pkmn.get('item', 'None')}")
                lines.append(f"   Speed: {pkmn['stats']['spe']}")
                lines.append(f"   Moves:")
                for move in pkmn.get('moves', []):
                    lines.append(f"     - {move['name']} ({move.get('type', 'Unknown')})")
            lines.append("\n" + "=" * 60)
            return '\n'.join(lines)
    
    def list_strategies(self) -> List[str]:
        """Get list of available strategies."""
        return self.strategies.list_strategies()


# Example usage
if __name__ == '__main__':
    generator = TeamGenerator()
    
    print("Team Generator Test")
    print("=" * 60)
    
    # List available strategies
    strategies = generator.list_strategies()
    print(f"\nAvailable Strategies ({len(strategies)}):")
    for strategy in strategies:
        print(f"  - {strategy}")
    
    # Generate a Balanced team
    print("\n" + "=" * 60)
    print("Generating Balanced Team...")
    team = generator.generate('Balanced')
    
    print(f"\nGenerated Team ({len(team)} Pokemon):")
    for i, pkmn in enumerate(team, 1):
        print(f"\n{i}. {pkmn['name']} ({', '.join(pkmn['types'])})")
        print(f"   Speed: {pkmn['stats']['spe']}, HP: {pkmn['stats']['hp']}")
        print(f"   Ability: {pkmn.get('ability', 'Unknown')}")
        print(f"   Item: {pkmn.get('item', 'None')}")
        print(f"   Moves: {', '.join(m['name'] for m in pkmn.get('moves', []))}")
    
    # Evaluate team
    print("\n" + "=" * 60)
    print("Team Evaluation:")
    evaluation = generator.evaluate_team(team)
    if 'overall_score' in evaluation:
        print(f"Overall Score: {evaluation['overall_score']}/10")
    if 'strengths' in evaluation:
        print("\nStrengths:")
        for strength in evaluation.get('strengths', [])[:3]:
            print(f"  {strength}")
    if 'weaknesses' in evaluation:
        print("\nWeaknesses:")
        for weakness in evaluation.get('weaknesses', [])[:3]:
            print(f"  {weakness}")

