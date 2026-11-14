"""
Play the new VGC doubles player on a LOCAL Showdown server.

    python -m fp.doubles_v2.run --team teams/my_vgc_team.txt --challenge YourName
    python -m fp.doubles_v2.run --team teams/my_vgc_team.txt --accept 3
    python -m fp.doubles_v2.run --team teams/my_vgc_team.txt --self-play 10

This only connects to ws://localhost:8000. Playing on the public
Showdown server requires registering the bot with Showdown's staff
first, so there is deliberately no option for it here yet.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from poke_env import AccountConfiguration, LocalhostServerConfiguration

from fp.battle_db import BattlePriors, BattleStore

from .player import VGCHeuristicPlayer


def build_player(name: str, team: str, fmt: str, priors) -> VGCHeuristicPlayer:
    return VGCHeuristicPlayer(
        account_configuration=AccountConfiguration(name, None),
        server_configuration=LocalhostServerConfiguration,
        battle_format=fmt,
        team=team,
        priors=priors,
        max_concurrent_battles=1,
    )


async def _main(args) -> None:
    team = Path(args.team).read_text(encoding="utf-8")
    priors = None
    if not args.no_priors:
        priors = BattlePriors(
            BattleStore(args.db), format_id=args.format, min_rating=args.min_rating
        )
    bot = build_player(args.name, team, args.format, priors)

    if args.challenge:
        await bot.send_challenges(args.challenge, n_challenges=args.games)
    elif args.accept:
        await bot.accept_challenges(None, args.accept)
    elif args.self_play:
        baseline = build_player(args.name + "Base", team, args.format, None)
        await bot.battle_against(baseline, n_battles=args.self_play)
        print(f"With priors: won {bot.n_won_battles} of {bot.n_finished_battles}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--team", required=True, help="Team in Showdown export format")
    ap.add_argument("--format", default="gen9vgc2026regi")
    ap.add_argument("--name", default="BattleBuddyLocal")
    ap.add_argument("--db", default=None)
    ap.add_argument("--min-rating", type=int, default=1300)
    ap.add_argument("--no-priors", action="store_true")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--challenge", help="Local username to challenge")
    mode.add_argument("--accept", type=int, help="Accept this many challenges")
    mode.add_argument(
        "--self-play", type=int, help="Play N games vs the same bot without priors"
    )
    ap.add_argument("--games", type=int, default=1)
    asyncio.run(_main(ap.parse_args(argv)))


if __name__ == "__main__":
    main()
