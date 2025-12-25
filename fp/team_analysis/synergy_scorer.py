"""
Synergy Scorer

Calculates how well Pokemon work together based on type synergy,
move synergy, ability synergy, and speed relationships.

Phase 10 - Team Synergy Engine
"""

from typing import Dict, List, Tuple
import json
import os


class SynergyScorer:
    """Calculates synergy scores between Pokemon pairs and for the team."""
    
    def __init__(self):
        """Initialize synergy scorer with type chart."""
        self.type_chart = self._load_type_chart()
    
    def _load_type_chart(self) -> Dict:
        """Load type effectiveness chart."""
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
        
        # Return minimal chart if not found
        return {'type_effectiveness': {}, 'all_types': []}
    
    def calculate_pair_synergy(self, pokemon1: Dict, pokemon2: Dict) -> Dict:
        """
        Calculate synergy score between two Pokemon.
        
        Args:
            pokemon1, pokemon2: Pokemon dicts with stats, moves, ability, types
        
        Returns:
            Dict with synergy score and breakdown
        """
        score = 0
        details = []
        
        # Type synergy (does P1 cover P2's weaknesses?)
        type_synergy, type_details = self._calculate_type_synergy(pokemon1, pokemon2)
        score += type_synergy
        details.extend(type_details)
        
        # Speed synergy (can they position well together?)
        speed_synergy, speed_details = self._calculate_speed_synergy(pokemon1, pokemon2)
        score += speed_synergy
        details.extend(speed_details)
        
        # Move synergy (combo potential)
        move_synergy, move_details = self._calculate_move_synergy(pokemon1, pokemon2)
        score += move_synergy
        details.extend(move_details)
        
        # Ability synergy
        ability_synergy, ability_details = self._calculate_ability_synergy(pokemon1, pokemon2)
        score += ability_synergy
        details.extend(ability_details)
        
        return {
            'score': score,
            'details': details,
            'breakdown': {
                'type': type_synergy,
                'speed': speed_synergy,
                'move': move_synergy,
                'ability': ability_synergy
            }
        }
    
    def _calculate_type_synergy(self, pkmn1: Dict, pkmn2: Dict) -> Tuple[float, List[str]]:
        """Calculate defensive type synergy."""
        score = 0.0
        details = []
        
        # Get weaknesses of pkmn2
        pkmn2_weaknesses = self._get_weaknesses(pkmn2.get('types', []))
        
        # Check if pkmn1 can hit those threats
        pkmn1_moves = pkmn1.get('moves', [])
        
        coverage_count = 0
        for weakness in pkmn2_weaknesses:
            for move in pkmn1_moves:
                move_type = move.get('type', '').lower()
                if move_type == weakness.lower():
                    coverage_count += 1
                    score += 5.0
                    details.append(f"✅ {pkmn1.get('name')} covers {pkmn2.get('name')}'s {weakness} weakness")
                    break
        
        # Check reciprocal coverage
        pkmn1_weaknesses = self._get_weaknesses(pkmn1.get('types', []))
        pkmn2_moves = pkmn2.get('moves', [])
        
        for weakness in pkmn1_weaknesses:
            for move in pkmn2_moves:
                move_type = move.get('type', '').lower()
                if move_type == weakness.lower():
                    score += 5.0
                    details.append(f"✅ {pkmn2.get('name')} covers {pkmn1.get('name')}'s {weakness} weakness")
                    break
        
        return score, details
    
    def _calculate_speed_synergy(self, pkmn1: Dict, pkmn2: Dict) -> Tuple[float, List[str]]:
        """Calculate speed relationship synergy."""
        score = 0.0
        details = []
        
        speed1 = pkmn1.get('stats', {}).get('spe', 100)
        speed2 = pkmn2.get('stats', {}).get('spe', 100)
        
        speed_diff = abs(speed1 - speed2)
        
        # Similar speeds = good for synchronized plays
        if speed_diff < 20:
            score += 5.0
            details.append(f"✅ Similar speeds ({speed1} vs {speed2}) - good positioning")
        
        # Very different speeds = good for speed control
        elif speed_diff > 100:
            score += 3.0
            details.append(f"✅ Speed diversity ({speed1} vs {speed2}) - TR or Tailwind flexibility")
        
        # Check if one has Fake Out (enables slower Pokemon setup)
        pkmn1_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn1.get('moves', [])}
        pkmn2_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn2.get('moves', [])}
        
        has_setup_p1 = any(m in ['nastyplot', 'swordsdance', 'dragondance', 'calmmind'] for m in pkmn1_moves)
        has_setup_p2 = any(m in ['nastyplot', 'swordsdance', 'dragondance', 'calmmind'] for m in pkmn2_moves)
        
        if 'fakeout' in pkmn1_moves and has_setup_p2:
            score += 10.0
            details.append(f"✅ {pkmn1.get('name')} Fake Out enables {pkmn2.get('name')} setup")
        
        if 'fakeout' in pkmn2_moves and has_setup_p1:
            score += 10.0
            details.append(f"✅ {pkmn2.get('name')} Fake Out enables {pkmn1.get('name')} setup")
        
        return score, details
    
    def _calculate_move_synergy(self, pkmn1: Dict, pkmn2: Dict) -> Tuple[float, List[str]]:
        """Calculate move combo synergy."""
        score = 0.0
        details = []
        
        pkmn1_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn1.get('moves', [])}
        pkmn2_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn2.get('moves', [])}
        
        # Helping Hand combos
        if 'helpinghand' in pkmn1_moves:
            # Check if pkmn2 is a sweeper
            atk2 = pkmn2.get('stats', {}).get('atk', 0)
            spa2 = pkmn2.get('stats', {}).get('spa', 0)
            if max(atk2, spa2) >= 150:
                score += 10.0
                details.append(f"✅ {pkmn1.get('name')} Helping Hand boosts {pkmn2.get('name')} (sweeper)")
        
        if 'helpinghand' in pkmn2_moves:
            atk1 = pkmn1.get('stats', {}).get('atk', 0)
            spa1 = pkmn1.get('stats', {}).get('spa', 0)
            if max(atk1, spa1) >= 150:
                score += 10.0
                details.append(f"✅ {pkmn2.get('name')} Helping Hand boosts {pkmn1.get('name')} (sweeper)")
        
        # Follow Me / Rage Powder combos
        redirect_moves = {'followme', 'ragepowder'}
        has_redirect_p1 = any(m in redirect_moves for m in pkmn1_moves)
        has_redirect_p2 = any(m in redirect_moves for m in pkmn2_moves)
        
        # Check if one can redirect for the other's setup
        has_setup_p1 = any(m in ['nastyplot', 'swordsdance', 'calmmind'] for m in pkmn1_moves)
        has_setup_p2 = any(m in ['nastyplot', 'swordsdance', 'calmmind'] for m in pkmn2_moves)
        
        if has_redirect_p1 and has_setup_p2:
            score += 15.0
            details.append(f"✅ {pkmn1.get('name')} redirection enables {pkmn2.get('name')} setup")
        
        if has_redirect_p2 and has_setup_p1:
            score += 15.0
            details.append(f"✅ {pkmn2.get('name')} redirection enables {pkmn1.get('name')} setup")
        
        # Check for fragile Pokemon being protected
        hp1 = pkmn1.get('stats', {}).get('hp', 0)
        hp2 = pkmn2.get('stats', {}).get('hp', 0)
        
        if has_redirect_p1 and hp2 < 150:
            score += 8.0
            details.append(f"✅ {pkmn1.get('name')} protects fragile {pkmn2.get('name')}")
        
        if has_redirect_p2 and hp1 < 150:
            score += 8.0
            details.append(f"✅ {pkmn2.get('name')} protects fragile {pkmn1.get('name')}")
        
        return score, details
    
    def _calculate_ability_synergy(self, pkmn1: Dict, pkmn2: Dict) -> Tuple[float, List[str]]:
        """Calculate ability-based synergy."""
        score = 0.0
        details = []
        
        ability1 = pkmn1.get('ability', '').lower()
        ability2 = pkmn2.get('ability', '').lower()
        
        pkmn1_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn1.get('moves', [])}
        pkmn2_moves = {m.get('name', '').lower().replace(' ', '') for m in pkmn2.get('moves', [])}
        
        # Grassy Surge + Grassy Glide
        if ability1 == 'grassysurge' and 'grassyglide' in pkmn2_moves:
            score += 20.0
            details.append(f"✅✅ {pkmn1.get('name')} Grassy Surge enables {pkmn2.get('name')} priority Grassy Glide")
        
        if ability2 == 'grassysurge' and 'grassyglide' in pkmn1_moves:
            score += 20.0
            details.append(f"✅✅ {pkmn2.get('name')} Grassy Surge enables {pkmn1.get('name')} priority Grassy Glide")
        
        # Electric Surge + Terrain Pulse
        if ability1 == 'electricsurge' and 'terrainpulse' in pkmn2_moves:
            score += 15.0
            details.append(f"✅ {pkmn1.get('name')} Electric Surge boosts {pkmn2.get('name')} Terrain Pulse")
        
        if ability2 == 'electricsurge' and 'terrainpulse' in pkmn1_moves:
            score += 15.0
            details.append(f"✅ {pkmn2.get('name')} Electric Surge boosts {pkmn1.get('name')} Terrain Pulse")
        
        # Intimidate (helps everyone)
        if ability1 == 'intimidate':
            score += 5.0
            details.append(f"✅ {pkmn1.get('name')} Intimidate supports team")
        
        if ability2 == 'intimidate':
            score += 5.0
            details.append(f"✅ {pkmn2.get('name')} Intimidate supports team")
        
        # Double Intimidate
        if ability1 == 'intimidate' and ability2 == 'intimidate':
            score += 5.0  # Bonus for stacking
            details.append(f"✅ Double Intimidate stack!")
        
        # Weather synergies
        weather_abilities = {
            'drought': ('fire', 'solarpower'),
            'drizzle': ('water', 'swiftswim'),
            'sandstream': ('rock', 'ground', 'sandforce'),
            'snowwarning': ('ice', 'snowcloak')
        }
        
        for weather_setter, boosted_types in weather_abilities.items():
            if ability1 == weather_setter:
                pkmn2_types = {t.lower() for t in pkmn2.get('types', [])}
                if pkmn2_types.intersection(boosted_types):
                    score += 10.0
                    details.append(f"✅ {pkmn1.get('name')} {weather_setter} benefits {pkmn2.get('name')}")
            
            if ability2 == weather_setter:
                pkmn1_types = {t.lower() for t in pkmn1.get('types', [])}
                if pkmn1_types.intersection(boosted_types):
                    score += 10.0
                    details.append(f"✅ {pkmn2.get('name')} {weather_setter} benefits {pkmn1.get('name')}")
        
        return score, details
    
    def _get_weaknesses(self, types: List[str]) -> List[str]:
        """Get types that this Pokemon is weak to."""
        weaknesses = []
        
        if not types or not self.type_chart.get('type_effectiveness'):
            return weaknesses
        
        for attacking_type in self.type_chart.get('all_types', []):
            effectiveness = 1.0
            for defending_type in types:
                defending_type = defending_type.lower()
                if defending_type in self.type_chart['type_effectiveness'].get(attacking_type.lower(), {}):
                    effectiveness *= self.type_chart['type_effectiveness'][attacking_type.lower()][defending_type]
            
            if effectiveness >= 2.0:
                weaknesses.append(attacking_type)
        
        return weaknesses
    
    def analyze_team_synergy(self, team: List[Dict]) -> Dict:
        """
        Analyze synergy for the entire team.
        
        Returns:
            Dict with pair synergies and overall team synergy
        """
        pair_synergies = []
        
        # Calculate all pair combinations
        for i, pkmn1 in enumerate(team):
            for j, pkmn2 in enumerate(team):
                if i < j:  # Avoid duplicates
                    synergy = self.calculate_pair_synergy(pkmn1, pkmn2)
                    pair_synergies.append({
                        'pair': f"{pkmn1.get('name')} + {pkmn2.get('name')}",
                        'pokemon1': pkmn1.get('name'),
                        'pokemon2': pkmn2.get('name'),
                        'score': synergy['score'],
                        'details': synergy['details']
                    })
        
        # Sort by synergy score
        pair_synergies.sort(key=lambda x: -x['score'])
        
        # Calculate overall team synergy score
        total_score = sum(p['score'] for p in pair_synergies)
        max_possible = len(pair_synergies) * 50  # Assume max 50 points per pair
        team_score = min(10.0, (total_score / max_possible) * 10) if max_possible > 0 else 5.0
        
        return {
            'pair_synergies': pair_synergies,
            'team_score': round(team_score, 1),
            'top_pairs': pair_synergies[:5],
            'summary': self._generate_synergy_summary(pair_synergies)
        }
    
    def _generate_synergy_summary(self, pair_synergies: List[Dict]) -> str:
        """Generate human-readable synergy summary."""
        lines = []
        
        lines.append("TOP SYNERGY PAIRS:")
        
        for i, pair in enumerate(pair_synergies[:5], 1):
            lines.append(f"\n{i}. {pair['pair']} (Score: {pair['score']:.1f})")
            for detail in pair['details'][:3]:  # Show top 3 details
                lines.append(f"   {detail}")
        
        return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    example_team = [
        {
            'name': 'Rillaboom',
            'types': ['Grass'],
            'stats': {'hp': 207, 'atk': 194, 'def': 110, 'spa': 58, 'spd': 91, 'spe': 105},
            'ability': 'Grassy Surge',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Grassy Glide', 'type': 'Grass'},
                {'name': 'Wood Hammer', 'type': 'Grass'},
                {'name': 'U-turn', 'type': 'Bug'}
            ]
        },
        {
            'name': 'Iron Hands',
            'types': ['Fighting', 'Electric'],
            'stats': {'hp': 261, 'atk': 211, 'def': 128, 'spa': 49, 'spd': 89, 'spe': 70},
            'ability': 'Quark Drive',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Close Combat', 'type': 'Fighting'},
                {'name': 'Wild Charge', 'type': 'Electric'},
                {'name': 'Heavy Slam', 'type': 'Steel'}
            ]
        },
        {
            'name': 'Incineroar',
            'types': ['Fire', 'Dark'],
            'stats': {'hp': 202, 'atk': 136, 'def': 110, 'spa': 76, 'spd': 156, 'spe': 80},
            'ability': 'Intimidate',
            'moves': [
                {'name': 'Fake Out', 'type': 'Normal'},
                {'name': 'Knock Off', 'type': 'Dark'},
                {'name': 'Flare Blitz', 'type': 'Fire'},
                {'name': 'Parting Shot', 'type': 'Dark'}
            ]
        },
        {
            'name': 'Flutter Mane',
            'types': ['Ghost', 'Fairy'],
            'stats': {'hp': 131, 'atk': 54, 'def': 75, 'spa': 187, 'spd': 155, 'spe': 205},
            'ability': 'Protosynthesis',
            'moves': [
                {'name': 'Moonblast', 'type': 'Fairy'},
                {'name': 'Shadow Ball', 'type': 'Ghost'},
                {'name': 'Protect', 'type': 'Normal'}
            ]
        }
    ]
    
    scorer = SynergyScorer()
    results = scorer.analyze_team_synergy(example_team)
    
    print("=" * 60)
    print("SYNERGY ANALYSIS")
    print("=" * 60)
    print(results['summary'])
    print()
    print(f"Team Synergy Score: {results['team_score']}/10")

