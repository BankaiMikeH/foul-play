"""
Team utilities for unpacking Pokemon Showdown packed team format.
"""
import logging
from typing import List, Dict, Optional

from fp.helpers import normalize_name

logger = logging.getLogger(__name__)


def unpack_team(packed_team_string: str) -> List[Dict]:
    """
    Unpack a Pokemon Showdown packed team string into a list of Pokemon set dictionaries.
    
    Packed format: name|species|item|ability|moves|nature|evs|gender|ivs|shiny|pokeball|hiddenpowertype|gigantamax|dynamaxlevel|teratype|level|evs_alt]
    Each Pokemon is separated by ']' character.
    
    Args:
        packed_team_string: The packed team string from |showteam| message
        
    Returns:
        List of dictionaries, each containing:
        - name: Pokemon nickname (or species if no nickname)
        - species: Pokemon species name
        - item: Item name (or empty string)
        - ability: Ability name (or empty string)
        - moves: List of move names
        - nature: Nature name (or empty string)
        - evs: Tuple of 6 EV values (hp, atk, def, spa, spd, spe)
        - gender: Gender ('M', 'F', or empty string)
        - tera_type: Tera type (for Gen 9, or None)
        - level: Level (defaults to 100)
    """
    if not packed_team_string:
        return []
    
    team = []
    # Split by ']' to get individual Pokemon
    pokemon_strings = packed_team_string.split(']')
    
    for pokemon_str in pokemon_strings:
        if not pokemon_str.strip():
            continue
            
        # Split by '|' to get fields
        fields = pokemon_str.split('|')
        
        # Need at least name and some basic fields
        if len(fields) < 3:
            logger.warning(f"Invalid Pokemon string in packed team (too few fields): {pokemon_str[:50]}")
            continue
        
        # Extract fields according to packed format
        # Format: name|species|item|ability|moves|nature|evs|gender|ivs|shiny|pokeball|hiddenpowertype|gigantamax|dynamaxlevel|level|evs_alt|teratype]
        # Actual format from logs: Flutter Mane||BoosterEnergy|Protosynthesis|Moonblast,...|...|...|...|...|...|...|...|...|...|50|,,,,,|Fairy]
        name = fields[0] if len(fields) > 0 else ""
        species = fields[1] if len(fields) > 1 and fields[1] else name  # Default to name if species is empty
        item = fields[2] if len(fields) > 2 else ""
        ability = fields[3] if len(fields) > 3 else ""
        moves_str = fields[4] if len(fields) > 4 else ""
        nature = fields[5] if len(fields) > 5 else ""
        evs_str = fields[6] if len(fields) > 6 else ""
        gender = fields[7] if len(fields) > 7 else ""
        # Fields 8-9: ivs, shiny, pokeball, hiddenpowertype, gigantamax, dynamaxlevel (may be empty)
        # Field 10: level (Gen 9 format)
        # Field 11: EVs (comma-separated) + tera type (no separator between them, e.g., ",,,,,Fairy")
        tera_type = None
        level = 100  # Default level
        
        # Check for level in field 10 (Gen 9 format)
        if len(fields) > 10:
            try:
                potential_level = int(fields[10])
                if 1 <= potential_level <= 100:
                    level = potential_level
            except (ValueError, IndexError):
                pass
        
        # Check field 11 for EVs and tera type (combined, e.g., ",,,,,Fairy")
        if len(fields) > 11 and fields[11]:
            field_11 = fields[11]
            # Split by comma to separate EVs from tera type
            # Format: ",,,,,Fairy" -> ['', '', '', '', '', 'Fairy']
            # EVs are the first 6 parts (may be empty strings), tera type is the last non-empty part
            parts = field_11.split(',')
            # EVs are the first 6 parts (may be empty strings)
            evs_parts = parts[:6]
            # Tera type is the last non-empty part in the entire list
            # Check from the end backwards to find the tera type
            for part in reversed(parts):
                if part.strip():
                    potential_tera = part.strip()
                    normalized_tera = normalize_name(potential_tera)
                    if normalized_tera in ['normal', 'fire', 'water', 'electric', 'grass', 'ice',
                                         'fighting', 'poison', 'ground', 'flying', 'psychic',
                                         'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel',
                                         'fairy', 'typeless']:
                        tera_type = normalized_tera
                        break
            # Use field 11 for EVs if it contains commas
            if ',' in field_11:
                evs_str = ','.join(evs_parts)
        
        # Parse moves (comma-separated)
        moves = [m.strip() for m in moves_str.split(',') if m.strip()] if moves_str else []
        
        # Parse EVs (comma-separated, 6 values: hp, atk, def, spa, spd, spe)
        evs_list = evs_str.split(',') if evs_str else []
        evs = tuple(int(ev) if ev.strip() and ev.strip().isdigit() else 0 for ev in evs_list[:6])
        # Pad to 6 if needed
        while len(evs) < 6:
            evs = evs + (0,)
        
        # Normalize names
        species = normalize_name(species) if species else ""
        item = normalize_name(item) if item else ""
        ability = normalize_name(ability) if ability else ""
        nature = normalize_name(nature) if nature else ""
        moves = [normalize_name(m) for m in moves]
        
        pokemon_set = {
            'name': name,
            'species': species,
            'item': item,
            'ability': ability,
            'moves': moves,
            'nature': nature,
            'evs': evs,
            'gender': gender,
            'tera_type': tera_type,
            'level': level,
        }
        
        team.append(pokemon_set)
    
    return team

