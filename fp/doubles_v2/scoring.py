"""
Heuristic scoring for VGC doubles decisions.

Pure functions over plain numbers, so they can be tested without a
battle in progress. The poke-env player in ``player.py`` turns a live
DoubleBattle into these inputs.

The idea is the simplest thing a decent VGC player does every turn:
  * hit the target you damage most, weighted by accuracy and STAB
  * spread moves lose 25% per target but hit both foes
  * don't hit your partner, and don't use a move that also hurts them
  * Protect when you're threatened, never twice in a row
  * lean toward what strong players actually click (priors from the DB)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SPREAD_MULTIPLIER = 0.75
KO_BONUS = 60.0
PRIOR_WEIGHT = 40.0
# Rough "damage points" a full-HP target can take: a 120 BP STAB super
# effective hit (~360) usually KOs, a neutral 90 BP STAB hit (~135) doesn't.
FULL_HP_POINTS = 250.0


@dataclass
class AttackInput:
    base_power: float
    accuracy: float = 1.0  # 0..1
    stab: float = 1.0  # 1.0, 1.5 or 2.0 (tera STAB)
    effectiveness: float = 1.0  # vs the chosen target
    spread: bool = False  # hits both foes
    hits_ally: bool = False  # e.g. Earthquake
    ally_effectiveness: float = 0.0
    target_hp: float = 1.0  # 0..1 of the target's HP
    second_target_effectiveness: float = 0.0  # spread: the other foe
    second_target_hp: float = 1.0
    target_protect_rate: float = 0.0  # how often this species Protects (DB prior)
    priority: int = 0
    user_hp: float = 1.0
    prior: float = 0.0  # share of DB choices that were this move


def expected_damage(
    power: float, accuracy: float, stab: float, eff: float, spread: bool
) -> float:
    if power <= 0 or eff <= 0:
        return 0.0
    dmg = power * accuracy * stab * eff
    return dmg * (SPREAD_MULTIPLIER if spread else 1.0)


def _ko_bonus(dmg: float, hp: float) -> float:
    # Keeps KO chasing without a full damage calc.
    return KO_BONUS if likely_ko(dmg, hp) else 0.0


def likely_ko(dmg: float, hp: float) -> bool:
    return hp > 0 and dmg >= FULL_HP_POINTS * hp


def score_attack(a: AttackInput) -> float:
    main = expected_damage(a.base_power, a.accuracy, a.stab, a.effectiveness, a.spread)
    score = main + _ko_bonus(main, a.target_hp)
    if a.spread:
        second = expected_damage(
            a.base_power, a.accuracy, a.stab, a.second_target_effectiveness, True
        )
        score += second + _ko_bonus(second, a.second_target_hp)
    # A target that Protects a lot wastes single-target hits more than spread.
    protect_tax = a.target_protect_rate * (0.25 if a.spread else 0.5)
    score *= 1.0 - protect_tax
    if a.hits_ally and a.ally_effectiveness > 0:
        ally_dmg = expected_damage(
            a.base_power, a.accuracy, a.stab, a.ally_effectiveness, True
        )
        score -= 1.5 * ally_dmg
    # Priority matters most when the user is low and might not move otherwise.
    if a.priority > 0 and a.user_hp < 0.4:
        score *= 1.25
    return score + PRIOR_WEIGHT * a.prior


def score_ally_hit(base_power: float, effectiveness: float) -> float:
    """Attacking your own partner: only fine if it does nothing (e.g. an absorb ability)."""
    if base_power > 0 and effectiveness > 0:
        return -1000.0
    return -5.0


def score_protect(
    user_hp: float, threat: float, protected_last_turn: bool, prior: float = 0.0
) -> float:
    """``threat`` is the best expected damage a foe can do to this Pokemon (0..~300)."""
    if protected_last_turn:
        return -200.0  # consecutive Protect usually fails
    base = 15.0 + 0.35 * threat
    if user_hp < 0.5:
        base *= 1.3
    return base + PRIOR_WEIGHT * prior


def score_status(prior: float, base: float = 20.0) -> float:
    """Status moves (Tailwind, Fake Out without power data, redirection...)."""
    return base + PRIOR_WEIGHT * 1.5 * prior


def score_switch(incoming_defense: float, outgoing_threat_taken: float) -> float:
    """
    ``incoming_defense``: average effectiveness of the foes' STAB types on the
    switch-in (lower is better). ``outgoing_threat_taken``: same for the
    Pokemon leaving the field.
    """
    gain = outgoing_threat_taken - incoming_defense
    return 25.0 * gain - 10.0  # switching costs tempo


def joint_adjustment(
    first_target: Optional[int],
    second_target: Optional[int],
    first_is_protect: bool,
    second_is_protect: bool,
    first_ko_target: bool,
    second_ko_target: bool,
) -> float:
    """Penalties/bonuses for how the two slots' choices combine."""
    adj = 0.0
    if first_is_protect and second_is_protect:
        adj -= 40.0  # passing the whole turn
    if (
        first_target is not None
        and first_target == second_target
        and first_ko_target
        and second_ko_target
    ):
        adj -= 50.0  # both going for a KO only one needs
    if (
        first_target is not None
        and first_target == second_target
        and not (first_ko_target or second_ko_target)
    ):
        adj += 10.0  # focus fire on something that needs two hits
    return adj
