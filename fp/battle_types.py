"""
Singles and Doubles Battle class implementations
"""
import logging
from fp.battle_base import Battle  # Import base Battle class
from fp.battler_singles import SinglesBattler
from fp.battler_doubles import DoublesBattler

logger = logging.getLogger(__name__)


class SinglesBattle(Battle):
    """Battle class for singles format - inherits all methods from Battle"""
    
    def __init__(self, battle_tag):
        # Initialize battle state but use SinglesBattler instead of Battler
        self.battle_tag = battle_tag
        self.user = SinglesBattler()
        self.opponent = SinglesBattler()
        
        # ALL battle state attributes (must match original Battle.__init__)
        self.weather = None
        self.weather_turns_remaining = -1
        self.weather_source = ""
        self.field = None
        self.field_turns_remaining = 0
        self.trick_room = False
        self.trick_room_turns_remaining = 0
        self.gravity = False
        self.team_preview = False
        
        self.turn = 0
        self.started = False
        self.rqid = None
        
        self.force_switch = False
        self.wait = False
        
        self.battle_type = None
        self.pokemon_format = None
        self.generation = None
        self.time_remaining = None
        
        self.request_json = None
        self.msg_list = []
        
        # Team preview tracking
        self.user_selected_team = None  # List of Pokemon names selected in team preview
        self.opponent_revealed_pokemon = set()  # Set of opponent Pokemon that have been revealed
        
        # Open team sheets (Bo3 format)
        self.opponent_open_team_sets = None  # List of dicts from |showteam| messages
    
    def __deepcopy__(self, memo):
        """Custom deepcopy to preserve class types"""
        from copy import deepcopy
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        # Verify battlers are correct type
        if not isinstance(result.user, SinglesBattler):
            logger.error(f"Singles deepcopy: user became {type(result.user)}")
        if not isinstance(result.opponent, SinglesBattler):
            logger.error(f"Singles deepcopy: opponent became {type(result.opponent)}")
        return result
    
    @property
    def is_doubles(self):
        """Always False for singles"""
        return False


class DoublesBattle(Battle):
    """Battle class for doubles format - inherits all methods from Battle"""
    
    def __init__(self, battle_tag):
        # Initialize battle state but use DoublesBattler instead of Battler
        self.battle_tag = battle_tag
        self.user = DoublesBattler()
        self.opponent = DoublesBattler()
        
        # ALL battle state attributes (must match original Battle.__init__)
        self.weather = None
        self.weather_turns_remaining = -1
        self.weather_source = ""
        self.field = None
        self.field_turns_remaining = 0
        self.trick_room = False
        self.trick_room_turns_remaining = 0
        self.gravity = False
        self.team_preview = False
        
        self.turn = 0
        self.started = False
        self.rqid = None
        
        self.force_switch = False
        self.wait = False
        
        self.battle_type = None
        self.pokemon_format = None
        self.generation = None
        self.time_remaining = None
        
        self.request_json = None
        self.msg_list = []
        
        # Team preview tracking
        self.user_selected_team = None  # List of 4 Pokemon names selected in team preview
        self.opponent_revealed_pokemon = set()  # Set of opponent Pokemon that have been revealed
        
        # Decision tracking for doubles positions
        self.position_decisions_made = [False, False]  # Track if position 0 and 1 have decisions
        self.position_alive_at_turn_start = [False, False]  # Track if positions were alive at turn start
        self.position_switch_targets = [None, None]  # Track which Pokemon each position is switching to
    
    def __deepcopy__(self, memo):
        """Custom deepcopy to preserve class types"""
        from copy import deepcopy
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        # Verify battlers are correct type
        if not isinstance(result.user, DoublesBattler):
            logger.error(f"Doubles deepcopy: user became {type(result.user)}")
        if not isinstance(result.opponent, DoublesBattler):
            logger.error(f"Doubles deepcopy: opponent became {type(result.opponent)}")
        return result
    
    @property
    def is_doubles(self):
        """Always True for doubles"""
        return True
