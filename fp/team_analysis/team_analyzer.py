"""
Team Analyzer - Main Class

Coordinates all team analysis modules to provide comprehensive team evaluation.

Phase 10 - Team Synergy Engine
"""

from typing import Dict, List
from .type_coverage import TypeCoverageAnalyzer
from .speed_analysis import SpeedTierAnalyzer
from .role_system import RoleIdentifier
from .synergy_scorer import SynergyScorer


class TeamAnalyzer:
    """
    Main team analysis class that coordinates all analysis modules.
    
    Provides:
    - Type coverage analysis
    - Speed tier evaluation  
    - Role identification
    - Synergy scoring
    - Overall team evaluation
    """
    
    def __init__(self):
        """Initialize all analysis modules."""
        self.type_analyzer = TypeCoverageAnalyzer()
        self.speed_analyzer = SpeedTierAnalyzer()
        self.role_identifier = RoleIdentifier()
        self.synergy_scorer = SynergyScorer()
    
    def analyze_team(self, team: List[Dict]) -> Dict:
        """
        Perform comprehensive team analysis.
        
        Args:
            team: List of Pokemon dicts with complete data
        
        Returns:
            Dict containing all analysis results
        """
        # Perform individual analyses
        type_analysis = self.type_analyzer.analyze_team(team)
        speed_analysis = self.speed_analyzer.analyze_team_speeds(team)
        role_analysis = self.role_identifier.analyze_team_roles(team)
        synergy_analysis = self.synergy_scorer.analyze_team_synergy(team)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            type_analysis['score'],
            speed_analysis,
            role_analysis['balance_score'],
            synergy_analysis['team_score']
        )
        
        return {
            'team_name': self._get_team_name(team),
            'team_size': len(team),
            'type_coverage': type_analysis,
            'speed_tiers': speed_analysis,
            'roles': role_analysis,
            'synergy': synergy_analysis,
            'overall_score': overall_score,
            'strengths': self._identify_strengths(type_analysis, speed_analysis, role_analysis, synergy_analysis),
            'weaknesses': self._identify_weaknesses(type_analysis, speed_analysis, role_analysis, synergy_analysis),
            'recommendations': self._generate_recommendations(type_analysis, speed_analysis, role_analysis, synergy_analysis)
        }
    
    def _get_team_name(self, team: List[Dict]) -> str:
        """Generate a team name based on key Pokemon."""
        if not team:
            return "Empty Team"
        
        # Use first Pokemon as team identifier
        lead = team[0].get('name', 'Unknown')
        return f"{lead} Core"
    
    def _calculate_overall_score(self, type_score: float, speed_analysis: Dict,
                                  role_score: float, synergy_score: float) -> float:
        """
        Calculate overall team score (0-10).
        
        Weighted average:
        - Type coverage: 25%
        - Speed positioning: 20%
        - Role balance: 25%
        - Synergy: 30%
        """
        speed_score = speed_analysis.get('meta_comparison', [])
        # Count how many meta threats we outspeed
        if speed_score:
            outspeed_count = sum(1 for threat in speed_score if threat.get('coverage', 0) >= 3)
            speed_metric = min(10.0, (outspeed_count / max(len(speed_score), 1)) * 10)
        else:
            speed_metric = 5.0
        
        overall = (
            type_score * 0.25 +
            speed_metric * 0.20 +
            role_score * 0.25 +
            synergy_score * 0.30
        )
        
        return round(overall, 1)
    
    def _identify_strengths(self, type_analysis: Dict, speed_analysis: Dict,
                           role_analysis: Dict, synergy_analysis: Dict) -> List[str]:
        """Identify team strengths."""
        strengths = []
        
        # Type coverage strengths
        if type_analysis['score'] >= 8.0:
            strengths.append("✅ Excellent type coverage")
        
        strong_against = type_analysis['offensive'].get('strong_against', [])
        if len(strong_against) >= 8:
            strengths.append(f"✅ Super-effective coverage vs {len(strong_against)} types")
        
        # Speed strengths
        speed_control = speed_analysis.get('speed_control', {})
        if speed_control.get('tailwind'):
            strengths.append(f"✅ Tailwind support ({', '.join(speed_control['tailwind'])})")
        if speed_control.get('trick_room'):
            strengths.append(f"✅ Trick Room support ({', '.join(speed_control['trick_room'])})")
        if len(speed_control.get('choice_scarf', [])) >= 1:
            strengths.append(f"✅ Choice Scarf speed control")
        
        # Role strengths
        roles = role_analysis.get('role_distribution', {})
        if roles.get('INTIMIDATE'):
            intimidate_count = len(roles['INTIMIDATE'])
            if intimidate_count >= 2:
                strengths.append(f"✅ Strong Intimidate presence ({intimidate_count}x)")
            else:
                strengths.append(f"✅ Intimidate support")
        
        if roles.get('SUPPORT'):
            strengths.append(f"✅ Good support options")
        
        # Synergy strengths
        if synergy_analysis['team_score'] >= 7.0:
            strengths.append("✅ Excellent team synergy")
        
        top_pair = synergy_analysis['top_pairs'][0] if synergy_analysis['top_pairs'] else None
        if top_pair and top_pair['score'] >= 30:
            strengths.append(f"✅ Strong core: {top_pair['pair']}")
        
        return strengths if strengths else ["No major strengths identified"]
    
    def _identify_weaknesses(self, type_analysis: Dict, speed_analysis: Dict,
                            role_analysis: Dict, synergy_analysis: Dict) -> List[str]:
        """Identify team weaknesses."""
        weaknesses = []
        
        # Type coverage weaknesses
        if type_analysis['score'] < 5.0:
            weaknesses.append("❌ Poor type coverage")
        
        no_coverage = type_analysis['offensive'].get('no_coverage', [])
        if len(no_coverage) >= 3:
            weaknesses.append(f"⚠️ No coverage vs {len(no_coverage)} types")
        
        defensive_weak = type_analysis['defensive'].get('weak_to', [])
        if defensive_weak:
            top_weakness = defensive_weak[0]
            if top_weakness['count'] >= 4:
                weaknesses.append(f"❌ {top_weakness['count']}/6 weak to {top_weakness['type'].upper()}")
        
        # Speed weaknesses
        speed_control = speed_analysis.get('speed_control', {})
        if not speed_control.get('tailwind') and not speed_control.get('trick_room'):
            weaknesses.append("❌ No Tailwind or Trick Room (critical weakness!)")
        
        # Role weaknesses
        roles = role_analysis.get('role_distribution', {})
        if 'SPEED_CONTROL' not in roles:
            weaknesses.append("⚠️ No speed control moves")
        
        if 'SUPPORT' not in roles and 'REDIRECTOR' not in roles:
            weaknesses.append("⚠️ Limited support options")
        
        if role_analysis.get('balance_score', 5.0) < 5.0:
            weaknesses.append("⚠️ Poor role balance")
        
        # Synergy weaknesses
        if synergy_analysis['team_score'] < 4.0:
            weaknesses.append("⚠️ Low team synergy")
        
        return weaknesses if weaknesses else ["No major weaknesses identified"]
    
    def _generate_recommendations(self, type_analysis: Dict, speed_analysis: Dict,
                                  role_analysis: Dict, synergy_analysis: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Type coverage recommendations
        gaps = type_analysis['offensive'].get('no_coverage', [])
        if gaps:
            recommendations.append(f"Consider adding coverage for: {', '.join(gaps[:3])}")
        
        suggestions = self.type_analyzer.suggest_coverage_improvements(
            [{'types': [], 'moves': []}]  # Dummy, we already have gaps
        )
        
        # Speed recommendations
        speed_control = speed_analysis.get('speed_control', {})
        if not speed_control.get('tailwind'):
            recommendations.append("Add Tailwind user for speed control")
        if not speed_control.get('trick_room'):
            recommendations.append("Consider Trick Room for slow Pokemon")
        
        # Role recommendations
        role_suggestions = self.role_identifier.suggest_role_additions([])
        recommendations.extend(role_suggestions[:2])  # Add top 2 role suggestions
        
        # Remove duplicates
        recommendations = list(dict.fromkeys(recommendations))
        
        return recommendations[:5]  # Top 5 recommendations
    
    def generate_report(self, team: List[Dict], detailed: bool = True) -> str:
        """
        Generate a human-readable team analysis report.
        
        Args:
            team: List of Pokemon dicts
            detailed: If True, include detailed breakdowns
        
        Returns:
            str: Formatted report
        """
        analysis = self.analyze_team(team)
        
        lines = []
        lines.append("═" * 65)
        lines.append(f"   TEAM ANALYSIS: {analysis['team_name']}")
        lines.append("═" * 65)
        lines.append("")
        
        # Team composition
        lines.append("TEAM COMPOSITION:")
        for i, pokemon in enumerate(team, 1):
            types = '/'.join(pokemon.get('types', ['Unknown']))
            lines.append(f"{i}. {pokemon.get('name', 'Unknown')} ({types})")
        lines.append("")
        
        # Scores
        lines.append("─" * 65)
        lines.append("SCORES:")
        lines.append("─" * 65)
        lines.append(f"Type Coverage:    {analysis['type_coverage']['score']}/10 {'⭐' * int(analysis['type_coverage']['score'] / 2)}")
        lines.append(f"Role Balance:     {analysis['roles']['balance_score']}/10 {'⭐' * int(analysis['roles']['balance_score'] / 2)}")
        lines.append(f"Team Synergy:     {analysis['synergy']['team_score']}/10 {'⭐' * int(analysis['synergy']['team_score'] / 2)}")
        lines.append(f"Overall Score:    {analysis['overall_score']}/10 {'⭐' * int(analysis['overall_score'] / 2)}")
        lines.append("")
        
        # Strengths
        lines.append("─" * 65)
        lines.append("STRENGTHS:")
        lines.append("─" * 65)
        for strength in analysis['strengths']:
            lines.append(f"  {strength}")
        lines.append("")
        
        # Weaknesses
        lines.append("─" * 65)
        lines.append("WEAKNESSES:")
        lines.append("─" * 65)
        for weakness in analysis['weaknesses']:
            lines.append(f"  {weakness}")
        lines.append("")
        
        # Recommendations
        lines.append("─" * 65)
        lines.append("RECOMMENDATIONS:")
        lines.append("─" * 65)
        for i, rec in enumerate(analysis['recommendations'], 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")
        
        if detailed:
            # Type coverage details
            lines.append("─" * 65)
            lines.append(analysis['type_coverage']['summary'])
            lines.append("")
            
            # Speed details
            lines.append("─" * 65)
            lines.append(analysis['speed_tiers']['summary'])
            lines.append("")
            
            # Role details
            lines.append("─" * 65)
            lines.append(analysis['roles']['summary'])
            lines.append("")
            
            # Synergy details
            lines.append("─" * 65)
            lines.append(analysis['synergy']['summary'])
            lines.append("")
        
        lines.append("═" * 65)
        
        return '\n'.join(lines)
    
    def compare_teams(self, team1: List[Dict], team2: List[Dict]) -> Dict:
        """
        Compare two teams side by side.
        
        Args:
            team1, team2: Teams to compare
        
        Returns:
            Dict with comparison data
        """
        analysis1 = self.analyze_team(team1)
        analysis2 = self.analyze_team(team2)
        
        return {
            'team1': analysis1,
            'team2': analysis2,
            'comparison': {
                'type_coverage': analysis1['type_coverage']['score'] - analysis2['type_coverage']['score'],
                'role_balance': analysis1['roles']['balance_score'] - analysis2['roles']['balance_score'],
                'synergy': analysis1['synergy']['team_score'] - analysis2['synergy']['team_score'],
                'overall': analysis1['overall_score'] - analysis2['overall_score']
            },
            'winner': 'Team 1' if analysis1['overall_score'] > analysis2['overall_score'] else 
                     'Team 2' if analysis2['overall_score'] > analysis1['overall_score'] else 
                     'Tie'
        }


# Example usage
if __name__ == "__main__":
    example_team = [
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
    
    analyzer = TeamAnalyzer()
    report = analyzer.generate_report(example_team)
    
    print(report)

