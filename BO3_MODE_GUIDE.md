# Best of 3 (Bo3) Mode Guide

## Overview

Bo3 Mode allows the bot to play **Best of 3 series** instead of single games. This is designed for competitive VGC play where matches are traditionally played in Bo3 format, requiring a player to win 2 games to win the series.

## What is Bo3?

In Best of 3:
- Each series consists of **up to 3 games**
- The first player to win **2 games** wins the series
- If one player wins games 1 and 2, game 3 is not played (series ends 2-0)
- If players split games 1 and 2, game 3 decides the series (final score 2-1)

## Why Use Bo3 Mode?

1. **Competitive Practice**: VGC tournaments use Bo3 format
2. **Better Testing**: Multiple games against the same opponent reveal team strengths/weaknesses
3. **Strategic Depth**: Players can adapt their strategy between games
4. **Realistic Experience**: Mirrors real VGC competition format

## Enabling Bo3 Mode

Add the `--bo3` flag to your command:

```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username YourBot \
  --ps-password YourPassword \
  --pokemon-format gen9vgc2026regf \
  --bot-mode challenge_user \
  --user-to-challenge OpponentName \
  --bo3 \
  --run-count 5
```

## Important Configuration Notes

### `--run-count` with Bo3

When Bo3 is enabled, `--run-count` specifies the **number of series** to play, not individual games.

**Example:**
```bash
--bo3 --run-count 3
```

This will play:
- **3 series** (not 3 games)
- Each series is up to 3 games
- Total games played: 6-9 games (depending on series outcomes)

### Bot Modes with Bo3

Bo3 mode works with all bot modes:

#### Challenge User (Recommended for Bo3)
```bash
--bot-mode challenge_user \
--user-to-challenge FriendName \
--bo3
```
Continuously challenges the same opponent for all games in the series.

#### Accept Challenge
```bash
--bot-mode accept_challenge \
--room-name lobby \
--bo3
```
⚠️ **Note**: Opponent must also accept multiple challenges for the series to complete.

#### Search Ladder
```bash
--bot-mode search_ladder \
--bo3
```
⚠️ **Warning**: Each ladder search may match you with a different opponent. Bo3 mode expects to play the same opponent for all games in a series. Not recommended for ladder play.

**Best Practice**: Use `challenge_user` mode for Bo3.

## VGC 2026 Regulation F

### Format Name
```bash
--pokemon-format gen9vgc2026regf
```

### What's Allowed in Reg F?
- Paldea, Kitakami, and Blueberry Pokédex Pokémon
- Select event-distributed Pokémon
- Pokémon transferred via Pokémon HOME
- **Restricted**: Most Legendary and Mythical Pokémon are banned

### Regulation F Timeline
- **Start**: December 1, 2025
- **End**: March 31, 2026

## Example Commands

### 1. Bo3 Challenge Mode (Recommended)
```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username MyBot \
  --ps-password MyPassword \
  --bot-mode challenge_user \
  --user-to-challenge FriendName \
  --pokemon-format gen9vgc2026regf \
  --bo3 \
  --run-count 5 \
  --team-selection-strategy rotation \
  --log-level INFO
```

**What this does:**
- Challenges "FriendName" to 5 Bo3 series (10-15 total games)
- Uses VGC 2026 Reg F format
- Rotates through available teams
- Shows detailed logs

### 2. Single Game Mode (Traditional)
```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username MyBot \
  --ps-password MyPassword \
  --bot-mode search_ladder \
  --pokemon-format gen9vgc2026regf \
  --run-count 20 \
  --team-selection-strategy best \
  --log-level INFO
```

**What this does:**
- Searches ladder for 20 individual games (not series)
- Uses VGC 2026 Reg F format
- Uses the best performing team
- No Bo3 mode (single games only)

### 3. Bo3 with Specific Team
```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username MyBot \
  --ps-password MyPassword \
  --bot-mode challenge_user \
  --user-to-challenge TestOpponent \
  --pokemon-format gen9vgc2026regf \
  --bo3 \
  --run-count 3 \
  --team-selection-strategy specific \
  --team-id miraidon_balance_1 \
  --log-level INFO
```

**What this does:**
- Plays 3 Bo3 series using only one specific team
- Good for testing a particular team composition

## Bo3 Output Example

```
==================================================
Starting Bo3 Series #1
==================================================

--- Game 1 of Series #1 ---
Series Score: 0-0
✓ Won Game 1 with team: Miraidon Balanced Team
Series Score: 1-0
Overall Record - W: 1	L: 0
Waiting 5 seconds before next game...

--- Game 2 of Series #1 ---
Series Score: 1-0
✗ Lost Game 2 with team: Miraidon Balanced Team
Series Score: 1-1
Overall Record - W: 1	L: 1
Waiting 5 seconds before next game...

--- Game 3 of Series #1 ---
Series Score: 1-1
✓ Won Game 3 with team: Miraidon Balanced Team
Series Score: 2-1

==================================================
🏆 WON Series #1 (2-1)
==================================================

Series Record: 1W - 0L
Overall Game Record: 2W - 1L
```

## Quick Start Guide

### Using the Batch File (Windows)

1. **Edit `start_test_bot.bat`**:
   ```batch
   --user-to-challenge YOUR_FRIEND_USERNAME_HERE
   ```
   Replace with your friend's Pokemon Showdown username.

2. **Run the batch file**:
   ```
   start_test_bot.bat
   ```

3. **The bot will**:
   - Challenge your friend to Bo3 series
   - Play up to 5 series (configurable with `--run-count`)
   - Use VGC 2026 Reg F format
   - Show series scores after each game

## Team Selection with Bo3

You can use different team selection strategies with Bo3 mode:

### Best Team (`--team-selection-strategy best`)
Uses the team with the highest win rate for all games in the series.

### Rotation (`--team-selection-strategy rotation`)
**Recommended for Bo3**: Cycles through different teams, which:
- Tests multiple team compositions
- Adapts to opponent's strategy
- Provides variety in gameplay

### Random (`--team-selection-strategy random`)
Selects a random team for each game. Good for testing but less strategic.

### Specific (`--team-selection-strategy specific --team-id TEAM_ID`)
Uses one specific team for all games. Best for focused team testing.

## Tips for Bo3 Play

### 1. Team Selection Strategy
Consider changing teams between games in a series:
- Game 1: Use your "safe" team to scout opponent
- Game 2+: Adapt based on opponent's style

**To manually control this**: Use specific team selection and manually change the team between series.

### 2. Understanding Series Dynamics
- **2-0 Victory**: Dominant performance, team matchup favors you
- **2-1 Victory**: Close match, could go either way with different RNG
- **0-2 Loss**: Opponent has advantage, consider team changes
- **1-2 Loss**: Close loss, small adjustments might turn it around

### 3. Learning from Series
After a Bo3 series, review:
- Which games did you win/lose?
- What Pokemon caused problems?
- Did your strategy work across multiple games?
- Should you adjust team/strategy for next series?

## Troubleshooting

### Issue: Opponent doesn't accept second/third challenge
**Solution**: 
- Communicate with opponent beforehand about Bo3 format
- Use `--bot-mode accept_challenge` if they prefer to send challenges
- Ensure both players understand it's a series, not single game

### Issue: Series count doesn't match games played
**Explanation**: This is normal!
- `--run-count 3` with Bo3 = 3 series
- Each series is 2-3 games
- Total games: 6-9 games

### Issue: Bot uses same team for every game
**Solution**:
- Use `--team-selection-strategy rotation` for variety
- Check that you have multiple teams loaded for the format
- Verify TeamManager is active (only works for doubles formats)

## Disabling Bo3 Mode

Simply omit the `--bo3` flag:

```bash
python run.py \
  --websocket-uri ws://localhost:8000/showdown/websocket \
  --ps-username MyBot \
  --ps-password MyPassword \
  --bot-mode search_ladder \
  --pokemon-format gen9vgc2026regf \
  --run-count 20
```

This plays 20 individual games (not series).

## Statistics Tracking

### Game-Level Stats
- **Individual Wins/Losses**: Tracked for each game
- **Team Performance**: Each game result recorded to team stats
- **Overall Record**: Total W-L across all series

### Series-Level Stats
- **Series Wins/Losses**: How many series won vs lost
- **Series Scores**: Tracked as 2-0, 2-1, 1-2, or 0-2
- **Series Count**: Number of series completed

### Example Final Output
```
Series Record: 3W - 2L
Overall Game Record: 8W - 7L

Team Performance Summary:
- Miraidon Balanced Team: 5W-3L (62.5%)
- Trick Room Squad: 3W-4L (42.9%)
```

## Summary

- **Enable Bo3**: Add `--bo3` flag
- **Best Mode**: `challenge_user` with a specific opponent
- **Run Count**: Specifies number of **series**, not games
- **Format**: Use `gen9vgc2026regf` for VGC 2026 Reg F
- **Competitive**: Bo3 mimics real VGC tournament format
- **Team Strategy**: Consider using rotation or specific teams

Happy battling! 🎮

