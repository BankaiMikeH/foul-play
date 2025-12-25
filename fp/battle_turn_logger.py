"""
Battle Turn Logger - Tracks per-turn decisions and game events.

Creates three types of logs:
1. Bot decision log - what the bot chose each turn ({bot_name}_decisions.log)
2. Game events log - what actually happened according to showdown (game_events.log)

Logs are written immediately to disk to persist even if the bot crashes.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Get project root (go up from foul-play/fp/ to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "battle_logs"


class BattleTurnLogger:
    """Logs turn-by-turn battle decisions and game events."""
    
    _instances: Dict[str, 'BattleTurnLogger'] = {}
    
    def __init__(self, bot_name: str, battle_tag: str, log_dir: Optional[str] = None):
        self.bot_name = bot_name
        self.battle_tag = battle_tag.replace("battle-", "").replace("/", "_")
        
        # Use provided log_dir or default to project root battle_logs/
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = DEFAULT_LOG_DIR
        
        self.current_turn = 0
        self.decisions: List[Dict[str, Any]] = []
        self.game_events: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file paths with timestamp
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        safe_name = bot_name.replace(" ", "_")
        
        # Per-bot decision log
        self.decision_log_path = self.log_dir / f"{safe_name}_{self.battle_tag}_{timestamp}_decisions.log"
        
        # Shared game events log - check if one exists for this battle already
        self.events_log_path = self.log_dir / f"game_{self.battle_tag}_{timestamp}_events.log"
        
        # Per-bot client messages log - all raw messages received from server
        self.client_messages_log_path = self.log_dir / f"{safe_name}_{self.battle_tag}_{timestamp}_client_messages.log"
        
        # Initialize log files
        self._init_decision_log()
        self._init_events_log()
        self._init_client_messages_log()
        
        logger.info(f"BattleTurnLogger initialized for {bot_name} in {battle_tag}")
        logger.info(f"Decision log: {self.decision_log_path}")
        logger.info(f"Events log: {self.events_log_path}")
        logger.info(f"Client messages log: {self.client_messages_log_path}")
    
    def _init_decision_log(self):
        """Initialize the bot decision log file."""
        with open(self.decision_log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"BOT DECISION LOG: {self.bot_name}\n")
            f.write("=" * 60 + "\n")
            f.write(f"Battle: {self.battle_tag}\n")
            f.write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write("This log tracks what moves the bot CHOSE each turn.\n")
            f.write("-" * 60 + "\n\n")
    
    def _init_events_log(self):
        """Initialize the game events log file if it doesn't exist."""
        # Don't overwrite if another bot already created it
        if self.events_log_path.exists():
            return
            
        with open(self.events_log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("GAME EVENTS LOG - What Actually Happened\n")
            f.write("=" * 60 + "\n")
            f.write(f"Battle: {self.battle_tag}\n")
            f.write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write("This log tracks what ACTUALLY happened according to Showdown.\n")
            f.write("-" * 60 + "\n\n")
    
    def _init_client_messages_log(self):
        """Initialize the client messages log file."""
        with open(self.client_messages_log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"CLIENT MESSAGES LOG: {self.bot_name}\n")
            f.write("=" * 60 + "\n")
            f.write(f"Battle: {self.battle_tag}\n")
            f.write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write("This log tracks ALL raw messages received from the Pokemon Showdown server.\n")
            f.write("Messages are logged with timestamps to track battle progress.\n")
            f.write("-" * 60 + "\n\n")
    
    def log_turn_start(self, turn: int):
        """Log the start of a new turn."""
        self.current_turn = turn
        
        turn_header = f"\n{'='*40}\nTURN {turn}\n{'='*40}\n"
        self._append_to_file(self.events_log_path, turn_header)
    
    def log_decision(self, turn: int, raw_decision: str, formatted_decision: str, 
                     mcts_time_ms: Optional[float] = None, 
                     active_pokemon: Optional[List[str]] = None,
                     opponent_pokemon: Optional[List[str]] = None):
        """Log a decision made by this bot."""
        decision_data = {
            "turn": turn,
            "raw_decision": raw_decision,
            "formatted_decision": formatted_decision,
            "mcts_time_ms": mcts_time_ms,
            "active_pokemon": active_pokemon or [],
            "opponent_pokemon": opponent_pokemon or [],
            "timestamp": datetime.now().isoformat()
        }
        self.decisions.append(decision_data)
        
        # Format nicely for decision log
        lines = [
            f"\n{'─'*50}",
            f"TURN {turn}",
            f"{'─'*50}",
            f"  My Pokemon: {', '.join(active_pokemon or ['Unknown'])}",
            f"  Opponent:   {', '.join(opponent_pokemon or ['Unknown'])}",
            f"",
            f"  ► DECISION: {raw_decision}",
            f"  → Sent: {formatted_decision}",
        ]
        if mcts_time_ms is not None:
            lines.append(f"  ⏱ Time: {mcts_time_ms:.1f}ms")
        
        self._append_to_file(self.decision_log_path, "\n".join(lines) + "\n")
        
        # Also log to game events with bot identifier
        time_str = f" ({mcts_time_ms:.0f}ms)" if mcts_time_ms else ""
        event_line = f"  [{self.bot_name}] CHOSE: {raw_decision}{time_str}\n"
        self._append_to_file(self.events_log_path, event_line)
    
    def log_team_composition(self, my_team: List[str], opponent_team: Optional[List[str]] = None, 
                            selected_team: Optional[List[str]] = None,
                            revealed_opponent: Optional[List[str]] = None):
        """Log the team composition for this bot and optionally the opponent."""
        # Format team list nicely
        my_team_str = ", ".join(my_team) if my_team else "Unknown"
        
        lines = [
            "\n" + "="*60,
            "TEAM COMPOSITION",
            "="*60,
            f"  {self.bot_name}'s Full Team ({len(my_team)} Pokemon):",
            f"    {my_team_str}",
        ]
        
        # Show selected team if different from full team (team preview)
        if selected_team and len(selected_team) < len(my_team):
            selected_str = ", ".join(selected_team)
            lines.append(f"")
            lines.append(f"  {self.bot_name}'s Selected Team ({len(selected_team)} Pokemon):")
            lines.append(f"    {selected_str}")
        
        if opponent_team:
            opponent_team_str = ", ".join(opponent_team)
            lines.append(f"")
            lines.append(f"  Opponent's Full Team ({len(opponent_team)} Pokemon):")
            lines.append(f"    {opponent_team_str}")
        
        # Show revealed opponent Pokemon (what we've actually seen)
        if revealed_opponent:
            revealed_str = ", ".join(revealed_opponent)
            lines.append(f"")
            lines.append(f"  Opponent's Revealed Pokemon ({len(revealed_opponent)}):")
            lines.append(f"    {revealed_str}")
        
        lines.append("="*60)
        lines.append("")
        
        self._append_to_file(self.decision_log_path, "\n".join(lines) + "\n")
        
        # Also log to events log
        team_info = f"[{self.bot_name}] Full Team ({len(my_team)}): {my_team_str}"
        if selected_team and len(selected_team) < len(my_team):
            team_info += f" | Selected ({len(selected_team)}): {', '.join(selected_team)}"
        if opponent_team:
            team_info += f" | Opponent Full: {', '.join(opponent_team)}"
        if revealed_opponent:
            team_info += f" | Opponent Revealed: {', '.join(revealed_opponent)}"
        self._append_to_file(self.events_log_path, team_info + "\n")
    
    def log_team_preview_selection(self, full_team: List[str], selected_team: List[str]):
        """Log which Pokemon were selected in team preview."""
        lines = [
            "\n" + "="*60,
            "TEAM PREVIEW SELECTION",
            "="*60,
            f"  Full Team ({len(full_team)} Pokemon): {', '.join(full_team)}",
            f"  Selected Team ({len(selected_team)} Pokemon): {', '.join(selected_team)}",
            f"  Not Selected: {', '.join([p for p in full_team if p not in selected_team])}",
            "="*60,
            ""
        ]
        self._append_to_file(self.decision_log_path, "\n".join(lines) + "\n")
        self._append_to_file(self.events_log_path, 
                           f"[{self.bot_name}] TEAM PREVIEW: Selected {len(selected_team)}/{len(full_team)} - {', '.join(selected_team)}\n")
    
    def log_team_preview(self, team: List[str], lead_choice: str):
        """Log team preview selection."""
        lines = [
            "\n" + "="*50,
            "TEAM PREVIEW",
            "="*50,
            f"  Full Team: {', '.join(team)}",
            f"  Lead Choice: {lead_choice}",
            ""
        ]
        self._append_to_file(self.decision_log_path, "\n".join(lines) + "\n")
        self._append_to_file(self.events_log_path, 
                           f"[{self.bot_name}] TEAM PREVIEW - Lead: {lead_choice}\n")
    
    def log_game_event(self, event_type: str, details: str, turn: Optional[int] = None):
        """Log a game event (move used, switch, damage, etc)."""
        turn_str = f"T{turn}" if turn is not None else f"T{self.current_turn}"
        event_data = {
            "turn": turn or self.current_turn,
            "type": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.game_events.append(event_data)
        
        event_line = f"  {event_type}: {details}\n"
        self._append_to_file(self.events_log_path, event_line)
    
    def log_raw_showdown_event(self, line: str):
        """Log a raw showdown protocol line that represents a game action."""
        if not line.startswith("|"):
            return
        
        parts = line.split("|")
        if len(parts) < 2:
            return
        
        event_type = parts[1]
        
        # Events we care about
        important_events = {
            "turn": "TURN",
            "move": "MOVE",
            "switch": "SWITCH",
            "drag": "DRAG",
            "-damage": "DAMAGE",
            "-heal": "HEAL",
            "faint": "FAINT",
            "-status": "STATUS",
            "-boost": "BOOST",
            "-unboost": "UNBOOST",
            "-ability": "ABILITY",
            "-item": "ITEM",
            "-enditem": "ENDITEM",
            "-weather": "WEATHER",
            "-fieldstart": "FIELD",
            "-sidestart": "SIDE",
            "cant": "CANT",
            "-fail": "FAIL",
            "-miss": "MISS",
            "-crit": "CRIT",
            "-supereffective": "SUPER_EFFECTIVE",
            "-resisted": "RESISTED",
            "-immune": "IMMUNE",
            "win": "WIN",
            "tie": "TIE",
            "-terastallize": "TERA",
            "-protect": "PROTECT",
        }
        
        if event_type in important_events:
            formatted_type = important_events[event_type]
            
            # Special handling for turn
            if event_type == "turn":
                self.current_turn = int(parts[2]) if len(parts) > 2 else self.current_turn + 1
                turn_header = f"\n{'='*50}\nTURN {self.current_turn}\n{'='*50}\n"
                self._append_to_file(self.events_log_path, turn_header)
            
            elif event_type == "move":
                # Format: |move|p1a: Pokemon|MoveName|p2a: Target
                if len(parts) >= 4:
                    attacker = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    move = parts[3]
                    target = parts[4].split(": ")[-1] if len(parts) > 4 and ": " in parts[4] else ""
                    target_str = f" → {target}" if target else ""
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {attacker} used {move}{target_str}\n")
            
            elif event_type == "switch" or event_type == "drag":
                # Format: |switch|p1a: Pokemon|Species, L50|100/100
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    hp = parts[4] if len(parts) > 4 else ""
                    action = "switched in" if event_type == "switch" else "was dragged in"
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} {action} ({hp})\n")
            
            elif event_type == "-damage":
                # Format: |-damage|p1a: Pokemon|75/100
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    hp = parts[3].split(" ")[0]  # Remove status conditions
                    source = ""
                    if len(parts) > 4:
                        source = f" from {parts[4]}"
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} took damage → {hp}{source}\n")
            
            elif event_type == "-heal":
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    hp = parts[3].split(" ")[0]
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} healed → {hp}\n")
            
            elif event_type == "faint":
                if len(parts) >= 3:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    self._append_to_file(self.events_log_path, 
                        f"  *** [{player}] {pokemon} FAINTED ***\n")
            
            elif event_type == "win":
                if len(parts) >= 3:
                    winner = parts[2]
                    self._append_to_file(self.events_log_path, 
                        f"\n{'*'*50}\n*** WINNER: {winner} ***\n{'*'*50}\n")
            
            elif event_type == "-fail" or event_type == "-miss":
                if len(parts) >= 3:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon}'s move {formatted_type}!\n")
            
            elif event_type == "cant":
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    reason = parts[3]
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} can't move: {reason}\n")
            
            elif event_type == "-boost" or event_type == "-unboost":
                if len(parts) >= 5:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    stat = parts[3]
                    amount = parts[4]
                    direction = "+" if event_type == "-boost" else "-"
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon}'s {stat} {direction}{amount}\n")
            
            elif event_type == "-status":
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    status = parts[3]
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} was inflicted with {status}\n")
            
            elif event_type == "-weather":
                weather = parts[2] if len(parts) > 2 else "none"
                source = ""
                if len(parts) > 3:
                    source = f" ({parts[3]})"
                self._append_to_file(self.events_log_path, 
                    f"  [WEATHER] {weather}{source}\n")
            
            elif event_type == "-terastallize":
                if len(parts) >= 4:
                    pokemon = parts[2].split(": ")[-1] if ": " in parts[2] else parts[2]
                    player = "P1" if parts[2].startswith("p1") else "P2"
                    tera_type = parts[3]
                    self._append_to_file(self.events_log_path, 
                        f"  [{player}] {pokemon} terastallized to {tera_type}!\n")
            
            else:
                # Generic logging for other important events
                details = "|".join(parts[2:]) if len(parts) > 2 else ""
                self._append_to_file(self.events_log_path, 
                    f"  [{formatted_type}] {details}\n")
    
    def log_inactivity(self, reason: str):
        """Log an inactivity notice."""
        inactivity_msg = f"\n{'!'*50}\n!!! INACTIVITY: {reason} !!!\n{'!'*50}\n"
        self._append_to_file(self.decision_log_path, inactivity_msg)
        self._append_to_file(self.events_log_path, 
                           f"\n*** [{self.bot_name}] INACTIVITY: {reason} ***\n")
    
    def log_client_message(self, message: str):
        """Log a raw client message received from the server with timestamp."""
        if not message:
            return
        
        # Get current timestamp
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Include milliseconds
        
        # Calculate time since battle start
        elapsed = (timestamp - self.start_time).total_seconds()
        
        # Format the message for logging
        # Split multi-line messages and log each line with timestamp
        lines = message.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Log with timestamp and elapsed time
            log_entry = f"[{timestamp_str}] (+{elapsed:.3f}s) {line}\n"
            self._append_to_file(self.client_messages_log_path, log_entry)
    
    def log_error(self, error: str):
        """Log an error."""
        error_msg = f"\n*** ERROR: {error} ***\n"
        self._append_to_file(self.decision_log_path, error_msg)
        self._append_to_file(self.events_log_path, f"*** [{self.bot_name}] ERROR: {error} ***\n")
    
    def finalize(self, winner: Optional[str] = None):
        """Finalize the logs with summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        summary = [
            "",
            "="*60,
            "BATTLE SUMMARY",
            "="*60,
            f"Duration: {duration.total_seconds():.1f} seconds",
            f"Total Turns: {self.current_turn}",
            f"Decisions Made: {len(self.decisions)}",
            f"Winner: {winner or 'Unknown'}",
        ]
        
        # Calculate average decision time
        times = [d["mcts_time_ms"] for d in self.decisions if d.get("mcts_time_ms")]
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            summary.append(f"Avg Decision Time: {avg_time:.1f}ms")
            summary.append(f"Min Decision Time: {min_time:.1f}ms")
            summary.append(f"Max Decision Time: {max_time:.1f}ms")
        
        # Check if this bot won
        if winner:
            did_win = winner.lower() in self.bot_name.lower() or self.bot_name.lower() in winner.lower()
            summary.append(f"Result for {self.bot_name}: {'WIN' if did_win else 'LOSS'}")
        
        summary.append("="*60)
        
        summary_text = "\n".join(summary) + "\n"
        self._append_to_file(self.decision_log_path, summary_text)
        
        # Only write summary to events log if we're the first to finish
        events_summary = [
            "",
            "="*60,
            "BATTLE COMPLETE",
            "="*60,
            f"Winner: {winner or 'Unknown'}",
            f"Total Turns: {self.current_turn}",
            "="*60,
        ]
        self._append_to_file(self.events_log_path, "\n".join(events_summary) + "\n")
        
        logger.info(f"Battle logs finalized for {self.bot_name}")
        logger.info(f"  Decision log: {self.decision_log_path}")
        logger.info(f"  Events log: {self.events_log_path}")
        logger.info(f"  Client messages log: {self.client_messages_log_path}")
    
    def _append_to_file(self, path: Path, content: str):
        """Append content to a log file, flushing immediately."""
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
        except Exception as e:
            logger.error(f"Failed to write to {path}: {e}")
    
    @classmethod
    def get_or_create(cls, bot_name: str, battle_tag: str, log_dir: Optional[str] = None) -> 'BattleTurnLogger':
        """Get existing logger or create a new one."""
        key = f"{bot_name}_{battle_tag}"
        if key not in cls._instances:
            cls._instances[key] = cls(bot_name, battle_tag, log_dir)
        return cls._instances[key]
    
    @classmethod
    def clear_instance(cls, bot_name: str, battle_tag: str):
        """Remove a logger instance."""
        key = f"{bot_name}_{battle_tag}"
        if key in cls._instances:
            del cls._instances[key]
    
    @classmethod
    def clear_all_instances(cls):
        """Clear all logger instances."""
        cls._instances.clear()
