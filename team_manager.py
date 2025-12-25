"""
Team Manager for VGC/Doubles Teams

Handles loading, selection, rotation, and performance tracking of competitive doubles teams.
"""

import json
import os
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TeamPerformanceStats:
    """Track performance statistics for a team"""
    team_id: str
    battles_played: int = 0
    wins: int = 0
    losses: int = 0
    last_used: Optional[str] = None  # ISO timestamp
    
    @property
    def winrate(self) -> float:
        """Calculate current winrate"""
        if self.battles_played == 0:
            return 0.0
        return self.wins / self.battles_played
    
    def record_battle(self, won: bool):
        """Record a battle result"""
        self.battles_played += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        self.last_used = datetime.utcnow().isoformat()


@dataclass
class Team:
    """Represents a competitive Pokemon team"""
    id: str
    name: str
    format: str
    archetype: str
    author: str
    description: str
    core: List[str]
    pokemon: List[Dict]
    paste: Optional[str] = None
    expected_winrate: float = 0.5
    usage_rank: int = 999
    
    def to_showdown_format(self) -> str:
        """Convert team to Pokemon Showdown team format"""
        lines = []
        for mon in self.pokemon:
            # Species and item
            species = mon["species"]
            item = mon.get("item", "")
            if item:
                lines.append(f"{species} @ {item}")
            else:
                lines.append(species)
            
            # Ability
            ability = mon.get("ability", "")
            if ability:
                lines.append(f"Ability: {ability}")
            
            # Tera Type
            tera_type = mon.get("tera_type", "")
            if tera_type:
                lines.append(f"Tera Type: {tera_type}")
            
            # EVs
            evs = mon.get("evs", {})
            if evs and any(evs.values()):
                ev_str = " / ".join([f"{v} {k.upper()}" for k, v in evs.items() if v > 0])
                lines.append(f"EVs: {ev_str}")
            
            # Nature
            nature = mon.get("nature", "")
            if nature:
                lines.append(f"{nature} Nature")
            
            # IVs (only if not 31)
            ivs = mon.get("ivs", {})
            if ivs and any(v != 31 for v in ivs.values()):
                iv_str = " / ".join([f"{v} {k.upper()}" for k, v in ivs.items() if v != 31])
                lines.append(f"IVs: {iv_str}")
            
            # Moves
            moves = mon.get("moves", [])
            for move in moves:
                lines.append(f"- {move}")
            
            # Blank line between Pokemon
            lines.append("")
        
        return "\n".join(lines)
    
    def to_packed_format(self) -> str:
        """Convert team to packed format for Pokemon Showdown"""
        # Import here to avoid circular dependency
        from teams.team_converter import export_to_packed
        return export_to_packed(self.to_showdown_format())


class TeamManager:
    """Manages loading and selection of competitive doubles teams"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize TeamManager
        
        Args:
            data_dir: Path to data directory containing team files
        """
        if data_dir is None:
            # Default to foul-play/data directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, "data")
        
        self.data_dir = data_dir
        self.teams_dir = os.path.join(data_dir, "teams")
        self.teams: Dict[str, Team] = {}
        self.performance: Dict[str, TeamPerformanceStats] = {}
        self.current_format: Optional[str] = None
        self._rotation_index: int = 0
        
        # Load performance stats if available
        self._load_performance_stats()
    
    def load_teams(self, format_name: str) -> int:
        """
        Load teams for a specific format
        
        Args:
            format_name: Format to load teams for (e.g., 'gen9vgc2024', 'gen9doublesou')
        
        Returns:
            Number of teams loaded
        """
        self.current_format = format_name
        format_dir = os.path.join(self.teams_dir, format_name)
        
        if not os.path.exists(format_dir):
            raise ValueError(f"Format directory not found: {format_dir}")
        
        # Load rental teams JSON
        rental_teams_path = os.path.join(format_dir, "rental_teams.json")
        if os.path.exists(rental_teams_path):
            with open(rental_teams_path, 'r') as f:
                data = json.load(f)
                for team_data in data.get("teams", []):
                    team = Team(
                        id=team_data["id"],
                        name=team_data["name"],
                        format=data.get("format", format_name),
                        archetype=team_data.get("archetype", "Unknown"),
                        author=team_data.get("author", "Unknown"),
                        description=team_data.get("description", ""),
                        core=team_data.get("core", []),
                        pokemon=team_data["pokemon"],
                        paste=team_data.get("paste"),
                        expected_winrate=team_data.get("winrate", 0.5),
                        usage_rank=team_data.get("usage_rank", 999)
                    )
                    self.teams[team.id] = team
                    
                    # Initialize performance tracking if not exists
                    if team.id not in self.performance:
                        self.performance[team.id] = TeamPerformanceStats(team_id=team.id)
        
        return len(self.teams)
    
    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get a specific team by ID"""
        return self.teams.get(team_id)
    
    def get_best_team(self, min_battles: int = 5) -> Optional[Team]:
        """
        Get the team with the highest actual winrate
        
        Args:
            min_battles: Minimum number of battles required to be considered
        
        Returns:
            Team with highest winrate, or highest expected winrate if no data
        """
        # Filter teams with enough battles
        experienced_teams = [
            (team_id, self.performance[team_id].winrate)
            for team_id in self.teams.keys()
            if team_id in self.performance and self.performance[team_id].battles_played >= min_battles
        ]
        
        if experienced_teams:
            # Return team with highest actual winrate
            best_team_id = max(experienced_teams, key=lambda x: x[1])[0]
            return self.teams[best_team_id]
        else:
            # No teams with enough data, use expected winrate
            if not self.teams:
                return None
            best_team_id = max(
                self.teams.keys(),
                key=lambda tid: self.teams[tid].expected_winrate
            )
            return self.teams[best_team_id]
    
    def get_random_team(self) -> Optional[Team]:
        """Get a random team"""
        if not self.teams:
            return None
        return random.choice(list(self.teams.values()))
    
    def get_next_rotation_team(self) -> Optional[Team]:
        """Get next team in rotation order (by usage rank)"""
        if not self.teams:
            return None
        
        # Sort teams by usage rank
        sorted_teams = sorted(self.teams.values(), key=lambda t: t.usage_rank)
        
        # Get next team in rotation
        team = sorted_teams[self._rotation_index % len(sorted_teams)]
        self._rotation_index += 1
        
        return team
    
    def get_team_by_archetype(self, archetype: str) -> Optional[Team]:
        """Get a random team of a specific archetype"""
        matching_teams = [
            team for team in self.teams.values()
            if team.archetype.lower() == archetype.lower()
        ]
        
        if not matching_teams:
            return None
        
        return random.choice(matching_teams)
    
    def get_least_used_team(self) -> Optional[Team]:
        """Get the team that has been used least recently"""
        if not self.teams:
            return None
        
        # Find team with no battles or oldest last_used
        least_used_id = None
        oldest_timestamp = None
        
        for team_id in self.teams.keys():
            stats = self.performance.get(team_id)
            if stats is None or stats.battles_played == 0:
                # Never used - highest priority
                return self.teams[team_id]
            
            if oldest_timestamp is None or (stats.last_used and stats.last_used < oldest_timestamp):
                oldest_timestamp = stats.last_used
                least_used_id = team_id
        
        return self.teams.get(least_used_id) if least_used_id else None
    
    def record_battle_result(self, team_id: str, won: bool):
        """
        Record the result of a battle
        
        Args:
            team_id: ID of team that was used
            won: Whether the battle was won
        """
        if team_id not in self.performance:
            self.performance[team_id] = TeamPerformanceStats(team_id=team_id)
        
        self.performance[team_id].record_battle(won)
        
        # Save stats after each battle
        self._save_performance_stats()
    
    def get_team_stats(self, team_id: str) -> Optional[TeamPerformanceStats]:
        """Get performance statistics for a team"""
        return self.performance.get(team_id)
    
    def get_all_team_stats(self) -> Dict[str, Dict]:
        """Get performance statistics for all teams"""
        stats = {}
        for team_id, team in self.teams.items():
            perf = self.performance.get(team_id, TeamPerformanceStats(team_id=team_id))
            stats[team_id] = {
                "name": team.name,
                "archetype": team.archetype,
                "expected_winrate": team.expected_winrate,
                "actual_winrate": perf.winrate,
                "battles": perf.battles_played,
                "wins": perf.wins,
                "losses": perf.losses,
                "last_used": perf.last_used
            }
        return stats
    
    def _load_performance_stats(self):
        """Load performance statistics from file"""
        stats_file = os.path.join(self.data_dir, "team_performance.json")
        
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    for team_id, stats_data in data.items():
                        self.performance[team_id] = TeamPerformanceStats(
                            team_id=team_id,
                            battles_played=stats_data.get("battles_played", 0),
                            wins=stats_data.get("wins", 0),
                            losses=stats_data.get("losses", 0),
                            last_used=stats_data.get("last_used")
                        )
            except Exception as e:
                print(f"Warning: Could not load performance stats: {e}")
    
    def _save_performance_stats(self):
        """Save performance statistics to file"""
        stats_file = os.path.join(self.data_dir, "team_performance.json")
        
        try:
            data = {}
            for team_id, stats in self.performance.items():
                data[team_id] = {
                    "battles_played": stats.battles_played,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "last_used": stats.last_used
                }
            
            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save performance stats: {e}")
    
    def list_teams(self, sort_by: str = "usage_rank") -> List[Tuple[str, str, str]]:
        """
        List all available teams
        
        Args:
            sort_by: Field to sort by ('usage_rank', 'winrate', 'name', 'archetype')
        
        Returns:
            List of (team_id, name, archetype) tuples
        """
        teams_list = list(self.teams.values())
        
        if sort_by == "usage_rank":
            teams_list.sort(key=lambda t: t.usage_rank)
        elif sort_by == "winrate":
            teams_list.sort(key=lambda t: t.expected_winrate, reverse=True)
        elif sort_by == "name":
            teams_list.sort(key=lambda t: t.name)
        elif sort_by == "archetype":
            teams_list.sort(key=lambda t: t.archetype)
        
        return [(t.id, t.name, t.archetype) for t in teams_list]
    
    def get_format_summary(self) -> Dict:
        """Get summary statistics for the current format"""
        if not self.teams:
            return {}
        
        archetypes = {}
        for team in self.teams.values():
            arch = team.archetype
            if arch not in archetypes:
                archetypes[arch] = 0
            archetypes[arch] += 1
        
        total_battles = sum(p.battles_played for p in self.performance.values())
        total_wins = sum(p.wins for p in self.performance.values())
        
        return {
            "format": self.current_format,
            "total_teams": len(self.teams),
            "archetypes": archetypes,
            "total_battles": total_battles,
            "total_wins": total_wins,
            "overall_winrate": total_wins / total_battles if total_battles > 0 else 0.0
        }


def main():
    """Example usage of TeamManager"""
    # Initialize manager
    manager = TeamManager()
    
    # Load VGC 2024 teams
    print("Loading VGC 2024 teams...")
    count = manager.load_teams("gen9vgc2024")
    print(f"Loaded {count} teams")
    
    # List all teams
    print("\n=== Available Teams ===")
    for team_id, name, archetype in manager.list_teams():
        print(f"  [{archetype:15}] {name}")
    
    # Get best team
    print("\n=== Best Team (Expected) ===")
    best = manager.get_best_team()
    if best:
        print(f"  {best.name} ({best.archetype})")
        print(f"  Expected Winrate: {best.expected_winrate:.1%}")
        print(f"  Core: {', '.join(best.core)}")
    
    # Get format summary
    print("\n=== Format Summary ===")
    summary = manager.get_format_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Example: Convert team to Showdown format
    print("\n=== Example Team (Showdown Format) ===")
    team = manager.get_team_by_id("miraidon_balance_1")
    if team:
        print(f"Team: {team.name}")
        print("-" * 40)
        print(team.to_showdown_format()[:500] + "...")  # First 500 chars


if __name__ == "__main__":
    main()











