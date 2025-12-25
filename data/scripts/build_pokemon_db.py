"""
Build local Pokemon database from PokeAPI

Fetches Pokemon data from https://pokeapi.co/api/v2/pokemon/{id}
and stores it locally for offline use during battles.

Usage:
    python build_pokemon_db.py --range 1-1025          # All Pokemon
    python build_pokemon_db.py --list 25,94,282        # Specific Pokemon
    python build_pokemon_db.py --names flutter-mane,iron-hands
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fp.helpers import normalize_name


class PokeAPIFetcher:
    """Fetch Pokemon data from PokeAPI and build local database"""
    
    BASE_URL = "https://pokeapi.co/api/v2/pokemon"
    SPECIES_URL = "https://pokeapi.co/api/v2/pokemon-species"
    
    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: Directory to store Pokemon data (default: data/pokemon_db)
        """
        if output_dir is None:
            # Default to data/pokemon_db relative to this script
            script_dir = Path(__file__).parent
            output_dir = script_dir.parent / "pokemon_db"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "pokemon").mkdir(exist_ok=True)
        (self.output_dir / "species").mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PokemonBattleBot/1.0'
        })
    
    def fetch_pokemon(self, identifier: str | int) -> Dict[str, Any]:
        """
        Fetch Pokemon data from PokeAPI
        
        Args:
            identifier: Pokemon ID (int) or name (str)
        
        Returns:
            Pokemon data dict
        """
        url = f"{self.BASE_URL}/{identifier}"
        print(f"Fetching {identifier}... ", end="", flush=True)
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(f"OK {data['name']} (#{data['id']})")
            return data
        except requests.exceptions.RequestException as e:
            print(f"ERROR: {e}")
            return None
    
    def fetch_species(self, identifier: str | int) -> Dict[str, Any]:
        """
        Fetch Pokemon species data (for forms, evolution, etc.)
        
        Args:
            identifier: Species ID (int) or name (str)
        
        Returns:
            Species data dict
        """
        url = f"{self.SPECIES_URL}/{identifier}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  Warning: Could not fetch species data: {e}")
            return None
    
    def simplify_pokemon_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplify PokeAPI data to only what we need for battles
        
        Args:
            data: Full PokeAPI response
        
        Returns:
            Simplified Pokemon data
        """
        if not data:
            return None
        
        # Extract base stats
        stats = {}
        for stat_data in data['stats']:
            stat_name = stat_data['stat']['name']
            # Convert to our naming: hp, atk, def, spa, spd, spe
            stat_map = {
                'hp': 'hp',
                'attack': 'atk',
                'defense': 'def',
                'special-attack': 'spa',
                'special-defense': 'spd',
                'speed': 'spe'
            }
            if stat_name in stat_map:
                stats[stat_map[stat_name]] = stat_data['base_stat']
        
        # Extract types
        types = [t['type']['name'].capitalize() for t in sorted(data['types'], key=lambda x: x['slot'])]
        
        # Extract abilities
        abilities = []
        hidden_ability = None
        for ability_data in data['abilities']:
            ability_name = ability_data['ability']['name']
            # Convert to proper case (e.g., "poison-puppeteer" -> "Poison Puppeteer")
            ability_name = ' '.join(word.capitalize() for word in ability_name.split('-'))
            
            if ability_data['is_hidden']:
                hidden_ability = ability_name
            else:
                abilities.append(ability_name)
        
        # Extract all possible moves
        moves = []
        for move_data in data['moves']:
            move_name = move_data['move']['name']
            # Convert to proper case
            move_name = ' '.join(word.capitalize() for word in move_name.split('-'))
            
            # Get learn methods for this gen (scarlet-violet = gen 9)
            for version_detail in move_data['version_group_details']:
                if version_detail['version_group']['name'] == 'scarlet-violet':
                    moves.append({
                        'name': move_name,
                        'learn_method': version_detail['move_learn_method']['name'],
                        'level': version_detail['level_learned_at']
                    })
                    break
        
        # Build simplified data
        simplified = {
            'id': data['id'],
            'name': data['name'].replace('-', ''),  # Normalize: "flutter-mane" -> "fluttermane"
            'display_name': ' '.join(word.capitalize() for word in data['name'].split('-')),
            'types': types,
            'base_stats': stats,
            'abilities': abilities,
            'hidden_ability': hidden_ability,
            'height': data['height'],  # in decimeters
            'weight': data['weight'],  # in hectograms
            'moves': moves,
            'sprite': data['sprites']['front_default'],
            'official_artwork': data['sprites']['other']['official-artwork']['front_default']
        }
        
        return simplified
    
    def save_pokemon(self, data: Dict[str, Any]):
        """
        Save Pokemon data to local file
        
        Args:
            data: Simplified Pokemon data
        """
        if not data:
            return
        
        # Save by normalized name (e.g., "fluttermane.json")
        filename = f"{data['name']}.json"
        filepath = self.output_dir / "pokemon" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  Saved to {filepath.relative_to(self.output_dir.parent)}")
    
    def build_index(self):
        """
        Build an index file mapping names/IDs to files
        """
        index = {
            'by_id': {},
            'by_name': {},
            'by_display_name': {},
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Scan all saved Pokemon
        pokemon_dir = self.output_dir / "pokemon"
        for filepath in sorted(pokemon_dir.glob("*.json")):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            index['by_id'][data['id']] = data['name']
            index['by_name'][data['name']] = data['id']
            index['by_display_name'][data['display_name']] = data['id']
        
        # Save index
        index_path = self.output_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\nBuilt index with {len(index['by_id'])} Pokemon")
        print(f"  Saved to {index_path.relative_to(self.output_dir.parent)}")
    
    def fetch_range(self, start: int, end: int, delay: float = 0.1):
        """
        Fetch a range of Pokemon by ID
        
        Args:
            start: Starting Pokedex number
            end: Ending Pokedex number (inclusive)
            delay: Delay between requests in seconds (be nice to the API)
        """
        print(f"Fetching Pokemon #{start} to #{end}")
        print("=" * 50)
        
        for pokemon_id in range(start, end + 1):
            data = self.fetch_pokemon(pokemon_id)
            if data:
                simplified = self.simplify_pokemon_data(data)
                self.save_pokemon(simplified)
            
            # Be nice to the API
            if pokemon_id < end:
                time.sleep(delay)
        
        self.build_index()
    
    def fetch_list(self, identifiers: List[str | int], delay: float = 0.1):
        """
        Fetch specific Pokemon by ID or name
        
        Args:
            identifiers: List of Pokemon IDs or names
            delay: Delay between requests in seconds
        """
        print(f"Fetching {len(identifiers)} Pokemon")
        print("=" * 50)
        
        for i, identifier in enumerate(identifiers):
            data = self.fetch_pokemon(identifier)
            if data:
                simplified = self.simplify_pokemon_data(data)
                self.save_pokemon(simplified)
            
            # Be nice to the API
            if i < len(identifiers) - 1:
                time.sleep(delay)
        
        self.build_index()
    
    def fetch_vgc_common(self, delay: float = 0.1):
        """
        Fetch commonly used VGC Pokemon (curated list)
        """
        # Common VGC 2024-2026 Pokemon
        common_vgc = [
            # Paradox Pokemon
            "flutter-mane", "iron-hands", "iron-bundle", "roaring-moon",
            "iron-valiant", "great-tusk", "walking-wake", "gouging-fire",
            
            # Pseudo-legendaries
            "dragonite", "salamence", "garchomp", "metagross",
            
            # Common VGC staples
            "rillaboom", "incineroar", "landorus-therian", "tornadus",
            "thundurus", "amoonguss", "urshifu-rapid-strike", "urshifu-single-strike",
            
            # Utility Pokemon
            "grimmsnarl", "indeedee-female", "arcanine", "arcanine-hisui",
            "whimsicott", "talonflame",
            
            # Special attackers
            "volcarona", "chi-yu", "chien-pao", "wo-chien", "ting-lu",
            
            # Tanks/Support
            "torkoal", "oranguru", "ursaluna", "cresselia", "dondozo",
            
            # Physical attackers
            "kingambit", "baxcalibur", "annihilape", "sneasler",
            
            # Other meta picks
            "maushold", "gholdengo", "tatsugiri", "pelipper",
            "ninetales-alola", "calyrex-ice", "calyrex-shadow"
        ]
        
        print(f"Fetching {len(common_vgc)} common VGC Pokemon")
        self.fetch_list(common_vgc, delay=delay)


def main():
    parser = argparse.ArgumentParser(
        description="Build local Pokemon database from PokeAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all Pokemon
  python build_pokemon_db.py --range 1-1025
  
  # Fetch specific Pokemon by ID
  python build_pokemon_db.py --list 1,25,94,282
  
  # Fetch specific Pokemon by name
  python build_pokemon_db.py --names pikachu,charizard,flutter-mane
  
  # Fetch common VGC Pokemon
  python build_pokemon_db.py --vgc
        """
    )
    
    parser.add_argument(
        '--range',
        type=str,
        help='Range of Pokemon IDs (e.g., 1-151, 1-1025)'
    )
    
    parser.add_argument(
        '--list',
        type=str,
        help='Comma-separated list of Pokemon IDs (e.g., 1,25,94)'
    )
    
    parser.add_argument(
        '--names',
        type=str,
        help='Comma-separated list of Pokemon names (e.g., pikachu,charizard)'
    )
    
    parser.add_argument(
        '--vgc',
        action='store_true',
        help='Fetch commonly used VGC Pokemon'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory (default: data/pokemon_db)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.1,
        help='Delay between API requests in seconds (default: 0.1)'
    )
    
    args = parser.parse_args()
    
    # Create fetcher
    fetcher = PokeAPIFetcher(output_dir=args.output)
    
    # Execute based on arguments
    if args.range:
        # Parse range (e.g., "1-151")
        start, end = map(int, args.range.split('-'))
        fetcher.fetch_range(start, end, delay=args.delay)
    
    elif args.list:
        # Parse list (e.g., "1,25,94")
        ids = [int(x.strip()) for x in args.list.split(',')]
        fetcher.fetch_list(ids, delay=args.delay)
    
    elif args.names:
        # Parse names (e.g., "pikachu,charizard")
        names = [x.strip().lower() for x in args.names.split(',')]
        fetcher.fetch_list(names, delay=args.delay)
    
    elif args.vgc:
        # Fetch common VGC Pokemon
        fetcher.fetch_vgc_common(delay=args.delay)
    
    else:
        parser.print_help()
        print("\n⚠️  Please specify --range, --list, --names, or --vgc")
        sys.exit(1)


if __name__ == "__main__":
    main()

