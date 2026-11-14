"""
What the battle database knows, in a form the bot can use while playing.

Everything here is a plain SQL read over the replay tables, so it works
offline once replays are imported.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .store import BattleStore


class BattlePriors:
    """Usage and win-rate priors learned from stored battles.

    ``min_rating`` filters to games at or above a ladder rating, so the
    bot can learn from stronger players only.
    """

    def __init__(self, store: Optional[BattleStore] = None, db_path: Optional[str] = None,
                 format_id: Optional[str] = None, min_rating: int = 0):
        self.store = store or BattleStore(db_path)
        self.format_id = format_id
        self.min_rating = min_rating

    def _filter(self, alias: str = "") -> Tuple[str, list]:
        p = f"{alias}." if alias else ""
        clauses, args = [f"COALESCE({p}rating, 0) >= ?"], [self.min_rating]
        if self.format_id:
            clauses.append(f"{p}format = ?")
            args.append(self.format_id)
        return " AND ".join(clauses), args

    # ------------------------------------------------------------- per species

    def move_frequencies(self, species: str, top: int = 10) -> Dict[str, float]:
        """Share of a species' chosen moves that went to each move."""
        where, args = self._filter()
        rows = self.store.conn.execute(
            f"""SELECT move, COUNT(*) AS n FROM replay_move_choices
                WHERE species = ? AND {where}
                GROUP BY move ORDER BY n DESC""",
            [species, *args],
        ).fetchall()
        total = sum(r["n"] for r in rows) or 1
        return {r["move"]: r["n"] / total for r in rows[:top]}

    def move_win_rates(self, species: str, min_uses: int = 5) -> Dict[str, Tuple[float, int]]:
        """move -> (win rate of the side that chose it, uses)."""
        where, args = self._filter()
        rows = self.store.conn.execute(
            f"""SELECT move, AVG(won) AS wr, COUNT(*) AS n FROM replay_move_choices
                WHERE species = ? AND {where}
                GROUP BY move HAVING n >= ? ORDER BY n DESC""",
            [species, *args, min_uses],
        ).fetchall()
        return {r["move"]: (r["wr"], r["n"]) for r in rows}

    def tera_types(self, species: str) -> Dict[str, float]:
        where, args = self._filter("b")
        rows = self.store.conn.execute(
            f"""SELECT t.tera_type, COUNT(*) AS n
                FROM replay_team t JOIN replay_battles b USING (replay_id)
                WHERE t.species = ? AND t.tera_type IS NOT NULL AND {where}
                GROUP BY t.tera_type ORDER BY n DESC""",
            [species, *args],
        ).fetchall()
        total = sum(r["n"] for r in rows) or 1
        return {r["tera_type"]: r["n"] / total for r in rows}

    def species_win_rate(self, species: str) -> Tuple[Optional[float], int]:
        where, args = self._filter()
        r = self.store.conn.execute(
            f"""SELECT AVG(won) AS wr, COUNT(*) AS n FROM replay_species_results
                WHERE species = ? AND {where}""",
            [species, *args],
        ).fetchone()
        return (r["wr"], r["n"])

    def protect_rate(self, species: str) -> float:
        """How often this species clicks a protecting move when it acts."""
        freqs = self.move_frequencies(species, top=100)
        return sum(v for k, v in freqs.items() if k in PROTECT_MOVES)

    # -------------------------------------------------------- team preview

    def best_leads(self, team: Sequence[str], min_games: int = 3, top: int = 5
                   ) -> List[Tuple[Tuple[str, str], float, int]]:
        """Rank lead pairs from ``team`` by how often that lead won."""
        team_set = set(team)
        where, args = self._filter()
        rows = self.store.conn.execute(
            f"""SELECT lead_a, lead_b, AVG(won) AS wr, COUNT(*) AS n
                FROM replay_lead_pairs WHERE {where}
                GROUP BY lead_a, lead_b HAVING n >= ?""",
            [*args, min_games],
        ).fetchall()
        ranked = [
            ((r["lead_a"], r["lead_b"]), r["wr"], r["n"])
            for r in rows
            if r["lead_a"] in team_set and r["lead_b"] in team_set
        ]
        # Smooth toward 50% so a 2-0 lead doesn't beat a 60-40 one.
        ranked.sort(key=lambda x: (x[1] * x[2] + 0.5 * 10) / (x[2] + 10), reverse=True)
        return ranked[:top]

    def common_partners(self, species: str, top: int = 6) -> List[Tuple[str, int]]:
        where, args = self._filter("b")
        rows = self.store.conn.execute(
            f"""SELECT o.species AS partner, COUNT(*) AS n
                FROM replay_team t
                JOIN replay_team o ON o.replay_id = t.replay_id AND o.side = t.side
                                   AND o.species != t.species AND o.brought = 1
                JOIN replay_battles b ON b.replay_id = t.replay_id
                WHERE t.species = ? AND t.brought = 1 AND {where}
                GROUP BY o.species ORDER BY n DESC LIMIT ?""",
            [species, *args, top],
        ).fetchall()
        return [(r["partner"], r["n"]) for r in rows]

    def top_species(self, top: int = 20) -> List[Tuple[str, int, float]]:
        where, args = self._filter()
        rows = self.store.conn.execute(
            f"""SELECT species, COUNT(*) AS n, AVG(won) AS wr FROM replay_species_results
                WHERE {where} GROUP BY species ORDER BY n DESC LIMIT ?""",
            [*args, top],
        ).fetchall()
        return [(r["species"], r["n"], r["wr"]) for r in rows]


PROTECT_MOVES = frozenset({
    "Protect", "Detect", "Spiky Shield", "King's Shield", "Baneful Bunker",
    "Silk Trap", "Burning Bulwark", "Obstruct", "Max Guard",
})
