import logging
import random
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy

from constants import BattleType
from fp.battle import Battle
from config import FoulPlayConfig
from .standard_battles import prepare_battles
from .random_battles import prepare_random_battles

from poke_engine import State as PokeEngineState, mcts

from fp.search.poke_engine_helpers import battle_to_poke_engine_state
from fp.search.simple_doubles_ai import select_random_doubles_move, select_random_singles_move

logger = logging.getLogger(__name__)


def parse_rust_doubles_decision(rust_decision):
    """
    Parse Rust DoubleAction format to Python doubles format.
    
    Rust format: "[move1, move2]" or "[move1-tera, switch pokemon2]"
    Python format: "move1, move2" or "move1-tera, switch pokemon2"
    
    Args:
        rust_decision: String from Rust like "[tackle, thunderbolt]"
        
    Returns:
        Python format string like "tackle, thunderbolt"
    """
    if rust_decision.startswith("[") and rust_decision.endswith("]"):
        # Remove brackets and return
        return rust_decision[1:-1]
    # Already in Python format or singles format
    return rust_decision


def select_move_from_mcts_results(mcts_results):  # list[(dict, float, int)]) -> str:
    """
    Select the best move from MCTS results.
    
    Args:
        mcts_results: list of (mcts_dict, sample_chance, index) tuples
            where mcts_dict has keys: iteration_count, s1, s2
    """
    final_policy = {}
    for mcts_result, sample_chance, index in mcts_results:
        # mcts_result['s1'] is now a list of dicts
        this_policy = max(mcts_result['s1'], key=lambda x: x['visits'])
        logger.info(
            "Policy {}: {} visited {}% avg_score={} sample_chance_multiplier={}".format(
                index,
                this_policy['move_choice'],
                round(100 * this_policy['visits'] / mcts_result['iteration_count'], 2),
                round(this_policy['total_score'] / this_policy['visits'], 3),
                round(sample_chance, 3),
            )
        )
        for s1_option in mcts_result['s1']:
            final_policy[s1_option['move_choice']] = final_policy.get(
                s1_option['move_choice'], 0
            ) + (sample_chance * (s1_option['visits'] / mcts_result['iteration_count']))

    final_policy = sorted(final_policy.items(), key=lambda x: x[1], reverse=True)

    # Consider all moves that are close to the best move
    highest_percentage = final_policy[0][1]
    final_policy = [i for i in final_policy if i[1] >= highest_percentage * 0.75]
    logger.info("Considered Choices:")
    for i, policy in enumerate(final_policy):
        logger.info(f"\t{round(policy[1] * 100, 3)}%: {policy[0]}")

    choice = random.choices(final_policy, weights=[p[1] for p in final_policy])[0]
    rust_decision = choice[0]
    
    # Parse Rust doubles format if needed
    parsed_decision = parse_rust_doubles_decision(rust_decision)
    logger.info(f"Final decision: {parsed_decision}")
    return parsed_decision


def get_result_from_mcts(state: str, search_time_ms: int, index: int):  # -> dict:
    """
    Run MCTS and return a picklable dictionary of results.
    
    Returns a dict with:
        - iteration_count: total iterations
        - s1: list of dicts with {move_choice, total_score, visits}
        - s2: list of dicts with {move_choice, total_score, visits}
    """
    logger.debug("Calling with {} state: {}".format(index, state))
    poke_engine_state = PokeEngineState.from_string(state)

    # Log active Pokemon positions for debugging
    if hasattr(poke_engine_state, 'side_one') and hasattr(poke_engine_state.side_one, 'pokemon'):
        try:
            side_one_p0 = poke_engine_state.side_one.pokemon[0] if len(poke_engine_state.side_one.pokemon) > 0 else None
            side_one_p1 = poke_engine_state.side_one.pokemon[1] if len(poke_engine_state.side_one.pokemon) > 1 else None
            if side_one_p0:
                logger.debug(f"MCTS input - Side 1 Position 0: {side_one_p0.id}")
            if side_one_p1:
                logger.debug(f"MCTS input - Side 1 Position 1: {side_one_p1.id}")
        except Exception as e:
            logger.debug(f"Could not log active Pokemon positions: {e}")

    res = mcts(poke_engine_state, search_time_ms)
    logger.info("Iterations {}: {}".format(index, res.iteration_count))
    
    # Log top decisions for debugging
    if res.s1:
        top_s1 = max(res.s1, key=lambda x: x.visits)
        logger.debug(f"MCTS top decision for s1: {top_s1.move_choice} (visits: {top_s1.visits})")
    
    # Extract data into a picklable format
    return {
        'iteration_count': res.iteration_count,
        's1': [{'move_choice': opt.move_choice, 'total_score': opt.total_score, 'visits': opt.visits} 
               for opt in res.s1],
        's2': [{'move_choice': opt.move_choice, 'total_score': opt.total_score, 'visits': opt.visits} 
               for opt in res.s2],
    }


def search_time_num_battles_randombattles(battle):
    revealed_pkmn = len(battle.opponent.reserve)
    
    # Handle both singles and doubles
    is_active_list = isinstance(battle.opponent.active, list)
    
    if is_active_list:
        # Doubles: count revealed Pokemon from active list
        revealed_pkmn += sum(1 for p in battle.opponent.active if p is not None)
        
        # Count total moves from all active Pokemon
        opponent_active_num_moves = 0
        for pkmn in battle.opponent.active:
            if pkmn is not None and hasattr(pkmn, 'moves'):
                opponent_active_num_moves += len(pkmn.moves)
        
        # Check if any active Pokemon has HP
        opponent_has_hp = any(p is not None and hasattr(p, 'hp') and p.hp > 0 for p in battle.opponent.active)
    else:
        # Singles: original logic
        if battle.opponent.active is not None:
            revealed_pkmn += 1
            opponent_active_num_moves = len(battle.opponent.active.moves)
            opponent_has_hp = battle.opponent.active.hp > 0
        else:
            opponent_active_num_moves = 0
            opponent_has_hp = False
    
    in_time_pressure = battle.time_remaining is not None and battle.time_remaining <= 60

    # it is still quite early in the battle and the pkmn in front of us
    # hasn't revealed any moves: search a lot of battles shallowly
    if (
        revealed_pkmn <= 3
        and opponent_has_hp
        and opponent_active_num_moves == 0
    ):
        num_battles_multiplier = 2 if in_time_pressure else 4
        return FoulPlayConfig.parallelism * num_battles_multiplier, int(
            FoulPlayConfig.search_time_ms // 2
        )

    else:
        num_battles_multiplier = 1 if in_time_pressure else 2
        return FoulPlayConfig.parallelism * num_battles_multiplier, int(
            FoulPlayConfig.search_time_ms
        )


def search_time_num_battles_standard_battle(battle):
    # Handle both singles and doubles
    # Check if active is actually a list (doubles) or single Pokemon (singles)
    is_active_list = isinstance(battle.opponent.active, list)
    
    if is_active_list:
        # For doubles, count total moves from both active Pokemon
        opponent_moves = 0
        for pkmn in battle.opponent.active:
            if pkmn is not None and hasattr(pkmn, 'moves'):
                opponent_moves += len(pkmn.moves)
        opponent_active_num_moves = opponent_moves if opponent_moves > 0 else 4
        
        # Check HP for any active Pokemon
        opponent_has_hp = any(p is not None and hasattr(p, 'hp') and p.hp > 0 for p in battle.opponent.active)
    else:
        # Singles - original logic
        if battle.opponent.active and hasattr(battle.opponent.active, 'moves'):
            opponent_active_num_moves = len(battle.opponent.active.moves)
            opponent_has_hp = battle.opponent.active.hp > 0
        else:
            opponent_active_num_moves = 4
            opponent_has_hp = False
    
    in_time_pressure = battle.time_remaining is not None and battle.time_remaining <= 60

    if (
        battle.team_preview
        or (opponent_has_hp and opponent_active_num_moves == 0)
        or opponent_active_num_moves < 3
    ):
        num_battles_multiplier = 1 if in_time_pressure else 2
        return FoulPlayConfig.parallelism * num_battles_multiplier, int(
            FoulPlayConfig.search_time_ms
        )
    else:
        return FoulPlayConfig.parallelism, FoulPlayConfig.search_time_ms


def find_best_move(battle: Battle) -> str:
    battle = deepcopy(battle)
    
    # TEAM PREVIEW: Just select Pokemon order (no MCTS needed)
    if battle.team_preview:
        logger.info("Team preview - selecting Pokemon order")
        num_pokemon = len(battle.user.reserve) if hasattr(battle.user, 'reserve') else 6
        team_order = ''.join(str(i) for i in range(1, num_pokemon + 1))
        logger.info(f"Team preview selection: {team_order} ({num_pokemon} Pokemon total)")
        return "switch 1"  # Special value that gets converted to team order
    
    # Use MCTS AI for both singles and doubles
    # Rust engine now supports doubles battles!
    return _find_best_move_mcts(battle)


def _find_best_move_mcts(battle: Battle) -> str:
    """Internal MCTS-based move selection."""
    logger.info(f"🤖 Using Rust MCTS AI for {'doubles' if battle.is_doubles else 'singles'} battle")

    if battle.battle_type == BattleType.RANDOM_BATTLE:
        num_battles, search_time_per_battle = search_time_num_battles_randombattles(
            battle
        )
        battles = prepare_random_battles(battle, num_battles)
    elif battle.battle_type == BattleType.BATTLE_FACTORY:
        num_battles, search_time_per_battle = search_time_num_battles_standard_battle(
            battle
        )
        battles = prepare_random_battles(battle, num_battles)
    elif battle.battle_type == BattleType.STANDARD_BATTLE:
        num_battles, search_time_per_battle = search_time_num_battles_standard_battle(
            battle
        )
        battles = prepare_battles(battle, num_battles)
    else:
        raise ValueError("Unsupported battle type: {}".format(battle.battle_type))

    logger.info("Searching for a move using MCTS...")
    logger.info(
        "Sampling {} battles at {}ms each".format(num_battles, search_time_per_battle)
    )
    
    # If parallelism is 1 or less, run sequentially to avoid multiprocessing overhead
    if FoulPlayConfig.parallelism <= 1:
        logger.debug("Running MCTS sequentially (parallelism <= 1)")
        mcts_results = []
        for index, (b, chance) in enumerate(battles):
            result = get_result_from_mcts(
                battle_to_poke_engine_state(b).to_string(),
                search_time_per_battle,
                index,
            )
            mcts_results.append((result, chance, index))
    else:
        # Use multiprocessing for parallel execution
        logger.debug(f"Running MCTS in parallel with {FoulPlayConfig.parallelism} workers")
        with ProcessPoolExecutor(max_workers=FoulPlayConfig.parallelism) as executor:
            futures = []
            for index, (b, chance) in enumerate(battles):
                fut = executor.submit(
                    get_result_from_mcts,
                    battle_to_poke_engine_state(b).to_string(),
                    search_time_per_battle,
                    index,
                )
                futures.append((fut, chance, index))

        mcts_results = [(fut.result(), chance, index) for (fut, chance, index) in futures]
    choice = select_move_from_mcts_results(mcts_results)
    logger.info("Choice: {}".format(choice))
    return choice
