"""
Integration module for TeamManager with the battle system

Provides functions to seamlessly integrate team management into the battle loop.
"""

import logging
from typing import Optional, Tuple
from team_manager import TeamManager, Team

logger = logging.getLogger(__name__)


class TeamSelectionStrategy:
    """Enum for team selection strategies"""
    BEST = "best"
    RANDOM = "random"
    ROTATION = "rotation"
    LEAST_USED = "least_used"
    ARCHETYPE = "archetype"
    SPECIFIC = "specific"


class BattleTeamManager:
    """Manages team selection and tracking for battles"""
    
    def __init__(self, 
                 format_name: str,
                 strategy: str = TeamSelectionStrategy.BEST,
                 archetype: Optional[str] = None,
                 specific_team_id: Optional[str] = None):
        """
        Initialize BattleTeamManager
        
        Args:
            format_name: Pokemon format (e.g., 'gen9vgc2024')
            strategy: Team selection strategy
            archetype: Required if strategy is 'archetype'
            specific_team_id: Required if strategy is 'specific'
        """
        self.manager = TeamManager()
        self.format_name = format_name
        self.strategy = strategy
        self.archetype = archetype
        self.specific_team_id = specific_team_id
        self.current_team: Optional[Team] = None
        self.current_team_id: Optional[str] = None
        
        # Load teams for the format
        try:
            count = self.manager.load_teams(format_name)
            logger.info(f"Loaded {count} teams for format: {format_name}")
        except Exception as e:
            logger.error(f"Failed to load teams for {format_name}: {e}")
            raise
    
    def select_team(self) -> Tuple[str, dict, str]:
        """
        Select a team based on the configured strategy
        
        Returns:
            Tuple of (packed_team, team_dict, team_name)
        """
        # Select team based on strategy
        if self.strategy == TeamSelectionStrategy.BEST:
            team = self.manager.get_best_team()
        elif self.strategy == TeamSelectionStrategy.RANDOM:
            team = self.manager.get_random_team()
        elif self.strategy == TeamSelectionStrategy.ROTATION:
            team = self.manager.get_next_rotation_team()
        elif self.strategy == TeamSelectionStrategy.LEAST_USED:
            team = self.manager.get_least_used_team()
        elif self.strategy == TeamSelectionStrategy.ARCHETYPE:
            if not self.archetype:
                raise ValueError("Archetype must be specified for archetype strategy")
            team = self.manager.get_team_by_archetype(self.archetype)
        elif self.strategy == TeamSelectionStrategy.SPECIFIC:
            if not self.specific_team_id:
                raise ValueError("Team ID must be specified for specific strategy")
            team = self.manager.get_team_by_id(self.specific_team_id)
        else:
            raise ValueError(f"Unknown team selection strategy: {self.strategy}")
        
        if team is None:
            raise ValueError(f"Could not select team with strategy: {self.strategy}")
        
        # Store current team for later tracking
        self.current_team = team
        self.current_team_id = team.id
        
        logger.info(f"Selected team: {team.name} ({team.archetype})")
        
        # Convert to formats needed by the battle system
        packed_team = team.to_packed_format()
        
        # Create team dict for battle tracking
        # Battle.py expects team_dict to be a list of pokemon dicts, not a dict with team_name
        team_dict = team.pokemon
        
        return packed_team, team_dict, team.name
    
    def record_battle_result(self, winner: str, username: str):
        """
        Record the result of a battle
        
        Args:
            winner: Username of the winner
            username: Our bot's username
        """
        if self.current_team_id is None:
            logger.warning("No current team to record result for")
            return
        
        won = (winner == username)
        self.manager.record_battle_result(self.current_team_id, won)
        
        # Get updated stats
        stats = self.manager.get_team_stats(self.current_team_id)
        if stats:
            logger.info(
                f"Team '{self.current_team.name}' record: "
                f"{stats.wins}W-{stats.losses}L ({stats.winrate:.1%})"
            )
    
    def get_summary(self) -> dict:
        """Get summary of all team statistics"""
        return self.manager.get_all_team_stats()
    
    def print_summary(self):
        """Print a summary of all team performance"""
        logger.info("\n" + "="*60)
        logger.info("TEAM PERFORMANCE SUMMARY")
        logger.info("="*60)
        
        stats = self.manager.get_all_team_stats()
        for team_id, team_stats in sorted(
            stats.items(), 
            key=lambda x: x[1]["actual_winrate"], 
            reverse=True
        ):
            name = team_stats["name"]
            arch = team_stats["archetype"]
            battles = team_stats["battles"]
            winrate = team_stats["actual_winrate"]
            expected = team_stats["expected_winrate"]
            
            if battles > 0:
                logger.info(
                    f"  [{arch:15}] {name:35} | "
                    f"{winrate:5.1%} WR ({battles} games) | Expected: {expected:.1%}"
                )
        
        # Format summary
        format_summary = self.manager.get_format_summary()
        logger.info("-"*60)
        logger.info(
            f"Overall: {format_summary['total_wins']}W-"
            f"{format_summary['total_battles'] - format_summary['total_wins']}L "
            f"({format_summary['overall_winrate']:.1%})"
        )
        logger.info("="*60 + "\n")


def is_doubles_format(format_name: str) -> bool:
    """
    Check if a format is a doubles format that should use TeamManager
    
    Args:
        format_name: Pokemon Showdown format name
    
    Returns:
        True if this is a doubles format
    """
    doubles_keywords = [
        "vgc",
        "doubles",
        "vgc2024",
        "vgc2023",
        "doublesou",
        "doublescustomgame"
    ]
    
    format_lower = format_name.lower()
    return any(keyword in format_lower for keyword in doubles_keywords)


def should_use_team_manager(format_name: str, team_name: Optional[str] = None) -> bool:
    """
    Determine if TeamManager should be used for this format
    
    Args:
        format_name: Pokemon Showdown format name
        team_name: Team name from config (if specified)
    
    Returns:
        True if TeamManager should be used
    """
    # Don't use for random battles or battle factory
    if "random" in format_name.lower() or "battlefactory" in format_name.lower():
        return False
    
    # Use for doubles formats
    if is_doubles_format(format_name):
        return True
    
    # Use if team_name explicitly refers to a managed format
    if team_name and is_doubles_format(team_name):
        return True
    
    return False


def create_team_manager_if_needed(
    format_name: str,
    team_name: Optional[str] = None,
    strategy: str = TeamSelectionStrategy.BEST,
    archetype: Optional[str] = None,
    team_id: Optional[str] = None
) -> Optional[BattleTeamManager]:
    """
    Create a BattleTeamManager if needed for this format
    
    Args:
        format_name: Pokemon Showdown format name
        team_name: Team name from config
        strategy: Team selection strategy
        archetype: Team archetype (if using archetype strategy)
        team_id: Specific team ID (if using specific strategy)
    
    Returns:
        BattleTeamManager if applicable, None otherwise
    """
    if not should_use_team_manager(format_name, team_name):
        return None
    
    try:
        # Determine the actual format name for loading teams
        if team_name and is_doubles_format(team_name):
            actual_format = team_name
        else:
            actual_format = format_name
        
        return BattleTeamManager(
            format_name=actual_format,
            strategy=strategy,
            archetype=archetype,
            specific_team_id=team_id
        )
    except Exception as e:
        logger.error(f"Failed to create BattleTeamManager: {e}")
        return None


