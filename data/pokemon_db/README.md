# Pokemon Database

Local Pokemon database built from [PokeAPI](https://pokeapi.co/). Provides fast, offline access to Pokemon data during battles.

## Structure

```
pokemon_db/
├── pokemon/           # Individual Pokemon JSON files
│   ├── fluttermane.json
│   ├── ironhands.json
│   └── ...
├── index.json        # Fast lookup index
└── README.md         # This file
```

## Current Database

**47 Pokemon** - Common VGC/Doubles Pokemon

Includes:
- Paradox Pokemon (Flutter Mane, Iron Hands, Great Tusk, etc.)
- Pseudo-legendaries (Dragonite, Salamence, Garchomp, Metagross)
- VGC staples (Rillaboom, Incineroar, Landorus-Therian, Amoonguss)
- Legendary Pokemon (Calyrex forms, Treasures of Ruin)
- Regional forms (Arcanine-Hisui, Ninetales-Alola)

## Building/Updating the Database

### Fetch Common VGC Pokemon
```bash
cd foul-play
python data/scripts/build_pokemon_db.py --vgc
```

### Fetch Specific Pokemon
```bash
# By ID
python data/scripts/build_pokemon_db.py --list 1,25,94,282

# By name
python data/scripts/build_pokemon_db.py --names pikachu,charizard,flutter-mane

# Range of IDs
python data/scripts/build_pokemon_db.py --range 1-151
```

## Using the Database

### Python Code

```python
from data.pokemon_db_loader import get_pokemon_db

# Get database instance
db = get_pokemon_db()

# Get Pokemon by name
flutter_mane = db.get_pokemon('flutter-mane')
# Also works: 'Flutter Mane', 'fluttermane', 'FLUTTER-MANE'

# Get Pokemon by ID
rillaboom = db.get_pokemon(812)

# Get specific data
stats = db.get_base_stats('iron-hands')
# Returns: {'hp': 154, 'atk': 140, 'def': 108, 'spa': 50, 'spd': 68, 'spe': 50}

types = db.get_types('volcarona')
# Returns: ['Bug', 'Fire']

abilities = db.get_abilities('gholdengo')
# Returns: {'normal': ['Good As Gold'], 'hidden': None}

learnset = db.get_learnset('rillaboom')
# Returns: ['Fake Out', 'Grassy Glide', 'Wood Hammer', ...]
```

### Convenience Functions

```python
from data.pokemon_db_loader import (
    get_pokemon,
    get_base_stats,
    get_types,
    get_abilities,
    get_learnset
)

# Direct access without creating db instance
stats = get_base_stats('flutter-mane')
types = get_types(987)  # By ID
```

## Data Format

Each Pokemon file contains:

```json
{
  "id": 987,
  "name": "fluttermane",
  "display_name": "Flutter Mane",
  "types": ["Ghost", "Fairy"],
  "base_stats": {
    "hp": 55,
    "atk": 55,
    "def": 55,
    "spa": 135,
    "spd": 135,
    "spe": 135
  },
  "abilities": ["Protosynthesis"],
  "hidden_ability": null,
  "height": 14,
  "weight": 40,
  "moves": [
    {
      "name": "Moonblast",
      "learn_method": "level-up",
      "level": 42
    }
  ],
  "sprite": "https://...",
  "official_artwork": "https://..."
}
```

## Benefits Over API Calls

✅ **No network dependency** - Works offline  
✅ **Instant access** - No HTTP request delays  
✅ **Reliable** - No API downtime or rate limits  
✅ **Curated** - Only Pokemon you actually need  
✅ **Normalized names** - Handles "Flutter Mane", "flutter-mane", "fluttermane"  

## Updating Data

To add new Pokemon or update existing ones:

1. Run the build script with new Pokemon
2. Data will be merged with existing database
3. Index is automatically rebuilt

```bash
# Add Scarlet/Violet DLC Pokemon
python data/scripts/build_pokemon_db.py --names ogerpon,munkidori,fezandipiti
```

## Data Source

All data from [PokeAPI](https://pokeapi.co/) - A free, public Pokemon API.

Last Updated: 2025-11-27

