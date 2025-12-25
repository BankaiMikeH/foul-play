"""
Role Identification System

Classifies Pokemon by their battle roles based on stats, moves, abilities, and items.

Phase 10 - Team Synergy Engine
"""

from typing import Dict, List, Set
from collections import defaultdict


class RoleIdentifier:
    """Identifies and analyzes Pokemon roles within a team."""
    
    # Role definitions
    ROLES = {
        'FAST_SWEEPER': 'High speed + high attacking stat',
        'SLOW_ATTACKER': 'High attacking stat + low speed (TR candidate)',
        'WALL': 'High defensive stats',
        'SUPPORT': 'Support moves (Tailwind, Follow Me, etc.)',
        'SPEED_CONTROL': 'Has speed control moves',
        'INTIMIDATE': 'Intimidate ability',
        'PIVOT': 'Has pivot moves (U-turn, Volt Switch, Parting Shot)',
        'SETUP_SWEEPER': 'Has setup moves + sweeping potential',
        'CLEANER': 'Fast Pokemon with priority or setup moves',
        'REDIRECTOR': 'Redirection moves (Follow Me, Rage Powder)',
        'SCREEN_SETTER': 'Sets screens (Light Screen, Reflect)',
        'TERRAIN_SETTER': 'Sets terrain',
        'WEATHER_SETTER': 'Sets weather',
        'HAZARD_SETTER': 'Sets hazards (Stealth Rock, Spikes)',
        'STATUS_SPREADER': 'Spreads status (Thunder Wave, Will-O-Wisp)',
        'TANK': 'Bulky with recovery',
    }
    
    # Move categories
    SUPPORT_MOVES = {
        'tailwind', 'trickroom', 'followme', 'ragepowder', 'helpinghand',
        'wideguard', 'quickguard', 'coaching', 'allyswitch', 'skillswap'
    }
    
    SPEED_CONTROL_MOVES = {
        'tailwind', 'trickroom', 'icywind', 'electroweb', 'stringshot',
        'rockytomb', 'bulldoze'
    }
    
    REDIRECT_MOVES = {
        'followme', 'ragepowder', 'spotlight'
    }
    
    SCREEN_MOVES = {
        'lightscreen', 'reflect', 'auroraveil'
    }
    
    TERRAIN_MOVES = {
        'electricterrain', 'grassyterrain', 'mistyterrain', 'psychicterrain'
    }
    
    WEATHER_MOVES = {
        'raindance', 'sunnyday', 'sandstorm', 'hail', 'snowscape'
    }
    
    HAZARD_MOVES = {
        'stealthrock', 'spikes', 'toxicspikes', 'stickyweb'
    }
    
    STATUS_MOVES = {
        'thunderwave', 'willowisp', 'toxic', 'stunspore', 'glare',
        'nuzzle', 'sacredsword'
    }
    
    SETUP_MOVES = {
        'swordsdance', 'nastyplot', 'dragondance', 'calmmind', 'agility',
        'bulkup', 'irondefense', 'rockpolish', 'quiverdance', 'shellsmash'
    }
    
    PIVOT_MOVES = {
        'uturn', 'voltswitch', 'partingshot', 'flipturn', 'batonpass',
        'teleport', 'chillyreception'
    }
    
    RECOVERY_MOVES = {
        'recover', 'roost', 'slackoff', 'softboiled', 'moonlight',
        'synthesis', 'morningsun', 'shoreup', 'rest', 'drainpunch',
        'gigadrain', 'leechseed'
    }
    
    PRIORITY_MOVES = {
        'fakeout', 'extremespeed', 'accelerock', 'aquajet', 'machpunch',
        'bulletpunch', 'iceshard', 'suckerpunch', 'shadowsneak',
        'grassyglide'
    }
    
    def __init__(self):
        """Initialize the role identifier."""
        pass
    
    def identify_role(self, pokemon: Dict) -> List[str]:
        """
        Identify all roles that a Pokemon fulfills.
        
        Args:
            pokemon: Dict with 'name', 'stats', 'moves', 'ability', 'item' fields
        
        Returns:
            List of role identifiers
        """
        roles = []
        stats = pokemon.get('stats', {})
        moves = pokemon.get('moves', [])
        ability = pokemon.get('ability', '').lower()
        item = pokemon.get('item', '').lower()
        
        # Get move names for checking
        move_names = {move.get('name', '').lower().replace(' ', '') for move in moves}
        
        # Check offensive roles
        atk = stats.get('atk', 0)
        spa = stats.get('spa', 0)
        spe = stats.get('spe', 0)
        highest_attack = max(atk, spa)
        
        if highest_attack >= 150:
            if spe >= 110:
                roles.append('FAST_SWEEPER')
                
                # Check if cleaner (fast + priority)
                if any(m in self.PRIORITY_MOVES for m in move_names):
                    roles.append('CLEANER')
            elif spe <= 70:
                roles.append('SLOW_ATTACKER')  # Trick Room candidate
            else:
                roles.append('FAST_SWEEPER')  # Mid-speed attacker
        
        # Check defensive roles
        hp = stats.get('hp', 0)
        def_ = stats.get('def', 0)
        spd = stats.get('spd', 0)
        
        if hp >= 170 or (def_ + spd) >= 220:
            roles.append('WALL')
            
            # Check if tank (wall + recovery)
            if any(m in self.RECOVERY_MOVES for m in move_names):
                roles.append('TANK')
        
        # Check support roles
        if any(m in self.SUPPORT_MOVES for m in move_names):
            roles.append('SUPPORT')
        
        if any(m in self.SPEED_CONTROL_MOVES for m in move_names):
            roles.append('SPEED_CONTROL')
        
        if any(m in self.REDIRECT_MOVES for m in move_names):
            roles.append('REDIRECTOR')
        
        if any(m in self.SCREEN_MOVES for m in move_names):
            roles.append('SCREEN_SETTER')
        
        if any(m in self.STATUS_MOVES for m in move_names):
            roles.append('STATUS_SPREADER')
        
        # Check setup sweeper
        if any(m in self.SETUP_MOVES for m in move_names):
            if highest_attack >= 120:  # Has sweeping potential
                roles.append('SETUP_SWEEPER')
        
        # Check pivot
        if any(m in self.PIVOT_MOVES for m in move_names):
            roles.append('PIVOT')
        
        # Check abilities
        if 'intimidate' in ability:
            roles.append('INTIMIDATE')
        
        if 'grassysurge' in ability or 'electricsurge' in ability or \
           'psychicsurge' in ability or 'mistysurge' in ability:
            roles.append('TERRAIN_SETTER')
        
        if 'drought' in ability or 'drizzle' in ability or \
           'sandstream' in ability or 'snowwarning' in ability:
            roles.append('WEATHER_SETTER')
        
        # If no roles identified, classify as generic attacker/support
        if not roles:
            if highest_attack >= 100:
                roles.append('FAST_SWEEPER' if spe >= 90 else 'SLOW_ATTACKER')
            else:
                roles.append('SUPPORT')
        
        return roles
    
    def analyze_team_roles(self, team: List[Dict]) -> Dict:
        """
        Analyze role distribution across the team.
        
        Args:
            team: List of Pokemon dicts
        
        Returns:
            Dict containing role analysis
        """
        role_distribution = defaultdict(list)
        pokemon_roles = []
        
        for pokemon in team:
            pkmn_name = pokemon.get('name', 'Unknown')
            roles = self.identify_role(pokemon)
            
            pokemon_roles.append({
                'pokemon': pkmn_name,
                'roles': roles
            })
            
            for role in roles:
                role_distribution[role].append(pkmn_name)
        
        # Calculate balance score
        balance_score = self._calculate_role_balance(role_distribution)
        
        return {
            'pokemon_roles': pokemon_roles,
            'role_distribution': dict(role_distribution),
            'balance_score': balance_score,
            'summary': self._generate_role_summary(pokemon_roles, role_distribution)
        }
    
    def _calculate_role_balance(self, role_distribution: Dict[str, List[str]]) -> float:
        """
        Calculate how well-balanced the team roles are (0-10).
        
        Good teams typically have:
        - 3-5 attackers
        - 1-3 support Pokemon
        - 1-2 speed control options
        - Some defensive presence
        """
        score = 5.0
        
        # Count key role categories
        attackers = len(set(
            role_distribution.get('FAST_SWEEPER', []) +
            role_distribution.get('SLOW_ATTACKER', []) +
            role_distribution.get('SETUP_SWEEPER', [])
        ))
        
        support = len(set(
            role_distribution.get('SUPPORT', []) +
            role_distribution.get('REDIRECTOR', [])
        ))
        
        speed_control = len(role_distribution.get('SPEED_CONTROL', []))
        
        walls = len(role_distribution.get('WALL', []))
        
        intimidate = len(role_distribution.get('INTIMIDATE', []))
        
        # Evaluate balance
        if 3 <= attackers <= 5:
            score += 1.5
        elif attackers < 2:
            score -= 2.0  # Too defensive
        elif attackers > 5:
            score -= 1.0  # Too offensive
        
        if 1 <= support <= 3:
            score += 1.5
        elif support == 0:
            score -= 1.0
        
        if speed_control >= 1:
            score += 2.0
        else:
            score -= 1.5  # No speed control is bad in doubles
        
        if walls >= 1:
            score += 0.5
        
        if intimidate >= 1:
            score += 1.0
        if intimidate >= 2:
            score += 0.5
        
        return min(10.0, max(0.0, round(score, 1)))
    
    def _generate_role_summary(self, pokemon_roles: List[Dict], 
                               role_distribution: Dict[str, List[str]]) -> str:
        """Generate human-readable role summary."""
        lines = []
        
        lines.append("TEAM ROLES:")
        for i, pr in enumerate(pokemon_roles, 1):
            roles_str = ', '.join(pr['roles'])
            lines.append(f"  {i}. {pr['pokemon']}: {roles_str}")
        
        lines.append("")
        lines.append("ROLE BALANCE:")
        
        # Count categories
        attackers = len(set(
            role_distribution.get('FAST_SWEEPER', []) +
            role_distribution.get('SLOW_ATTACKER', [])
        ))
        support = len(set(role_distribution.get('SUPPORT', [])))
        speed_control = len(role_distribution.get('SPEED_CONTROL', []))
        intimidate = len(role_distribution.get('INTIMIDATE', []))
        walls = len(role_distribution.get('WALL', []))
        
        lines.append(f"  • Attackers: {attackers}/6")
        lines.append(f"  • Support: {support}/6")
        lines.append(f"  • Speed Control: {speed_control}/6")
        lines.append(f"  • Intimidate: {intimidate}/6")
        lines.append(f"  • Walls: {walls}/6")
        
        # Recommendations
        lines.append("")
        lines.append("ASSESSMENT:")
        
        if attackers >= 4:
            lines.append("  ✅ Good offensive pressure")
        elif attackers <= 2:
            lines.append("  ⚠️ Low offensive pressure")
        
        if support >= 1:
            lines.append("  ✅ Has support options")
        else:
            lines.append("  ❌ No support Pokemon")
        
        if speed_control >= 1:
            lines.append(f"  ✅ Speed control: {', '.join(role_distribution['SPEED_CONTROL'])}")
        else:
            lines.append("  ❌ No speed control (critical weakness!)")
        
        if intimidate >= 1:
            lines.append(f"  ✅ Intimidate: {', '.join(role_distribution['INTIMIDATE'])}")
        
        return '\n'.join(lines)
    
    def suggest_role_additions(self, team: List[Dict]) -> List[str]:
        """Suggest what roles the team is missing."""
        analysis = self.analyze_team_roles(team)
        roles = analysis['role_distribution']
        suggestions = []
        
        # Check for missing critical roles
        if 'SPEED_CONTROL' not in roles:
            suggestions.append("⚠️ CRITICAL: Add Tailwind or Trick Room user")
        
        if 'INTIMIDATE' not in roles:
            suggestions.append("Consider adding Intimidate support")
        
        if 'SUPPORT' not in roles and 'REDIRECTOR' not in roles:
            suggestions.append("Consider adding support Pokemon (Follow Me, Helping Hand)")
        
        attackers = len(set(
            roles.get('FAST_SWEEPER', []) +
            roles.get('SLOW_ATTACKER', [])
        ))
        
        if attackers < 3:
            suggestions.append("Add more offensive threats")
        elif attackers > 5:
            suggestions.append("Team may be too offensive, consider defensive options")
        
        if 'WALL' not in roles and 'TANK' not in roles:
            suggestions.append("Consider adding a bulky Pokemon for defensive matchups")
        
        if not suggestions:
            return ["✅ Team role distribution looks good!"]
        
        return suggestions


# Example usage
if __name__ == "__main__":
    example_team = [
        {
            'name': 'Flutter Mane',
            'stats': {'hp': 131, 'atk': 54, 'def': 75, 'spa': 187, 'spd': 155, 'spe': 205},
            'ability': 'Protosynthesis',
            'item': 'Booster Energy',
            'moves': [
                {'name': 'Moonblast'},
                {'name': 'Shadow Ball'},
                {'name': 'Protect'}
            ]
        },
        {
            'name': 'Iron Hands',
            'stats': {'hp': 261, 'atk': 211, 'def': 128, 'spa': 49, 'spd': 89, 'spe': 70},
            'ability': 'Quark Drive',
            'item': 'Assault Vest',
            'moves': [
                {'name': 'Fake Out'},
                {'name': 'Close Combat'},
                {'name': 'Wild Charge'}
            ]
        },
        {
            'name': 'Rillaboom',
            'stats': {'hp': 207, 'atk': 194, 'def': 110, 'spa': 58, 'spd': 91, 'spe': 105},
            'ability': 'Grassy Surge',
            'item': 'Miracle Seed',
            'moves': [
                {'name': 'Fake Out'},
                {'name': 'Grassy Glide'},
                {'name': 'Wood Hammer'},
                {'name': 'U-turn'}
            ]
        },
        {
            'name': 'Incineroar',
            'stats': {'hp': 202, 'atk': 136, 'def': 110, 'spa': 76, 'spd': 156, 'spe': 80},
            'ability': 'Intimidate',
            'item': 'Sitrus Berry',
            'moves': [
                {'name': 'Fake Out'},
                {'name': 'Knock Off'},
                {'name': 'Flare Blitz'},
                {'name': 'Parting Shot'}
            ]
        },
        {
            'name': 'Gholdengo',
            'stats': {'hp': 194, 'atk': 58, 'def': 115, 'spa': 203, 'spd': 112, 'spe': 104},
            'ability': 'Good as Gold',
            'item': 'Leftovers',
            'moves': [
                {'name': 'Make It Rain'},
                {'name': 'Shadow Ball'},
                {'name': 'Protect'},
                {'name': 'Nasty Plot'}
            ]
        },
        {
            'name': 'Landorus-Therian',
            'stats': {'hp': 165, 'atk': 197, 'def': 110, 'spa': 99, 'spd': 100, 'spe': 157},
            'ability': 'Intimidate',
            'item': 'Choice Scarf',
            'moves': [
                {'name': 'Earthquake'},
                {'name': 'Rock Slide'},
                {'name': 'U-turn'}
            ]
        }
    ]
    
    identifier = RoleIdentifier()
    results = identifier.analyze_team_roles(example_team)
    
    print("=" * 60)
    print("ROLE ANALYSIS")
    print("=" * 60)
    print(results['summary'])
    print()
    print(f"Role Balance Score: {results['balance_score']}/10")
    print()
    
    suggestions = identifier.suggest_role_additions(example_team)
    print("SUGGESTIONS:")
    for suggestion in suggestions:
        print(f"  {suggestion}")

