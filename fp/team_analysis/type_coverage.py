"""
Type Coverage Analyzer

Analyzes offensive and defensive type coverage for Pokemon teams.
Identifies gaps, weaknesses, and strengths.

Phase 10 - Team Synergy Engine
"""

import json
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class TypeCoverageAnalyzer:
    """Analyzes type coverage for Pokemon teams."""
    
    def __init__(self):
        """Initialize the type coverage analyzer with type chart data."""
        self.type_chart = self._load_type_chart()
        self.all_types = self.type_chart['all_types']
    
    def _load_type_chart(self) -> Dict:
        """Load the type effectiveness chart from JSON."""
        # Try to find the type chart file
        possible_paths = [
            'fp/data/type_chart.json',
            'data/type_chart.json',
            '../data/type_chart.json',
            os.path.join(os.path.dirname(__file__), '../data/type_chart.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        # Fallback: return minimal chart if file not found
        raise FileNotFoundError("Could not find type_chart.json in any expected location")
    
    def get_type_effectiveness(self, attacking_type: str, defending_types: List[str]) -> float:
        """
        Calculate type effectiveness multiplier.
        
        Args:
            attacking_type: The type of the attacking move
            defending_types: List of defending Pokemon's types (1 or 2 types)
        
        Returns:
            float: Effectiveness multiplier (0, 0.25, 0.5, 1, 2, or 4)
        """
        if not defending_types:
            return 1.0
        
        attacking_type = attacking_type.lower()
        multiplier = 1.0
        
        for defending_type in defending_types:
            defending_type = defending_type.lower()
            if defending_type in self.type_chart['type_effectiveness'].get(attacking_type, {}):
                multiplier *= self.type_chart['type_effectiveness'][attacking_type][defending_type]
        
        return multiplier
    
    def analyze_team(self, team: List[Dict]) -> Dict:
        """
        Analyze complete type coverage for a team.
        
        Args:
            team: List of Pokemon dicts with 'types' and 'moves' fields
        
        Returns:
            Dict containing coverage analysis
        """
        offensive_coverage = self._analyze_offensive_coverage(team)
        defensive_coverage = self._analyze_defensive_coverage(team)
        
        return {
            'offensive': offensive_coverage,
            'defensive': defensive_coverage,
            'score': self._calculate_coverage_score(offensive_coverage, defensive_coverage),
            'summary': self._generate_summary(offensive_coverage, defensive_coverage)
        }
    
    def _analyze_offensive_coverage(self, team: List[Dict]) -> Dict:
        """Analyze what types the team can hit super-effectively."""
        coverage = defaultdict(float)
        move_types_seen = set()
        
        for pokemon in team:
            for move in pokemon.get('moves', []):
                move_type = move.get('type', '').lower()
                if move_type and move_type in self.all_types:
                    move_types_seen.add(move_type)
                    
                    # Calculate what this move hits super-effectively
                    for target_type in self.all_types:
                        effectiveness = self.get_type_effectiveness(move_type, [target_type])
                        coverage[target_type] = max(coverage.get(target_type, 0), effectiveness)
        
        # Categorize coverage
        strong_against = [t for t, e in coverage.items() if e >= 2.0]
        neutral_against = [t for t, e in coverage.items() if 0.5 < e < 2.0]
        weak_against = [t for t, e in coverage.items() if 0 < e <= 0.5]
        immune = [t for t, e in coverage.items() if e == 0]
        no_coverage = [t for t in self.all_types if t not in coverage]
        
        return {
            'coverage_map': dict(coverage),
            'move_types': list(move_types_seen),
            'strong_against': sorted(strong_against),
            'neutral_against': sorted(neutral_against),
            'weak_against': sorted(weak_against),
            'immune': sorted(immune),
            'no_coverage': sorted(no_coverage)
        }
    
    def _analyze_defensive_coverage(self, team: List[Dict]) -> Dict:
        """Analyze team's defensive resistances and weaknesses."""
        type_matchups = defaultdict(list)
        
        for pokemon in team:
            pokemon_types = [t.lower() for t in pokemon.get('types', [])]
            
            for attacking_type in self.all_types:
                effectiveness = self.get_type_effectiveness(attacking_type, pokemon_types)
                type_matchups[attacking_type].append({
                    'pokemon': pokemon.get('name', 'Unknown'),
                    'effectiveness': effectiveness
                })
        
        # Analyze overall team weaknesses/resistances
        team_size = len(team)
        weak_to = []
        resistant_to = []
        neutral_to = []
        
        for attack_type, matchups in type_matchups.items():
            weak_count = sum(1 for m in matchups if m['effectiveness'] >= 2.0)
            resist_count = sum(1 for m in matchups if m['effectiveness'] <= 0.5)
            
            if weak_count >= team_size * 0.4:  # 40%+ of team weak
                weak_to.append({
                    'type': attack_type,
                    'count': weak_count,
                    'pokemon': [m['pokemon'] for m in matchups if m['effectiveness'] >= 2.0]
                })
            elif resist_count >= team_size * 0.4:  # 40%+ of team resists
                resistant_to.append({
                    'type': attack_type,
                    'count': resist_count,
                    'pokemon': [m['pokemon'] for m in matchups if m['effectiveness'] <= 0.5]
                })
            else:
                neutral_to.append(attack_type)
        
        return {
            'type_matchups': dict(type_matchups),
            'weak_to': sorted(weak_to, key=lambda x: -x['count']),
            'resistant_to': sorted(resistant_to, key=lambda x: -x['count']),
            'neutral_to': sorted(neutral_to)
        }
    
    def _calculate_coverage_score(self, offensive: Dict, defensive: Dict) -> float:
        """
        Calculate overall coverage score (0-10).
        
        Scoring:
        - Offensive coverage: 5 points max
        - Defensive coverage: 5 points max
        """
        # Offensive score (0-5)
        offensive_score = 0
        total_types = len(self.all_types)
        strong_coverage = len(offensive['strong_against'])
        no_coverage = len(offensive['no_coverage'])
        
        # Award points for good coverage
        offensive_score += (strong_coverage / total_types) * 3.5  # Max 3.5 points
        
        # Deduct for gaps
        offensive_score -= (no_coverage / total_types) * 2  # Max -2 points
        offensive_score = max(0, min(5, offensive_score))
        
        # Defensive score (0-5)
        defensive_score = 5.0
        weak_count = len(defensive['weak_to'])
        resistant_count = len(defensive['resistant_to'])
        
        # Deduct for many weaknesses
        defensive_score -= (weak_count / total_types) * 3  # Deduct up to 3 points
        
        # Award for resistances
        defensive_score += (resistant_count / total_types) * 1  # Add up to 1 point
        defensive_score = max(0, min(5, defensive_score))
        
        return round(offensive_score + defensive_score, 1)
    
    def _generate_summary(self, offensive: Dict, defensive: Dict) -> str:
        """Generate human-readable summary."""
        lines = []
        
        # Offensive summary
        lines.append("OFFENSIVE COVERAGE:")
        if offensive['strong_against']:
            lines.append(f"  ✅ Strong vs: {', '.join(offensive['strong_against'][:5])}")
        if offensive['weak_against']:
            lines.append(f"  ⚠️ Weak vs: {', '.join(offensive['weak_against'][:5])}")
        if offensive['no_coverage']:
            lines.append(f"  ❌ No coverage: {', '.join(offensive['no_coverage'][:5])}")
        
        lines.append("")
        
        # Defensive summary
        lines.append("DEFENSIVE COVERAGE:")
        if defensive['weak_to']:
            for weakness in defensive['weak_to'][:3]:
                pkmn_list = ', '.join(weakness['pokemon'][:3])
                lines.append(f"  ⚠️ {weakness['count']}x weak to {weakness['type'].upper()}: {pkmn_list}")
        
        if defensive['resistant_to']:
            for resistance in defensive['resistant_to'][:3]:
                pkmn_list = ', '.join(resistance['pokemon'][:3])
                lines.append(f"  ✅ {resistance['count']}x resistant to {resistance['type'].upper()}: {pkmn_list}")
        
        return '\n'.join(lines)
    
    def find_coverage_gaps(self, team: List[Dict]) -> List[str]:
        """
        Find types that the team has no super-effective coverage against.
        
        Returns:
            List of type names
        """
        analysis = self.analyze_team(team)
        return analysis['offensive']['no_coverage'] + analysis['offensive']['immune']
    
    def suggest_coverage_improvements(self, team: List[Dict]) -> List[Dict]:
        """
        Suggest moves or Pokemon to improve coverage.
        
        Returns:
            List of suggestions
        """
        gaps = self.find_coverage_gaps(team)
        suggestions = []
        
        if not gaps:
            return [{'message': 'Team has complete type coverage!'}]
        
        # Suggest move types that would cover gaps
        for gap in gaps:
            # Find types that hit this gap super-effectively
            effective_types = []
            for attack_type in self.all_types:
                if self.get_type_effectiveness(attack_type, [gap]) >= 2.0:
                    effective_types.append(attack_type)
            
            if effective_types:
                suggestions.append({
                    'gap': gap,
                    'suggestion': f"Add {' or '.join(effective_types[:3])}-type coverage",
                    'coverage_types': effective_types
                })
        
        return suggestions


# Example usage and testing
if __name__ == "__main__":
    # Example team
    example_team = [
        {
            'name': 'Flutter Mane',
            'types': ['Ghost', 'Fairy'],
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
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Close Combat', 'type': 'Fighting'},
                {'name': 'Wild Charge', 'type': 'Electric'},
                {'name': 'Heavy Slam', 'type': 'Steel'}
            ]
        },
        {
            'name': 'Landorus',
            'types': ['Ground', 'Flying'],
            'moves': [
                {'name': 'Earthquake', 'type': 'Ground'},
                {'name': 'Rock Slide', 'type': 'Rock'},
                {'name': 'U-turn', 'type': 'Bug'},
                {'name': 'Stomping Tantrum', 'type': 'Ground'}
            ]
        }
    ]
    
    analyzer = TypeCoverageAnalyzer()
    results = analyzer.analyze_team(example_team)
    
    print("=" * 60)
    print("TYPE COVERAGE ANALYSIS")
    print("=" * 60)
    print(results['summary'])
    print()
    print(f"Overall Score: {results['score']}/10")
    print()
    
    # Show gaps
    gaps = analyzer.find_coverage_gaps(example_team)
    if gaps:
        print("Coverage Gaps:")
        for gap in gaps:
            print(f"  ❌ {gap}")
        print()
        
        # Show suggestions
        suggestions = analyzer.suggest_coverage_improvements(example_team)
        print("Suggestions:")
        for suggestion in suggestions:
            if 'gap' in suggestion:
                print(f"  • {suggestion['suggestion']}")

