import asyncio
import json
import logging
import traceback
from copy import deepcopy

from config import FoulPlayConfig, init_logging, BotModes

from teams import load_team
from fp.run_battle import pokemon_battle
# #region agent log
try:
    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
        import json, time
        f.write(json.dumps({'location':'run.py:11','message':'Starting imports','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
except Exception as e:
    pass
# #endregion

try:
    from fp.websocket_client import PSWebsocketClient
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:18','message':'PSWebsocketClient imported','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
    except Exception as e:
        pass
    # #endregion
except ImportError as e:
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:25','message':'PSWebsocketClient import failed','data':{'error':str(e)},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
    except Exception as e2:
        pass
    # #endregion
    raise

try:
    from fp.browser_client import BrowserClient
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:33','message':'BrowserClient imported','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
    except Exception as e:
        pass
    # #endregion
except ImportError as e:
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:40','message':'BrowserClient import failed','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
    except Exception as e2:
        pass
    # #endregion
    raise
from team_integration import create_team_manager_if_needed

from data import all_move_json
from data import pokedex
from data.mods.apply_mods import apply_mods


logger = logging.getLogger(__name__)


def check_dictionaries_are_unmodified(original_pokedex, original_move_json):
    # The bot should not modify the data dictionaries
    # This is a "just-in-case" check to make sure and will stop the bot if it mutates either of them
    if original_move_json != all_move_json:
        logger.critical(
            "Move JSON changed!\nDumping modified version to `modified_moves.json`"
        )
        with open("modified_moves.json", "w") as f:
            json.dump(all_move_json, f, indent=4)
        exit(1)
    else:
        logger.debug("Move JSON unmodified!")

    if original_pokedex != pokedex:
        logger.critical(
            "Pokedex JSON changed!\nDumping modified version to `modified_pokedex.json`"
        )
        with open("modified_pokedex.json", "w") as f:
            json.dump(pokedex, f, indent=4)
        exit(1)
    else:
        logger.debug("Pokedex JSON unmodified!")


async def run_foul_play():
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:47','message':'Starting run_foul_play','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'A'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    FoulPlayConfig.configure()
    
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:52','message':'Config configured','data':{'use_browser':FoulPlayConfig.use_browser,'browser_url':getattr(FoulPlayConfig,'browser_url',None),'username':FoulPlayConfig.username},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    init_logging(FoulPlayConfig.log_level, FoulPlayConfig.log_to_file)
    apply_mods(FoulPlayConfig.pokemon_format)

    original_pokedex = deepcopy(pokedex)
    original_move_json = deepcopy(all_move_json)

    # Choose client based on configuration
    # #region agent log
    try:
        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({'location':'run.py:66','message':'Checking use_browser flag','data':{'use_browser':FoulPlayConfig.use_browser,'type':type(FoulPlayConfig.use_browser).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
    except Exception as e:
        pass
    # #endregion
    
    if FoulPlayConfig.use_browser:
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'run.py:69','message':'Creating BrowserClient','data':{'username':FoulPlayConfig.username,'browser_url':getattr(FoulPlayConfig,'browser_url',None),'wait_timeout':getattr(FoulPlayConfig,'browser_wait_timeout',10)},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        try:
            # Always create a new browser window for each bot instance
            client = await BrowserClient.create(
                FoulPlayConfig.username, 
                FoulPlayConfig.password, 
                FoulPlayConfig.browser_url,
                FoulPlayConfig.browser_wait_timeout,
                new_window=True  # Always create new window
            )
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'run.py:78','message':'BrowserClient created successfully','data':{'client_type':type(client).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e:
                pass
            # #endregion
            
            FoulPlayConfig.user_id = await client.login()
            
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'run.py:85','message':'BrowserClient login completed','data':{'user_id':FoulPlayConfig.user_id},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'D'})+'\n')
            except Exception as e:
                pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'run.py:90','message':'BrowserClient creation/login failed','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e2:
                pass
            # #endregion
            raise
        client = await BrowserClient.create(
            FoulPlayConfig.username, 
            FoulPlayConfig.password, 
            FoulPlayConfig.browser_url,
            FoulPlayConfig.browser_wait_timeout
        )
        FoulPlayConfig.user_id = await client.login()
    else:
        client = await PSWebsocketClient.create(
            FoulPlayConfig.username, FoulPlayConfig.password, FoulPlayConfig.websocket_uri
        )
        FoulPlayConfig.user_id = await client.login()

    if FoulPlayConfig.avatar is not None and not FoulPlayConfig.use_browser:
        # Avatar setting via WebSocket (browser mode may handle this differently)
        await client.avatar(FoulPlayConfig.avatar)

    battles_run = 0
    wins = 0
    losses = 0
    team_file_name = "None"
    team_dict = None
    
    # Bo3 tracking
    series_count = 0
    series_wins = 0
    series_losses = 0
    
    # Initialize TeamManager for doubles formats
    team_manager = create_team_manager_if_needed(
        FoulPlayConfig.pokemon_format,
        FoulPlayConfig.team_name,
        FoulPlayConfig.team_selection_strategy,
        FoulPlayConfig.team_archetype,
        FoulPlayConfig.team_id
    )
    
    if team_manager:
        logger.info(f"Using TeamManager with strategy: {FoulPlayConfig.team_selection_strategy}")
    
    if FoulPlayConfig.bo3_mode:
        logger.info("Bo3 Mode: Enabled - Playing best of 3 series")
    
    while True:
        # Bo3 Series Mode
        if FoulPlayConfig.bo3_mode:
            series_count += 1
            bo3_wins = 0
            bo3_losses = 0
            game_number = 1
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Starting Bo3 Series #{series_count}")
            logger.info(f"{'='*50}\n")
            
            # Play games until someone wins 2
            while bo3_wins < 2 and bo3_losses < 2:
                logger.info(f"\n--- Game {game_number} of Series #{series_count} ---")
                logger.info(f"Series Score: {bo3_wins}-{bo3_losses}")
                
                if FoulPlayConfig.requires_team():
                    # Use TeamManager if available, otherwise use traditional team loading
                    if team_manager:
                        team_packed, team_dict, team_file_name = team_manager.select_team()
                    else:
                        team_packed, team_dict, team_file_name = load_team(FoulPlayConfig.team_name)
                    if not FoulPlayConfig.use_browser:
                        await client.update_team(team_packed)
                    # Browser mode may handle team upload differently
                else:
                    if not FoulPlayConfig.use_browser:
                        await client.update_team("None")

                if FoulPlayConfig.bot_mode == BotModes.challenge_user:
                    # #region agent log
                    try:
                        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            import json, time
                            f.write(json.dumps({'location':'run.py:251','message':'Challenging user (Bo3 mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_challenge_user':hasattr(client,'challenge_user'),'user_to_challenge':FoulPlayConfig.user_to_challenge},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                    except Exception as e:
                        pass
                    # #endregion
                    await client.challenge_user(
                        FoulPlayConfig.user_to_challenge,
                        FoulPlayConfig.pokemon_format,
                    )
                elif FoulPlayConfig.bot_mode == BotModes.accept_challenge:
                    # #region agent log
                    try:
                        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            import json, time
                            f.write(json.dumps({'location':'run.py:263','message':'Accepting challenge (Bo3 mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_accept_challenge':hasattr(client,'accept_challenge'),'room_name':FoulPlayConfig.room_name},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                    except Exception as e:
                        pass
                    # #endregion
                    await client.accept_challenge(
                        FoulPlayConfig.pokemon_format, FoulPlayConfig.room_name
                    )
                elif FoulPlayConfig.bot_mode == BotModes.search_ladder:
                    # #region agent log
                    try:
                        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            import json, time
                            f.write(json.dumps({'location':'run.py:267','message':'Searching for battle (Bo3 mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_search_for_battle':hasattr(client,'search_for_battle'),'has_search_for_match':hasattr(client,'search_for_match')},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                    except Exception as e:
                        pass
                    # #endregion
                    if FoulPlayConfig.use_browser:
                        await client.search_for_battle(FoulPlayConfig.pokemon_format)
                    else:
                        await client.search_for_match(FoulPlayConfig.pokemon_format)
                else:
                    raise ValueError("Invalid Bot Mode: {}".format(FoulPlayConfig.bot_mode))

                winner = await pokemon_battle(
                    client, FoulPlayConfig.pokemon_format, team_dict
                )
                
                # Record game result
                if winner == FoulPlayConfig.username:
                    wins += 1
                    bo3_wins += 1
                    logger.info(f"✓ Won Game {game_number} with team: {team_file_name}")
                else:
                    losses += 1
                    bo3_losses += 1
                    logger.info(f"✗ Lost Game {game_number} with team: {team_file_name}")
                
                # Update TeamManager if being used
                if team_manager:
                    team_manager.record_battle_result(winner, FoulPlayConfig.username)

                logger.info(f"Series Score: {bo3_wins}-{bo3_losses}")
                logger.info(f"Overall Record - W: {wins}\tL: {losses}")
                check_dictionaries_are_unmodified(original_pokedex, original_move_json)
                
                game_number += 1
                battles_run += 1
                
                # Small delay between games in the series
                if bo3_wins < 2 and bo3_losses < 2:
                    logger.info("Waiting 5 seconds before next game...")
                    await asyncio.sleep(5)
            
            # Series complete
            if bo3_wins > bo3_losses:
                series_wins += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"🏆 WON Series #{series_count} ({bo3_wins}-{bo3_losses})")
                logger.info(f"{'='*50}\n")
            else:
                series_losses += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"❌ LOST Series #{series_count} ({bo3_wins}-{bo3_losses})")
                logger.info(f"{'='*50}\n")
            
            logger.info(f"Series Record: {series_wins}W - {series_losses}L")
            logger.info(f"Overall Game Record: {wins}W - {losses}L")
            
            # Check if we've completed enough series
            if series_count >= FoulPlayConfig.run_count:
                break
                
        else:
            # Standard single game mode
            if FoulPlayConfig.requires_team():
                # Use TeamManager if available, otherwise use traditional team loading
                if team_manager:
                    team_packed, team_dict, team_file_name = team_manager.select_team()
                else:
                    team_packed, team_dict, team_file_name = load_team(FoulPlayConfig.team_name)
                if not FoulPlayConfig.use_browser:
                    await client.update_team(team_packed)
            else:
                if not FoulPlayConfig.use_browser:
                    await client.update_team("None")

            if FoulPlayConfig.bot_mode == BotModes.challenge_user:
                # #region agent log
                try:
                    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({'location':'run.py:334','message':'Challenging user (standard mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_challenge_user':hasattr(client,'challenge_user'),'user_to_challenge':FoulPlayConfig.user_to_challenge},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                except Exception as e:
                    pass
                # #endregion
                await client.challenge_user(
                    FoulPlayConfig.user_to_challenge,
                    FoulPlayConfig.pokemon_format,
                )
            elif FoulPlayConfig.bot_mode == BotModes.accept_challenge:
                # #region agent log
                try:
                    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({'location':'run.py:344','message':'Accepting challenge (standard mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_accept_challenge':hasattr(client,'accept_challenge'),'room_name':FoulPlayConfig.room_name},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                except Exception as e:
                    pass
                # #endregion
                await client.accept_challenge(
                    FoulPlayConfig.pokemon_format, FoulPlayConfig.room_name
                )
            elif FoulPlayConfig.bot_mode == BotModes.search_ladder:
                # #region agent log
                try:
                    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({'location':'run.py:300','message':'Searching for battle (standard mode)','data':{'use_browser':FoulPlayConfig.use_browser,'has_search_for_battle':hasattr(client,'search_for_battle'),'has_search_for_match':hasattr(client,'search_for_match')},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                except Exception as e:
                    pass
                # #endregion
                if FoulPlayConfig.use_browser:
                    await client.search_for_battle(FoulPlayConfig.pokemon_format)
                else:
                    await client.search_for_match(FoulPlayConfig.pokemon_format)
            else:
                raise ValueError("Invalid Bot Mode: {}".format(FoulPlayConfig.bot_mode))

            winner = await pokemon_battle(
                client, FoulPlayConfig.pokemon_format, team_dict
            )
            
            # Record result
            if winner == FoulPlayConfig.username:
                wins += 1
                logger.info("Won with team: {}".format(team_file_name))
            else:
                losses += 1
                logger.info("Lost with team: {}".format(team_file_name))
            
            # Update TeamManager if being used
            if team_manager:
                team_manager.record_battle_result(winner, FoulPlayConfig.username)

            logger.info("W: {}\tL: {}".format(wins, losses))
            check_dictionaries_are_unmodified(original_pokedex, original_move_json)

            battles_run += 1
            if battles_run >= FoulPlayConfig.run_count:
                break
    
    # Print team summary if using TeamManager
    if team_manager:
        team_manager.print_summary()
    
    # Close client (works for both WebSocket and Browser clients)
    if hasattr(client, 'close'):
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_foul_play())
    except Exception:
        logger.error(traceback.format_exc())
        raise
