"""
Local Pokemon Database Loader

Loads Pokemon data from local cache built from PokeAPI.
Provides fast, offline access to Pokemon stats, moves, and abilities.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class PokemonDatabase:
    """Local Pokemon database for fast offline access"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize Pokemon database
        
        Args:
            db_path: Path to pokemon_db directory (default: data/pokemon_db)
        """
        if db_path is None:
            # Default to data/pokemon_db relative to this file
            db_path = Path(__file__).parent / "pokemon_db"
        
        self.db_path = Path(db_path)
        self.pokemon_dir = self.db_path / "pokemon"
        self.index_path = self.db_path / "index.json"
        
        # Cache for loaded Pokemon
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Load index
        self._index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the Pokemon index"""
        if not self.index_path.exists():
            logger.warning(f"Pokemon database index not found at {self.index_path}")
            logger.warning("Run 'python data/scripts/build_pokemon_db.py --vgc' to build it")
            return {'by_id': {}, 'by_name': {}, 'by_display_name': {}}
        
        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        logger.info(f"Loaded Pokemon database with {len(index['by_id'])} Pokemon")
        return index
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize Pokemon name for lookups
        
        Args:
            name: Pokemon name (e.g., "Flutter Mane", "flutter-mane", "fluttermane")
        
        Returns:
            Normalized name (e.g., "fluttermane")
        """
        return name.lower().replace(' ', '').replace('-', '').replace("'", '')
    
    def get_pokemon(self, identifier: str | int) -> Optional[Dict[str, Any]]:
        """
        Get Pokemon data by ID or name
        
        Args:
            identifier: Pokemon ID (int) or name (str)
        
        Returns:
            Pokemon data dict or None if not found
        """
        # If it's an ID
        if isinstance(identifier, int):
            if str(identifier) in self._index['by_id']:
                pokemon_name = self._index['by_id'][str(identifier)]
                return self._load_pokemon(pokemon_name)
            else:
                logger.warning(f"Pokemon #{identifier} not in database")
                return None
        
        # If it's a name, normalize it
        normalized = self.normalize_name(identifier)
        
        # Check cache first
        if normalized in self._cache:
            return self._cache[normalized]
        
        # Check if it exists in index
        if normalized in self._index['by_name']:
            return self._load_pokemon(normalized)
        
        # Try display name lookup
        for display_name, pokemon_id in self._index['by_display_name'].items():
            if self.normalize_name(display_name) == normalized:
                pokemon_name = self._index['by_id'][str(pokemon_id)]
                return self._load_pokemon(pokemon_name)
        
        logger.warning(f"Pokemon '{identifier}' not in database")
        return None
    
    def _load_pokemon(self, pokemon_name: str) -> Optional[Dict[str, Any]]:
        """
        Load Pokemon data from file
        
        Args:
            pokemon_name: Normalized Pokemon name
        
        Returns:
            Pokemon data dict
        """
        # Check cache
        if pokemon_name in self._cache:
            return self._cache[pokemon_name]
        
        # Load from file
        filepath = self.pokemon_dir / f"{pokemon_name}.json"
        if not filepath.exists():
            logger.warning(f"Pokemon file not found: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Cache it
        self._cache[pokemon_name] = data
        return data
    
    def get_base_stats(self, identifier: str | int) -> Optional[Dict[str, int]]:
        """
        Get base stats for a Pokemon
        
        Args:
            identifier: Pokemon ID or name
        
        Returns:
            Dict with hp, atk, def, spa, spd, spe
        """
        pokemon = self.get_pokemon(identifier)
        return pokemon['base_stats'] if pokemon else None
    
    def get_types(self, identifier: str | int) -> Optional[List[str]]:
        """
        Get types for a Pokemon
        
        Args:
            identifier: Pokemon ID or name
        
        Returns:
            List of types (e.g., ['Poison', 'Ghost'])
        """
        pokemon = self.get_pokemon(identifier)
        return pokemon['types'] if pokemon else None
    
    def get_abilities(self, identifier: str | int) -> Optional[Dict[str, Any]]:
        """
        Get abilities for a Pokemon
        
        Args:
            identifier: Pokemon ID or name
        
        Returns:
            Dict with 'normal' and 'hidden' abilities
        """
        pokemon = self.get_pokemon(identifier)
        if not pokemon:
            return None
        
        return {
            'normal': pokemon['abilities'],
            'hidden': pokemon['hidden_ability']
        }
    
    def get_moves(self, identifier: str | int, 
                  learn_method: str = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get moves for a Pokemon
        
        Args:
            identifier: Pokemon ID or name
            learn_method: Filter by learn method (e.g., 'level-up', 'machine', 'egg')
        
        Returns:
            List of move dicts with name, learn_method, level
        """
        pokemon = self.get_pokemon(identifier)
        if not pokemon:
            return None
        
        moves = pokemon['moves']
        
        # Filter by learn method if specified
        if learn_method:
            moves = [m for m in moves if m['learn_method'] == learn_method]
        
        return moves
    
    def get_learnset(self, identifier: str | int) -> Optional[List[str]]:
        """
        Get complete learnset (all move names) for a Pokemon
        
        Args:
            identifier: Pokemon ID or name
        
        Returns:
            List of move names
        """
        moves = self.get_moves(identifier)
        if not moves:
            return None
        
        # Return unique move names
        return sorted(set(m['name'] for m in moves))
    
    def is_available(self) -> bool:
        """Check if database is available and loaded"""
        return len(self._index['by_id']) > 0
    
    def get_pokemon_count(self) -> int:
        """Get number of Pokemon in database"""
        return len(self._index['by_id'])
    
    def list_all(self) -> List[Dict[str, Any]]:
        """
        Get list of all Pokemon in database
        
        Returns:
            List of dicts with id, name, display_name
        """
        result = []
        for pokemon_id, pokemon_name in self._index['by_id'].items():
            pokemon = self.get_pokemon(int(pokemon_id))
            if pokemon:
                result.append({
                    'id': pokemon['id'],
                    'name': pokemon['name'],
                    'display_name': pokemon['display_name']
                })
        
        return sorted(result, key=lambda x: x['id'])


# Global instance for easy access
_db_instance = None

def get_pokemon_db() -> PokemonDatabase:
    """Get global Pokemon database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = PokemonDatabase()
    return _db_instance


# Convenience functions
def get_pokemon(identifier: str | int) -> Optional[Dict[str, Any]]:
    """Get Pokemon data by ID or name"""
    return get_pokemon_db().get_pokemon(identifier)


def get_base_stats(identifier: str | int) -> Optional[Dict[str, int]]:
    """Get base stats for a Pokemon"""
    return get_pokemon_db().get_base_stats(identifier)


def get_types(identifier: str | int) -> Optional[List[str]]:
    """Get types for a Pokemon"""
    return get_pokemon_db().get_types(identifier)


def get_abilities(identifier: str | int) -> Optional[Dict[str, Any]]:
    """Get abilities for a Pokemon"""
    return get_pokemon_db().get_abilities(identifier)


def get_learnset(identifier: str | int) -> Optional[List[str]]:
    """Get complete learnset for a Pokemon"""
    return get_pokemon_db().get_learnset(identifier)

