"""
Browser-specific battle functions.

These functions handle battle flow when using browser automation instead of WebSocket.
"""
import asyncio
import logging
from fp.browser_client import BrowserClient
from fp.battle import Battle
from fp.battle_factory import create_battle
from fp.battle_modifier import async_update_battle
from fp.search.main import find_best_move
from fp.battle_turn_logger import BattleTurnLogger
from fp.helpers import is_doubles_format
from constants import BattleType
from config import FoulPlayConfig, SaveReplay
from data.pkmn_sets import RandomBattleTeamDatasets, TeamDatasets
from data.pkmn_sets import SmogonSets
# Import from run_battle to avoid circular import
import fp.run_battle as run_battle_module

logger = logging.getLogger(__name__)


async def pokemon_battle_browser_loop(browser_client: BrowserClient, battle: Battle, turn_logger, bot_name: str):
    """Browser-based battle loop - polls browser state instead of receiving messages."""
    poll_interval = 0.5  # Poll browser every 0.5 seconds
    
    while True:
        # Poll browser for battle state
        battle_state = await browser_client.get_battle_state()
        
        # Check if battle finished
        if battle_state.get("battle_finished", False):
            winner = battle_state.get("winner")
            logger.info("Winner: {}".format(winner))
            
            # Finalize the turn logger
            if turn_logger:
                turn_logger.finalize(winner)
                BattleTurnLogger.clear_instance(bot_name, battle.battle_tag)
                run_battle_module.set_turn_logger(None)
            
            # Note: Browser client may handle gg/replay/leave differently
            # For now, just return winner
            return winner
        
        # Check if we need to make a move
        turn_state = battle_state.get("turn_state", "waiting")
        if turn_state == "waiting_for_move":
            # Update battle state from browser (this is complex - may need to reconstruct)
            # For now, check if action is required based on battle state
            # In a full implementation, we'd need to parse browser state into battle updates
            
            # Check if we need to act
            if not battle.wait:
                try:
                    best_move = await run_battle_module.async_pick_move(battle)
                    await browser_client.select_move(best_move, battle.is_doubles)
                except Exception as e:
                    logger.error(f"Error selecting/sending move on turn {battle.turn}: {e}", exc_info=True)
                    # Fallback move
                    try:
                        fallback_move = run_battle_module.get_fallback_move(battle)
                        logger.warning(f"Using fallback move: {fallback_move}")
                        await browser_client.select_move(fallback_move, battle.is_doubles)
                    except Exception as fallback_error:
                        logger.error(f"Fallback move also failed: {fallback_error}", exc_info=True)
        
        # Wait before next poll
        await asyncio.sleep(poll_interval)


async def start_battle_browser(browser_client: BrowserClient, pokemon_battle_type: str, team_dict):
    """
    Start a battle using browser client.
    
    This is a simplified version that works with browser automation.
    Full implementation would need to parse battle state from browser.
    """
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run_battle_browser.py:45','message':'start_battle_browser called','data':{'pokemon_battle_type':pokemon_battle_type},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    # Wait for battle to start
    try:
        await browser_client._wait_for_battle_start()
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'run_battle_browser.py:54','message':'wait_for_battle_start completed','data':{'battle_tag':browser_client.battle_tag},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'run_battle_browser.py:61','message':'wait_for_battle_start failed','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e2:
            pass
        # #endregion
        raise
    
    # Extract battle info
    battle_tag = browser_client.battle_tag
    opponent_name = browser_client.opponent_name
    
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
    
    # Try to get request JSON from browser (may need to reconstruct from UI)
    # For now, we'll need to work with what we can see in the browser
    # This is a placeholder - full implementation would parse from browser
    
    battle.battle_type = BattleType.RANDOM_BATTLE if "random" in pokemon_battle_type else BattleType.STANDARD_BATTLE
    
    # Initialize datasets if needed
    if battle.battle_type == BattleType.RANDOM_BATTLE:
        RandomBattleTeamDatasets.initialize(battle.generation)
    else:
        battle.user.team_dict = team_dict
        # Initialize datasets when we have Pokemon names
    
    return battle

