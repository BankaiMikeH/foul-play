"""
Doubles-specific Battler implementation
"""
import logging
from collections import defaultdict
from fp.helpers import normalize_name, get_pokemon_info_from_condition
from fp.pokemon import Pokemon, LastUsedMove
import constants
from data import all_move_json, pokedex

logger = logging.getLogger(__name__)


class DoublesBattler:
    """Battler for doubles battles - has two active Pokemon"""
    
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
        
        # Doubles-specific: active is a list of 2 Pokemon
        self.active = [None, None]  # [left position, right position]
    
    def __deepcopy__(self, memo):
        """Custom deepcopy to preserve class type and structure"""
        from copy import deepcopy
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        # Ensure active stays as a list of 2 elements
        if not isinstance(result.active, list) or len(result.active) != 2:
            logger.warning(f"DoublesBattler deepcopy: active was {type(result.active)}, correcting to [None, None]")
            result.active = [None, None]
        return result
    
    @property
    def is_doubles(self):
        """Always True for doubles"""
        return True
    
    # ============================================================================
    # POLYMORPHIC METHODS - Active Pokemon Access
    # ============================================================================
    
    def get_active_pokemon(self, position=0):
        """Get the active Pokemon at specified position (0=left, 1=right)"""
        if 0 <= position < 2:
            return self.active[position]
        return None
    
    def set_active_pokemon(self, pokemon, position=0):
        """Set the active Pokemon at specified position (0=left, 1=right)"""
        if 0 <= position < 2:
            self.active[position] = pokemon
    
    def get_all_active_pokemon(self):
        """Get all active Pokemon as a list (excluding None)"""
        return [p for p in self.active if p is not None]
    
    def get_active_count(self):
        """Get count of active Pokemon"""
        return sum(1 for p in self.active if p is not None)
    
    def has_pokemon_at_position(self, position):
        """Check if there's a Pokemon at position"""
        return 0 <= position < 2 and self.active[position] is not None
    
    # ============================================================================
    # MOVE LOCKING METHODS
    # ============================================================================
    
    def lock_active_pkmn_first_turn_moves(self):
        """Disable first-turn-only moves if Pokemon didn't just switch in"""
        for pkmn in self.active:
            if pkmn and self.last_used_move.pokemon_name == pkmn.name:
                for m in pkmn.moves:
                    if m.name in constants.FIRST_TURN_MOVES:
                        m.disabled = True
    
    def lock_active_pkmn_status_moves_if_active_has_assaultvest(self):
        """Disable status moves if Pokemon has Assault Vest"""
        for pkmn in self.active:
            if pkmn and pkmn.item == "assaultvest":
                for m in pkmn.moves:
                    if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                        m.disabled = True
    
    def choice_lock_moves(self):
        """Lock moves if Pokemon has choice item and already used a move"""
        for pkmn in self.active:
            if (
                pkmn
                and pkmn.item in constants.CHOICE_ITEMS
                and self.last_used_move.pokemon_name == pkmn.name
                and self.last_used_move.move not in ["trick", "switcheroo"]
            ):
                for m in pkmn.moves:
                    if (
                        self.last_used_move.move == constants.HIDDEN_POWER
                        and m.name.startswith(constants.HIDDEN_POWER)
                    ):
                        pass
                    elif m.name != self.last_used_move.move:
                        m.disabled = True
    
    def taunt_lock_moves(self):
        """Lock status moves if Pokemon is taunted"""
        for pkmn in self.active:
            if pkmn and constants.TAUNT in pkmn.volatile_statuses:
                for m in pkmn.moves:
                    if all_move_json[m.name][constants.CATEGORY] == constants.STATUS:
                        m.disabled = True
    
    def locked_move_lock(self):
        """Lock other moves if Pokemon is locked into one move"""
        for pkmn in self.active:
            if pkmn and constants.LOCKED_MOVE in pkmn.volatile_statuses:
                for m in pkmn.moves:
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
        """Initialize active Pokemon data from request JSON (doubles version)"""
        # Doubles mode - up to 2 active Pokemon
        for position, active_data in enumerate(request_json[constants.ACTIVE]):
            pkmn = self.get_active_pokemon(position)
            if pkmn is None:
                continue  # No Pokemon at this position
            
            # Set special move capabilities
            pkmn.can_mega_evo = active_data.get(constants.CAN_MEGA_EVO, False)
            pkmn.can_ultra_burst = active_data.get(constants.CAN_ULTRA_BURST, False)
            pkmn.can_dynamax = active_data.get(constants.CAN_DYNAMAX, False)
            pkmn.can_terastallize = active_data.get(constants.CAN_TERASTALLIZE, False)

            # Update moves for this Pokemon
            pkmn.moves.clear()
            for index, move in enumerate(active_data[constants.MOVES]):
                if move[constants.ID] == constants.HIDDEN_POWER:
                    pkmn.add_move(normalize_name(move["move"]))
                else:
                    pkmn.add_move(move[constants.ID])
                pkmn.moves[-1].disabled = move.get(constants.DISABLED, False)
                pkmn.moves[-1].current_pp = move.get(constants.PP, 1)

                # Re-enable certain moves
                if self.last_used_move.move in ["gigatonhammer", "bloodmoon"]:
                    for m in pkmn.moves:
                        if m.name == self.last_used_move.move and m.disabled:
                            m.disabled = False

                # Handle Z-moves
                try:
                    pkmn.moves[index].can_z = active_data[constants.CAN_Z_MOVE][index]
                except KeyError:
                    pass
    
    def initialize_first_turn_user_from_json(self, request_json):
        """Initialize battler from first request JSON (doubles version)"""
        logger.debug(f"=== INITIALIZE FIRST TURN (Doubles) ===")
        logger.debug(f"Team preview: {request_json.get('teamPreview', False)}")
        
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
        
        # In doubles, we need to track which Pokemon are marked as active
        active_pokemon = []
        logger.debug(f"Processing {len(request_json[constants.SIDE][constants.POKEMON])} Pokemon from JSON...")
        
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

            # In doubles, active Pokemon are set during team preview
            # For now, add all to reserve
            if pkmn_dict[constants.ACTIVE]:
                logger.debug(f"  -> {pkmn.name} marked as ACTIVE")
                active_pokemon.append(pkmn)
            else:
                logger.debug(f"  -> {pkmn.name} added to reserves")
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
        
        # Add active Pokemon to reserve (will be set to active during team preview)
        logger.debug(f"Adding {len(active_pokemon)} active Pokemon to reserves temporarily")
        for pkmn in active_pokemon:
            self.reserve.append(pkmn)

        # Initialize active Pokemon moves/capabilities
        if constants.ACTIVE in request_json:
            # At this point, active Pokemon should be set by team preview
            # But we need to handle the case where this is called before team preview
            active_count = len(request_json[constants.ACTIVE])
            logger.debug(f"Request JSON has {active_count} active slots with move data")
            if active_count > 0:
                # Set active Pokemon from the ones marked as active
                logger.debug(f"Setting {len(active_pokemon[:2])} Pokemon to active positions")
                for i, pkmn in enumerate(active_pokemon[:2]):  # Max 2 active
                    self.active[i] = pkmn
                    logger.debug(f"  -> Position {i}: {pkmn.name}")
                self._initialize_user_active_from_request_json(request_json)
        
        logger.debug(f"=== INITIALIZATION COMPLETE ===")
        logger.debug(f"Active slots: {[p.name if p else None for p in self.active]}")
        logger.debug(f"Reserve count: {len(self.reserve)}")

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
        """Update battler from request JSON during battle (doubles version)"""
        logger.debug(f"=== UPDATE FROM REQUEST JSON (Doubles) ===")
        logger.debug(f"Current active Pokemon: {[p.name if p else None for p in self.active]}")
        logger.debug(f"Request JSON side Pokemon count: {len(request_json[constants.SIDE][constants.POKEMON])}")
        
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
            
            logger.debug(f"Processing Pokemon #{index}: {pkmn_name} (active={pkmn_dict[constants.ACTIVE]})")
            
            if pkmn_dict[constants.ACTIVE]:
                # This Pokemon is active - find which position
                logger.debug(f"  -> Marked as ACTIVE, searching in active positions...")
                pkmn = None
                for pos in range(2):
                    active_pkmn = self.get_active_pokemon(pos)
                    logger.debug(f"     Position {pos}: {active_pkmn.name if active_pkmn else 'None'}")
                    if active_pkmn and (active_pkmn.name == pkmn_name or active_pkmn.base_name == pkmn_name):
                        logger.debug(f"     ✓ MATCH found at position {pos}!")
                        pkmn = active_pkmn
                        break
                
                if pkmn is None:
                    # Pokemon marked as active but not found in active positions
                    # This can happen when self.active hasn't been initialized yet
                    # Try to find it in reserves instead
                    logger.warning(f"  -> NOT FOUND in active positions! Searching reserves...")
                    logger.debug(f"     Reserve Pokemon: {[p.name for p in self.reserve]}")
                    pkmn = self.find_pokemon_in_reserves(pkmn_name)
                    if pkmn is None:
                        # Still not found - create it from the request JSON
                        logger.warning(f"  -> NOT FOUND in reserves either! Creating new Pokemon from JSON")
                        pkmn = Pokemon.from_switch_string(pkmn_dict[constants.DETAILS])
                        pkmn.ability = pkmn_dict[constants.REQUEST_DICT_ABILITY]
                        pkmn.index = index + 1
                        pkmn.item = pkmn_dict[constants.ITEM] if pkmn_dict[constants.ITEM] else None
                        if constants.TERA_TYPE in pkmn_dict:
                            pkmn.tera_type = normalize_name(pkmn_dict[constants.TERA_TYPE])
                        for stat, number in pkmn_dict[constants.STATS].items():
                            pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number
                        for move_name in pkmn_dict[constants.MOVES]:
                            pkmn.add_move(move_name)
                        self.reserve.append(pkmn)
                        logger.debug(f"     ✓ Created and added to reserves")
                    else:
                        logger.debug(f"     ✓ Found in reserves!")
                
                # Update active Pokemon moves/capabilities
                if constants.ACTIVE in request_json:
                    self._initialize_user_active_from_request_json(request_json)
            else:
                # Pokemon is in reserves
                logger.debug(f"  -> Marked as RESERVE")
                pkmn = self.find_pokemon_in_reserves(pkmn_name)
                if pkmn:
                    logger.debug(f"     ✓ Found in reserves")
                    for move_name in pkmn_dict[constants.MOVES]:
                        if not pkmn.get_move(move_name):
                            pkmn.add_move(move_name)
                else:
                    # Not found in reserves - create it from the request JSON
                    logger.warning(f"     ✗ NOT FOUND in reserves! Creating new Pokemon from JSON")
                    pkmn = Pokemon.from_switch_string(pkmn_dict[constants.DETAILS])
                    pkmn.ability = pkmn_dict[constants.REQUEST_DICT_ABILITY]
                    pkmn.index = index + 1
                    pkmn.item = pkmn_dict[constants.ITEM] if pkmn_dict[constants.ITEM] else None
                    if constants.TERA_TYPE in pkmn_dict:
                        pkmn.tera_type = normalize_name(pkmn_dict[constants.TERA_TYPE])
                    for stat, number in pkmn_dict[constants.STATS].items():
                        pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number
                    for move_name in pkmn_dict[constants.MOVES]:
                        pkmn.add_move(move_name)
                    self.reserve.append(pkmn)
                    logger.debug(f"     ✓ Created and added to reserves")

            # Update common attributes (only if pkmn was found/created)
            if pkmn is None:
                logger.error(f"     ✗ CRITICAL: pkmn is still None after all attempts to find/create it!")
                continue
            pkmn.index = index + 1
            pkmn.level = pkmn_level
            pkmn.status = pkmn_status
            pkmn.nickname = pkmn.extract_nickname_from_pokemonshowdown_string(
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
        """Re-initialize active Pokemon after forme change (doubles version)"""
        # In doubles, we need to update all active Pokemon
        for position in range(2):
            pkmn = self.get_active_pokemon(position)
            if pkmn is None:
                continue  # No Pokemon at this position
            
            pokedex_name = normalize_name(pokedex[pkmn.name][constants.NAME])
            request_json_active_pkmn = [
                p
                for p in request_json["side"]["pokemon"]
                if p.get(constants.ACTIVE)
                and (normalize_name(p[constants.DETAILS]).split(",")[0] == pokedex_name
                or normalize_name(p[constants.DETAILS]).split(",")[0] == pkmn.base_name)
            ]
            
            # Handle Terapagos special case
            if pokedex_name == "terapagosstellar" and len(request_json_active_pkmn) == 0:
                request_json_active_pkmn = [
                    p
                    for p in request_json["side"]["pokemon"]
                    if p.get(constants.ACTIVE)
                    and (normalize_name(p[constants.DETAILS]).split(",")[0] == "terapagosterastal"
                    or normalize_name(p[constants.DETAILS]).split(",")[0] == pkmn.base_name)
                ]
            
            if len(request_json_active_pkmn) != 1:
                logger.warning(
                    f"Found {len(request_json_active_pkmn)} active Pokemon for {pokedex_name} at position {position}"
                )
                continue
            
            pkmn_info = request_json_active_pkmn[0]
            for stat, number in pkmn_info[constants.STATS].items():
                pkmn.stats[constants.STAT_ABBREVIATION_LOOKUPS[stat]] = number
            pkmn.hp, _, _ = get_pokemon_info_from_condition(pkmn_info[constants.CONDITION])
    
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

