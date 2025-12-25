"""
Pokemon Database

Loads and manages VGC Pokemon data for team generation.
Provides filtering, searching, and Pokemon selection capabilities.

Phase 11 - AI Team Generator
"""

import json
import os
import random
from typing import Dict, List, Optional


class PokemonDatabase:
    """Database of VGC-legal Pokemon with stats, moves, and common sets."""
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize Pokemon database.
        
        Args:
            database_path: Path to vgc_pokemon.json, or None to use default
        """
        self.pokemon_data = self._load_database(database_path)
        self.pokemon_list = list(self.pokemon_data.keys())
    
    def _load_database(self, database_path: Optional[str] = None) -> Dict:
        """Load Pokemon database from JSON file."""
        if database_path is None:
            # Try to find the database file
            possible_paths = [
                'fp/data/vgc_pokemon.json',
                'data/vgc_pokemon.json',
                '../data/vgc_pokemon.json',
                os.path.join(os.path.dirname(__file__), '../data/vgc_pokemon.json')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    database_path = path
                    break
        
        if database_path is None or not os.path.exists(database_path):
            raise FileNotFoundError("Could not find vgc_pokemon.json database file")
        
        with open(database_path, 'r') as f:
            data = json.load(f)
            return data.get('pokemon', {})
    
    def get_pokemon(self, name: str) -> Optional[Dict]:
        """Get Pokemon data by name."""
        name_key = name.lower().replace(' ', '_').replace('-', '_')
        return self.pokemon_data.get(name_key)
    
    def get_all_pokemon(self) -> List[str]:
        """Get list of all Pokemon names."""
        return [self.pokemon_data[key]['name'] for key in self.pokemon_list]
    
    def filter_by_type(self, pokemon_type: str) -> List[Dict]:
        """Filter Pokemon by type."""
        return [
            self.pokemon_data[key] 
            for key in self.pokemon_list 
            if pokemon_type in self.pokemon_data[key]['types']
        ]
    
    def filter_by_speed(self, min_speed: int = 0, max_speed: int = 255) -> List[Dict]:
        """Filter Pokemon by speed stat range."""
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if min_speed <= self.pokemon_data[key]['base_stats']['spe'] <= max_speed
        ]
    
    def filter_by_ability(self, ability: str) -> List[Dict]:
        """Filter Pokemon by ability."""
        ability_lower = ability.lower().replace(' ', '').replace('-', '')
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if any(ability_lower in a.lower().replace(' ', '').replace('-', '') 
                   for a in self.pokemon_data[key]['abilities'])
        ]
    
    def filter_by_tier(self, tier: str) -> List[Dict]:
        """Filter Pokemon by competitive tier."""
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if self.pokemon_data[key].get('tier', '').lower() == tier.lower()
        ]
    
    def filter_restricted(self) -> List[Dict]:
        """Get only restricted Pokemon (box legendaries)."""
        return self.filter_by_tier('Restricted')
    
    def filter_non_restricted(self) -> List[Dict]:
        """Get only non-restricted Pokemon."""
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if self.pokemon_data[key].get('tier', '').lower() != 'restricted'
        ]
    
    def get_pokemon_with_move(self, move_name: str) -> List[Dict]:
        """Find Pokemon that can learn a specific move."""
        move_lower = move_name.lower().replace(' ', '').replace('-', '')
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if any(move_lower in m.lower().replace(' ', '').replace('-', '')
                   for m in self.pokemon_data[key].get('common_moves', []))
        ]
    
    def get_high_usage_pokemon(self, min_usage: float = 0.3) -> List[Dict]:
        """Get Pokemon with high usage rates."""
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if self.pokemon_data[key].get('usage_rate', 0) >= min_usage
        ]
    
    def get_top_tier_pokemon(self, min_rank: str = 'A') -> List[Dict]:
        """Get top tier Pokemon (S+, S, A+, A, etc.)."""
        tier_order = ['S+', 'S', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C']
        min_index = tier_order.index(min_rank) if min_rank in tier_order else len(tier_order)
        
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if self.pokemon_data[key].get('viability_rank', 'C') in tier_order[:min_index + 1]
        ]
    
    def random_pokemon(self, count: int = 1, **filters) -> List[Dict]:
        """
        Get random Pokemon with optional filters.
        
        Args:
            count: Number of Pokemon to return
            **filters: Optional filters (tier, type, min_speed, max_speed, etc.)
        
        Returns:
            List of random Pokemon
        """
        # Start with all Pokemon
        candidates = [self.pokemon_data[key] for key in self.pokemon_list]
        
        # Apply filters
        if 'tier' in filters:
            candidates = [p for p in candidates if p.get('tier', '').lower() == filters['tier'].lower()]
        
        if 'type' in filters:
            candidates = [p for p in candidates if filters['type'] in p['types']]
        
        if 'min_speed' in filters:
            candidates = [p for p in candidates if p['base_stats']['spe'] >= filters['min_speed']]
        
        if 'max_speed' in filters:
            candidates = [p for p in candidates if p['base_stats']['spe'] <= filters['max_speed']]
        
        if 'ability' in filters:
            ability_lower = filters['ability'].lower().replace(' ', '').replace('-', '')
            candidates = [p for p in candidates 
                         if any(ability_lower in a.lower().replace(' ', '').replace('-', '') 
                               for a in p['abilities'])]
        
        # Return random selection
        if len(candidates) == 0:
            return []
        
        return random.sample(candidates, min(count, len(candidates)))
    
    def get_bulky_pokemon(self, min_bulk: int = 200) -> List[Dict]:
        """
        Get bulky Pokemon based on HP + Def + SpD.
        
        Args:
            min_bulk: Minimum total bulk (HP + Def + SpD)
        
        Returns:
            List of bulky Pokemon
        """
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if (self.pokemon_data[key]['base_stats']['hp'] +
                self.pokemon_data[key]['base_stats']['def'] +
                self.pokemon_data[key]['base_stats']['spd']) >= min_bulk
        ]
    
    def get_offensive_pokemon(self, min_attack: int = 120) -> List[Dict]:
        """
        Get offensive Pokemon based on Attack or Sp. Attack.
        
        Args:
            min_attack: Minimum Attack or Sp. Attack stat
        
        Returns:
            List of offensive Pokemon
        """
        return [
            self.pokemon_data[key]
            for key in self.pokemon_list
            if (self.pokemon_data[key]['base_stats']['atk'] >= min_attack or
                self.pokemon_data[key]['base_stats']['spa'] >= min_attack)
        ]
    
    def build_full_pokemon(self, pokemon_data: Dict, spread_type: str = 'offensive') -> Dict:
        """
        Build a complete Pokemon dict ready for team analysis.
        
        Args:
            pokemon_data: Pokemon data from database
            spread_type: Which spread to use ('offensive', 'defensive', etc.)
        
        Returns:
            Complete Pokemon dict with stats, moves, etc.
        """
        # Get the spread
        spreads = pokemon_data.get('common_spreads', {})
        spread = spreads.get(spread_type, list(spreads.values())[0] if spreads else {})
        
        # Calculate final stats (simplified - Level 50)
        final_stats = {}
        base_stats = pokemon_data['base_stats']
        evs = spread.get('evs', {})
        nature = spread.get('nature', 'Serious')
        
        # Nature modifiers
        nature_boosts = {
            'Adamant': ('atk', 'spa'), 'Jolly': ('spe', 'spa'),
            'Modest': ('spa', 'atk'), 'Timid': ('spe', 'atk'),
            'Careful': ('spd', 'spa'), 'Impish': ('def', 'atk'),
            'Bold': ('def', 'atk'), 'Calm': ('spd', 'atk'),
            'Brave': ('atk', 'spe'), 'Quiet': ('spa', 'spe'),
            'Relaxed': ('def', 'spe'), 'Sassy': ('spd', 'spe')
        }
        
        boosted, hindered = nature_boosts.get(nature, (None, None))
        
        for stat in ['hp', 'atk', 'def', 'spa', 'spd', 'spe']:
            base = base_stats[stat]
            ev = evs.get(stat, 0)
            
            if stat == 'hp':
                final_stats[stat] = int((2 * base + ev // 4) * 50 / 100) + 60
            else:
                value = int((2 * base + ev // 4) * 50 / 100) + 5
                
                # Apply nature
                if stat == boosted:
                    value = int(value * 1.1)
                elif stat == hindered:
                    value = int(value * 0.9)
                
                final_stats[stat] = value
        
        # Select moves (take first 4 common moves)
        moves = []
        for move_name in pokemon_data.get('common_moves', [])[:4]:
            # Guess move type based on Pokemon's type or common knowledge
            move_type = self._guess_move_type(move_name, pokemon_data['types'])
            moves.append({'name': move_name, 'type': move_type})
        
        # Get ability
        abilities = pokemon_data.get('abilities', ['Unknown'])
        ability = abilities[0]  # Use first ability
        
        # Get item
        items = pokemon_data.get('common_items', ['None'])
        item = items[0]
        
        return {
            'name': pokemon_data['name'],
            'types': pokemon_data['types'],
            'stats': final_stats,
            'ability': ability,
            'item': item,
            'moves': moves
        }
    
    def _guess_move_type(self, move_name: str, pkmn_types: List[str]) -> str:
        """Guess move type based on name (simplified)."""
        move_lower = move_name.lower()
        
        # Type-based keywords
        type_keywords = {
            'fire': 'Fire', 'flame': 'Fire', 'blitz': 'Fire',
            'water': 'Water', 'hydro': 'Water',
            'grass': 'Grass', 'wood': 'Grass', 'grassy': 'Grass',
            'electric': 'Electric', 'thunder': 'Electric', 'volt': 'Electric', 'wild charge': 'Electric',
            'ice': 'Ice', 'freeze': 'Ice',
            'fighting': 'Fighting', 'combat': 'Fighting', 'punch': 'Fighting',
            'poison': 'Poison', 'sludge': 'Poison',
            'ground': 'Ground', 'earthquake': 'Ground', 'rush': 'Ground',
            'flying': 'Flying', 'storm': 'Flying',
            'psychic': 'Psychic',
            'bug': 'Bug',
            'rock': 'Rock', 'slide': 'Rock',
            'ghost': 'Ghost', 'shadow': 'Ghost', 'astral': 'Ghost',
            'dragon': 'Dragon', 'draco': 'Dragon',
            'dark': 'Dark', 'knock': 'Dark', 'snarl': 'Dark',
            'steel': 'Steel', 'metal': 'Steel', 'iron': 'Steel', 'slam': 'Steel',
            'fairy': 'Fairy', 'moonblast': 'Fairy', 'gleam': 'Fairy', 'puff': 'Fairy'
        }
        
        for keyword, move_type in type_keywords.items():
            if keyword in move_lower:
                return move_type
        
        # Default to first Pokemon type
        return pkmn_types[0] if pkmn_types else 'Normal'


# Example usage
if __name__ == '__main__':
    db = PokemonDatabase()
    
    print("Pokemon Database Test")
    print("=" * 60)
    
    # Get all Pokemon
    all_pkmn = db.get_all_pokemon()
    print(f"\nTotal Pokemon: {len(all_pkmn)}")
    print(f"Pokemon: {', '.join(all_pkmn[:5])}...")
    
    # Get restricted Pokemon
    restricted = db.filter_restricted()
    print(f"\nRestricted Pokemon: {len(restricted)}")
    for p in restricted:
        print(f"  - {p['name']} (Usage: {p['usage_rate']*100:.1f}%)")
    
    # Get high usage Pokemon
    popular = db.get_high_usage_pokemon(min_usage=0.4)
    print(f"\nHigh Usage Pokemon (40%+): {len(popular)}")
    for p in popular:
        print(f"  - {p['name']} (Usage: {p['usage_rate']*100:.1f}%)")
    
    # Get Intimidate users
    intimidate = db.filter_by_ability('Intimidate')
    print(f"\nIntimidate Users: {len(intimidate)}")
    for p in intimidate:
        print(f"  - {p['name']}")
    
    # Build a complete Pokemon
    incineroar = db.get_pokemon('Incineroar')
    if incineroar:
        complete = db.build_full_pokemon(incineroar, 'defensive')
        print(f"\nBuilt Incineroar:")
        print(f"  Stats: {complete['stats']}")
        print(f"  Moves: {[m['name'] for m in complete['moves']]}")
        print(f"  Ability: {complete['ability']}")
        print(f"  Item: {complete['item']}")

