"""
Singles-specific Battler implementation
"""
import logging
from collections import defaultdict
from fp.helpers import normalize_name, get_pokemon_info_from_condition
from fp.pokemon import Pokemon, LastUsedMove
import constants
from data import all_move_json, pokedex

logger = logging.getLogger(__name__)


class SinglesBattler:
    """Battler for singles battles - has one active Pokemon"""
    
    def __init__(self):
        # Common attributes (MUST be initialized first)
        self.reserve = []
        self.side_conditions = defaultdict(lambda: 0)
        self.name = None
        self.trapped = False
        self.baton_passing = False
        self.shed_tailing = False
        self.wish = (0, 0)
        self.future_sight = (0, "")
        self.account_name = None
        self.team_dict = None
        self.last_selected_move = LastUsedMove("", "", 0)
        self.last_used_move = LastUsedMove("", "", 0)
        
        # Singles-specific: active is a single Pokemon or None
        self.active = None
    
    def __deepcopy__(self, memo):
        """Custom deepcopy to preserve class type and structure"""
        from copy import deepcopy
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        # Ensure active stays as None or Pokemon (not list)
        if not isinstance(result.active, (type(None), Pokemon)):
            logger.warning(f"SinglesBattler deepcopy: active was {type(result.active)}, correcting to None")
            result.active = None
        return result
    
    @property
    def is_doubles(self):
        """Always False for singles"""
        return False
    
    # ============================================================================
    # POLYMORPHIC METHODS - Active Pokemon Access
    # ============================================================================
    
    def get_active_pokemon(self, position=0):
        """Get the active Pokemon (only position 0 is valid in singles)"""
        return self.active if position == 0 else None
    
    def set_active_pokemon(self, pokemon, position=0):
        """Set the active Pokemon (only position 0 is valid in singles)"""
        if position == 0:
            self.active = pokemon
    
    def get_all_active_pokemon(self):
        """Get all active Pokemon as a list"""
        return [self.active] if self.active is not None else []
    
    def get_active_count(self):
        """Get count of active Pokemon"""
        return 1 if self.active is not None else 0
    
    def has_pokemon_at_position(self, position):
        """Check if there's a Pokemon at position"""
        return position == 0 and self.active is not None
    
    # ============================================================================
    # MOVE LOCKING METHODS
    # ============================================================================
    
    def lock_active_pkmn_first_turn_moves(self):
        """Disable first-turn-only moves if Pokemon didn't just switch in"""
        if self.active and self.last_used_move.pokemon_name == self.active.name:
            for m in self.active.moves:
                if m.name in constants.FIRST_TURN_MOVES:
                    m.disabled = True
    
    def lock_active_pkmn_status_moves_if_active_has_assaultvest(self):
        """Disable status moves if Pokemon has Assault Vest"""
        if self.active and self.active.item == "assaultvest":
            for m in self.active.moves:
                if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                    m.disabled = True
    
    def choice_lock_moves(self):
        """Lock moves if Pokemon has choice item and already used a move"""
        if (
            self.active
            and self.active.item in constants.CHOICE_ITEMS
            and self.last_used_move.pokemon_name == self.active.name
            and self.last_used_move.move not in ["trick", "switcheroo"]
        ):
            for m in self.active.moves:
                if (
                    self.last_used_move.move == constants.HIDDEN_POWER
                    and m.name.startswith(constants.HIDDEN_POWER)
                ):
                    pass
                elif m.name != self.last_used_move.move:
                    m.disabled = True
    
    def taunt_lock_moves(self):
        """Lock status moves if Pokemon is taunted"""
        if self.active and constants.TAUNT in self.active.volatile_statuses:
            for m in self.active.moves:
                if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                    m.disabled = True
    
    def locked_move_lock(self):
        """Lock other moves if Pokemon is locked into one move"""
        if self.active and constants.LOCKED_MOVE in self.active.volatile_statuses:
            for m in self.active.moves:
                if m.name != self.last_used_move.move:
                    m.disabled = True
    
    def lock_moves(self):
        """Lock moves based on various conditions"""
        self.choice_lock_moves()
        self.lock_active_pkmn_status_moves_if_active_has_assaultvest()
        self.lock_active_pkmn_first_turn_moves()
        self.taunt_lock_moves()
        self.locked_move_lock()
    
    # ============================================================================
    # REQUEST JSON METHODS - Initialize/Update from Server
    # ============================================================================
    
    def _initialize_user_active_from_request_json(self, request_json):
        """Initialize active Pokemon data from request JSON (singles version)"""
        if not self.active:
            return
        
        # Set special move capabilities
        self.active.can_mega_evo = request_json[constants.ACTIVE][0].get(
            constants.CAN_MEGA_EVO, False
        )
        self.active.can_ultra_burst = request_json[constants.ACTIVE][0].get(
            constants.CAN_ULTRA_BURST, False
        )
        self.active.can_dynamax = request_json[constants.ACTIVE][0].get(
            constants.CAN_DYNAMAX, False
        )
        self.active.can_terastallize = request_json[constants.ACTIVE][0].get(
            constants.CAN_TERASTALLIZE, False
        )

        # Update moves from request JSON (source of truth)
        self.active.moves.clear()
        for index, move in enumerate(request_json[constants.ACTIVE][0][constants.MOVES]):
            # Handle hidden power special case
            if move[constants.ID] == constants.HIDDEN_POWER:
                self.active.add_move(normalize_name(move["move"]))
            else:
                self.active.add_move(move[constants.ID])
            
            self.active.moves[-1].disabled = move.get(constants.DISABLED, False)
            self.active.moves[-1].current_pp = move.get(constants.PP, 1)

            # Re-enable certain moves that PS disables but poke-engine handles differently
            if self.last_used_move.move in ["gigatonhammer", "bloodmoon"]:
                for m in self.active.moves:
                    if m.name == self.last_used_move.move and m.disabled:
                        m.disabled = False

            # Handle Z-moves
            try:
                self.active.moves[index].can_z = request_json[constants.ACTIVE][0][
                    constants.CAN_Z_MOVE
                ][index]
            except KeyError:
                pass
    
    def initialize_first_turn_user_from_json(self, request_json):
        """Initialize battler from first request JSON (singles version)"""
        # Set trapped status
        try:
            trapped = request_json[constants.ACTIVE][0].get(constants.TRAPPED, False)
            maybe_trapped = request_json[constants.ACTIVE][0].get(
                constants.MAYBE_TRAPPED, False
            )
            self.trapped = trapped or maybe_trapped
        except KeyError:
            self.trapped = False

        self.name = request_json[constants.SIDE][constants.ID]
        self.reserve.clear()
        
        for index, pkmn_dict in enumerate(request_json[constants.SIDE][constants.POKEMON]):
            nickname = pkmn_dict[constants.IDENT]
            pkmn_details = pkmn_dict[constants.DETAILS]
            pkmn_item = pkmn_dict[constants.ITEM] if pkmn_dict[constants.ITEM] else None
            pkmn = Pokemon.from_switch_string(pkmn_details, nickname=nickname)

            # Handle Zacian/Zamazenta special case
            if pkmn.name.startswith("zacian") and pkmn_item == "rustedsword":
                pkmn = Pokemon("zaciancrowned", pkmn.level)
                pkmn.nickname = nickname

            pkmn.ability = pkmn_dict[constants.REQUEST_DICT_ABILITY]
            pkmn.index = index + 1
            pkmn.reviving = pkmn_dict.get(constants.REVIVING, False)
            pkmn.hp, pkmn.max_hp, pkmn.status = get_pokemon_info_from_condition(
                pkmn_dict[constants.CONDITION]
            )
            for stat, number in pkmn_dict[constants.STATS].items():
                pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number

            pkmn.item = pkmn_item
            if constants.TERA_TYPE in pkmn_dict:
                pkmn.tera_type = normalize_name(pkmn_dict[constants.TERA_TYPE])

            # In singles, set active or add to reserve
            if pkmn_dict[constants.ACTIVE]:
                self.active = pkmn
            else:
                self.reserve.append(pkmn)

            # Handle special move replacements (Zacian/Zamazenta)
            for move_name in pkmn_dict[constants.MOVES]:
                if (
                    pkmn.name.startswith("zacian")
                    and pkmn_item == "rustedsword"
                    and move_name == "ironhead"
                ):
                    logger.info("Zacian with rusted sword: changing ironhead to behemothblade")
                    move_name = "behemothblade"
                elif (
                    pkmn.name.startswith("zamazenta")
                    and pkmn_item == "rustedshield"
                    and move_name == "ironhead"
                ):
                    logger.info("Zamazenta with rusted shield: changing ironhead to behemothbash")
                    move_name = "behemothbash"
                pkmn.add_move(move_name)

        # Initialize active Pokemon moves/capabilities
        if constants.ACTIVE in request_json:
            self._initialize_user_active_from_request_json(request_json)

        # Set nature/EVs from team_dict if available
        if self.team_dict is not None:
            team_dict_pkmn_names = [normalize_name(p["species"]) for p in self.team_dict]
            all_pkmn = self.get_all_active_pokemon() + self.reserve
            for pkmn in all_pkmn:
                pkmn_other_formes = [
                    normalize_name(n) for n in pokedex[pkmn.name].get("otherFormes", [])
                ]
                if pkmn.name in team_dict_pkmn_names:
                    team_dict_pkmn = next(
                        p for p in self.team_dict if normalize_name(p["species"]) == pkmn.name
                    )
                elif pkmn.base_name in team_dict_pkmn_names:
                    team_dict_pkmn = next(
                        p for p in self.team_dict if normalize_name(p["species"]) == pkmn.base_name
                    )
                elif any(p in team_dict_pkmn_names for p in pkmn_other_formes):
                    other_forme_in_team = next(
                        p for p in pkmn_other_formes if p in team_dict_pkmn_names
                    )
                    team_dict_pkmn = next(
                        p for p in self.team_dict if normalize_name(p["species"]) == other_forme_in_team
                    )
                else:
                    raise ValueError("Could not find {} in team_dict".format(pkmn.name))
                pkmn.nature = team_dict_pkmn["nature"] or "serious"
                pkmn.evs = (
                    int(team_dict_pkmn["evs"]["hp"] or 0),
                    int(team_dict_pkmn["evs"]["atk"] or 0),
                    int(team_dict_pkmn["evs"]["def"] or 0),
                    int(team_dict_pkmn["evs"]["spa"] or 0),
                    int(team_dict_pkmn["evs"]["spd"] or 0),
                    int(team_dict_pkmn["evs"]["spe"] or 0),
                )
    
    def update_from_request_json(self, request_json):
        """Update battler from request JSON during battle (singles version)"""
        # Update trapped status
        try:
            trapped = request_json[constants.ACTIVE][0].get(constants.TRAPPED, False)
            maybe_trapped = request_json[constants.ACTIVE][0].get(
                constants.MAYBE_TRAPPED, False
            )
            self.trapped = trapped or maybe_trapped
        except KeyError:
            self.trapped = False

        # Update all Pokemon from request JSON
        for index, pkmn_dict in enumerate(request_json[constants.SIDE][constants.POKEMON]):
            switch_string_pkmn = Pokemon.from_switch_string(pkmn_dict[constants.DETAILS])
            pkmn_name = switch_string_pkmn.name
            pkmn_level = switch_string_pkmn.level
            pkmn_status = switch_string_pkmn.status
            
            if pkmn_dict[constants.ACTIVE]:
                # This Pokemon is active
                if self.active.name != pkmn_name and self.active.base_name != pkmn_name:
                    raise ValueError(
                        "Active pokemon mismatch: expected {} or {}, got {}".format(
                            self.active.name, self.active.base_name, pkmn_name
                        )
                    )
                pkmn = self.active
                
                # Update active Pokemon moves/capabilities
                if constants.ACTIVE in request_json:
                    self._initialize_user_active_from_request_json(request_json)
            else:
                # Pokemon is in reserves
                pkmn = self.find_pokemon_in_reserves(pkmn_name)
                for move_name in pkmn_dict[constants.MOVES]:
                    if not pkmn.get_move(move_name):
                        pkmn.add_move(move_name)

            # Update common attributes
            pkmn.index = index + 1
            pkmn.level = pkmn_level
            pkmn.status = pkmn_status
            pkmn.nickname = self.active.extract_nickname_from_pokemonshowdown_string(
                pkmn_dict[constants.IDENT]
            )
            pkmn.reviving = pkmn_dict.get(constants.REVIVING, False)
            pkmn.hp, pkmn.max_hp, pkmn.status = get_pokemon_info_from_condition(
                pkmn_dict[constants.CONDITION]
            )
            pkmn.ability = pkmn_dict[constants.REQUEST_DICT_ABILITY]
            pkmn.item = pkmn_dict[constants.ITEM] if pkmn_dict[constants.ITEM] else None
            for stat, number in pkmn_dict[constants.STATS].items():
                pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number
    
    def re_initialize_active_pokemon_from_request_json(self, request_json):
        """Re-initialize active Pokemon after forme change (singles version)"""
        if not self.active:
            return
        
        pokedex_name = normalize_name(pokedex[self.active.name][constants.NAME])
        request_json_active_pkmn = [
            p
            for p in request_json["side"]["pokemon"]
            if normalize_name(p[constants.DETAILS]).split(",")[0] == pokedex_name
            or normalize_name(p[constants.DETAILS]).split(",")[0] == self.active.base_name
        ]
        
        # Handle Terapagos special case
        if pokedex_name == "terapagosstellar" and len(request_json_active_pkmn) == 0:
            request_json_active_pkmn = [
                p
                for p in request_json["side"]["pokemon"]
                if normalize_name(p[constants.DETAILS]).split(",")[0] == "terapagosterastal"
                or normalize_name(p[constants.DETAILS]).split(",")[0] == self.active.base_name
            ]
        
        assert (
            len(request_json_active_pkmn) == 1
        ), f"Didn't find exactly 1 {pokedex_name}, pokemon: {request_json}"
        
        pkmn_info = request_json_active_pkmn[0]
        for stat, number in pkmn_info[constants.STATS].items():
            self.active.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number
        self.active.hp, _, _ = get_pokemon_info_from_condition(pkmn_info[constants.CONDITION])
    
    # ============================================================================
    # COMMON METHODS (Same as base Battler)
    # ============================================================================
    
    def possible_mega_evolutions(self):
        """Get possible mega evolutions for team"""
        result = {}
        all_pokemon = self.reserve + self.get_all_active_pokemon()
        for pkmn in all_pokemon:
            megas_possible = pkmn.get_mega_pkmn_info()
            for m in megas_possible:
                if pkmn.item == constants.UNKNOWN_ITEM or pkmn.item == m[1]:
                    if pkmn.name not in result:
                        result[pkmn.name] = []
                    result[pkmn.name].append(m)
        return result

    def num_fainted_pkmn(self):
        """Count fainted Pokemon"""
        num_fainted = 0
        all_pokemon = self.reserve + self.get_all_active_pokemon()
        for pkmn in all_pokemon:
            if not pkmn.is_alive():
                num_fainted += 1
        return num_fainted

    def mega_revealed(self):
        """Check if mega evolution has been revealed"""
        active_has_mega = any(p.is_mega for p in self.get_all_active_pokemon())
        return active_has_mega or any(p.is_mega for p in self.reserve)

    def find_pokemon_in_reserves(self, pkmn_name):
        """Find a Pokemon in reserves by name"""
        for reserve_pkmn in self.reserve:
            if reserve_pkmn.name == pkmn_name or reserve_pkmn.base_name == pkmn_name:
                return reserve_pkmn
            if pkmn_name in [
                normalize_name(n)
                for n in pokedex[reserve_pkmn.name].get("otherFormes", [])
            ]:
                return reserve_pkmn
        return None

    def find_reserve_pkmn_by_unknown_forme(self, pkmn_name):
        """Find reserve Pokemon by unknown forme"""
        for reserve_pkmn in filter(lambda x: x.unknown_forme, self.reserve):
            pkmn_base_forme = normalize_name(pokedex[pkmn_name].get("changesFrom", ""))
            if pkmn_base_forme == reserve_pkmn.base_name:
                return reserve_pkmn
        return None

    def find_reserve_pokemon_by_nickname(self, pkmn_nickname):
        """Find reserve Pokemon by nickname"""
        for reserve_pkmn in self.reserve:
            if pkmn_nickname == reserve_pkmn.nickname:
                return reserve_pkmn
        return None

