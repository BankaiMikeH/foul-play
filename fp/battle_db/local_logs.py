"""
Load the bot's own battles into the battle database.

The bot's BattleTurnLogger writes every raw server message to
``battle_logs/<bot>_<battle>_<timestamp>_client_messages.log``. Those
lines are ordinary Showdown protocol with a timestamp in front, so the
same parser used for public replays reads them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .store import BattleStore

_NAME_RE = re.compile(r"^(?P<bot>.+?)_(?P<battle>[a-z0-9]+-\d+)_(?P<ts>\d{8}_\d{6})_client_messages\.log$")


def import_local_logs(store: BattleStore, log_dir: str, replace: bool = False) -> dict:
    stats = {"files": 0, "imported": 0, "skipped_existing": 0, "unfinished": 0}
    for path in sorted(Path(log_dir).glob("*_client_messages.log")):
        stats["files"] += 1
        m = _NAME_RE.match(path.name)
        battle_id = m.group("battle") if m else path.stem
        # One battle can have a log per bot (bot vs bot); keep the first.
        replay_id = f"local-{battle_id}"
        if store.has_battle(replay_id) and not replace:
            stats["skipped_existing"] += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = store.add_battle(replay_id, text, source="local_log",
                                  format_id=_format_from_id(battle_id), replace=replace)
        if parsed is None:
            continue
        stats["imported"] += 1
        if not parsed.is_complete:
            stats["unfinished"] += 1
    return stats


def _format_from_id(battle_id: str) -> Optional[str]:
    return battle_id.rsplit("-", 1)[0] if "-" in battle_id else None
