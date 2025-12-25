import argparse
import logging
import os
import sys
from enum import Enum, auto
from logging.handlers import RotatingFileHandler
from typing import Optional


class CustomFormatter(logging.Formatter):
    def format(self, record):
        lvl = "{}".format(record.levelname)
        return "{} {}".format(lvl.ljust(8), record.msg)


class CustomRotatingFileHandler(RotatingFileHandler):
    def __init__(self, file_name, **kwargs):
        self.base_dir = "logs"
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)

        super().__init__("{}/{}".format(self.base_dir, file_name), **kwargs)

    def do_rollover(self, new_file_name):
        new_file_name = new_file_name.replace("/", "_")
        self.baseFilename = "{}/{}".format(self.base_dir, new_file_name)
        self.doRollover()


def init_logging(level, log_to_file):
    websockets_logger = logging.getLogger("websockets")
    websockets_logger.setLevel(logging.INFO)
    requests_logger = logging.getLogger("urllib3")
    requests_logger.setLevel(logging.INFO)

    # Gets the root logger to set handlers/formatters
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Configure stdout with UTF-8 encoding to handle Unicode characters
    import io
    stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    stdout_handler = logging.StreamHandler(stdout_utf8)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(CustomFormatter())
    logger.addHandler(stdout_handler)
    FoulPlayConfig.stdout_log_handler = stdout_handler

    if log_to_file:
        file_handler = CustomRotatingFileHandler("init.log")
        file_handler.setLevel(logging.DEBUG)  # file logs are always debug
        file_handler.setFormatter(CustomFormatter())
        logger.addHandler(file_handler)
        FoulPlayConfig.file_log_handler = file_handler


class SaveReplay(Enum):
    always = auto()
    never = auto()
    on_loss = auto()


class BotModes(Enum):
    challenge_user = auto()
    accept_challenge = auto()
    search_ladder = auto()


class _FoulPlayConfig:
    websocket_uri: str
    username: str
    password: str
    user_id: str
    avatar: str
    bot_mode: BotModes
    pokemon_format: str = ""
    smogon_stats: str = None
    search_time_ms: int
    parallelism: int
    run_count: int
    team_name: str
    user_to_challenge: str
    save_replay: SaveReplay
    room_name: str
    log_level: str
    log_to_file: bool
    stdout_log_handler: logging.StreamHandler
    file_log_handler: Optional[CustomRotatingFileHandler]
    # Team Manager options
    team_selection_strategy: str = "best"
    team_archetype: Optional[str] = None
    team_id: Optional[str] = None
    # Bo3 options
    bo3_mode: bool = False
    # Browser automation options
    use_browser: bool = True
    browser_url: str = None
    browser_wait_timeout: int = 10

    def configure(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--websocket-uri",
            required=False,
            default="ws://localhost:8000/showdown/websocket",
            help="The PokemonShowdown websocket URI, e.g. wss://sim3.psim.us/showdown/websocket (not needed if using browser)",
        )
        parser.add_argument("--ps-username", required=True)
        parser.add_argument("--ps-password", required=True)
        parser.add_argument("--ps-avatar", default=None)
        parser.add_argument(
            "--bot-mode", required=True, choices=[e.name for e in BotModes]
        )
        parser.add_argument(
            "--user-to-challenge",
            default=None,
            help="If bot_mode is `challenge_user`, this is required",
        )
        parser.add_argument(
            "--pokemon-format", required=True, help="e.g. gen9randombattle"
        )
        parser.add_argument(
            "--smogon-stats-format",
            default=None,
            help="Overwrite which smogon stats are used to infer unknowns. If not set, defaults to the --pokemon-format value.",
        )
        parser.add_argument(
            "--search-time-ms",
            type=int,
            default=100,
            help="Time to search per battle in milliseconds",
        )
        parser.add_argument(
            "--search-parallelism",
            type=int,
            default=1,
            help="Number of states to search in parallel",
        )
        parser.add_argument(
            "--run-count",
            type=int,
            default=1,
            help="Number of PokemonShowdown battles to run",
        )
        parser.add_argument(
            "--team-name",
            default=None,
            help="Which team to use. Can be a filename or a foldername relative to ./teams/teams/. "
            "If a foldername, a random team from that folder will be chosen each battle. "
            "If not set, defaults to the --pokemon-format value.",
        )
        parser.add_argument(
            "--save-replay",
            default="never",
            choices=[e.name for e in SaveReplay],
            help="When to save replays",
        )
        parser.add_argument(
            "--room-name",
            default=None,
            help="If bot_mode is `accept_challenge`, the room to join while waiting",
        )
        parser.add_argument("--log-level", default="DEBUG", help="Python logging level")
        parser.add_argument(
            "--log-to-file",
            action="store_true",
            help="When enabled, DEBUG logs will be written to a file in the logs/ directory",
        )
        parser.add_argument(
            "--team-selection-strategy",
            default="best",
            choices=["best", "random", "rotation", "least_used", "archetype", "specific"],
            help="Strategy for selecting teams from TeamManager (for doubles formats)",
        )
        parser.add_argument(
            "--team-archetype",
            default=None,
            help="If team-selection-strategy is 'archetype', which archetype to use",
        )
        parser.add_argument(
            "--team-id",
            default=None,
            help="If team-selection-strategy is 'specific', which team ID to use",
        )
        parser.add_argument(
            "--bo3",
            action="store_true",
            help="Enable Best of 3 mode - play series of up to 3 games against same opponent",
        )
        parser.add_argument(
            "--use-browser",
            action="store_true",
            default=False,  # Changed: store_true defaults to False, use --no-browser to disable
            help="Use browser automation instead of WebSocket",
        )
        parser.add_argument(
            "--no-browser",
            dest="use_browser",
            action="store_false",
            help="Disable browser automation and use WebSocket instead",
        )
        parser.add_argument(
            "--browser-url",
            default=None,
            help="Pokemon Showdown URL for browser (default: http://localhost:8000 or https://play.pokemonshowdown.com)",
        )
        parser.add_argument(
            "--browser-wait-timeout",
            type=int,
            default=10,
            help="Timeout in seconds for waiting for UI elements (default: 10)",
        )

        args = parser.parse_args()
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'config.py:214','message':'Parsing arguments','data':{'use_browser_arg':getattr(args,'use_browser',None),'has_use_browser':hasattr(args,'use_browser')},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        self.websocket_uri = args.websocket_uri
        self.username = args.ps_username
        self.password = args.ps_password
        self.avatar = args.ps_avatar
        self.bot_mode = BotModes[args.bot_mode]
        self.pokemon_format = args.pokemon_format
        self.smogon_stats = args.smogon_stats_format
        self.search_time_ms = args.search_time_ms
        self.parallelism = args.search_parallelism
        self.run_count = args.run_count
        self.team_name = args.team_name or self.pokemon_format
        self.user_to_challenge = args.user_to_challenge
        self.save_replay = SaveReplay[args.save_replay]
        self.room_name = args.room_name
        self.log_level = args.log_level
        self.log_to_file = args.log_to_file
        self.team_selection_strategy = args.team_selection_strategy
        self.team_archetype = args.team_archetype
        self.team_id = args.team_id
        self.bo3_mode = args.bo3
        self.use_browser = getattr(args, 'use_browser', False)  # Get from args, default to False
        self.browser_wait_timeout = args.browser_wait_timeout
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'config.py:240','message':'Config values set','data':{'use_browser':self.use_browser,'browser_url_set':hasattr(self,'browser_url')},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        # Determine browser URL
        if args.browser_url:
            self.browser_url = args.browser_url
        elif "localhost" in self.websocket_uri or "127.0.0.1" in self.websocket_uri:
            self.browser_url = "http://localhost:8000"
        else:
            self.browser_url = "https://play.pokemonshowdown.com"

        self.validate_config()

    def requires_team(self) -> bool:
        return not (
            "random" in self.pokemon_format or "battlefactory" in self.pokemon_format
        )

    def validate_config(self):
        if self.bot_mode == BotModes.challenge_user:
            assert (
                self.user_to_challenge is not None
            ), "If bot_mode is `CHALLENGE_USER`, you must declare USER_TO_CHALLENGE"


FoulPlayConfig = _FoulPlayConfig()
