"""
Turn-by-turn battle database.

Lives in the same SQLite file as the existing PerformanceDatabase
(fp/data/battles.db by default) so the bot has one local database.
All new tables are prefixed ``replay_`` and never touch the existing
``battles`` / ``team_performance`` tables.
"""

from __future__ import annotations

import os
import sqlite3
import zlib
from datetime import datetime, timezone
from typing import Iterable, Optional

from .parser import PARSER_VERSION, ParsedBattle, parse_log

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "battles.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS replay_battles (
    replay_id      TEXT PRIMARY KEY,
    source         TEXT NOT NULL,            -- showdown_replay | local_log
    format         TEXT,
    uploadtime     INTEGER,
    rating         INTEGER,
    p1             TEXT,
    p2             TEXT,
    p1_rating      INTEGER,
    p2_rating      INTEGER,
    winner_side    TEXT,                     -- p1 | p2 | NULL for tie/unfinished
    tie            INTEGER DEFAULT 0,
    turns          INTEGER,
    parser_version INTEGER,
    imported_at    TEXT
);

CREATE TABLE IF NOT EXISTS replay_logs (
    replay_id TEXT PRIMARY KEY REFERENCES replay_battles(replay_id) ON DELETE CASCADE,
    log_zlib  BLOB NOT NULL                 -- raw protocol, kept so we can re-parse later
);

CREATE TABLE IF NOT EXISTS replay_team (
    replay_id TEXT NOT NULL REFERENCES replay_battles(replay_id) ON DELETE CASCADE,
    side      TEXT NOT NULL,
    species   TEXT NOT NULL,
    brought   INTEGER DEFAULT 0,
    lead      INTEGER DEFAULT 0,
    tera_type TEXT,
    fainted   INTEGER DEFAULT 0,
    PRIMARY KEY (replay_id, side, species)
);

CREATE TABLE IF NOT EXISTS replay_actions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    replay_id      TEXT NOT NULL REFERENCES replay_battles(replay_id) ON DELETE CASCADE,
    seq            INTEGER NOT NULL,
    turn           INTEGER NOT NULL,
    side           TEXT NOT NULL,
    slot           TEXT,
    actor          TEXT NOT NULL,
    kind           TEXT NOT NULL,            -- move | switch | replacement | lead | dragged | tera | cant
    name           TEXT NOT NULL,
    target_side    TEXT,
    target_slot    TEXT,
    target_species TEXT,
    spread         INTEGER DEFAULT 0,
    forced         INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_replay_actions_actor ON replay_actions(actor, kind);
CREATE INDEX IF NOT EXISTS idx_replay_actions_replay ON replay_actions(replay_id, turn);
CREATE INDEX IF NOT EXISTS idx_replay_team_species ON replay_team(species);
CREATE INDEX IF NOT EXISTS idx_replay_battles_format ON replay_battles(format, uploadtime);

CREATE TABLE IF NOT EXISTS replay_import_state (
    format          TEXT PRIMARY KEY,
    oldest_seen     INTEGER,                 -- uploadtime of the oldest replay listed so far
    newest_seen     INTEGER,                 -- uploadtime of the newest replay listed so far
    updated_at      TEXT
);

-- Did the side that brought this species win?
CREATE VIEW IF NOT EXISTS replay_species_results AS
SELECT t.species, t.side, t.lead, t.tera_type, b.format, b.rating,
       CASE WHEN b.winner_side = t.side THEN 1 ELSE 0 END AS won
FROM replay_team t JOIN replay_battles b USING (replay_id)
WHERE t.brought = 1 AND (b.winner_side IS NOT NULL);

-- Voluntary move choices (no forced/locked moves).
CREATE VIEW IF NOT EXISTS replay_move_choices AS
SELECT a.actor AS species, a.name AS move, a.spread, a.target_side, a.side,
       b.format, b.rating,
       CASE WHEN b.winner_side = a.side THEN 1 ELSE 0 END AS won
FROM replay_actions a JOIN replay_battles b USING (replay_id)
WHERE a.kind = 'move' AND a.forced = 0;

-- The pair each side opened with.
CREATE VIEW IF NOT EXISTS replay_lead_pairs AS
SELECT t.replay_id, t.side, b.format, b.rating,
       MIN(t.species) AS lead_a, MAX(t.species) AS lead_b,
       CASE WHEN b.winner_side = t.side THEN 1 ELSE 0 END AS won
FROM replay_team t JOIN replay_battles b USING (replay_id)
WHERE t.lead = 1 AND b.winner_side IS NOT NULL
GROUP BY t.replay_id, t.side
HAVING COUNT(*) = 2;
"""


class BattleStore:
    """Read/write access to the turn-by-turn battle tables."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------ writes

    def has_battle(self, replay_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM replay_battles WHERE replay_id = ?", (replay_id,)
        ).fetchone()
        return row is not None

    def add_battle(
        self,
        replay_id: str,
        log_text: str,
        source: str = "showdown_replay",
        format_id: Optional[str] = None,
        uploadtime: Optional[int] = None,
        rating: Optional[int] = None,
        replace: bool = False,
    ) -> Optional[ParsedBattle]:
        """Parse a log and store it. Returns None if it was already stored."""
        if self.has_battle(replay_id):
            if not replace:
                return None
            self.conn.execute(
                "DELETE FROM replay_battles WHERE replay_id = ?", (replay_id,)
            )

        parsed = parse_log(log_text)
        fmt = format_id or parsed.format_id
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO replay_battles
               (replay_id, source, format, uploadtime, rating, p1, p2, p1_rating, p2_rating,
                winner_side, tie, turns, parser_version, imported_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                replay_id,
                source,
                fmt,
                uploadtime,
                rating,
                parsed.players.get("p1"),
                parsed.players.get("p2"),
                parsed.ratings.get("p1"),
                parsed.ratings.get("p2"),
                parsed.winner_side,
                int(parsed.tie),
                parsed.turns,
                PARSER_VERSION,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        cur.execute(
            "INSERT INTO replay_logs (replay_id, log_zlib) VALUES (?, ?)",
            (replay_id, zlib.compress(log_text.encode("utf-8"))),
        )
        cur.executemany(
            """INSERT OR REPLACE INTO replay_team
               (replay_id, side, species, brought, lead, tera_type, fainted)
               VALUES (?,?,?,?,?,?,?)""",
            [
                (
                    replay_id,
                    side,
                    m.species,
                    int(m.brought),
                    int(m.lead),
                    m.tera_type,
                    int(m.fainted),
                )
                for side, members in parsed.teams.items()
                for m in members.values()
            ],
        )
        cur.executemany(
            """INSERT INTO replay_actions
               (replay_id, seq, turn, side, slot, actor, kind, name,
                target_side, target_slot, target_species, spread, forced)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    replay_id,
                    a.seq,
                    a.turn,
                    a.side,
                    a.slot,
                    a.actor,
                    a.kind,
                    a.name,
                    a.target_side,
                    a.target_slot,
                    a.target_species,
                    int(a.spread),
                    int(a.forced),
                )
                for a in parsed.actions
            ],
        )
        self.conn.commit()
        return parsed

    def reparse_all(self) -> int:
        """Re-run the parser over every stored raw log (after a parser upgrade)."""
        rows = self.conn.execute(
            """SELECT b.replay_id, b.source, b.format, b.uploadtime, b.rating, l.log_zlib
               FROM replay_battles b JOIN replay_logs l USING (replay_id)"""
        ).fetchall()
        for r in rows:
            log_text = zlib.decompress(r["log_zlib"]).decode("utf-8")
            self.add_battle(
                r["replay_id"],
                log_text,
                r["source"],
                r["format"],
                r["uploadtime"],
                r["rating"],
                replace=True,
            )
        return len(rows)

    # ------------------------------------------------------------ import state

    def get_import_state(self, format_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM replay_import_state WHERE format = ?", (format_id,)
        ).fetchone()

    def update_import_state(self, format_id: str, uploadtimes: Iterable[int]) -> None:
        times = [t for t in uploadtimes if t]
        if not times:
            return
        oldest, newest = min(times), max(times)
        prev = self.get_import_state(format_id)
        if prev:
            oldest = min(oldest, prev["oldest_seen"] or oldest)
            newest = max(newest, prev["newest_seen"] or newest)
        self.conn.execute(
            """INSERT INTO replay_import_state (format, oldest_seen, newest_seen, updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(format) DO UPDATE SET
                 oldest_seen = excluded.oldest_seen,
                 newest_seen = excluded.newest_seen,
                 updated_at = excluded.updated_at""",
            (
                format_id,
                oldest,
                newest,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()

    # ----------------------------------------------------------------- summary

    def summary(self, format_id: Optional[str] = None) -> dict:
        where, args = ("WHERE format = ?", (format_id,)) if format_id else ("", ())
        row = self.conn.execute(
            f"""SELECT COUNT(*) AS battles,
                       SUM(CASE WHEN winner_side IS NOT NULL THEN 1 ELSE 0 END) AS decided,
                       AVG(turns) AS avg_turns, AVG(rating) AS avg_rating,
                       MIN(uploadtime) AS oldest, MAX(uploadtime) AS newest
                FROM replay_battles {where}""",
            args,
        ).fetchone()
        actions = self.conn.execute(
            f"""SELECT COUNT(*) FROM replay_actions a JOIN replay_battles b USING (replay_id)
                {where.replace('format', 'b.format')}""",
            args,
        ).fetchone()[0]
        out = dict(row)
        out["actions"] = actions
        return out
