"""
VGC doubles player built on poke-env's DoubleBattle.

Replaces the old path that pushed doubles through the singles-only Rust
engine. Every turn it scores each legal action for both Pokemon with
``scoring.py``, combines the two, and sends the best pair. When a battle
database is available it also uses what strong players chose in the
same spot (move priors, Protect habits, best leads).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Tuple

from poke_env.battle import DoubleBattle, Move, MoveCategory, Pokemon, Target
from poke_env.player import Player
from poke_env.player.battle_order import (
    DoubleBattleOrder,
    SingleBattleOrder,
)

from . import scoring

logger = logging.getLogger(__name__)

SPREAD_TARGETS = {Target.ALL_ADJACENT_FOES, Target.ALL_ADJACENT}
TOP_PER_SLOT = 6


def _species_name(mon: Optional[Pokemon]) -> str:
    """poke-env lowercases species ids; the DB stores Showdown display names."""
    if mon is None:
        return ""
    try:
        from poke_env.data import GenData
        entry = GenData.from_gen(9).pokedex.get(mon.species)
        if entry and entry.get("name"):
            return entry["name"]
    except Exception:
        pass
    return mon.species


class VGCHeuristicPlayer(Player):
    """Greedy two-slot heuristic player with optional database priors."""

    def __init__(self, *args, priors=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.priors = priors
        self._protected_last_turn: dict = {}

    # ----------------------------------------------------------- priors

    def _move_prior(self, mon: Pokemon, move: Move) -> float:
        if not self.priors:
            return 0.0
        try:
            return self.priors.move_frequencies(_species_name(mon), top=50).get(move.entry.get("name", move.id), 0.0)
        except Exception:
            return 0.0

    def _protect_rate(self, mon: Optional[Pokemon]) -> float:
        if not self.priors or mon is None:
            return 0.0
        try:
            return self.priors.protect_rate(_species_name(mon))
        except Exception:
            return 0.0

    # ------------------------------------------------------ team preview

    def teampreview(self, battle: DoubleBattle) -> str:
        team = list(battle.team.values())
        names = [_species_name(m) for m in team]
        order: List[int] = []
        if self.priors:
            try:
                leads = self.priors.best_leads(names, min_games=3, top=1)
                if leads:
                    (a, b), _, _ = leads[0]
                    order = [names.index(a), names.index(b)]
            except Exception as e:
                logger.debug("lead prior failed: %s", e)
        if not order:
            order = [0, 1]
        rest = [i for i in range(len(team)) if i not in order]
        if self.priors:
            rest.sort(key=lambda i: -(self.priors.species_win_rate(names[i])[0] or 0.5))
        picks = (order + rest)[: max(4, len(order))]
        return "/team " + "".join(str(i + 1) for i in picks)

    # ------------------------------------------------------------ turns

    def choose_move(self, battle: DoubleBattle):
        if any(battle.force_switch):
            return self._forced_switches(battle)

        per_slot: List[List[Tuple[float, SingleBattleOrder, dict]]] = []
        for slot, mon in enumerate(battle.active_pokemon):
            if mon is None or not (battle.available_moves[slot] or battle.available_switches[slot]):
                per_slot.append([])
                continue
            options = self._slot_options(battle, slot, mon)
            options.sort(key=lambda x: x[0], reverse=True)
            per_slot.append(options[:TOP_PER_SLOT])

        best = self._best_joint(per_slot)
        for slot, mon in enumerate(battle.active_pokemon):
            if mon is not None:
                chosen = best.first_order if slot == 0 else best.second_order
                self._protected_last_turn[(battle.battle_tag, mon.species)] = bool(
                    chosen and isinstance(chosen.order, Move) and chosen.order.is_protect_move
                )
        return best

    def _best_joint(self, per_slot) -> DoubleBattleOrder:
        first = per_slot[0] if per_slot else []
        second = per_slot[1] if len(per_slot) > 1 else []
        if not first and not second:
            return DoubleBattleOrder(None, None)
        if not first or not second:
            only = first or second
            score, order, _ = max(only, key=lambda x: x[0])
            return DoubleBattleOrder(order, None) if first else DoubleBattleOrder(None, order)

        best, best_score = None, float("-inf")
        for s1, o1, m1 in first:
            for s2, o2, m2 in second:
                if not DoubleBattleOrder.join_orders([o1], [o2]):
                    continue  # e.g. both terastallizing, or same switch-in
                total = s1 + s2 + scoring.joint_adjustment(
                    m1.get("target"), m2.get("target"), m1.get("protect", False),
                    m2.get("protect", False), m1.get("ko", False), m2.get("ko", False),
                )
                if total > best_score:
                    best, best_score = DoubleBattleOrder(o1, o2), total
        return best or DoubleBattleOrder(first[0][1], None)

    def _slot_options(self, battle: DoubleBattle, slot: int, mon: Pokemon):
        options = []
        foes = [f for f in battle.opponent_active_pokemon]
        ally = battle.active_pokemon[1 - slot]
        threat = self._threat_to(mon, foes)

        for move in battle.available_moves[slot]:
            prior = self._move_prior(mon, move)
            if move.is_protect_move:
                key = (battle.battle_tag, mon.species)
                s = scoring.score_protect(mon.current_hp_fraction, threat,
                                          self._protected_last_turn.get(key, False), prior)
                options.append((s, SingleBattleOrder(move), {"protect": True}))
                continue
            if move.category == MoveCategory.STATUS or move.base_power == 0:
                for tgt in battle.get_possible_showdown_targets(move, mon):
                    options.append((scoring.score_status(prior), SingleBattleOrder(move, move_target=tgt), {}))
                continue

            for tera in self._tera_choices(battle, slot, mon, move):
                for tgt in battle.get_possible_showdown_targets(move, mon):
                    s, meta = self._score_attack(battle, mon, ally, foes, move, tgt, tera, prior)
                    options.append((s, SingleBattleOrder(move, move_target=tgt, terastallize=tera), meta))

        for sw in battle.available_switches[slot]:
            s = scoring.score_switch(self._defense_vs(sw, foes), self._defense_vs(mon, foes))
            options.append((s, SingleBattleOrder(sw), {}))
        return options

    def _tera_choices(self, battle, slot, mon, move) -> Sequence[bool]:
        can = battle.can_tera[slot] if isinstance(battle.can_tera, (list, tuple)) else battle.can_tera
        if can and mon.tera_type is not None and mon.tera_type == move.type:
            return (False, True)
        return (False,)

    def _score_attack(self, battle, mon, ally, foes, move, tgt, tera, prior):
        spread = move.target in SPREAD_TARGETS or move.deduced_target in SPREAD_TARGETS
        stab = 1.5 if move.type in mon.types else 1.0
        if tera:
            stab = 2.0 if move.type in mon.types else 1.5
        acc = move.accuracy if isinstance(move.accuracy, (int, float)) else 1.0

        if tgt in (battle.POKEMON_1_POSITION, battle.POKEMON_2_POSITION):
            return scoring.score_ally_hit(move.base_power, ally.damage_multiplier(move) if ally else 0), {}

        target = None
        if tgt == battle.OPPONENT_1_POSITION:
            target = foes[0]
        elif tgt == battle.OPPONENT_2_POSITION:
            target = foes[1] if len(foes) > 1 else None
        if target is None:
            target = next((f for f in foes if f is not None), None)
        other = next((f for f in foes if f is not None and f is not target), None)

        a = scoring.AttackInput(
            base_power=move.base_power, accuracy=acc, stab=stab,
            effectiveness=target.damage_multiplier(move) if target else 1.0,
            spread=spread,
            hits_ally=move.target == Target.ALL_ADJACENT and ally is not None,
            ally_effectiveness=ally.damage_multiplier(move) if ally else 0.0,
            target_hp=target.current_hp_fraction if target else 1.0,
            second_target_effectiveness=other.damage_multiplier(move) if other else 0.0,
            second_target_hp=other.current_hp_fraction if other else 1.0,
            target_protect_rate=self._protect_rate(target),
            priority=move.priority, user_hp=mon.current_hp_fraction, prior=prior,
        )
        dmg = scoring.expected_damage(a.base_power, a.accuracy, a.stab, a.effectiveness, a.spread)
        return scoring.score_attack(a), {
            "target": None if spread else tgt,
            "ko": target is not None and scoring.likely_ko(dmg, target.current_hp_fraction),
        }

    # ---------------------------------------------------------- helpers

    @staticmethod
    def _defense_vs(mon: Pokemon, foes) -> float:
        """Average of the foes' best STAB effectiveness against ``mon`` (lower = safer)."""
        vals = []
        for foe in foes:
            if foe is None:
                continue
            vals.append(max((mon.damage_multiplier(t) for t in foe.types if t is not None), default=1.0))
        return sum(vals) / len(vals) if vals else 1.0

    def _threat_to(self, mon: Pokemon, foes) -> float:
        best = 0.0
        for foe in foes:
            if foe is None:
                continue
            for t in foe.types:
                if t is None:
                    continue
                best = max(best, 90.0 * 1.5 * mon.damage_multiplier(t))
        return best

    def _forced_switches(self, battle: DoubleBattle) -> DoubleBattleOrder:
        foes = battle.opponent_active_pokemon
        chosen: List[Optional[SingleBattleOrder]] = [None, None]
        used = set()
        for slot in (0, 1):
            if not battle.force_switch[slot]:
                continue
            options = [s for s in battle.available_switches[slot] if s.species not in used]
            if not options:
                continue
            pick = min(options, key=lambda s: (self._defense_vs(s, foes), -s.current_hp_fraction))
            used.add(pick.species)
            chosen[slot] = SingleBattleOrder(pick)
        return DoubleBattleOrder(chosen[0], chosen[1])
