import json
import asyncio
import concurrent.futures
from copy import deepcopy
import logging
import time

from data.pkmn_sets import RandomBattleTeamDatasets, TeamDatasets
from data.pkmn_sets import SmogonSets
import constants
from constants import BattleType
from config import FoulPlayConfig, SaveReplay
from fp.pokemon import LastUsedMove, Pokemon
from fp.battle import Battle  # For type hints
from fp.battle_factory import create_battle
from fp.battle_modifier import async_update_battle, process_battle_updates
from fp.helpers import normalize_name, is_doubles_format
from fp.search.main import find_best_move
from fp.battle_turn_logger import BattleTurnLogger

from fp.websocket_client import PSWebsocketClient
from fp.browser_client import BrowserClient
from fp.run_battle_browser import pokemon_battle_browser_loop, start_battle_browser

logger = logging.getLogger(__name__)

# Global turn logger reference (set per battle)
_current_turn_logger: BattleTurnLogger = None

def get_turn_logger() -> BattleTurnLogger:
    """Get the current turn logger."""
    return _current_turn_logger

def set_turn_logger(turn_logger: BattleTurnLogger):
    """Set the current turn logger."""
    global _current_turn_logger
    _current_turn_logger = turn_logger


def get_fallback_move(battle):
    """Get a safe fallback move when normal move selection fails."""
    try:
        # Try to use the first available move from request JSON
        if battle.request_json and constants.SIDE in battle.request_json:
            side_data = battle.request_json[constants.SIDE]
            if constants.ACTIVE in side_data and side_data[constants.ACTIVE]:
                active_data = side_data[constants.ACTIVE][0]
                if constants.MOVES in active_data and active_data[constants.MOVES]:
                    first_move = active_data[constants.MOVES][0]
                    move_id = first_move.get("id", "1")
                    
                    if battle.is_doubles:
                        # For doubles, use move 1 for both positions
                        rqid = battle.request_json.get("rqid", "")
                        return [f"/choose move {move_id}, move {move_id}", str(rqid)]
                    else:
                        # For singles
                        rqid = battle.request_json.get("rqid", "")
                        return [f"/choose move {move_id}", str(rqid)]
    except Exception as e:
        logger.debug(f"Could not get fallback from request JSON: {e}")
    
    # Ultimate fallback: use move 1
    if battle.is_doubles:
        rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
        return [f"/choose move 1, move 1", str(rqid)]
    else:
        rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
        return [f"/choose move 1", str(rqid)]


def format_decision(battle, decision):
    """
    Formats a decision for communication with Pokemon-Showdown.
    
    Singles format:
        - "move 1" -> "/choose move 1"
        - "switch pokemonname" -> "/switch 2"
        - "move 1-mega" -> "/choose move 1 mega"
    
    Doubles format:
        - "move 1 1, move 2 2" -> "/choose move 1 1, move 2 2"
        - "move 1 1, switch pokemonname" -> "/choose move 1 1, switch 3"
        - "switch pkmn1, switch pkmn2" -> "/choose switch 2, switch 3"
    """
    if battle.is_doubles:
        return format_doubles_decision(battle, decision)
    else:
        return format_singles_decision(battle, decision)


def format_singles_decision(battle, decision):
    """Format a decision for singles battles (original implementation)."""
    # Defensive check: ensure active Pokemon exists
    if battle.user.active is None:
        logger.error("Active Pokemon is None, cannot format decision. Using fallback move.")
        return get_fallback_move(battle)
    
    if decision.startswith(constants.SWITCH_STRING + " "):
        switch_pokemon = decision.split("switch ")[-1]
        
        # Validate that the Pokemon is in the selected team (if team preview was used)
        if hasattr(battle, 'user_selected_team') and battle.user_selected_team:
            if switch_pokemon not in battle.user_selected_team:
                logger.error(f"Tried to switch to {switch_pokemon} which is NOT in selected team: {battle.user_selected_team}")
                # Find a valid Pokemon to switch to instead
                available_reserves = [p.name for p in battle.user.reserve if p.name in battle.user_selected_team]
                if available_reserves:
                    switch_pokemon = available_reserves[0]
                    logger.warning(f"Switching to {switch_pokemon} instead (first available from selected team)")
                else:
                    logger.error(f"No valid Pokemon to switch to from selected team, using fallback")
                    return get_fallback_move(battle)
        
        for pkmn in battle.user.reserve:
            if pkmn.name == switch_pokemon:
                message = "/switch {}".format(pkmn.index)
                break
        else:
            logger.error("Tried to switch to: {}, but not found in reserves. Using fallback.".format(switch_pokemon))
            return get_fallback_move(battle)
    else:
        tera = False
        mega = False
        if decision.endswith("-tera"):
            decision = decision.replace("-tera", "")
            tera = True
        elif decision.endswith("-mega"):
            decision = decision.replace("-mega", "")
            mega = True
        message = "/choose move {}".format(decision)

        try:
            if battle.user.active.can_mega_evo and mega:
                message = "{} {}".format(message, constants.MEGA)
            elif battle.user.active.can_ultra_burst:
                message = "{} {}".format(message, constants.ULTRA_BURST)

            # only dynamax on last pokemon
            if battle.user.active.can_dynamax and all(
                p.hp == 0 for p in battle.user.reserve
            ):
                message = "{} {}".format(message, constants.DYNAMAX)

            if tera:
                message = "{} {}".format(message, constants.TERASTALLIZE)

            move_obj = battle.user.active.get_move(decision)
            if move_obj and move_obj.can_z:
                message = "{} {}".format(message, constants.ZMOVE)
        except (AttributeError, KeyError) as e:
            logger.warning(f"Error accessing move attributes: {e}. Continuing without modifiers.")

    return [message, str(battle.rqid)]


def format_doubles_decision(battle, decision):
    """
    Format a decision for doubles battles.
    
    Decision format examples:
        - "move 1 1, move 2 2" (two moves with targeting)
        - "move 1 1, switch pokemonname" (move + switch)
        - "switch pkmn1, switch pkmn2" (two switches)
        - "[move0, move1]" (Rust MCTS format with brackets)
    
    Args:
        battle: Battle object
        decision: String representing the decision
        
    Returns:
        [message, rqid] for sending to Pokemon Showdown
    """
    # Handle Rust MCTS format with brackets: "[move0, move1]"
    original_decision = decision
    if decision.startswith("[") and decision.endswith("]"):
        decision = decision[1:-1].strip()  # Remove brackets
    
    # Split decision into left and right position decisions
    # Try multiple split patterns to handle different formats
    if ", " in decision:
        decisions = decision.split(", ")
    elif "," in decision:
        decisions = decision.split(",")
    else:
        # Single action (may happen during force switch scenarios)
        decisions = [decision]
    
    left_decision = decisions[0].strip() if len(decisions) > 0 and decisions[0].strip() else None
    right_decision = decisions[1].strip() if len(decisions) > 1 and decisions[1].strip() else None
    
    # Log for debugging
    logger.info(f"Formatting doubles decision: original='{original_decision}', left='{left_decision}', right='{right_decision}'")
    
    # Get active Pokemon names for logging
    left_pkmn = battle.user.get_active_pokemon(0)
    right_pkmn = battle.user.get_active_pokemon(1)
    left_name = left_pkmn.name if left_pkmn else "None"
    right_name = right_pkmn.name if right_pkmn else "None"
    logger.info(f"Active Pokemon - Position 0 (left): {left_name}, Position 1 (right): {right_name}")
    
    # Validate we have decisions for both positions
    if left_decision is None:
        logger.error(f"No left decision found in: {original_decision}")
        left_decision = "pass"
    if right_decision is None:
        logger.warning(f"No right decision found in: {original_decision}, using pass")
        right_decision = "pass"
    
    # Validate positions are alive before making decisions
    if not battle.position_alive_at_turn_start[0] and left_decision and left_decision != "pass":
        logger.warning(f"Position 0 was not alive at turn start, but got decision: {left_decision}")
        left_decision = "pass"
    
    if not battle.position_alive_at_turn_start[1] and right_decision and right_decision != "pass":
        logger.warning(f"Position 1 was not alive at turn start, but got decision: {right_decision}")
        right_decision = "pass"
    
    # Format each decision with explicit position and track decisions
    left_msg = format_single_pokemon_decision(battle, left_decision, position=0)
    if left_msg and left_msg != "pass":
        battle.position_decisions_made[0] = True
    
    right_msg = format_single_pokemon_decision(battle, right_decision, position=1)
    if right_msg and right_msg != "pass":
        battle.position_decisions_made[1] = True
    
    # Validate switch conflicts: if one Pokemon switches, the other must switch to different Pokemon or attack
    left_is_switch = left_decision and left_decision.startswith(constants.SWITCH_STRING + " ")
    right_is_switch = right_decision and right_decision.startswith(constants.SWITCH_STRING + " ")
    
    if left_is_switch and right_is_switch:
        # Both are switching - extract switch targets
        left_switch_target = left_decision.split("switch ")[-1] if left_is_switch else None
        right_switch_target = right_decision.split("switch ")[-1] if right_is_switch else None
        
        if left_switch_target == right_switch_target:
            # Both trying to switch to same Pokemon - invalid!
            logger.error(
                f"Both positions trying to switch to same Pokemon: {left_switch_target}. "
                f"Position 1 must switch to different Pokemon or attack."
            )
            # Force position 1 to use a move instead
            right_pkmn = battle.user.get_active_pokemon(1)
            if right_pkmn and right_pkmn.moves:
                # Use first available move
                available_moves = [m for m in right_pkmn.moves if not m.disabled and m.current_pp > 0]
                if available_moves:
                    move_index = right_pkmn.moves.index(available_moves[0]) + 1
                    right_decision = f"move {move_index}"
                    right_msg = format_single_pokemon_decision(battle, right_decision, position=1)
                    logger.warning(f"Changed position 1 to use move {move_index} instead of switch")
                else:
                    # No moves available - must switch to different Pokemon
                    # Find a different reserve Pokemon
                    for reserve_pkmn in battle.user.reserve:
                        if reserve_pkmn.name != left_switch_target and reserve_pkmn.is_alive():
                            right_decision = f"switch {reserve_pkmn.name}"
                            right_msg = format_single_pokemon_decision(battle, right_decision, position=1)
                            logger.warning(f"Changed position 1 to switch to {reserve_pkmn.name} instead")
                            break
    
    # If one position switches and other doesn't, validate the non-switching position
    # When one Pokemon switches, the other must either switch to a different Pokemon or use a move
    if left_is_switch and not right_is_switch:
        # Position 0 is switching - position 1 must use a move (not switch)
        # If right_decision is empty/invalid, force it to use a move
        # Note: format_single_pokemon_decision handles both "move X" format and move names
        if not right_decision or right_decision == "pass":
            # Ensure position 1 uses a move
            right_pkmn = battle.user.get_active_pokemon(1)
            if right_pkmn and right_pkmn.moves:
                available_moves = [m for m in right_pkmn.moves if not m.disabled and m.current_pp > 0]
                if available_moves:
                    move_index = right_pkmn.moves.index(available_moves[0]) + 1
                    right_decision = f"move {move_index}"
                    right_msg = format_single_pokemon_decision(battle, right_decision, position=1)
                    logger.warning(f"Position 0 switching, ensuring position 1 uses move {move_index}")
    
    if right_is_switch and not left_is_switch:
        # Position 1 is switching - position 0 must use a move (not switch)
        # If left_decision is empty/invalid, force it to use a move
        # Note: format_single_pokemon_decision handles both "move X" format and move names
        if not left_decision or left_decision == "pass":
            # Ensure position 0 uses a move
            left_pkmn = battle.user.get_active_pokemon(0)
            if left_pkmn and left_pkmn.moves:
                available_moves = [m for m in left_pkmn.moves if not m.disabled and m.current_pp > 0]
                if available_moves:
                    move_index = left_pkmn.moves.index(available_moves[0]) + 1
                    left_decision = f"move {move_index}"
                    left_msg = format_single_pokemon_decision(battle, left_decision, position=0)
                    logger.warning(f"Position 1 switching, ensuring position 0 uses move {move_index}")
    
    # Combine into full message
    if right_msg:
        message = "/choose {}, {}".format(left_msg, right_msg)
    else:
        message = "/choose {}".format(left_msg)
    
    logger.info(f"Formatted doubles message: {message}")
    logger.debug(
        f"Decisions made - Position 0: {battle.position_decisions_made[0]}, "
        f"Position 1: {battle.position_decisions_made[1]}"
    )
    return [message, str(battle.rqid)]


def format_single_pokemon_decision(battle, decision, position):
    """
    Format a decision for a single Pokemon in doubles.
    
    Args:
        battle: Battle object
        decision: String like "move 1 2", "switch pokemonname", or just "movename"
        position: 0 for left, 1 for right
        
    Returns:
        Formatted string like "move 1 2" or "switch 3"
    """
    if decision is None or decision == "" or decision == "No Move":
        # No action needed (e.g., Pokemon fainted or no valid moves)
        return ""
    
    # Get the Pokemon at this position for logging and validation
    active_pkmn = battle.user.get_active_pokemon(position)
    pkmn_name = active_pkmn.name if active_pkmn else "None"
    logger.debug(f"Formatting decision for position {position} (Pokemon: {pkmn_name}): '{decision}'")
    
    if active_pkmn is None:
        logger.warning(f"No active Pokemon at position {position}, cannot format decision: {decision}")
        return "pass"
    
    # Handle switch decisions
    if decision.startswith(constants.SWITCH_STRING + " "):
        switch_pokemon = decision.split("switch ")[-1]
        
        # Track the switch target for this position
        battle.position_switch_targets[position] = switch_pokemon
        
        # Validate that the Pokemon is in the selected team (if team preview was used)
        if hasattr(battle, 'user_selected_team') and battle.user_selected_team:
            if switch_pokemon not in battle.user_selected_team:
                logger.error(f"Tried to switch to {switch_pokemon} which is NOT in selected team: {battle.user_selected_team}")
                # Find a valid Pokemon to switch to instead
                available_reserves = [p.name for p in battle.user.reserve if p.name in battle.user_selected_team]
                if available_reserves:
                    switch_pokemon = available_reserves[0]
                    logger.warning(f"Switching to {switch_pokemon} instead (first available from selected team)")
                else:
                    logger.error(f"No valid Pokemon to switch to from selected team")
                    return "pass"
        
        # First, check reserves
        for pkmn in battle.user.reserve:
            if pkmn.name == switch_pokemon:
                return "switch {}".format(pkmn.index)
        
        # Also check active Pokemon (in case we need to switch to a currently active slot)
        # This handles edge cases where MCTS suggests switching to an already-active Pokemon
        if hasattr(battle.user, 'get_active_pokemon'):
            for pos in range(2):
                active_pkmn = battle.user.get_active_pokemon(pos)
                if active_pkmn and active_pkmn.name == switch_pokemon:
                    # Can't switch to already active Pokemon - fall back to pass
                    logger.warning(f"Can't switch to {switch_pokemon} - already active at position {pos}")
                    return "pass"
        
        # Log available reserves for debugging
        reserve_names = [p.name for p in battle.user.reserve]
        logger.error(f"Tried to switch to: {switch_pokemon}, but reserves are: {reserve_names}")
        
        # Fall back to pass if switch target not found
        return "pass"
    
    # Handle move decisions
    tera = False
    mega = False
    dynamax = False
    
    if "-tera" in decision:
        decision = decision.replace("-tera", "")
        tera = True
    elif "-mega" in decision:
        decision = decision.replace("-mega", "")
        mega = True
    
    # Parse move and target
    # Format can be: "move 1 2", "move 1", or just "movename" (from Rust MCTS)
    parts = decision.split()
    
    if len(parts) >= 2 and parts[0] == "move":
        # Old format: "move 1 2" or "move movename"
        move_id = parts[1]
        target = parts[2] if len(parts) > 2 else None
    elif len(parts) == 1:
        # Rust MCTS format: just the move name like "tackle"
        move_name = parts[0]
        
        # Find the move index for this Pokemon at this specific position
        # CRITICAL: Use the position parameter to get the correct Pokemon
        active_pkmn = battle.user.get_active_pokemon(position)
        if active_pkmn:
            logger.debug(f"Looking for move '{move_name}' in {active_pkmn.name} (position {position})")
            logger.debug(f"Available moves: {[m.name for m in active_pkmn.moves]}")
            try:
                move_found = False
                for i, move in enumerate(active_pkmn.moves):
                    if move.name == move_name:
                        move_id = str(i + 1)  # Showdown uses 1-based indices
                        move_found = True
                        logger.debug(f"Found move '{move_name}' at index {i+1} for {active_pkmn.name}")
                        break
                
                if not move_found:
                    # Move not found in this Pokemon's moveset - this is a bug in Rust engine
                    # Fall back to first available move for this Pokemon
                    logger.error(f"INVALID: Move '{move_name}' not found in {active_pkmn.name} (position {position}) moves: {[m.name for m in active_pkmn.moves]}")
                    logger.error(f"Rust engine suggested invalid move for position {position}. Using first available move instead.")
                    if active_pkmn.moves:
                        # Use first non-disabled move, or first move if all disabled
                        available_moves = [m for m in active_pkmn.moves if not m.disabled and m.current_pp > 0]
                        if available_moves:
                            move_id = str(active_pkmn.moves.index(available_moves[0]) + 1)
                            logger.warning(f"Using fallback move: {available_moves[0].name} (index {move_id})")
                        else:
                            # All moves disabled, use first move anyway
                            move_id = "1"
                            logger.warning(f"All moves disabled, using move 1 as fallback")
                    else:
                        move_id = "1"  # Struggle fallback
            except (AttributeError, IndexError) as e:
                logger.warning(f"Error accessing moves for Pokemon {active_pkmn.name} at position {position}: {e}")
                move_id = "1"  # Fallback to move 1
        else:
            logger.error(f"No active Pokemon at position {position}, cannot find move '{move_name}'")
            move_id = "1"  # Fallback to move 1
        target = None
    else:
        logger.error("Invalid move decision format: {}. Using fallback.".format(decision))
        return "pass"
    
    # If no target specified, determine default target
    if target is None:
        target = get_default_doubles_target(battle, move_id, position)
    
    message = "move {} {}".format(move_id, target)
    
    # Add modifiers (mega, tera, dynamax, etc.)
    active_pkmn = battle.user.get_active_pokemon(position)
    if active_pkmn:
        if active_pkmn.can_mega_evo and mega:
            message = "{} {}".format(message, constants.MEGA)
        elif active_pkmn.can_ultra_burst:
            message = "{} {}".format(message, constants.ULTRA_BURST)
        
        # Only dynamax on last pokemon
        if active_pkmn.can_dynamax and all(p.hp == 0 for p in battle.user.reserve):
            message = "{} {}".format(message, constants.DYNAMAX)
        
        if tera:
            message = "{} {}".format(message, constants.TERASTALLIZE)
        
        # Check Z-move capability (handle None case when move not found)
        move = active_pkmn.get_move(move_id)
        if move and move.can_z:
            message = "{} {}".format(message, constants.ZMOVE)
    
    return message


def get_default_doubles_target(battle, move_id, attacker_position):
    """
    Determine the default target for a move in doubles.
    
    Args:
        battle: Battle object
        move_id: Move identifier (string or int)
        attacker_position: Position of attacking Pokemon (0 or 1)
        
    Returns:
        Target identifier (1 or 2 for opponents, 0 for ally, -1 for self)
    """
    # Get move data
    active_pkmn = battle.user.get_active_pokemon(attacker_position)
    if not active_pkmn:
        return constants.TARGET_LEFT_OPPONENT  # Default fallback
    
    move = active_pkmn.get_move(move_id)
    if not move:
        return constants.TARGET_LEFT_OPPONENT  # Default fallback
    
    # Check move targeting based on category
    # For now, use simple logic:
    # - Damaging moves: target opponent (prioritize left, then right if left is fainted)
    # - Status moves that could be support: may target ally or self
    # - Most moves: target left opponent by default
    
    # Check if opponent positions are available
    left_opponent = battle.opponent.get_active_pokemon(0)
    right_opponent = battle.opponent.get_active_pokemon(1)
    
    # Default: target left opponent if alive, otherwise right
    if left_opponent and left_opponent.hp > 0:
        return constants.TARGET_LEFT_OPPONENT  # 1
    elif right_opponent and right_opponent.hp > 0:
        return constants.TARGET_RIGHT_OPPONENT  # 2
    else:
        # Both fainted? Just return left as default
        return constants.TARGET_LEFT_OPPONENT  # 1


def battle_is_finished(battle_tag, msg):
    return (
        msg.startswith(">{}".format(battle_tag))
        and (constants.WIN_STRING in msg or constants.TIE_STRING in msg)
        and constants.CHAT_STRING not in msg
    )


def extract_battle_factory_tier_from_msg(msg):
    start = msg.find("Battle Factory Tier: ") + len("Battle Factory Tier: ")
    end = msg.find("</b>", start)
    tier_name = msg[start:end]

    return normalize_name(tier_name)


async def async_pick_move(battle):
    try:
        battle_copy = deepcopy(battle)
        
        # No need to set is_doubles or fix active structure - custom __deepcopy__ handles this
        # The class type (SinglesBattle/DoublesBattle) determines is_doubles
        # The Battler type (SinglesBattler/DoublesBattler) ensures correct active structure
        
        # Reset decision tracking for doubles at start of each turn
        if battle.is_doubles:
            # Check which positions are alive at turn start
            battle.position_alive_at_turn_start[0] = (
                battle.user.get_active_pokemon(0) is not None 
                and battle.user.get_active_pokemon(0).hp > 0
            )
            battle.position_alive_at_turn_start[1] = (
                battle.user.get_active_pokemon(1) is not None 
                and battle.user.get_active_pokemon(1).hp > 0
            )
            
            # Reset decision tracking
            battle.position_decisions_made = [False, False]
            battle.position_switch_targets = [None, None]
            
            logger.debug(
                f"Turn {battle.turn}: Position 0 alive={battle.position_alive_at_turn_start[0]}, "
                f"Position 1 alive={battle.position_alive_at_turn_start[1]}"
            )
        
        if not battle_copy.team_preview:
            battle_copy.user.update_from_request_json(battle_copy.request_json)

        # Time the decision
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)
        
        # Validate the result
        if not best_move or not isinstance(best_move, str):
            raise ValueError(f"Invalid move returned from find_best_move: {best_move}")
        
        decision_time_ms = (time.time() - start_time) * 1000
        
        # Update last_selected_move
        # For singles: track the single active Pokemon's move
        # For doubles: track the left Pokemon's move (primary decision tracking)
        if battle.is_doubles:
            # Parse doubles decision to get primary move
            # Format: "move 1 1, move 2 2" or "switch pkmn, move 1 1"
            left_decision = best_move.split(", ")[0] if ", " in best_move else best_move
            left_pkmn = battle.user.get_active_pokemon(0)
            
            # Extract move name (remove targeting and modifiers)
            move_name = left_decision.removesuffix("-tera").removesuffix("-mega")
            if " " in move_name:
                # Remove targeting info: "move 1 2" -> "move 1"
                move_name = " ".join(move_name.split()[:2])
            
            battle.user.last_selected_move = LastUsedMove(
                left_pkmn.name if left_pkmn else "",
                move_name,
                battle.turn,
            )
            
            # Get active Pokemon names for logging
            active_pokemon = []
            for i in range(2):
                pkmn = battle.user.get_active_pokemon(i)
                if pkmn:
                    active_pokemon.append(pkmn.name)
            
            opponent_pokemon = []
            for i in range(2):
                pkmn = battle.opponent.get_active_pokemon(i)
                if pkmn:
                    opponent_pokemon.append(pkmn.name if hasattr(pkmn, 'name') else str(pkmn))
        else:
            # Singles: original behavior
            battle.user.last_selected_move = LastUsedMove(
                battle.user.active.name if battle.user.active else "",
                best_move.removesuffix("-tera").removesuffix("-mega"),
                battle.turn,
            )
            active_pokemon = [battle.user.active.name] if battle.user.active else []
            opponent_pokemon = [battle.opponent.active.name] if battle.opponent.active else []
        
        # Don't format team preview decisions - they're handled separately
        if battle_copy.team_preview:
            return best_move
        
        formatted = format_decision(battle_copy, best_move)
        
        # Log the decision if we have a turn logger
        turn_logger = get_turn_logger()
        if turn_logger:
            turn_logger.log_decision(
                turn=battle.turn,
                raw_decision=best_move,
                formatted_decision=formatted,
                mcts_time_ms=decision_time_ms,
                active_pokemon=active_pokemon,
                opponent_pokemon=opponent_pokemon
            )
        
        logger.info(f"[Turn {battle.turn}] Decision: {formatted} (took {decision_time_ms:.1f}ms)")
        
        return formatted
    except Exception as e:
        logger.error(f"Error in async_pick_move on turn {battle.turn}: {e}", exc_info=True)
        raise  # Re-raise to be caught by outer handler


async def handle_team_preview(battle, ps_websocket_client):
    battle_copy = deepcopy(battle)
    
    # No need to set is_doubles - it's determined by the class type (SinglesBattle vs DoublesBattle)
    # The deepcopy preserves the correct class type via custom __deepcopy__ methods
    
    # Set dummy active Pokemon - use list for doubles, single for singles
    # We explicitly set these regardless of deepcopy result to ensure correct structure
    if battle_copy.is_doubles:
        battle_copy.user.active = [Pokemon.get_dummy(), Pokemon.get_dummy()]
        battle_copy.opponent.active = [Pokemon.get_dummy(), Pokemon.get_dummy()]
        logger.debug("Team preview: Set dummy Pokemon as list for doubles")
    else:
        battle_copy.user.active = Pokemon.get_dummy()
        battle_copy.opponent.active = Pokemon.get_dummy()
    battle_copy.team_preview = True

    best_move = await async_pick_move(battle_copy)
    
    logger.info(f"Team preview best_move: {best_move}")
    logger.info(f"Team preview best_move type: {type(best_move)}")

    # best_move is a string (not a list!) - e.g., "switch 1"
    move_parts = best_move.split()
    logger.info(f"Team preview move_parts: {move_parts}")
    
    # Expected format: "switch <number>"
    if len(move_parts) < 2:
        logger.error(f"Invalid team preview decision format: {best_move}")
        # Fallback: use first Pokemon
        choice_digit = 1
    else:
        try:
            choice_digit = int(move_parts[1])
        except ValueError:
            logger.error(f"Could not parse team preview choice from: {best_move}")
            # Fallback: use first Pokemon
            choice_digit = 1
    
    # Get Pokemon name from team preview order (not reserve order)
    if hasattr(battle, 'user_team_preview_order') and battle.user_team_preview_order:
        if choice_digit <= len(battle.user_team_preview_order):
            pkmn_name = battle.user_team_preview_order[choice_digit - 1]
        else:
            logger.error(f"Invalid choice_digit {choice_digit}, using first Pokemon")
            pkmn_name = battle.user_team_preview_order[0]
    else:
        # Fallback to reserve order
        pkmn_name = battle.user.reserve[choice_digit - 1].name
    
    battle.user.last_selected_move = LastUsedMove(
        "teampreview", "switch {}".format(pkmn_name), battle.turn
    )

    size_of_team = len(battle.user.reserve) + 1
    team_list_indexes = list(range(1, size_of_team))
    # choice_digit already set above, just verify it's in range
    if choice_digit not in team_list_indexes:
        logger.error(f"Invalid choice_digit {choice_digit}, defaulting to 1")
        choice_digit = 1

    team_list_indexes.remove(choice_digit)
    
    # For VGC/doubles, we typically select 4 Pokemon from 6
    # The format is: /team {lead}{other3}|{rqid}
    # For example: /team 1234|2 means select Pokemon 1,2,3,4 with 1 as lead
    selected_indices = [choice_digit] + team_list_indexes[:3]  # First 4 Pokemon
    selected_team_names = []
    
    # Get the names of selected Pokemon using team preview order (not reserve order!)
    # Team preview indices (1-6) refer to the order Pokemon appear in the team preview message
    if hasattr(battle, 'user_team_preview_order') and battle.user_team_preview_order:
        team_preview_order = battle.user_team_preview_order
        logger.debug(f"Using team preview order: {team_preview_order}")
        
        for idx in selected_indices:
            if idx <= len(team_preview_order):
                pokemon_name = team_preview_order[idx - 1]  # Indices are 1-based
                selected_team_names.append(pokemon_name)
            else:
                logger.warning(f"Invalid team preview index {idx}, preview has {len(team_preview_order)} Pokemon")
    else:
        # Fallback to reserve order if team preview order not available
        logger.warning("Team preview order not available, using reserve order (may be incorrect)")
        for idx in selected_indices:
            if idx <= len(battle.user.reserve):
                pkmn = battle.user.reserve[idx - 1]
                selected_team_names.append(pkmn.name)
            else:
                logger.warning(f"Invalid team preview index {idx}, reserve has {len(battle.user.reserve)} Pokemon")
    
    # Store selected team on battle object
    battle.user_selected_team = selected_team_names
    logger.info(f"Selected team preview: {', '.join(selected_team_names)} (from {len(battle.user.reserve)} total)")
    
    # Log team preview selection
    turn_logger = get_turn_logger()
    if turn_logger:
        full_team = [p.name for p in battle.user.reserve]
        turn_logger.log_team_preview_selection(full_team, selected_team_names)
    
    message = [
        "/team {}{}|{}".format(
            choice_digit, "".join(str(x) for x in team_list_indexes[:3]), battle.rqid
        )
    ]

    await ps_websocket_client.send_message(battle.battle_tag, message)


async def get_battle_tag_and_opponent(ps_websocket_client: PSWebsocketClient):
    # Keep reading messages until we have battle tag + opponent for a battle with team preview
    battle_tag = None
    opponent_name = None
    player_id = None  # NEW: Also extract p1/p2
    has_team_preview = False
    consumed_messages = []  # NEW: Save messages for later processing
    
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run_battle.py:374','message':'Waiting for battle initialization','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'D'})+'\n')
    except Exception as e:
        logger.error(f"Debug log write failed: {e}")
    # #endregion
    
    message_count = 0
    while True:
        msg = await ps_websocket_client.receive_message()
        message_count += 1
        consumed_messages.append(msg)  # NEW: Save message
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'run_battle.py:385','message':'Received message in battle init loop','data':{'msg_count':message_count,'msg_preview':msg[:100] if msg else 'empty','has_battle_tag':'>battle-' in msg,'has_teampreview':'|teampreview|' in msg},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'D'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        lines = msg.split("\n")
        
        # Check if this message contains a battle tag
        current_battle_tag = None
        for line in lines:
            if line.startswith(">battle-"):
                current_battle_tag = line.replace(">", "").strip()
                break
        
        # If we found a battle tag in this message, check if it has team preview
        if current_battle_tag:
            if "|teampreview|" in msg:
                # This battle has team preview! Lock onto it
                if battle_tag is None:
                    battle_tag = current_battle_tag
                    has_team_preview = True
                    logger.debug(f"Found battle room with team preview: {battle_tag}")
        
        # Check if this message contains title info (which has the opponent name)
        if "|title|" in msg and (battle_tag is None or battle_tag in msg):
            for line in lines:
                if line.startswith("|title|"):
                    title = line.replace("|title|", "").strip()
                    user_name = FoulPlayConfig.username
                    # Extract opponent from "BotName vs. OpponentName"
                    if " vs. " in title:
                        opponent_name = title.split(" vs. ")[1].strip()
                    else:
                        opponent_name = title.replace(user_name, "").replace("vs.", "").strip()
                    logger.debug(f"Found opponent from title: {opponent_name}")
                    break
        
        # NEW: Also extract player ID (p1 or p2) from |player| messages
        if "|player|" in msg and opponent_name and (battle_tag is None or battle_tag in msg):
            for line in lines:
                if line.startswith("|player|") and opponent_name in line:
                    parts = line.split("|")
                    if len(parts) > 2:
                        player_id = parts[2].strip()  # p1 or p2
                        logger.debug(f"Found player ID for opponent: {player_id}")
                        break
        
        # Once we have everything, return
        if battle_tag and opponent_name and player_id and has_team_preview:
            logger.info("Initialized {} against: {} (player: {})".format(battle_tag, opponent_name, player_id))
            return battle_tag, opponent_name, player_id, consumed_messages


async def start_battle_common(
    ps_websocket_client: PSWebsocketClient, pokemon_battle_type
):
    battle_tag, opponent_name, player_id, consumed_messages = await get_battle_tag_and_opponent(ps_websocket_client)
    if FoulPlayConfig.log_to_file:
        FoulPlayConfig.file_log_handler.do_rollover(
            "{}_{}.log".format(battle_tag, opponent_name)
        )

    # Detect if this is a doubles format
    is_doubles = is_doubles_format(pokemon_battle_type)
    logger.info("Battle format: {} (Doubles: {})".format(pokemon_battle_type, is_doubles))
    
    battle = create_battle(battle_tag, pokemon_format=pokemon_battle_type, is_doubles=is_doubles)
    battle.opponent.account_name = opponent_name
    battle.pokemon_format = pokemon_battle_type
    battle.generation = pokemon_battle_type[:4]

    # Set opponent player ID (p1 or p2) from what we already parsed
    battle.opponent.name = player_id
    if player_id in constants.ID_LOOKUP:
        battle.user.name = constants.ID_LOOKUP[player_id]
        logger.debug(f"Set opponent.name={player_id}, user.name={battle.user.name}")
    else:
        logger.warning(f"Invalid player ID: {player_id}")

    # Return the last consumed message (which likely has team info)
    return battle, consumed_messages[-1] if consumed_messages else ""


async def get_first_request_json(
    ps_websocket_client: PSWebsocketClient, battle: Battle
):
    while True:
        msg = await ps_websocket_client.receive_message()
        msg_split = msg.split("|")
        # Message format: ">battle-tag||request|{json}" or "||request|{json}"
        # After split: [">battle-tag\n", "", "request", "{json}"] or ["", "", "request", "{json}"]
        # So we need to check if "request" is in the message, not at a specific index
        if "request" in msg_split and len(msg_split) > 2:
            # Find the index of "request"
            request_idx = msg_split.index("request")
            if request_idx > 0 and request_idx + 1 < len(msg_split) and msg_split[request_idx + 1].strip():
                user_json = json.loads(msg_split[request_idx + 1].strip("'"))
                logger.debug(f"Received battle JSON from server: {user_json}")
                battle.request_json = user_json
                battle.user.initialize_first_turn_user_from_json(user_json)
                battle.rqid = user_json[constants.RQID]
                return


async def start_random_battle(
    ps_websocket_client: PSWebsocketClient, pokemon_battle_type
):
    battle, msg = await start_battle_common(ps_websocket_client, pokemon_battle_type)
    battle.battle_type = BattleType.RANDOM_BATTLE
    RandomBattleTeamDatasets.initialize(battle.generation)

    while True:
        if constants.START_STRING in msg:
            battle.started = True

            # hold onto some messages to apply after we get the request JSON
            # omit the bot's switch-in message because we won't need that
            # parsing the request JSON will set the bot's active pkmn
            battle.msg_list = [
                m
                for m in msg.split(constants.START_STRING)[1].strip().split("\n")
                if not (m.startswith("|switch|{}".format(battle.user.name)))
            ]
            break
        msg = await ps_websocket_client.receive_message()

    await get_first_request_json(ps_websocket_client, battle)

    # apply the messages that were held onto
    process_battle_updates(battle)

    best_move = await async_pick_move(battle)
    await ps_websocket_client.send_message(battle.battle_tag, best_move)

    return battle


async def start_standard_battle(
    ps_websocket_client: PSWebsocketClient, pokemon_battle_type, team_dict
):
    battle, msg = await start_battle_common(ps_websocket_client, pokemon_battle_type)
    battle.user.team_dict = team_dict
    if "battlefactory" in pokemon_battle_type:
        battle.battle_type = BattleType.BATTLE_FACTORY
    else:
        battle.battle_type = BattleType.STANDARD_BATTLE

    if battle.generation in constants.NO_TEAM_PREVIEW_GENS:
        while True:
            if constants.START_STRING in msg:
                battle.started = True

                # hold onto some messages to apply after we get the request JSON
                # omit the bot's switch-in message because we won't need that
                # parsing the request JSON will set the bot's active pkmn
                battle.msg_list = [
                    m
                    for m in msg.split(constants.START_STRING)[1].strip().split("\n")
                    if not (m.startswith("|switch|{}".format(battle.user.name)))
                ]
                break
            msg = await ps_websocket_client.receive_message()

        await get_first_request_json(ps_websocket_client, battle)

        # Get active Pokemon names - handle both singles and doubles
        if isinstance(battle.user.active, list):
            active_names = [p.name for p in battle.user.active if p is not None]
        else:
            active_names = [battle.user.active.name] if battle.user.active else []
        
        unique_pkmn_names = set(
            [p.name for p in battle.user.reserve] + active_names
        )
        SmogonSets.initialize(
            FoulPlayConfig.smogon_stats or pokemon_battle_type, unique_pkmn_names
        )
        TeamDatasets.initialize(pokemon_battle_type, unique_pkmn_names)

        # apply the messages that were held onto
        process_battle_updates(battle)

        best_move = await async_pick_move(battle)
        await ps_websocket_client.send_message(battle.battle_tag, best_move)

    else:
        while constants.START_TEAM_PREVIEW not in msg:
            msg = await ps_websocket_client.receive_message()

        preview_string_lines = msg.split(constants.START_TEAM_PREVIEW)[-1].split("\n")

        opponent_pokemon = []
        user_pokemon_preview_order = []  # Store user Pokemon in team preview order
        
        for line in preview_string_lines:
            if not line:
                continue

            split_line = line.split("|")
            if split_line[1] == constants.TEAM_PREVIEW_POKE:
                player_id = split_line[2].strip()
                pokemon_string = split_line[3] if len(split_line) > 3 else ""
                
                # Extract Pokemon name from string (format: "PokemonName, L50" or just "PokemonName")
                pokemon_name = pokemon_string.split(",")[0].strip() if pokemon_string else ""
                
                if player_id == battle.opponent.name:
                    opponent_pokemon.append(split_line[3])
                elif player_id == battle.user.name or player_id == FoulPlayConfig.username:
                    # This is the user's Pokemon - store in team preview order
                    # Normalize the name to match how it's stored in battle objects
                    normalized_name = normalize_name(pokemon_name)
                    user_pokemon_preview_order.append(normalized_name)
                    logger.debug(f"Team preview user Pokemon {len(user_pokemon_preview_order)}: {pokemon_name} -> {normalized_name}")

        # Store team preview order on battle object
        battle.user_team_preview_order = user_pokemon_preview_order
        logger.info(f"Team preview order: {user_pokemon_preview_order}")

        await get_first_request_json(ps_websocket_client, battle)
        battle.initialize_team_preview(opponent_pokemon, pokemon_battle_type)
        battle.during_team_preview()

        unique_pkmn_names = set(
            p.name for p in battle.opponent.reserve + battle.user.reserve
        )

        if battle.battle_type == BattleType.BATTLE_FACTORY:
            battle.battle_type = BattleType.BATTLE_FACTORY
            tier_name = extract_battle_factory_tier_from_msg(msg)
            logger.info("Battle Factory Tier: {}".format(tier_name))
            TeamDatasets.initialize(
                pokemon_battle_type,
                unique_pkmn_names,
                battle_factory_tier_name=tier_name,
            )
        else:
            battle.battle_type = BattleType.STANDARD_BATTLE
            
            # For VGC/Doubles formats with team_dict, we have complete team data
            # Only initialize SmogonSets if we don't have team_dict or it's random battle
            if team_dict and any(fmt in pokemon_battle_type.lower() for fmt in ['vgc', 'doubles', 'bss']):
                logger.info("Skipping Smogon stats initialization - using preset team data")
            else:
                SmogonSets.initialize(
                    FoulPlayConfig.smogon_stats or pokemon_battle_type, unique_pkmn_names
                )
            
            TeamDatasets.initialize(pokemon_battle_type, unique_pkmn_names)

        await handle_team_preview(battle, ps_websocket_client)

    return battle


async def start_battle(ps_websocket_client, pokemon_battle_type, team_dict):
    if "random" in pokemon_battle_type:
        battle = await start_random_battle(ps_websocket_client, pokemon_battle_type)
    else:
        battle = await start_standard_battle(
            ps_websocket_client, pokemon_battle_type, team_dict
        )

    await ps_websocket_client.send_message(battle.battle_tag, ["hf"])
    await ps_websocket_client.send_message(battle.battle_tag, ["/timer on"])

    return battle


async def pokemon_battle(client, pokemon_battle_type, team_dict):
    """
    Main battle function that works with both WebSocket and Browser clients.
    
    Args:
        client: Either PSWebsocketClient or BrowserClient
        pokemon_battle_type: Battle format
        team_dict: Team dictionary
    """
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run_battle.py:1046','message':'pokemon_battle called','data':{'client_type':type(client).__name__,'pokemon_battle_type':pokemon_battle_type},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    # Check if using browser mode
    use_browser = isinstance(client, BrowserClient)
    
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run_battle.py:1058','message':'Starting battle','data':{'use_browser':use_browser},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    if use_browser:
        try:
            battle = await start_battle_browser(client, pokemon_battle_type, team_dict)
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'run_battle.py:1065','message':'start_battle_browser completed','data':{'battle_tag':battle.battle_tag if hasattr(battle,'battle_tag') else None},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
            except Exception as e:
                pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'run_battle.py:1072','message':'start_battle_browser failed','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
            except Exception as e2:
                pass
            # #endregion
            raise
    else:
        battle = await start_battle(client, pokemon_battle_type, team_dict)
    
    # Initialize turn logger for this battle
    bot_name = FoulPlayConfig.username or "Bot"
    turn_logger = BattleTurnLogger.get_or_create(bot_name, battle.battle_tag)
    set_turn_logger(turn_logger)
    
    logger.info(f"Turn logger initialized for {bot_name} in {battle.battle_tag}")
    
    # Log team composition
    if turn_logger:
        # Get my team from reserve + active
        my_team = []
        
        # Add active Pokemon (handles both singles and doubles)
        if battle.is_doubles:
            # For doubles, active is a list
            if isinstance(battle.user.active, list):
                my_team.extend([p.name for p in battle.user.active if p is not None])
        else:
            # For singles, active is a single Pokemon
            if battle.user.active:
                my_team.append(battle.user.active.name)
        
        # Add reserve Pokemon (avoid duplicates)
        reserve_names = [p.name for p in battle.user.reserve if p is not None]
        for name in reserve_names:
            if name not in my_team:
                my_team.append(name)
        
        # Verify which Pokemon actually came to battle
        # After battle starts, only the selected 4 Pokemon should be available
        if hasattr(battle, 'user_selected_team') and battle.user_selected_team:
            # Check if the Pokemon we see match what we selected
            available_pokemon = set(my_team)
            selected_pokemon_set = set(battle.user_selected_team)
            
            # Find Pokemon that are available but weren't selected (shouldn't happen)
            unexpected = available_pokemon - selected_pokemon_set
            if unexpected:
                logger.warning(f"Unexpected Pokemon in battle (not in selected team): {unexpected}")
            
            # Find Pokemon that were selected but aren't available (fainted or not sent)
            missing = selected_pokemon_set - available_pokemon
            if missing:
                logger.debug(f"Selected Pokemon not yet in battle: {missing}")
            
            # Update selected team to only include Pokemon that actually came
            actual_team = [p for p in battle.user_selected_team if p in available_pokemon]
            if len(actual_team) != len(battle.user_selected_team):
                logger.info(f"Actual team: {actual_team} (selected: {battle.user_selected_team})")
                battle.user_selected_team = actual_team
        
        # Get opponent team (may be incomplete if not all Pokemon revealed yet)
        opponent_team = []
        
        # Add active opponent Pokemon
        if battle.is_doubles:
            if isinstance(battle.opponent.active, list):
                opponent_team.extend([p.name for p in battle.opponent.active if p is not None])
        else:
            if battle.opponent.active:
                opponent_team.append(battle.opponent.active.name)
        
        # Add reserve opponent Pokemon (avoid duplicates)
        opponent_reserve_names = [p.name for p in battle.opponent.reserve if p is not None]
        for name in opponent_reserve_names:
            if name not in opponent_team:
                opponent_team.append(name)
        
        # Log the teams (include selected team and revealed opponent if available)
        selected_team = battle.user_selected_team if hasattr(battle, 'user_selected_team') and battle.user_selected_team else None
        revealed_opponent = list(battle.opponent_revealed_pokemon) if hasattr(battle, 'opponent_revealed_pokemon') and battle.opponent_revealed_pokemon else None
        turn_logger.log_team_composition(my_team, opponent_team if opponent_team else None, selected_team, revealed_opponent)
    
    # Main battle loop - different for browser vs WebSocket
    if use_browser:
        # Browser mode: poll browser state
        return await pokemon_battle_browser_loop(client, battle, turn_logger, bot_name)
    else:
        # WebSocket mode: receive messages
        return await pokemon_battle_websocket_loop(client, battle, turn_logger, bot_name)


async def pokemon_battle_websocket_loop(ps_websocket_client, battle, turn_logger, bot_name):
    """WebSocket-based battle loop."""
    while True:
        msg = await ps_websocket_client.receive_message()
        
        # Log all raw client messages with timestamps
        if turn_logger and msg:
            turn_logger.log_client_message(msg)
        
        # Log game events from this message
        if turn_logger and msg:
            for line in msg.split("\n"):
                line = line.strip()
                if line.startswith("|"):
                    turn_logger.log_raw_showdown_event(line)
                # Check for inactivity messages
                if "lost due to inactivity" in line.lower() or "timed out" in line.lower():
                    turn_logger.log_inactivity(line)
        
        if battle_is_finished(battle.battle_tag, msg):
            winner = (
                msg.split(constants.WIN_STRING)[-1].split("\n")[0].strip()
                if constants.WIN_STRING in msg
                else None
            )
            logger.info("Winner: {}".format(winner))
            
            # Finalize the turn logger
            if turn_logger:
                turn_logger.finalize(winner)
                BattleTurnLogger.clear_instance(bot_name, battle.battle_tag)
                set_turn_logger(None)
            
            await ps_websocket_client.send_message(battle.battle_tag, ["gg"])
            if FoulPlayConfig.save_replay == SaveReplay.always or (
                FoulPlayConfig.save_replay == SaveReplay.on_loss
                and winner != FoulPlayConfig.username
            ):
                await ps_websocket_client.save_replay(battle.battle_tag)
            await ps_websocket_client.leave_battle(battle.battle_tag)
            return winner
        else:
            action_required = await async_update_battle(battle, msg)
            logger.debug(f"Turn {battle.turn}: action_required={action_required}, battle.wait={battle.wait}")
            
            if action_required and not battle.wait:
                try:
                    best_move = await async_pick_move(battle)
                    await ps_websocket_client.send_message(battle.battle_tag, best_move)
                except AttributeError as e:
                    logger.error(f"AttributeError selecting/sending move on turn {battle.turn}: {e}", exc_info=True)
                    # Fallback: try to send a default move
                    try:
                        fallback_move = get_fallback_move(battle)
                        logger.warning(f"Using fallback move: {fallback_move}")
                        await ps_websocket_client.send_message(battle.battle_tag, fallback_move)
                    except Exception as fallback_error:
                        logger.error(f"Fallback move also failed: {fallback_error}", exc_info=True)
                        # Last resort: send "pass" to avoid inactivity
                        try:
                            if battle.is_doubles:
                                rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
                                await ps_websocket_client.send_message(battle.battle_tag, ["/choose move 1, move 1", str(rqid)])
                            else:
                                rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
                                await ps_websocket_client.send_message(battle.battle_tag, ["/choose move 1", str(rqid)])
                        except Exception as last_error:
                            logger.critical(f"Even pass move failed! Battle may timeout. Error: {last_error}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error selecting/sending move on turn {battle.turn}: {e}", exc_info=True)
                    
                    # Fallback: try to send a default move
                    try:
                        fallback_move = get_fallback_move(battle)
                        logger.warning(f"Using fallback move: {fallback_move}")
                        await ps_websocket_client.send_message(battle.battle_tag, fallback_move)
                    except Exception as fallback_error:
                        logger.error(f"Fallback move also failed: {fallback_error}", exc_info=True)
                        # Last resort: send "pass" to avoid inactivity
                        try:
                            if battle.is_doubles:
                                rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
                                await ps_websocket_client.send_message(battle.battle_tag, ["/choose move 1, move 1", str(rqid)])
                            else:
                                rqid = battle.request_json.get("rqid", "") if battle.request_json else ""
                                await ps_websocket_client.send_message(battle.battle_tag, ["/choose move 1", str(rqid)])
                        except Exception as last_error:
                            logger.critical(f"Even pass move failed! Battle may timeout. Error: {last_error}", exc_info=True)
