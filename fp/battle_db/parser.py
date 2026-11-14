"""
Showdown protocol log parser for doubles (VGC) battles.

Turns a raw Showdown battle log (the same text found in a replay's
``log`` field, or the raw lines the bot receives over its websocket)
into a structured record: who played, what each side brought and led
with, what each Pokemon did every turn, and who won.

The parser only reads the protocol; it never talks to a server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PARSER_VERSION = 1

# "p1a: Nickname" -> ("p1", "a", "Nickname"); "p2: Name" -> ("p2", None, "Name")
_POS_RE = re.compile(r"^(p[1-4])([a-d])?:\s*(.*)$")
# Lines from the bot's client-message log look like "[ts] (+1.234s) |move|..."
_CLIENT_LOG_PREFIX_RE = re.compile(r"^\[[^\]]*\]\s*\(\+[0-9.]+s\)\s*")


@dataclass
class Action:
    """One thing a Pokemon did (or was told to do) on a turn."""

    turn: int
    side: str
    slot: Optional[str]
    actor: str
    kind: str  # move | switch | replacement | lead | tera | cant
    name: str
    target_side: Optional[str] = None
    target_slot: Optional[str] = None
    target_species: Optional[str] = None
    spread: bool = False
    forced: bool = False
    seq: int = 0


@dataclass
class TeamMember:
    species: str
    brought: bool = False
    lead: bool = False
    tera_type: Optional[str] = None
    fainted: bool = False


@dataclass
class ParsedBattle:
    format_id: Optional[str] = None
    players: Dict[str, str] = field(default_factory=dict)  # side -> name
    ratings: Dict[str, int] = field(default_factory=dict)  # side -> rating (if shown)
    teams: Dict[str, Dict[str, TeamMember]] = field(default_factory=dict)
    actions: List[Action] = field(default_factory=list)
    winner_name: Optional[str] = None
    winner_side: Optional[str] = None
    tie: bool = False
    turns: int = 0

    def team(self, side: str) -> Dict[str, TeamMember]:
        return self.teams.setdefault(side, {})

    @property
    def is_complete(self) -> bool:
        return self.winner_side is not None or self.tie


def base_species(details: str) -> str:
    """'Calyrex-Ice, L50, M' -> 'Calyrex-Ice'. Strips '-*' wildcard forms too."""
    species = details.split(",")[0].strip()
    if species.endswith("-*"):
        species = species[:-2]
    return species


def parse_position(token: str) -> Tuple[Optional[str], Optional[str], str]:
    m = _POS_RE.match(token.strip())
    if not m:
        return None, None, token.strip()
    return m.group(1), m.group(2), m.group(3)


def clean_line(line: str) -> str:
    line = line.rstrip("\r\n")
    line = _CLIENT_LOG_PREFIX_RE.sub("", line)
    return line.strip()


class _State:
    """Tracks which species sits in each position while parsing."""

    def __init__(self, battle: ParsedBattle):
        self.battle = battle
        self.active: Dict[Tuple[str, str], str] = {}  # (side, slot) -> species
        self.nick: Dict[Tuple[str, str], str] = {}  # (side, nickname) -> species
        self.fainted_slots: set = set()
        self.turn = 0
        self.seq = 0
        self.seen_actions: set = set()

    def species_at(self, side: Optional[str], slot: Optional[str], nickname: str) -> Optional[str]:
        if side is None:
            return None
        if slot and (side, slot) in self.active:
            return self.active[(side, slot)]
        return self.nick.get((side, nickname))

    def add(self, action: Action):
        # Two bots logging the same battle can send each line twice; keep one.
        key = (
            action.turn, action.side, action.slot, action.kind, action.name,
            action.target_side, action.target_slot, action.actor,
        )
        if action.kind != "move" and key in self.seen_actions:
            return
        self.seen_actions.add(key)
        self.seq += 1
        action.seq = self.seq
        self.battle.actions.append(action)


def parse_log(log_text: str) -> ParsedBattle:
    """Parse a whole Showdown battle log."""
    battle = ParsedBattle()
    state = _State(battle)

    for raw in log_text.splitlines():
        line = clean_line(raw)
        if not line.startswith("|"):
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        cmd = parts[1]
        try:
            _handle(cmd, parts, state)
        except (IndexError, ValueError):
            # One malformed line should never sink a whole replay.
            continue

    battle.turns = state.turn
    if battle.winner_name and not battle.winner_side:
        for side, name in battle.players.items():
            if _norm(name) == _norm(battle.winner_name):
                battle.winner_side = side
    return battle


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _handle(cmd: str, parts: List[str], st: _State) -> None:
    b = st.battle

    if cmd == "player" and len(parts) >= 4 and parts[3]:
        side = parts[2]
        b.players[side] = parts[3]
        if len(parts) >= 6 and parts[5].strip().isdigit():
            b.ratings[side] = int(parts[5].strip())

    elif cmd == "tier" and len(parts) >= 3:
        b.format_id = b.format_id or parts[2]

    elif cmd == "poke" and len(parts) >= 4:
        side = parts[2]
        species = base_species(parts[3])
        b.team(side).setdefault(species, TeamMember(species=species))

    elif cmd in ("switch", "drag", "replace") and len(parts) >= 4:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        species = base_species(parts[3])
        team = b.team(side)
        if species not in team:
            # Team preview hides some formes ("Urshifu-*"); swap in the real one.
            for k in list(team):
                if species.startswith(k + "-") and not team[k].brought:
                    team.pop(k)
                    break
        member = team.setdefault(species, TeamMember(species=species))
        member.brought = True
        if cmd == "replace":
            # Illusion broke: fix the species for this nickname/slot, not a new action.
            st.active[(side, slot)] = species
            st.nick[(side, nickname)] = species
            return
        st.nick[(side, nickname)] = species
        st.active[(side, slot)] = species
        if st.turn == 0:
            member.lead = True
            kind = "lead"
        elif (side, slot) in st.fainted_slots:
            kind = "replacement"
        elif cmd == "drag":
            kind = "dragged"
        else:
            kind = "switch"
        st.fainted_slots.discard((side, slot))
        st.add(Action(turn=st.turn, side=side, slot=slot, actor=species, kind=kind, name=species))

    elif cmd == "detailschange" and len(parts) >= 4:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        species = base_species(parts[3])
        b.team(side).setdefault(species, TeamMember(species=species, brought=True))
        st.active[(side, slot)] = species
        st.nick[(side, nickname)] = species

    elif cmd == "move" and len(parts) >= 4:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        actor = st.species_at(side, slot, nickname) or nickname
        move = parts[3]
        tags = parts[4:]
        t_side = t_slot = t_species = None
        if tags and _POS_RE.match(tags[0].strip()):
            t_side, t_slot, t_nick = parse_position(tags[0])
            t_species = st.species_at(t_side, t_slot, t_nick) or t_nick
            tags = tags[1:]
        spread = any(t.startswith("[spread]") for t in tags)
        forced = any(t.startswith("[from]") for t in tags)
        st.add(Action(
            turn=st.turn, side=side, slot=slot, actor=actor, kind="move", name=move,
            target_side=t_side, target_slot=t_slot, target_species=t_species,
            spread=spread, forced=forced,
        ))

    elif cmd == "-terastallize" and len(parts) >= 4:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        actor = st.species_at(side, slot, nickname) or nickname
        tera = parts[3].strip()
        member = b.team(side).setdefault(actor, TeamMember(species=actor, brought=True))
        member.tera_type = tera
        st.add(Action(turn=st.turn, side=side, slot=slot, actor=actor, kind="tera", name=tera))

    elif cmd == "cant" and len(parts) >= 4:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        actor = st.species_at(side, slot, nickname) or nickname
        st.add(Action(turn=st.turn, side=side, slot=slot, actor=actor, kind="cant", name=parts[3]))

    elif cmd == "faint" and len(parts) >= 3:
        side, slot, nickname = parse_position(parts[2])
        if side is None:
            return
        species = st.species_at(side, slot, nickname)
        if species and species in b.team(side):
            b.team(side)[species].fainted = True
        if slot:
            st.fainted_slots.add((side, slot))

    elif cmd == "turn" and len(parts) >= 3:
        st.turn = int(parts[2].strip())

    elif cmd == "win" and len(parts) >= 3:
        b.winner_name = parts[2].strip()

    elif cmd == "tie":
        b.tie = True
