import logging

import constants
from data import pokedex
from fp.battle import Battle, Pokemon, Battler, LastUsedMove

from poke_engine import (
    State as PokeEngineState,
    Side as PokeEngineSide,
    SideConditions as PokeEngineSideConditions,
    VolatileStatusDurations as PokeEngineVolatileStatusDurations,
    Pokemon as PokeEnginePokemon,
    Move as PokeEngineMove,
    calculate_damage,
)

logger = logging.getLogger(__name__)


def status_to_string(status):
    if status == constants.SLEEP:
        return "Sleep"
    elif status == constants.BURN:
        return "Burn"
    elif status == constants.FROZEN:
        return "Freeze"
    elif status == constants.PARALYZED:
        return "Paralyze"
    elif status == constants.POISON:
        return "Poison"
    elif status == constants.TOXIC:
        return "Toxic"
    elif status is None:
        return "None"
    raise ValueError(f"Unknown status: {status}")


def pokemon_to_poke_engine_pkmn(pkmn: Pokemon):
    """
    id,level,type0,type1,hp,maxhp,ability,item,atk,def,spa,spd,spe,atkb,defb,spab,spdb,speb,accb,evab,status,subhp,restturns
    nature,volatiles,m0,m1,m2,m3
    """

    # Gen 3/4 don't remove items if knocked off
    # but the item is not active, so lets remove it
    if pkmn.knocked_off or pkmn.item == "" or pkmn.item is None:
        pkmn.item = "None"

    base_types = pokedex[str(pkmn.name)][constants.TYPES]
    if len(base_types) == 1:
        base_types = (base_types[0], "typeless")
    if len(pkmn.types) == 1:
        pkmn.types = (pkmn.types[0], "typeless")
    num_moves = len(pkmn.moves)
    if num_moves > 4:
        logger.warning(
            "More than 4 moves on pokemon: {} moves: {}".format(
                pkmn.name, [m.name for m in pkmn.moves]
            )
        )
        logger.warning("Truncating moves to first 4")
        pkmn.moves = pkmn.moves[:4]

    pkmn_moves = [
        PokeEngineMove(id=str(m.name), disabled=m.disabled, pp=m.current_pp)
        for m in pkmn.moves
    ]
    while num_moves < 4:
        pkmn_moves.append(PokeEngineMove(id="none", disabled=True, pp=0))
        num_moves += 1

    base_ability = ""
    if pkmn.original_ability:
        base_ability = str(pkmn.original_ability)

    return PokeEnginePokemon(
        id=str(pkmn.name),
        level=pkmn.level,
        types=tuple(pkmn.types),
        base_types=tuple(base_types),
        hp=int(pkmn.hp),
        maxhp=int(pkmn.max_hp),
        ability=str(pkmn.ability),
        base_ability=base_ability,
        item=str(pkmn.item),
        nature=pkmn.nature,
        evs=tuple(pkmn.evs),
        attack=pkmn.stats[constants.ATTACK],
        defense=pkmn.stats[constants.DEFENSE],
        special_attack=pkmn.stats[constants.SPECIAL_ATTACK],
        special_defense=pkmn.stats[constants.SPECIAL_DEFENSE],
        speed=pkmn.stats[constants.SPEED],
        status=status_to_string(pkmn.status),
        rest_turns=pkmn.rest_turns,
        sleep_turns=pkmn.sleep_turns,
        weight_kg=float(pokedex[pkmn.name][constants.WEIGHT]),
        moves=pkmn_moves,
        tera_type=pkmn.tera_type or "typeless",
        terastallized=pkmn.terastallized,
    )


def get_dummy_poke_engine_pkmn():
    return PokeEnginePokemon(id="pikachu", level=1, hp=0)


def battler_to_poke_engine_side(
    battler: Battler, force_switch=False, stayed_in_on_switchout_move=False
):
    """
    Convert a Python Battler to a poke-engine Side.
    Supports both singles and doubles battles.
    
    For singles: battler.active is a single Pokemon
    For doubles: battler.active is a list of 2 Pokemon [left, right]
    """
    # For singles, use the original implementation
    if not battler.is_doubles:
        return _battler_to_poke_engine_side_singles(
            battler, force_switch, stayed_in_on_switchout_move
        )
    
    # For doubles, use the new doubles implementation
    return _battler_to_poke_engine_side_doubles(
        battler, force_switch, stayed_in_on_switchout_move
    )


def _battler_to_poke_engine_side_singles(
    battler: Battler, force_switch=False, stayed_in_on_switchout_move=False
):
    """Original singles implementation"""
    # Defensive check: ensure active Pokemon exists
    if battler.active is None:
        raise ValueError("Cannot convert battler with None active Pokemon (singles)")
    
    num_reserves = len(battler.reserve)
    last_used_move = "move:none"
    if battler.last_used_move.move.startswith("switch "):
        last_used_move = "switch:0"
    elif battler.last_used_move.move:
        try:
            pkmn_moves = [m.name for m in battler.active.moves]
            for i, move in enumerate(pkmn_moves):
                if move == battler.last_used_move.move:
                    last_used_move = "move:{}".format(i)
                    break
            else:
                last_used_move = "move:0"
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error accessing active Pokemon moves: {e}. Using default move:0")
            last_used_move = "move:0"

    # substitute health can't be known with certainty but the client can keep track of if the substitute was hit
    # to approximate: the substitute health is 1/10 of the pokemon's max_hp if it was hit, 1/4 if it wasn't
    substitute_health = 0
    if constants.SUBSTITUTE in battler.active.volatile_statuses:
        if battler.active.substitute_hit:
            substitute_health = int(battler.active.max_hp / 10)
        else:
            substitute_health = int(battler.active.max_hp / 4)

    future_sight_index = 0
    if battler.future_sight[0] > 0:
        if (
            battler.active.name == battler.future_sight[1]
            or battler.active.base_name == battler.future_sight[1]
        ):
            future_sight_index = 0
        else:
            index = 1
            for pkmn in battler.reserve:
                if (
                    pkmn.name == battler.future_sight[1]
                    or pkmn.base_name == battler.future_sight[1]
                ):
                    future_sight_index = index
                    break
                index += 1
            else:
                raise ValueError(
                    "Couldnt find future sight source: {} not in {} + {}".format(
                        battler.future_sight[1],
                        battler.active.name,
                        [p.name for p in battler.reserve],
                    )
                )

    side = PokeEngineSide(
        active_index="0",
        baton_passing=battler.baton_passing,
        shed_tailing=battler.shed_tailing,
        pokemon=[pokemon_to_poke_engine_pkmn(battler.active)]
        + [pokemon_to_poke_engine_pkmn(p) for p in battler.reserve],
        side_conditions=PokeEngineSideConditions(
            aurora_veil=battler.side_conditions[constants.AURORA_VEIL],
            crafty_shield=battler.side_conditions["craftyshield"],
            healing_wish=battler.side_conditions[constants.HEALING_WISH],
            light_screen=battler.side_conditions[constants.LIGHT_SCREEN],
            lucky_chant=battler.side_conditions["luckychant"],
            lunar_dance=battler.side_conditions["lunardance"],
            mat_block=battler.side_conditions["matblock"],
            mist=battler.side_conditions["mist"],
            protect=battler.side_conditions[constants.PROTECT],
            quick_guard=battler.side_conditions["quickguard"],
            reflect=battler.side_conditions[constants.REFLECT],
            safeguard=battler.side_conditions[constants.SAFEGUARD],
            spikes=battler.side_conditions[constants.SPIKES],
            stealth_rock=battler.side_conditions[constants.STEALTH_ROCK],
            sticky_web=battler.side_conditions[constants.STICKY_WEB],
            tailwind=battler.side_conditions[constants.TAILWIND],
            toxic_count=battler.side_conditions[constants.TOXIC_COUNT],
            toxic_spikes=battler.side_conditions[constants.TOXIC_SPIKES],
            wide_guard=battler.side_conditions["wideguard"],
        ),
        wish=(int(battler.wish[0]), int(battler.wish[1])),
        future_sight=(battler.future_sight[0], str(future_sight_index)),
        force_switch=force_switch,
        force_trapped=battler.trapped,
        slow_uturn_move=stayed_in_on_switchout_move,
        volatile_statuses=set(battler.active.volatile_statuses),
        volatile_status_durations=PokeEngineVolatileStatusDurations(
            confusion=battler.active.volatile_status_durations[constants.CONFUSION],
            lockedmove=battler.active.volatile_status_durations[constants.LOCKED_MOVE],
            encore=battler.active.volatile_status_durations["encore"],
            slowstart=battler.active.volatile_status_durations[constants.SLOW_START],
            taunt=battler.active.volatile_status_durations[constants.TAUNT],
            yawn=battler.active.volatile_status_durations[constants.YAWN],
        ),
        substitute_health=substitute_health,
        attack_boost=battler.active.boosts[constants.ATTACK],
        defense_boost=battler.active.boosts[constants.DEFENSE],
        special_attack_boost=battler.active.boosts[constants.SPECIAL_ATTACK],
        special_defense_boost=battler.active.boosts[constants.SPECIAL_DEFENSE],
        speed_boost=battler.active.boosts[constants.SPEED],
        accuracy_boost=0,
        evasion_boost=0,
        last_used_move=last_used_move,
        switch_out_move_second_saved_move="NONE",  # always none because we can't know this
    )

    while num_reserves < 5:
        side.pokemon.append(get_dummy_poke_engine_pkmn())
        num_reserves += 1

    return side


def _battler_to_poke_engine_side_doubles(
    battler: Battler, force_switch=False, stayed_in_on_switchout_move=False
):
    """
    Convert a doubles Battler to poke-engine Side.
    
    In doubles:
    - battler.active = [Pokemon, Pokemon] (or [Pokemon, None] or [None, Pokemon])
    - The two active Pokemon are stored as the first two entries in the pokemon list
    - The reserves follow after
    - active_index indicates which Pokemon are currently active (e.g., "0,1" for both)
    """
    # Get active Pokemon (may be None for empty slots)
    active_left = battler.get_active_pokemon(0)
    active_right = battler.get_active_pokemon(1)
    
    # Build pokemon list: [left_active, right_active, reserves...]
    pokemon_list = []
    active_indices = []
    
    # Add left active Pokemon (index 0)
    if active_left is not None:
        pokemon_list.append(pokemon_to_poke_engine_pkmn(active_left))
        active_indices.append("0")
    else:
        pokemon_list.append(get_dummy_poke_engine_pkmn())
    
    # Add right active Pokemon (index 1)
    if active_right is not None:
        pokemon_list.append(pokemon_to_poke_engine_pkmn(active_right))
        active_indices.append("1")
    else:
        pokemon_list.append(get_dummy_poke_engine_pkmn())
    
    # Add reserve Pokemon
    for pkmn in battler.reserve:
        pokemon_list.append(pokemon_to_poke_engine_pkmn(pkmn))
    
    # For doubles, we use the first active Pokemon's stats for side-level tracking
    # This is a simplification - in full implementation, we'd track per-Pokemon
    primary_active = active_left if active_left is not None else active_right
    
    if primary_active is None:
        # Both slots empty - use dummy data
        logger.warning("Both active slots empty in doubles battle")
        volatile_statuses = set()
        volatile_status_durations = PokeEngineVolatileStatusDurations(
            confusion=0, lockedmove=0, encore=0, slowstart=0, taunt=0, yawn=0
        )
        substitute_health = 0
        attack_boost = 0
        defense_boost = 0
        special_attack_boost = 0
        special_defense_boost = 0
        speed_boost = 0
    else:
        # Use primary active Pokemon's data
        volatile_statuses = set(primary_active.volatile_statuses)
        volatile_status_durations = PokeEngineVolatileStatusDurations(
            confusion=primary_active.volatile_status_durations[constants.CONFUSION],
            lockedmove=primary_active.volatile_status_durations[constants.LOCKED_MOVE],
            encore=primary_active.volatile_status_durations["encore"],
            slowstart=primary_active.volatile_status_durations[constants.SLOW_START],
            taunt=primary_active.volatile_status_durations[constants.TAUNT],
            yawn=primary_active.volatile_status_durations[constants.YAWN],
        )
        
        # Calculate substitute health
        substitute_health = 0
        if constants.SUBSTITUTE in primary_active.volatile_statuses:
            if primary_active.substitute_hit:
                substitute_health = int(primary_active.max_hp / 10)
            else:
                substitute_health = int(primary_active.max_hp / 4)
        
        # Get boosts
        attack_boost = primary_active.boosts[constants.ATTACK]
        defense_boost = primary_active.boosts[constants.DEFENSE]
        special_attack_boost = primary_active.boosts[constants.SPECIAL_ATTACK]
        special_defense_boost = primary_active.boosts[constants.SPECIAL_DEFENSE]
        speed_boost = primary_active.boosts[constants.SPEED]
    
    # Determine last used move
    last_used_move = "move:none"
    if battler.last_used_move.move.startswith("switch "):
        last_used_move = "switch:0"
    elif battler.last_used_move.move and primary_active is not None:
        pkmn_moves = [m.name for m in primary_active.moves]
        for i, move in enumerate(pkmn_moves):
            if move == battler.last_used_move.move:
                last_used_move = "move:{}".format(i)
                break
        else:
            last_used_move = "move:0"
    
    # Calculate future sight index
    future_sight_index = 0
    if battler.future_sight[0] > 0:
        found = False
        # Check active Pokemon first
        if active_left and (active_left.name == battler.future_sight[1] or 
                           active_left.base_name == battler.future_sight[1]):
            future_sight_index = 0
            found = True
        elif active_right and (active_right.name == battler.future_sight[1] or 
                               active_right.base_name == battler.future_sight[1]):
            future_sight_index = 1
            found = True
        
        # Check reserves
        if not found:
            index = 2  # Reserves start at index 2 in doubles
            for pkmn in battler.reserve:
                if (pkmn.name == battler.future_sight[1] or 
                    pkmn.base_name == battler.future_sight[1]):
                    future_sight_index = index
                    found = True
                    break
                index += 1
            
            if not found:
                logger.warning(
                    "Couldnt find future sight source: {} not in active or reserves".format(
                        battler.future_sight[1]
                    )
                )
    
    # Build the side object
    side = PokeEngineSide(
        active_index=":".join(active_indices) if active_indices else "0",  # Use colon separator for doubles
        baton_passing=battler.baton_passing,
        shed_tailing=battler.shed_tailing,
        pokemon=pokemon_list,
        side_conditions=PokeEngineSideConditions(
            aurora_veil=battler.side_conditions[constants.AURORA_VEIL],
            crafty_shield=battler.side_conditions["craftyshield"],
            healing_wish=battler.side_conditions[constants.HEALING_WISH],
            light_screen=battler.side_conditions[constants.LIGHT_SCREEN],
            lucky_chant=battler.side_conditions["luckychant"],
            lunar_dance=battler.side_conditions["lunardance"],
            mat_block=battler.side_conditions["matblock"],
            mist=battler.side_conditions["mist"],
            protect=battler.side_conditions[constants.PROTECT],
            quick_guard=battler.side_conditions["quickguard"],
            reflect=battler.side_conditions[constants.REFLECT],
            safeguard=battler.side_conditions[constants.SAFEGUARD],
            spikes=battler.side_conditions[constants.SPIKES],
            stealth_rock=battler.side_conditions[constants.STEALTH_ROCK],
            sticky_web=battler.side_conditions[constants.STICKY_WEB],
            tailwind=battler.side_conditions[constants.TAILWIND],
            toxic_count=battler.side_conditions[constants.TOXIC_COUNT],
            toxic_spikes=battler.side_conditions[constants.TOXIC_SPIKES],
            wide_guard=battler.side_conditions["wideguard"],
        ),
        wish=(int(battler.wish[0]), int(battler.wish[1])),
        future_sight=(battler.future_sight[0], str(future_sight_index)),
        force_switch=force_switch,
        force_trapped=battler.trapped,
        slow_uturn_move=stayed_in_on_switchout_move,
        volatile_statuses=volatile_statuses,
        volatile_status_durations=volatile_status_durations,
        substitute_health=substitute_health,
        attack_boost=attack_boost,
        defense_boost=defense_boost,
        special_attack_boost=special_attack_boost,
        special_defense_boost=special_defense_boost,
        speed_boost=speed_boost,
        accuracy_boost=0,
        evasion_boost=0,
        last_used_move=last_used_move,
        switch_out_move_second_saved_move="NONE",
    )
    
    # Pad with dummy Pokemon to reach 6 total
    while len(side.pokemon) < 6:
        side.pokemon.append(get_dummy_poke_engine_pkmn())
    
    return side


def get_weather_string(weather):
    if weather == constants.RAIN:
        return "rain"
    elif weather == constants.SUN:
        return "sun"
    elif weather == constants.SAND:
        return "sand"
    elif weather == constants.HAIL:
        return "hail"
    elif weather == constants.SNOW:
        return "snow"
    elif weather == constants.DESOLATE_LAND:
        return "harshsun"
    elif weather == constants.HEAVY_RAIN:
        return "heavyrain"
    elif weather is None:
        return "none"
    elif weather == "none":
        return "none"
    else:
        raise ValueError(f"Unknown weather {weather}")


def get_terrain_string(terrain):
    if terrain == constants.ELECTRIC_TERRAIN:
        return "electricterrain"
    elif terrain == constants.GRASSY_TERRAIN:
        return "grassyterrain"
    elif terrain == constants.MISTY_TERRAIN:
        return "mistyterrain"
    elif terrain == constants.PSYCHIC_TERRAIN:
        return "psychicterrain"
    elif terrain is None:
        return "none"
    elif terrain == "none":
        return "none"
    else:
        raise ValueError(f"Unknown terrain {terrain}")


def replace_hidden_power_last_used_move(battler: Battler):
    for mv in battler.active.moves:
        if mv.name.startswith(constants.HIDDEN_POWER):
            battler.last_used_move = LastUsedMove(
                pokemon_name=battler.last_used_move.pokemon_name,
                move=mv.name,
                turn=battler.last_used_move.turn,
            )
            break
    else:
        logger.warning("Could not replace hiddenpower")
        battler.last_used_move = LastUsedMove(
            pokemon_name=battler.last_used_move.pokemon_name,
            move="switch {}".format(battler.active.name),
            turn=battler.last_used_move.turn,
        )


def replace_return_last_used_move(battler: Battler):
    for mv in battler.active.moves:
        if mv.name.startswith("return"):
            battler.last_used_move = LastUsedMove(
                pokemon_name=battler.last_used_move.pokemon_name,
                move=mv.name,
                turn=battler.last_used_move.turn,
            )
            break
    else:
        logger.warning("Could not replace return")
        battler.last_used_move = LastUsedMove(
            pokemon_name=battler.last_used_move.pokemon_name,
            move="switch {}".format(battler.active.name),
            turn=battler.last_used_move.turn,
        )


def battle_to_poke_engine_state(battle: Battle, swap=False):
    # Boolean that represents if we have used a switch-out move first (i.e. fast uturn)
    # this is toggled to True if we did, and signifies to the engine that the opponent has
    # selected a move and that should be accounted for in the search
    opponent_switchout_move_stayed_in = False
    bot_lum = battle.user.last_used_move
    opp_lum = battle.opponent.last_used_move
    if bot_lum.move in constants.SWITCH_OUT_MOVES and opp_lum.turn != bot_lum.turn:
        opponent_switchout_move_stayed_in = True

    if battle.opponent.last_used_move.move == constants.HIDDEN_POWER:
        replace_hidden_power_last_used_move(battle.opponent)
    elif battle.opponent.last_used_move.move == "return":
        replace_return_last_used_move(battle.opponent)

    if battle.user.last_used_move.move == constants.HIDDEN_POWER:
        replace_hidden_power_last_used_move(battle.user)
    if battle.user.last_used_move.move == "return":
        replace_return_last_used_move(battle.user)

    # Filter user's reserve to only include selected Pokemon from team preview
    # This ensures the bot can't try to use Pokemon it didn't bring
    original_reserve = battle.user.reserve
    if hasattr(battle, 'user_selected_team') and battle.user_selected_team:
        selected_team_set = set(battle.user_selected_team)
        # Filter reserve to only selected Pokemon
        filtered_reserve = [p for p in battle.user.reserve if p.name in selected_team_set]
        # Also include active Pokemon if they're in the selected team
        if battle.is_doubles:
            active_pokemon = [p for p in battle.user.active if p is not None]
        else:
            active_pokemon = [battle.user.active] if battle.user.active else []
        
        # Check if active Pokemon are in selected team (they should be, but verify)
        for pkmn in active_pokemon:
            if pkmn and pkmn.name not in selected_team_set:
                logger.warning(f"Active Pokemon {pkmn.name} not in selected team {battle.user_selected_team}")
        
        # Temporarily replace reserve with filtered version
        battle.user.reserve = filtered_reserve
        logger.debug(f"Filtered reserve: {len(filtered_reserve)}/{len(original_reserve)} Pokemon (selected team: {battle.user_selected_team})")

    side_one = battler_to_poke_engine_side(
        battle.user, force_switch=battle.force_switch
    )
    
    # Restore original reserve after conversion
    if hasattr(battle, 'user_selected_team') and battle.user_selected_team:
        battle.user.reserve = original_reserve
    side_two = battler_to_poke_engine_side(
        battle.opponent, stayed_in_on_switchout_move=opponent_switchout_move_stayed_in
    )

    if swap:
        side_one, side_two = side_two, side_one

    state = PokeEngineState(
        side_one=side_one,
        side_two=side_two,
        weather=get_weather_string(battle.weather),
        weather_turns_remaining=battle.weather_turns_remaining,
        terrain=get_terrain_string(battle.field),
        terrain_turns_remaining=battle.field_turns_remaining,
        trick_room=battle.trick_room,
        trick_room_turns_remaining=battle.trick_room_turns_remaining,
        team_preview=battle.team_preview,
    )

    return state


def poke_engine_get_damage_rolls(
    battle: Battle, side_one_move, side_two_move, side_one_went_first
):
    # For doubles battles, the Rust engine doesn't support damage calculation yet
    # Return empty rolls as fallback
    if battle.is_doubles:
        logger.debug("Skipping Rust damage calculation for doubles battle")
        return [], []
    
    if side_one_move.startswith("switch"):
        side_one_move = "switch"
    if side_two_move.startswith("switch"):
        side_two_move = "switch"

    try:
        state = battle_to_poke_engine_state(battle)

        logger.debug(
            "Calling calculate damage with state: {}, m1: {}, m2: {}, s1_went_first: {}".format(
                state.to_string(),
                side_one_move,
                side_two_move,
                side_one_went_first,
            )
        )

        s1_rolls, s2_rolls = calculate_damage(
            state,
            side_one_move,
            side_two_move,
            side_one_went_first,
        )

        logger.debug(
            "Got Rolls s1_rolls: {}, s2_rolls: {}".format(
                s1_rolls,
                s2_rolls,
            )
        )

        return s1_rolls, s2_rolls
    except Exception as e:
        logger.warning(f"Rust damage calculation failed: {e}")
        return [], []


def parse_rust_decision_for_doubles(rust_decision: str) -> tuple:
    """
    Parse a Rust decision string for doubles battles.
    
    Rust returns decisions in format:
    - "move1,move2" - Both Pokemon use moves
    - "move1,switch1" - Left uses move, right switches
    - "switch1,move2" - Left switches, right uses move
    - "switch1,switch2" - Both switch
    
    Returns:
        tuple: (left_decision, right_decision) where each is a dict with:
            - 'type': 'move' or 'switch'
            - 'index': move index (0-3) or Pokemon index for switch
            - 'target': target position (for moves, optional)
    """
    parts = rust_decision.split(",")
    if len(parts) != 2:
        logger.warning(
            "Expected 2 decisions for doubles, got {}: {}".format(
                len(parts), rust_decision
            )
        )
        # Fallback: return default decisions
        return (
            {"type": "move", "index": 0, "target": 1},
            {"type": "move", "index": 0, "target": 2},
        )
    
    left_decision = _parse_single_rust_decision(parts[0].strip())
    right_decision = _parse_single_rust_decision(parts[1].strip())
    
    return (left_decision, right_decision)


def _parse_single_rust_decision(decision_str: str) -> dict:
    """
    Parse a single Rust decision string.
    
    Examples:
    - "move0" -> move at index 0
    - "move1target2" -> move at index 1 targeting position 2
    - "switch2" -> switch to Pokemon at index 2
    
    Returns:
        dict with 'type', 'index', and optionally 'target'
    """
    if decision_str.startswith("switch"):
        # Extract Pokemon index
        index_str = decision_str.replace("switch", "")
        try:
            index = int(index_str)
        except ValueError:
            logger.warning("Invalid switch index: {}".format(index_str))
            index = 0
        
        return {"type": "switch", "index": index}
    
    elif decision_str.startswith("move"):
        # Extract move index and optional target
        move_str = decision_str.replace("move", "")
        
        # Check for target specification
        if "target" in move_str:
            parts = move_str.split("target")
            try:
                move_index = int(parts[0])
                target = int(parts[1])
            except (ValueError, IndexError):
                logger.warning("Invalid move with target: {}".format(move_str))
                move_index = 0
                target = 1
            
            return {"type": "move", "index": move_index, "target": target}
        else:
            # No explicit target
            try:
                move_index = int(move_str)
            except ValueError:
                logger.warning("Invalid move index: {}".format(move_str))
                move_index = 0
            
            return {"type": "move", "index": move_index}
    
    else:
        logger.warning("Unknown decision type: {}".format(decision_str))
        return {"type": "move", "index": 0}


def rust_decision_to_showdown_decision_doubles(
    battle: Battle, rust_decision: str
) -> str:
    """
    Convert a Rust decision to Showdown format for doubles battles.
    
    Args:
        battle: The current battle state
        rust_decision: Decision string from Rust (e.g., "move0,move1" or "move0,switch2")
    
    Returns:
        Showdown decision string (e.g., "/choose move 1 1, move 2 2")
    """
    from fp.run_battle import format_decision
    
    # Parse the Rust decision
    left_dec, right_dec = parse_rust_decision_for_doubles(rust_decision)
    
    # Build decision objects compatible with format_decision
    decisions = []
    
    # Left Pokemon decision
    if left_dec["type"] == "move":
        move_index = left_dec["index"]
        target = left_dec.get("target", 1)  # Default to left opponent
        left_active = battle.user.get_active_pokemon(0)
        
        if left_active and move_index < len(left_active.moves):
            move_name = left_active.moves[move_index].name
            decisions.append({
                "type": "move",
                "move": move_name,
                "index": move_index,
                "target": target,
                "position": 0,
            })
        else:
            # Fallback to first move
            decisions.append({
                "type": "move",
                "move": "struggle",
                "index": 0,
                "target": 1,
                "position": 0,
            })
    else:
        # Switch
        pokemon_index = left_dec["index"]
        decisions.append({
            "type": "switch",
            "index": pokemon_index,
            "position": 0,
        })
    
    # Right Pokemon decision
    if right_dec["type"] == "move":
        move_index = right_dec["index"]
        target = right_dec.get("target", 2)  # Default to right opponent
        right_active = battle.user.get_active_pokemon(1)
        
        if right_active and move_index < len(right_active.moves):
            move_name = right_active.moves[move_index].name
            decisions.append({
                "type": "move",
                "move": move_name,
                "index": move_index,
                "target": target,
                "position": 1,
            })
        else:
            # Fallback to first move
            decisions.append({
                "type": "move",
                "move": "struggle",
                "index": 0,
                "target": 2,
                "position": 1,
            })
    else:
        # Switch
        pokemon_index = right_dec["index"]
        decisions.append({
            "type": "switch",
            "index": pokemon_index,
            "position": 1,
        })
    
    # Use the existing format_decision function
    return format_decision(battle, decisions)


def rust_decision_to_showdown_decision_singles(
    battle: Battle, rust_decision: str
) -> str:
    """
    Convert a Rust decision to Showdown format for singles battles.
    
    Args:
        battle: The current battle state
        rust_decision: Decision string from Rust (e.g., "move0" or "switch2")
    
    Returns:
        Showdown decision string (e.g., "/choose move 1" or "/choose switch 3")
    """
    decision = _parse_single_rust_decision(rust_decision)
    
    if decision["type"] == "move":
        move_index = decision["index"]
        # Move indices in Showdown are 1-based
        return "/choose move {}".format(move_index + 1)
    else:
        # Switch index + 1 for Showdown (1-based)
        # Also need to account for active Pokemon being index 0
        pokemon_index = decision["index"]
        return "/choose switch {}".format(pokemon_index + 1)


def rust_decision_to_showdown_decision(battle: Battle, rust_decision: str) -> str:
    """
    Convert a Rust decision to Showdown format.
    Automatically detects singles vs doubles.
    
    Args:
        battle: The current battle state
        rust_decision: Decision string from Rust
    
    Returns:
        Showdown decision string
    """
    if battle.is_doubles:
        return rust_decision_to_showdown_decision_doubles(battle, rust_decision)
    else:
        return rust_decision_to_showdown_decision_singles(battle, rust_decision)
