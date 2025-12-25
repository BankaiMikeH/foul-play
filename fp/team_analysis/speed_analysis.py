"""
Speed Tier Analyzer

Analyzes speed relationships and turn order for Pokemon teams.
Accounts for different speed modifiers and scenarios.

Phase 10 - Team Synergy Engine
"""

from typing import Dict, List, Tuple
from collections import defaultdict


class SpeedTierAnalyzer:
    """Analyzes speed tiers and turn order for Pokemon teams."""
    
    # Common speed modifiers
    SPEED_MODIFIERS = {
        'normal': 1.0,
        'tailwind': 2.0,
        'trick_room': -1.0,  # Negative to reverse order
        'choice_scarf': 1.5,
        'paralyzed': 0.5,
        'icy_wind': 0.5,  # After Icy Wind hit
        'electroweb': 0.5,  # After Electroweb hit
        'sticky_web': 0.75,  # After switching into Sticky Web
    }
    
    # Common priority levels
    PRIORITY_LEVELS = {
        'fake_out': 3,
        'extremespeed': 2,
        'accelerock': 2,
        'aquajet': 1,
        'machpunch': 1,
        'bulletpunch': 1,
        'iceshardsucker punch': 1,
        'suckerpunch': 1,
        'shadowsneak': 1,
        'grassyglide': 0,  # Priority in Grassy Terrain
        'protect': 4,
        'detect': 4,
        'kingsshield': 4,
    }
    
    def __init__(self):
        """Initialize the speed tier analyzer."""
        self.meta_speeds = self._load_meta_speeds()
    
    def _load_meta_speeds(self) -> Dict[str, int]:
        """
        Load common meta Pokemon speeds for comparison.
        
        Returns:
            Dict mapping Pokemon names to their common speed stats
        """
        # VGC 2026 Reg F common speeds (level 50, typical spreads)
        return {
            # Restricted Pokemon
            'miraidon': 220,  # Timid
            'koraidon': 185,  # Jolly
            'calyrex-shadow': 185,  # Timid
            'calyrex-ice': 90,  # Brave (TR)
            'zacian': 198,  # Jolly
            'zamazenta': 198,  # Jolly
            
            # Fast threats
            'flutter_mane': 205,  # Timid + Protosynthesis
            'iron_bundle': 192,  # Timid
            'tornadus': 177,  # Timid
            'chi-yu': 185,  # Timid
            
            # Mid-speed threats
            'landorus': 157,  # Jolly
            'rillaboom': 105,  # Adamant
            'incineroar': 80,  # Careful
            'amoonguss': 50,  # Sassy
            
            # Slow threats
            'iron_hands': 70,  # Adamant
            'torkoal': 40,  # Quiet
            'cresselia': 105,  # Bold
            
            # Common Scarf users
            'landorus_scarf': 235,  # Jolly + Scarf
            'chi-yu_scarf': 277,  # Timid + Scarf
        }
    
    def analyze_team_speeds(self, team: List[Dict]) -> Dict:
        """
        Analyze speed tiers for the entire team.
        
        Args:
            team: List of Pokemon dicts with 'name', 'stats', 'item', 'moves' fields
        
        Returns:
            Dict containing speed analysis
        """
        speed_tiers = []
        
        for pokemon in team:
            tier_data = self._analyze_pokemon_speed(pokemon)
            speed_tiers.append(tier_data)
        
        # Sort by normal speed (descending)
        speed_tiers.sort(key=lambda x: x['speeds']['normal'], reverse=True)
        
        # Analyze speed control options
        speed_control = self._analyze_speed_control(team)
        
        # Compare to meta
        meta_comparison = self._compare_to_meta(speed_tiers)
        
        return {
            'team_speeds': speed_tiers,
            'speed_control': speed_control,
            'meta_comparison': meta_comparison,
            'summary': self._generate_speed_summary(speed_tiers, speed_control)
        }
    
    def _analyze_pokemon_speed(self, pokemon: Dict) -> Dict:
        """Analyze a single Pokemon's speed in different scenarios."""
        base_speed = pokemon.get('stats', {}).get('spe', 100)
        item = pokemon.get('item', '').lower()
        ability = pokemon.get('ability', '').lower()
        
        # Calculate speed in different scenarios
        speeds = {}
        
        for scenario, modifier in self.SPEED_MODIFIERS.items():
            if scenario == 'trick_room':
                speeds[scenario] = -base_speed  # Negative for TR
            elif scenario == 'choice_scarf':
                # Only if holding Choice Scarf
                if 'scarf' in item:
                    speeds[scenario] = int(base_speed * modifier)
                else:
                    speeds[scenario] = base_speed
            else:
                speeds[scenario] = int(base_speed * modifier)
        
        # Handle Protosynthesis/Quark Drive speed boost
        if ability in ['protosynthesis', 'quarkdrive']:
            speeds['boosted'] = int(base_speed * 1.5)
        
        # Identify priority moves
        priority_moves = self._get_priority_moves(pokemon)
        
        return {
            'pokemon': pokemon.get('name', 'Unknown'),
            'base_speed': base_speed,
            'speeds': speeds,
            'priority_moves': priority_moves,
            'item': item,
            'ability': ability
        }
    
    def _get_priority_moves(self, pokemon: Dict) -> List[Dict]:
        """Identify priority moves on a Pokemon."""
        priority_moves = []
        
        for move in pokemon.get('moves', []):
            move_name = move.get('name', '').lower().replace(' ', '')
            
            if move_name in self.PRIORITY_LEVELS:
                priority_moves.append({
                    'move': move.get('name'),
                    'priority': self.PRIORITY_LEVELS[move_name]
                })
            
            # Special case: Grassy Glide gets priority in Grassy Terrain
            if move_name == 'grassyglide':
                priority_moves.append({
                    'move': move.get('name'),
                    'priority': 0,
                    'note': 'Priority in Grassy Terrain'
                })
        
        return sorted(priority_moves, key=lambda x: -x['priority'])
    
    def _analyze_speed_control(self, team: List[Dict]) -> Dict:
        """Identify speed control options on the team."""
        control_options = {
            'tailwind': [],
            'trick_room': [],
            'icy_wind': [],
            'electroweb': [],
            'choice_scarf': [],
            'priority_moves': [],
            'paralysis': []
        }
        
        for pokemon in team:
            pkmn_name = pokemon.get('name', 'Unknown')
            item = pokemon.get('item', '').lower()
            
            # Check for speed control moves
            for move in pokemon.get('moves', []):
                move_name = move.get('name', '').lower().replace(' ', '')
                
                if move_name == 'tailwind':
                    control_options['tailwind'].append(pkmn_name)
                elif move_name == 'trickroom':
                    control_options['trick_room'].append(pkmn_name)
                elif move_name == 'icywind':
                    control_options['icy_wind'].append(pkmn_name)
                elif move_name == 'electroweb':
                    control_options['electroweb'].append(pkmn_name)
                elif move_name in ['thunderwave', 'stunspore', 'glare']:
                    control_options['paralysis'].append(pkmn_name)
            
            # Check for Choice Scarf
            if 'scarf' in item:
                control_options['choice_scarf'].append(pkmn_name)
            
            # Check for priority moves
            priority = self._get_priority_moves(pokemon)
            if priority:
                control_options['priority_moves'].append({
                    'pokemon': pkmn_name,
                    'moves': priority
                })
        
        return control_options
    
    def _compare_to_meta(self, team_speeds: List[Dict]) -> Dict:
        """Compare team speeds to common meta threats."""
        comparisons = []
        
        for threat_name, threat_speed in sorted(self.meta_speeds.items(), key=lambda x: -x[1]):
            faster_than = []
            slower_than = []
            
            for pkmn in team_speeds:
                pkmn_speed = pkmn['speeds']['normal']
                pkmn_name = pkmn['pokemon']
                
                if pkmn_speed > threat_speed:
                    faster_than.append(pkmn_name)
                else:
                    slower_than.append(pkmn_name)
                
                # Check if Scarf would outspeed
                scarf_speed = pkmn['speeds'].get('choice_scarf', pkmn_speed)
                if scarf_speed > threat_speed and pkmn_speed <= threat_speed:
                    faster_than.append(f"{pkmn_name} (Scarf)")
            
            comparisons.append({
                'threat': threat_name,
                'speed': threat_speed,
                'faster_than': faster_than,
                'slower_than': slower_than,
                'coverage': len(faster_than)
            })
        
        return sorted(comparisons, key=lambda x: -x['speed'])
    
    def _generate_speed_summary(self, speed_tiers: List[Dict], speed_control: Dict) -> str:
        """Generate human-readable speed summary."""
        lines = []
        
        lines.append("SPEED TIER ANALYSIS:")
        for i, tier in enumerate(speed_tiers, 1):
            speed = tier['speeds']['normal']
            pkmn = tier['pokemon']
            
            # Add modifiers
            modifiers = []
            if 'scarf' in tier['item']:
                scarf_speed = tier['speeds'].get('choice_scarf', speed)
                modifiers.append(f"Scarf: {scarf_speed}")
            if tier['ability'] in ['protosynthesis', 'quarkdrive']:
                boosted = tier['speeds'].get('boosted', speed)
                modifiers.append(f"Boosted: {boosted}")
            
            mod_str = f" ({', '.join(modifiers)})" if modifiers else ""
            lines.append(f"  {i}. {pkmn}: {speed}{mod_str}")
            
            # Show priority moves
            if tier['priority_moves']:
                for pm in tier['priority_moves'][:2]:
                    priority = pm['priority']
                    move_name = pm['move']
                    lines.append(f"     • {move_name} (Priority +{priority})")
        
        lines.append("")
        lines.append("SPEED CONTROL OPTIONS:")
        
        if speed_control['tailwind']:
            lines.append(f"  ✅ Tailwind: {', '.join(speed_control['tailwind'])}")
        else:
            lines.append("  ❌ No Tailwind")
        
        if speed_control['trick_room']:
            lines.append(f"  ✅ Trick Room: {', '.join(speed_control['trick_room'])}")
        else:
            lines.append("  ❌ No Trick Room")
        
        if speed_control['choice_scarf']:
            lines.append(f"  ✅ Choice Scarf: {', '.join(speed_control['choice_scarf'])}")
        
        if speed_control['icy_wind']:
            lines.append(f"  ✅ Icy Wind: {', '.join(speed_control['icy_wind'])}")
        
        if speed_control['priority_moves']:
            count = len(speed_control['priority_moves'])
            lines.append(f"  ✅ Priority moves on {count} Pokemon")
        
        return '\n'.join(lines)
    
    def calculate_speed_score(self, team: List[Dict]) -> float:
        """
        Calculate a score (0-10) for team's speed positioning.
        
        Factors:
        - Speed diversity (good to have fast and slow options)
        - Speed control availability
        - Priority move access
        """
        analysis = self.analyze_team_speeds(team)
        score = 5.0  # Start at 5
        
        # Check speed diversity
        speeds = [t['speeds']['normal'] for t in analysis['team_speeds']]
        if speeds:
            speed_range = max(speeds) - min(speeds)
            if speed_range > 100:
                score += 1.5  # Good diversity
            elif speed_range < 30:
                score -= 1.0  # Too similar
        
        # Check speed control options
        control = analysis['speed_control']
        if control['tailwind']:
            score += 1.5
        if control['trick_room']:
            score += 1.5
        if control['choice_scarf']:
            score += 0.5
        if control['icy_wind'] or control['electroweb']:
            score += 0.5
        if control['priority_moves']:
            score += 1.0
        
        # Cap at 10
        return min(10.0, round(score, 1))


# Example usage
if __name__ == "__main__":
    example_team = [
        {
            'name': 'Flutter Mane',
            'stats': {'spe': 205},
            'item': 'Booster Energy',
            'ability': 'Protosynthesis',
            'moves': [
                {'name': 'Moonblast'},
                {'name': 'Shadow Ball'},
                {'name': 'Protect'}
            ]
        },
        {
            'name': 'Landorus-T',
            'stats': {'spe': 157},
            'item': 'Choice Scarf',
            'ability': 'Intimidate',
            'moves': [
                {'name': 'Earthquake'},
                {'name': 'Rock Slide'},
                {'name': 'U-turn'}
            ]
        },
        {
            'name': 'Incineroar',
            'stats': {'spe': 80},
            'item': 'Sitrus Berry',
            'ability': 'Intimidate',
            'moves': [
                {'name': 'Fake Out'},
                {'name': 'Knock Off'},
                {'name': 'Flare Blitz'}
            ]
        },
        {
            'name': 'Iron Hands',
            'stats': {'spe': 70},
            'item': 'Assault Vest',
            'ability': 'Quark Drive',
            'moves': [
                {'name': 'Fake Out'},
                {'name': 'Close Combat'},
                {'name': 'Wild Charge'}
            ]
        }
    ]
    
    analyzer = SpeedTierAnalyzer()
    results = analyzer.analyze_team_speeds(example_team)
    
    print("=" * 60)
    print("SPEED TIER ANALYSIS")
    print("=" * 60)
    print(results['summary'])
    print()
    
    score = analyzer.calculate_speed_score(example_team)
    print(f"Speed Score: {score}/10")
    print()
    
    # Show meta comparisons
    print("META COMPARISONS (Top Threats):")
    for comparison in results['meta_comparison'][:5]:
        threat = comparison['threat']
        speed = comparison['speed']
        faster = len(comparison['faster_than'])
        print(f"  {threat} ({speed}): {faster}/4 Pokemon faster")

