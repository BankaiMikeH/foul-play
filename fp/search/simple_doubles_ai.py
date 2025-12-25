"""
Simple AI for doubles battles - used as fallback until Rust engine supports doubles.
Uses random move selection with basic validity checking.
"""
import random
import logging
import constants

logger = logging.getLogger(__name__)


def select_random_doubles_move(battle):
    """
    Select a random valid move for a doubles battle.
    
    Returns:
        str: A decision string like "move 1 1, move 2 2" or "switch pokemon1, move 1 2"
    """
    # TEAM PREVIEW: Select Pokemon order for the battle
    if battle.team_preview:
        # In VGC doubles, we select 4 Pokemon from 6
        # For now, just use default order (first 4)
        # battle.user.reserve contains all 6 Pokemon before team preview
        num_pokemon = len(battle.user.reserve)
        
        # Generate team order - pick first 4, rest go at end
        # Format: "1234" means bring Pokemon 1,2,3,4 and leave 5,6 in back
        team_order = ''.join(str(i) for i in range(1, num_pokemon + 1))
        
        logger.info(f"Team preview selection: {team_order} ({num_pokemon} Pokemon total)")
        return "switch 1"  # This will be interpreted by handle_team_preview
    
    decisions = []
    
    # For each active position (0=left, 1=right)
    for position in range(2):
        pkmn = battle.user.get_active_pokemon(position)
        
        if pkmn is None:
            # No Pokemon at this position - shouldn't happen normally
            logger.warning(f"No Pokemon at position {position} during move selection")
            continue
        
        # Check if forced to switch
        if battle.force_switch:
            # Need to switch - pick a random reserve Pokemon
            alive_reserves = [p for p in battle.user.reserve if p.is_alive()]
            if alive_reserves:
                switch_pkmn = random.choice(alive_reserves) #- Bankaimike we need to make this not choose the same pokemon as the active pokemon or a random pokemon

                decisions.append(f"switch {switch_pkmn.name}")
            else:
                # No valid switches - use a random move (shouldn't happen)
                decisions.append(select_random_move_for_pokemon(pkmn, position))
        else:
            # Not forced to switch - can use a move or voluntarily switch
            # 90% chance to use a move, 10% chance to switch
            if random.random() < 0.9 or not battle.user.reserve:
                decisions.append(select_random_move_for_pokemon(pkmn, position))
            else:
                # Random switch
                alive_reserves = [p for p in battle.user.reserve if p.is_alive()]
                if alive_reserves:
                    switch_pkmn = random.choice(alive_reserves)
                    decisions.append(f"switch {switch_pkmn.name}")
                else:
                    decisions.append(select_random_move_for_pokemon(pkmn, position))
    
    # Join decisions with ", " for doubles format
    return ", ".join(decisions) if decisions else "move 1 1, move 1 2"


def select_random_move_for_pokemon(pkmn, position):
    """
    Select a random valid move for a single Pokemon in doubles.
    
    Args:
        pkmn: Pokemon object
        position: 0 for left, 1 for right
    
    Returns:
        str: Move decision like "move 1 1" (move index, target)
    """
    # Safety check: if Pokemon has no moves (e.g., during initialization), use move 1
    if not pkmn.moves or len(pkmn.moves) == 0:
        logger.warning(f"Pokemon {pkmn.name} has no moves - using move 1 target 1")
        return "move 1 1"
    
    # Get available (non-disabled) moves
    available_moves = [i for i, m in enumerate(pkmn.moves) if not m.disabled and m.current_pp > 0]
    
    if not available_moves:
        # All moves disabled/out of PP - use struggle (move 1)
        move_index = 1
    else:
        # Pick a random available move (1-indexed)
        move_index = random.choice(available_moves) + 1
    
    # Determine target
    # In doubles, targeting works like:
    # 1 = Opponent left
    # 2 = Opponent right  
    # -1 = Self/ally (for support moves)
    # 0 = Both opponents (spread moves)
    
    # For simplicity: target opponent in opposite position
    # Left position (0) targets opponent right (2)
    # Right position (1) targets opponent left (1)
    target = 2 if position == 0 else 1
    
    # Check if move is a spread move or self-target move
    # Safely get the move (handle case where move_index is out of bounds)
    if move_index <= len(pkmn.moves):
        move = pkmn.moves[move_index - 1]
        move_name = move.name
    else:
        # Fallback if index is invalid
        logger.warning(f"Invalid move index {move_index} for {pkmn.name}, using move 1")
        move_index = 1
        if pkmn.moves:
            move = pkmn.moves[0]
            move_name = move.name
        else:
            return "move 1 1"
    
    # Self-target moves (protect, nastyplot, etc.)
    self_target_moves = ["protect", "detect", "kingsshield", "spikyshield", "banefulbunker",
                         "obstruct", "silktrap", "burningbulwark", "substitute",
                         "nastyplot", "calmmind", "swordsdance", "dragondance", "agility",
                         "irondefense", "rockpolish", "tailwind", "trickroom"]
    
    if move_name in self_target_moves:
        target = -1  # Self
    
    return f"move {move_index} {target}"


def select_random_singles_move(battle):
    """
    Select a random valid move for a singles battle.
    
    Returns:
        str: A decision string like "move 1" or "switch pokemonname"
    """
    # TEAM PREVIEW: Just select which Pokemon to send out
    if battle.team_preview:
        if battle.user.reserve:
            return "switch 1"
        else:
            return "switch 1"
    
    pkmn = battle.user.active
    
    if not pkmn:
        logger.error("No active Pokemon in singles battle!")
        return "move 1"
    
    # Check if forced to switch
    if battle.force_switch:
        alive_reserves = [p for p in battle.user.reserve if p.is_alive()]
        if alive_reserves:
            switch_pkmn = random.choice(alive_reserves)
            return f"switch {switch_pkmn.name}"
        else:
            return "move 1"  # Shouldn't happen
    
    # 90% chance to use a move
    if random.random() < 0.9 or not battle.user.reserve:
        # Get available moves
        available_moves = [i for i, m in enumerate(pkmn.moves) if not m.disabled and m.current_pp > 0]
        
        if available_moves:
            move_index = random.choice(available_moves) + 1
        else:
            move_index = 1  # Struggle
        
        return f"move {move_index}"
    else:
        # Random switch
        alive_reserves = [p for p in battle.user.reserve if p.is_alive()]
        if alive_reserves:
            switch_pkmn = random.choice(alive_reserves)
            return f"switch {switch_pkmn.name}"
        else:
            return "move 1"

