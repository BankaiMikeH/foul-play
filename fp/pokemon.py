"""
Pokemon class and related utilities
"""
import logging
from collections import defaultdict, namedtuple
import constants
from data import pokedex, all_move_json
from fp.helpers import (
    normalize_name,
    calculate_stats,
    POKEMON_TYPE_INDICES,
)

logger = logging.getLogger(__name__)

# Named tuples
LastUsedMove = namedtuple("LastUsedMove", ["pokemon_name", "move", "turn"])
DamageDealt = namedtuple(
    "DamageDealt", ["attacker", "defender", "move", "percent_damage", "crit"]
)
StatRange = namedtuple("Range", ["min", "max"])

# Boost multiplier lookup table
boost_multiplier_lookup = {
    -6: 2 / 8,
    -5: 2 / 7,
    -4: 2 / 6,
    -3: 2 / 5,
    -2: 2 / 4,
    -1: 2 / 3,
    0: 2 / 2,
    1: 3 / 2,
    2: 4 / 2,
    3: 5 / 2,
    4: 6 / 2,
    5: 7 / 2,
    6: 8 / 2,
}


class Pokemon:
    def __init__(self, name: str, level: int, nature="serious", evs=(85,) * 6):
        self.name = normalize_name(name)
        self.nickname = None
        self.base_name = self.name
        self.level = level
        self.nature = nature
        self.evs = evs
        self.speed_range = StatRange(min=0, max=float("inf"))
        self.hidden_power_possibilities = set(POKEMON_TYPE_INDICES.keys())

        try:
            self.base_stats = pokedex[self.name][constants.BASESTATS]
        except KeyError:
            logger.info("Could not find pokedex entry for {}".format(self.name))
            self.name = [k for k in pokedex if self.name.startswith(k)][0]
            logger.info("Using {} instead".format(self.name))
            self.base_stats = pokedex[self.name][constants.BASESTATS]

        self.stats = calculate_stats(
            self.base_stats, self.level, nature=nature, evs=evs
        )

        self.max_hp = self.stats.pop(constants.HITPOINTS)
        self.hp = self.max_hp
        self.substitute_hit = False
        if self.name == "shedinja":
            self.max_hp = 1
            self.hp = 1

        self.ability = None
        self.index = None
        self.types = pokedex[self.name][constants.TYPES]
        self.item = constants.UNKNOWN_ITEM
        self.removed_item = None
        self.unknown_forme = False

        self.moves_used_since_switch_in = set()
        self.zoroark_disguised_as = None
        self.hp_at_switch_in = self.max_hp
        self.status_at_switch_in = None
        self.terastallized = False
        self.tera_type = None
        self.original_ability = None
        self.fainted = False
        self.reviving = False
        self.moves = []
        self.status = None
        self.volatile_statuses = []
        self.volatile_status_durations = defaultdict(lambda: 0)
        self.boosts = defaultdict(lambda: 0)
        self.rest_turns = 0
        self.sleep_turns = 0
        self.knocked_off = False
        self.can_mega_evo = False
        self.can_ultra_burst = False
        self.can_dynamax = False
        self.can_terastallize = False
        self.is_mega = False
        self.mega_name = None
        self.can_have_choice_item = True
        self.item_inferred = False
        self.gen_3_consecutive_sleep_talks = 0
        self.impossible_items = set()
        self.impossible_abilities = set()

    def get_mega_pkmn_info(self) -> list[tuple[str, str]]:
        """Get possible mega evolution forms and required items"""
        mega_names = []
        if self.name == "rayquaza":
            return [("rayquazamega", "none")]
        if f"{self.name}mega" in pokedex:
            mega_names.append(
                (
                    f"{self.name}mega",
                    normalize_name(pokedex[f"{self.name}mega"]["requiredItem"]),
                )
            )
        if f"{self.name}megax" in pokedex:
            mega_names.append(
                (
                    f"{self.name}megax",
                    normalize_name(pokedex[f"{self.name}megax"]["requiredItem"]),
                )
            )
        if f"{self.name}megay" in pokedex:
            mega_names.append(
                (
                    f"{self.name}megay",
                    normalize_name(pokedex[f"{self.name}megay"]["requiredItem"]),
                )
            )
        return mega_names

    def has_type(self, pkmn_type: str):
        """Check if Pokemon has a type (considers Terastallization)"""
        if self.terastallized:
            return pkmn_type == self.tera_type
        else:
            return pkmn_type in self.types

    def forme_change(self, new_forme_switch_string):
        """Change Pokemon's forme (e.g., Rotom form change)"""
        current_hp_percentage = self.hp / self.max_hp if self.max_hp > 0 else 0

        new_pokemon = Pokemon.from_switch_string(new_forme_switch_string)
        self.name = new_pokemon.name
        self.base_stats = new_pokemon.base_stats
        self.stats = calculate_stats(self.base_stats, self.level, self.nature, self.evs)
        self.max_hp = self.stats.pop(constants.HITPOINTS)
        self.hp = int(current_hp_percentage * self.max_hp)
        self.ability = new_pokemon.ability
        self.types = new_pokemon.types

    def is_alive(self):
        """Check if Pokemon is alive (HP > 0)"""
        return self.hp > 0

    def calculate_boosted_stats(self):
        """Calculate stats including boosts"""
        return {
            constants.ATTACK: boost_multiplier_lookup[self.boosts[constants.ATTACK]]
            * self.stats[constants.ATTACK],
            constants.DEFENSE: boost_multiplier_lookup[self.boosts[constants.DEFENSE]]
            * self.stats[constants.DEFENSE],
            constants.SPECIAL_ATTACK: boost_multiplier_lookup[
                self.boosts[constants.SPECIAL_ATTACK]
            ]
            * self.stats[constants.SPECIAL_ATTACK],
            constants.SPECIAL_DEFENSE: boost_multiplier_lookup[
                self.boosts[constants.SPECIAL_DEFENSE]
            ]
            * self.stats[constants.SPECIAL_DEFENSE],
            constants.SPEED: boost_multiplier_lookup[self.boosts[constants.SPEED]]
            * self.stats[constants.SPEED],
        }

    @classmethod
    def from_switch_string(cls, switch_string, nickname=None):
        """
        Create a Pokemon from a switch string like "Pikachu, L50, M"
        """
        details = switch_string.split(",")
        pkmn = Pokemon(details[0].strip(), 100)

        if len(details) > 1:
            for d in details[1:]:
                d = d.strip()
                if d.startswith("L"):
                    pkmn.level = int(d[1:])
                    pkmn.stats = calculate_stats(pkmn.base_stats, pkmn.level)
                    pkmn.max_hp = pkmn.stats.pop(constants.HITPOINTS)
                    pkmn.hp = pkmn.max_hp
                    if pkmn.name == "shedinja":
                        pkmn.max_hp = 1
                        pkmn.hp = 1

        if nickname:
            pkmn.nickname = pkmn.extract_nickname_from_pokemonshowdown_string(nickname)

        return pkmn

    @staticmethod
    def extract_nickname_from_pokemonshowdown_string(name_string):
        """
        Extract nickname from Pokemon Showdown identifier
        e.g., "p1a: Pikachu" -> "Pikachu"
        """
        return name_string.split(":")[1].strip()

    @staticmethod
    def get_dummy():
        """Get a dummy Pokemon for testing/initialization"""
        return Pokemon("pikachu", 1)

    def add_move(self, move_name):
        """Add a move to this Pokemon"""
        normalized_move = normalize_name(move_name)
        self.moves.append(Move(normalized_move))

    def get_move(self, move_name):
        """Get a move by name"""
        normalized_move = normalize_name(move_name)
        for m in self.moves:
            if m.name == normalized_move:
                return m
        return None

    def __repr__(self):
        return f"Pokemon({self.name}, L{self.level}, HP:{self.hp}/{self.max_hp})"

    def __eq__(self, other):
        if not isinstance(other, Pokemon):
            return False
        return (
            self.name == other.name
            and self.level == other.level
            and self.hp == other.hp
            and self.max_hp == other.max_hp
        )


class Move:
    def __init__(self, name):
        self.name = normalize_name(name)
        self.disabled = False
        self.current_pp = 1
        self.can_z = False

    def __repr__(self):
        return f"Move({self.name}, PP:{self.current_pp}, disabled:{self.disabled})"

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return self.name == other.name

