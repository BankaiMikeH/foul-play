"""
Base Battle class containing all battle logic common to singles and doubles.
This file contains ONLY the Battle class - Battler classes are in separate files.
"""
import constants
import logging

from fp.pokemon import Pokemon, LastUsedMove

logger = logging.getLogger(__name__)


# Based on the format, this dict controls which pokemon will be replaced during team preview
# Some pokemon's forms are not revealed in team preview
smart_team_preview = {
    "gen8ou": {
        "urshifu": "urshifurapidstrike"  # urshifu banned in gen8ou
    },
    "gen9ou": {
        "urshifu": "urshifurapidstrike"  # urshifu banned in gen9ou
    },
    "gen9nationaldex": {
        "urshifu": "urshifurapidstrike"  # urshifu banned in gen9nationaldex
    },
    "gen9battlefactory": {
        "zacian": "zaciancrowned"  # only zaciancrowned is used in gen9battlefactory
    },
}


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


class Battle:
    """
    Base Battle class - DO NOT INSTANTIATE DIRECTLY.
    Use SinglesBattle or DoublesBattle instead.
    
    This class contains all the battle logic that is common between
    singles and doubles battles.
    """
    
    # Note: __init__ is defined in subclasses (SinglesBattle/DoublesBattle)
    # to create the correct type of Battler (SinglesBattler/DoublesBattler)
    
    @property
    def is_doubles(self):
        """
        Returns True if this is a doubles battle.
        This property should be overridden in subclasses.
        """
        raise NotImplementedError("Subclass must define is_doubles property")
    
    def initialize_team_preview(self, opponent_pokemon, battle_type):
        """Initialize team preview phase"""
        # Move active Pokemon to reserve
        for pkmn in self.user.get_all_active_pokemon():
            self.user.reserve.insert(0, pkmn)
        
        # Clear active slots
        if self.is_doubles:
            self.user.active = [None, None]
        else:
            self.user.active = None

        for pkmn_string in opponent_pokemon:
            pokemon = Pokemon.from_switch_string(pkmn_string)

            if pokemon.name in smart_team_preview.get(battle_type, {}):
                new_pokemon_name = smart_team_preview[battle_type][pokemon.name]
                logger.info(
                    "Smart team preview: Replaced {} with {}".format(
                        pokemon.name, new_pokemon_name
                    )
                )
                pokemon = Pokemon(new_pokemon_name, pokemon.level)

            elif pkmn_string.endswith("-*"):
                pokemon.unknown_forme = True

            self.opponent.reserve.append(pokemon)

        self.started = True

    def during_team_preview(self):
        """Check if currently in team preview"""
        return self.team_preview

    def start_non_team_preview_battle(self, user_json, opponent_switch_string):
        """Start a battle without team preview"""
        self.user.initialize_first_turn_user_from_json(user_json)

        pkmn_information = opponent_switch_string.split("|")[3]
        pkmn = Pokemon.from_switch_string(pkmn_information)
        
        self.opponent.set_active_pokemon(pkmn, position=0)
        self.started = True
        self.rqid = user_json[constants.RQID]

    def mega_evolve_possible(self):
        """Check if mega evolution is possible in this battle"""
        return (
            any(g in self.generation for g in constants.MEGA_EVOLVE_GENERATIONS)
            or "nationaldex" in self.pokemon_format
        )

    def get_effective_speed(self, battler, position=0):
        """
        Get effective speed for a battler's active Pokemon.
        
        Args:
            battler: The Battler object
            position: Which active Pokemon (0 for singles/left, 1 for right in doubles)
        """
        active_pokemon = battler.get_active_pokemon(position)
        if active_pokemon is None:
            return 0
            
        boosted_speed = active_pokemon.calculate_boosted_stats()[constants.SPEED]

        if self.weather == constants.SUN and active_pokemon.ability == "chlorophyll":
            boosted_speed *= 2
        elif self.weather == constants.RAIN and active_pokemon.ability == "swiftswim":
            boosted_speed *= 2
        elif self.weather == constants.SAND and active_pokemon.ability == "sandrush":
            boosted_speed *= 2
        elif (
            self.weather in constants.HAIL_OR_SNOW
            and active_pokemon.ability == "slushrush"
        ):
            boosted_speed *= 2

        if (
            self.field == constants.ELECTRIC_TERRAIN
            and active_pokemon.ability == "surgesurfer"
        ):
            boosted_speed *= 2

        if active_pokemon.ability == "unburden" and not active_pokemon.item:
            boosted_speed *= 2
        elif (
            active_pokemon.ability == "quickfeet" and active_pokemon.status is not None
        ):
            boosted_speed *= 1.5

        if battler.side_conditions[constants.TAILWIND]:
            boosted_speed *= 2

        if "choicescarf" == active_pokemon.item:
            boosted_speed *= 1.5

        if (
            constants.PARALYZED == active_pokemon.status
            and active_pokemon.ability != "quickfeet"
        ):
            boosted_speed *= 0.5

        if any(
            vs in active_pokemon.volatile_statuses
            for vs in ["quarkdrivespe", "protosynthesisspe"]
        ):
            boosted_speed *= 1.5

        return int(boosted_speed)

    def __repr__(self):
        return f"Battle({self.battle_tag}, format={self.pokemon_format}, doubles={self.is_doubles})"

