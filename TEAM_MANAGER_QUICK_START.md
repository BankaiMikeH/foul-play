# Team Manager Quick Start Guide

Quick reference for using the Team Manager system for VGC/Doubles battles.

## Installation

No additional installation needed - all dependencies are in `requirements.txt`.

## Quick Test

Test that team loading works:

```bash
cd foul-play
python team_manager.py
```

You should see:
- List of loaded teams
- Format summary
- Example team output

## Basic Usage

### 1. List Available Teams

```python
from team_manager import TeamManager

manager = TeamManager()
manager.load_teams("gen9vgc2024")

# List all teams
for team_id, name, archetype in manager.list_teams():
    print(f"{archetype:15} - {name}")
```

### 2. Select a Team

```python
# Best performing team
team = manager.get_best_team()

# Random team
team = manager.get_random_team()

# Specific archetype
team = manager.get_team_by_archetype("Trick Room")

# Specific team by ID
team = manager.get_team_by_id("miraidon_balance_1")
```

### 3. Use in Battle

```python
# Convert to formats needed
showdown_format = team.to_showdown_format()  # Text format
packed_format = team.to_packed_format()      # Packed format for API
```

### 4. Track Performance

```python
# Record battle result
manager.record_battle_result(team.id, won=True)

# Get stats
stats = manager.get_team_stats(team.id)
print(f"Winrate: {stats.winrate:.1%}")

# View all stats
all_stats = manager.get_all_team_stats()
```

## Command-Line Usage

### Example 1: Best Team Strategy (Recommended)
```bash
python run.py \
  --websocket-uri wss://sim.smogon.com/showdown/websocket \
  --ps-username YourBot \
  --ps-password YourPassword \
  --pokemon-format gen9vgc2024regg \
  --bot-mode search_ladder \
  --run-count 10 \
  --team-selection-strategy best
```

### Example 2: Rotate Through All Teams
```bash
python run.py \
  --websocket-uri wss://sim.smogon.com/showdown/websocket \
  --ps-username YourBot \
  --ps-password YourPassword \
  --pokemon-format gen9doublesou \
  --bot-mode search_ladder \
  --run-count 20 \
  --team-selection-strategy rotation
```

### Example 3: Random Teams (Testing)
```bash
python run.py \
  --websocket-uri wss://sim.smogon.com/showdown/websocket \
  --ps-username YourBot \
  --ps-password YourPassword \
  --pokemon-format gen9vgc2024 \
  --bot-mode search_ladder \
  --run-count 50 \
  --team-selection-strategy random
```

### Example 4: Test One Specific Team
```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username TestBot \
  --ps-password test123 \
  --pokemon-format gen9vgc2024 \
  --bot-mode challenge_user \
  --user-to-challenge FriendName \
  --run-count 5 \
  --team-selection-strategy specific \
  --team-id miraidon_balance_1
```

## Team Selection Strategies

| Flag Value | Description | Best For |
|------------|-------------|----------|
| `best` | Uses team with highest actual winrate | Ladder climbing |
| `random` | Random team each battle | Testing variety |
| `rotation` | Cycles through all teams evenly | Testing all teams |
| `least_used` | Team used least recently | Balanced testing |
| `archetype` | Filter by archetype (requires `--team-archetype`) | Testing playstyle |
| `specific` | One specific team (requires `--team-id`) | Practicing |

## Adding Your Own Teams

### Option 1: JSON File (Recommended)
Edit `data/teams/gen9vgc2024/rental_teams.json`:

```json
{
  "id": "my_custom_team",
  "name": "My Custom Team",
  "archetype": "Balanced",
  "author": "Me",
  "winrate": 0.50,
  "usage_rank": 999,
  "paste": "",
  "description": "My custom team",
  "core": ["Mon1", "Mon2", "Mon3"],
  "pokemon": [
    {
      "species": "Miraidon",
      "ability": "Hadron Engine",
      "item": "Life Orb",
      "tera_type": "Electric",
      "nature": "Timid",
      "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252},
      "ivs": {"hp": 31, "atk": 0, "def": 31, "spa": 31, "spd": 31, "spe": 31},
      "moves": ["Electro Drift", "Draco Meteor", "Dazzling Gleam", "Protect"]
    }
    // ... 5 more Pokemon
  ]
}
```

### Option 2: Showdown Format File
Create file in `teams/teams/gen9/vgc2024/my_team`:

```
Miraidon @ Life Orb
Ability: Hadron Engine
Tera Type: Electric
EVs: 4 HP / 252 SpA / 252 Spe
Timid Nature
- Electro Drift
- Draco Meteor
- Dazzling Gleam
- Protect

[... 5 more Pokemon ...]
```

Then use traditional team loading:
```bash
python run.py \
  --team-name gen9/vgc2024/my_team \
  ...
```

## Performance Output

After battles complete, you'll see:

```
============================================================
TEAM PERFORMANCE SUMMARY
============================================================
  [Balanced       ] Miraidon Balanced Team              |  75.0% WR (8 games) | Expected: 70.0%
  [Hyper Offense  ] Flutter Mane + Iron Hands           |  66.7% WR (6 games) | Expected: 68.0%
  [Trick Room     ] Trick Room Torkoal-Oranguru         |  60.0% WR (5 games) | Expected: 65.0%
------------------------------------------------------------
Overall: 17W-11L (60.7%)
============================================================
```

## Available Teams

### Gen 9 VGC 2024 (5 teams)
- `miraidon_balance_1` - Miraidon Balanced Team
- `flutter_iron_hands_1` - Flutter Mane + Iron Hands
- `tr_torkoal_oranguru_1` - Trick Room Torkoal-Oranguru
- `rain_urshifu_1` - Rain Dance Urshifu-Rapid-Strike
- `calyrex_shadow_1` - Calyrex-Shadow Hyper Offense

### Gen 9 Doubles OU (3 teams)
- `dou_balance_1` - Balanced Goodstuff
- `dou_tailwind_1` - Tailwind Offense
- `dou_trick_room_1` - Trick Room Control

## Common Issues

### "Could not select team"
- Make sure you've loaded teams for the format: `gen9vgc2024` not `gen9vgc2024regg`
- Check that the team JSON file exists in `data/teams/[format]/`

### "Format directory not found"
- Create the directory: `mkdir data/teams/gen9vgc2024`
- Add a `rental_teams.json` file

### Performance stats not saving
- Check write permissions on `data/` directory
- Look for `data/team_performance.json` file

## Tips

1. **Start with rotation** - Test all teams evenly to gather data
2. **Switch to best** - Once you have data, use the best-performing team
3. **Track performance** - Performance data persists between sessions
4. **Add variety** - More teams = better testing and less predictability

## Next Steps

- **Add more teams** - Import from Pikalytics, Victory Road, Pokepaste
- **Test on ladder** - Climb with your best teams
- **Analyze results** - See which archetypes perform best
- **Optimize** - Adjust teams based on performance

## Full Documentation

See `PHASE7_TEAM_MANAGER.md` for complete documentation.











