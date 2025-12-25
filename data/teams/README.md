# Team Data Directory

This directory contains competitive Pokemon teams for various doubles formats.

## Structure

```
teams/
├── gen9vgc2024/
│   └── rental_teams.json          # VGC 2024 Regulation G teams
├── gen9doublesou/
│   └── rental_teams.json          # Gen 9 Doubles OU teams
└── README.md                       # This file
```

## Format

Each format directory contains a `rental_teams.json` file with the following structure:

```json
{
  "format": "gen9vgc2024",
  "description": "Format description",
  "last_updated": "2025-11-26",
  "teams": [
    {
      "id": "unique_team_id",
      "name": "Team Name",
      "archetype": "Trick Room|Balanced|Hyper Offense|etc.",
      "author": "Author Name",
      "winrate": 0.65,
      "usage_rank": 5,
      "paste": "https://pokepast.es/xxxxx",
      "description": "Team description",
      "core": ["Pokemon1", "Pokemon2", "Pokemon3"],
      "pokemon": [
        {
          "species": "PokemonName",
          "ability": "AbilityName",
          "item": "ItemName",
          "tera_type": "Type",
          "nature": "Nature",
          "evs": {"hp": 252, "atk": 0, "def": 4, "spa": 252, "spd": 0, "spe": 0},
          "ivs": {"hp": 31, "atk": 0, "def": 31, "spa": 31, "spd": 31, "spe": 0},
          "moves": ["Move1", "Move2", "Move3", "Move4"]
        }
        // ... 5 more Pokemon (total 6)
      ]
    }
  ]
}
```

## Current Teams

### Gen 9 VGC 2024 (5 teams)
1. **Trick Room Torkoal-Oranguru** - Classic TR with sun mode
2. **Flutter Mane + Iron Hands** - Fast hyper offense
3. **Calyrex-Shadow Hyper Offense** - Speed-based offense
4. **Rain Dance Urshifu-Rapid-Strike** - Rain weather team
5. **Miraidon Balanced Team** - Well-rounded legendary team

### Gen 9 Doubles OU (3 teams)
1. **Balanced Goodstuff** - All-around solid team
2. **Tailwind Offense** - Speed control
3. **Trick Room Control** - Slow attackers

## Adding Teams

### From Pokepaste
1. Copy team from https://pokepast.es/
2. Convert to JSON format (see structure above)
3. Add to appropriate format file
4. Give it a unique ID

### From Pikalytics
1. Go to https://pikalytics.com/
2. Find a high-usage team
3. Copy individual Pokemon sets
4. Build team JSON

### From Tournament Reports
1. Find team reports from Victory Road VGC or Smogon
2. Copy team paste
3. Convert to JSON format
4. Add metadata (author, tournament, etc.)

## Team Archetypes

Common archetypes to classify teams:
- **Balanced** - Well-rounded teams with good type coverage
- **Trick Room** - Slow teams using Trick Room
- **Hyper Offense** - Fast, aggressive teams
- **Rain** - Rain Dance weather teams
- **Sun** - Drought/Sunny Day weather teams
- **Tailwind** - Speed control with Tailwind
- **Bulky Offense** - Offensive teams with defensive pivots
- **Sand** - Sandstorm weather teams

## Team Quality Guidelines

Good teams should have:
- ✅ Proven tournament results or high ladder usage
- ✅ Clear win conditions
- ✅ Type coverage (offensive and defensive)
- ✅ Speed control options
- ✅ Answer to common threats
- ✅ Synergy between Pokemon

Avoid teams with:
- ❌ Multiple Pokemon to the same type (without good reason)
- ❌ No speed control
- ❌ No answer to common threats (e.g., Flutter Mane, Incineroar)
- ❌ Poor synergy

## Performance Tracking

Team performance is automatically tracked in `data/team_performance.json`:
```json
{
  "team_id": {
    "battles_played": 10,
    "wins": 7,
    "losses": 3,
    "last_used": "2025-11-26T12:00:00.000Z"
  }
}
```

This data is used by the `best` team selection strategy to choose the highest-performing team.

## Future Formats

You can add teams for other formats by:
1. Creating a new directory (e.g., `gen9vgc2025`)
2. Adding a `rental_teams.json` file
3. Following the same JSON structure

Supported formats (when data is added):
- `gen9vgc2025` - VGC 2025 (future)
- `gen8vgc2022` - VGC 2022 (historical)
- `gen8doublesou` - Gen 8 Doubles OU
- Any other doubles format

## Usage

Teams are loaded by the `TeamManager` class:

```python
from team_manager import TeamManager

manager = TeamManager()
manager.load_teams("gen9vgc2024")  # Load teams for this format
team = manager.get_best_team()     # Get best performing team
```

See `PHASE7_TEAM_MANAGER.md` for full usage documentation.











